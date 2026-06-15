from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import pytesseract
import numpy as np
from PIL import Image
import io
import re
from fuzzywuzzy import fuzz, process

app = FastAPI(title="TTB Label Verification API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class VerificationResult(BaseModel):
    field: str
    expected: str
    actual: Optional[str]
    status: str  # PASS, FAIL, WARNING
    confidence: float
    message: Optional[str]

class AnalysisResponse(BaseModel):
    filename: str
    overall_status: str
    results: List[VerificationResult]
    extracted_text: str

@app.get("/")
async def root():
    return {"message": "TTB Label Verification API is running"}

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_label(
    file: UploadFile = File(...),
    brand_name: str = Form(...),
    abv: str = Form(...),
    government_warning: str = Form(...)
):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert('RGB')

    # Perform OCR
    # pytesseract.image_to_string returns a string
    full_text = pytesseract.image_to_string(image)

    # Split into lines for the brand name check logic that follows
    extracted_text_list = [line.strip() for line in full_text.split('\n') if line.strip()]

    results = []

    # 1. Brand Name Verification (Fuzzy)
    # Check each extracted line or the whole text
    brand_match_score = 0
    best_match_text = ""
    for line in extracted_text_list:
        score = fuzz.token_set_ratio(brand_name.upper(), line.upper())
        if score > brand_match_score:
            brand_match_score = score
            best_match_text = line

    # Also check full text in case it's split
    full_text_score = fuzz.token_set_ratio(brand_name.upper(), full_text.upper())
    if full_text_score > brand_match_score:
        brand_match_score = full_text_score
        best_match_text = "See extracted text"

    status = "PASS" if brand_match_score >= 90 else "FAIL"
    if 80 <= brand_match_score < 90:
        status = "WARNING"

    results.append(VerificationResult(
        field="Brand Name",
        expected=brand_name,
        actual=best_match_text if status != "FAIL" else "Not clearly found",
        status=status,
        confidence=brand_match_score / 100.0,
        message=f"Match score: {brand_match_score}%"
    ))

    # 2. ABV/Proof Verification (Regex)
    # Common formats: "45% ALC/VOL", "90 PROOF", "45% ALC. BY VOL."
    # Extract numbers associated with % or PROOF
    abv_pattern = r'(\d+(?:\.\d+)?)\s*(?:%|ALC|PROOF)'
    abv_matches = re.findall(abv_pattern, full_text, re.IGNORECASE)

    # Also search in individual lines for better precision
    for line in extracted_text_list:
        line_matches = re.findall(abv_pattern, line, re.IGNORECASE)
        abv_matches.extend(line_matches)

    abv_matches = list(set(abv_matches)) # unique matches

    # Normalize expected ABV to just numbers for comparison
    expected_abv_nums = re.findall(r'(\d+(?:\.\d+)?)', abv)

    abv_status = "FAIL"
    abv_actual = "None found"
    abv_confidence = 0.0

    if abv_matches:
        abv_actual = ", ".join(abv_matches)
        # Check if any extracted number matches any expected number
        match_found = False
        for exp in expected_abv_nums:
            for act in abv_matches:
                if float(exp) == float(act):
                    match_found = True
                    break

        if match_found:
            abv_status = "PASS"
            abv_confidence = 1.0
        else:
            abv_status = "FAIL"
            abv_confidence = 0.5

    results.append(VerificationResult(
        field="Alcohol Content",
        expected=abv,
        actual=abv_actual,
        status=abv_status,
        confidence=abv_confidence,
        message=f"Found potential values: {abv_actual}"
    ))

    # 3. Government Warning Verification (Exact with normalization)
    # The requirement is very strict about "GOVERNMENT WARNING:" in caps and bold.
    # Since OCR might not give us bold info easily, we focus on exact wording and caps.

    # Normalize whitespace and case for the core text check, but check "GOVERNMENT WARNING:" separately
    def normalize(t):
        return re.sub(r'\s+', ' ', t).strip().upper()

    expected_warning_norm = normalize(government_warning)
    full_text_norm = normalize(full_text)

    warning_status = "FAIL"
    warning_message = ""

    if "GOVERNMENT WARNING:" in full_text:
        # Check for exact wording
        # We use fuzzy matching but with a very high threshold for the "exact" requirement
        warning_score = fuzz.token_set_ratio(expected_warning_norm, full_text_norm)

        if warning_score >= 95:
            warning_status = "PASS"
            warning_message = "Found with high accuracy."
        elif warning_score >= 85:
            warning_status = "WARNING"
            warning_message = "Wording might have minor discrepancies."
        else:
            warning_status = "FAIL"
            warning_message = f"Wording mismatch. Match score: {warning_score}%"
    else:
        if "GOVERNMENT WARNING" in full_text.upper():
            warning_status = "FAIL"
            warning_message = "Missing colon after 'GOVERNMENT WARNING' or not in all caps."
        else:
            warning_status = "FAIL"
            warning_message = "'GOVERNMENT WARNING:' header not found."

    results.append(VerificationResult(
        field="Government Warning",
        expected=government_warning[:50] + "...",
        actual="Extracted text contains warning" if warning_status != "FAIL" else "Not found/Incorrect",
        status=warning_status,
        confidence=1.0 if warning_status == "PASS" else 0.5,
        message=warning_message
    ))

    # Calculate overall status
    overall = "PASS"
    if any(r.status == "FAIL" for r in results):
        overall = "FAIL"
    elif any(r.status == "WARNING" for r in results):
        overall = "WARNING"

    return AnalysisResponse(
        filename=file.filename,
        overall_status=overall,
        results=results,
        extracted_text=full_text
    )

@app.post("/batch")
async def batch_analyze(
    files: List[UploadFile] = File(...),
    brand_name: str = Form(...),
    abv: str = Form(...),
    government_warning: str = Form(...)
):
    """
    Simplified batch endpoint that applies the same expected data to multiple files.
    In production, this would likely take a mapping of filename to expected values.
    """
    results = []
    for file in files:
        result = await analyze_label(file, brand_name, abv, government_warning)
        results.append(result)

    return {"batch_results": results}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
