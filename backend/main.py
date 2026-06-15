from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import pytesseract
import time
from PIL import Image
import io
import re
import math
from fuzzywuzzy import fuzz

# Global constants and pre-compiled regex patterns for performance
TESSERACT_CONFIG = '--psm 6'
WHITESPACE_PATTERN = re.compile(r'\s+')
GW_HEADER_PATTERN = re.compile(r'GOVERNMENT\s+WARNING', re.IGNORECASE)
GW_STRICT_HEADER_PATTERN = re.compile(r'GOVERNMENT\s+WARNING\s*:')
ABV_NUM_PATTERN = re.compile(r'(\d+(?:\.\d+)?)')

# Alcohol content regex components
_ALC_SUFFIX = r'(?:\s*(?:ALC\.?\/VOL\.?\.?|%\s*ALC\.?\/VOL\.?\.?|%\s*BY\s*VOLUME|%\s*BY\s*VOL\.?|%\s*VOLUME|%\s*VOL\.?|BY\s*VOLUME|BY\s*VOL\.?|VOLUME|VOL\.?|PROOF|%))'
_ALC_PREFIX = r'(?:(?:ALCOHOL|ALC\.?)\s*)'
ALCOHOL_PATTERN = re.compile(
    r'(?:' + _ALC_PREFIX + r'(\d+(?:\.\d+)?)(?:' + _ALC_SUFFIX + r')?)|(?:(\d+(?:\.\d+)?)' + _ALC_SUFFIX + r')',
    re.IGNORECASE
)

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

def verify_government_warning(full_text: str, expected_warning: str):
    """
    Verifies the Government Warning section based on strict TTB rules.
    1. Header must be "GOVERNMENT WARNING:" (all caps, trailing colon).
    2. Body wording is checked via fuzzy matching.
    3. Adds a manual verification note for font-weight.
    """
    def normalize(t):
        return WHITESPACE_PATTERN.sub(' ', t).strip().upper()

    expected_warning_norm = normalize(expected_warning)
    full_text_norm = normalize(full_text)

    warning_status = "FAIL"
    warning_message = ""
    confidence = 0.5
    manual_note = " (Note: Manually verify visual font-weight on physical label)"

    # Sequential checks for Jenny Park's compliance rules
    if not GW_HEADER_PATTERN.search(full_text):
        warning_status = "FAIL"
        warning_message = "'GOVERNMENT WARNING:' header not found."
        confidence = 0.0
    elif not GW_STRICT_HEADER_PATTERN.search(full_text):
        warning_status = "FAIL"
        warning_message = "Missing colon or not in all caps."
        confidence = 0.5
    else:
        # Strict header check passed, now check body wording
        warning_score = fuzz.token_set_ratio(expected_warning_norm, full_text_norm)

        if warning_score >= 95:
            warning_status = "PASS"
            warning_message = "Found with high accuracy." + manual_note
            confidence = 1.0
        elif warning_score >= 85:
            warning_status = "WARNING"
            warning_message = "Wording might have minor discrepancies." + manual_note
            confidence = 0.8
        else:
            warning_status = "FAIL"
            warning_message = f"Wording mismatch. Match score: {warning_score}%"
            confidence = 0.5

    return warning_status, warning_message, confidence

def parse_alcohol_content(text: str):
    """
    Robustly extract alcohol content values and their surrounding phrases.
    Keywords: alc, alc., alcohol, vol, vol., volume, alc/vol, alc./vol., %, proof
    """
    matches = []
    for match in ALCOHOL_PATTERN.finditer(text):
        full_phrase = match.group(0).strip()
        # The numeric value could be in group 1 or group 2
        value = match.group(1) if match.group(1) else match.group(2)
        if value:
            matches.append({
                "value": value,
                "phrase": full_phrase
            })
    return matches

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_label(
    file: UploadFile = File(...),
    brand_name: str = Form(...),
    abv: str = Form(...),
    government_warning: str = Form(...)
):
    start_load = time.time()
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert('RGB')

    # Resize image if width > 800
    if image.width > 800:
        aspect_ratio = image.height / image.width
        new_height = int(800 * aspect_ratio)
        image = image.resize((800, new_height), Image.Resampling.LANCZOS)

    load_time = time.time() - start_load
    print(f"Image loading time: {load_time:.4f} seconds")

    # Perform OCR
    # pytesseract.image_to_string returns a string
    start_ocr = time.time()
    full_text = pytesseract.image_to_string(image, config=TESSERACT_CONFIG)
    ocr_time = time.time() - start_ocr
    print(f"OCR processing time: {ocr_time:.4f} seconds")

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
    # Use robust parser for alcohol content
    abv_matches_info = parse_alcohol_content(full_text)

    # Also search in individual lines for better precision
    for line in extracted_text_list:
        line_matches = parse_alcohol_content(line)
        existing_phrases = [m["phrase"] for m in abv_matches_info]
        for lm in line_matches:
            if lm["phrase"] not in existing_phrases:
                abv_matches_info.append(lm)

    # Normalize expected ABV to just numbers for comparison
    expected_abv_nums = ABV_NUM_PATTERN.findall(abv)

    abv_status = "FAIL"
    abv_actual = "None found"
    abv_confidence = 0.0

    if abv_matches_info:
        # Collect unique numeric values for comparison and phrases for display
        abv_values = []
        abv_phrases = []
        for m in abv_matches_info:
            if m["value"] not in abv_values:
                abv_values.append(m["value"])
            if m["phrase"] not in abv_phrases:
                abv_phrases.append(m["phrase"])

        abv_actual = ", ".join(abv_phrases)

        # Check if any extracted number matches any expected number with tolerance
        match_found = False
        for exp in expected_abv_nums:
            for act in abv_values:
                try:
                    if math.isclose(float(exp), float(act), abs_tol=0.1):
                        match_found = True
                        break
                except (ValueError, TypeError):
                    continue
            if match_found:
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
    warning_status, warning_message, confidence = verify_government_warning(full_text, government_warning)

    results.append(VerificationResult(
        field="Government Warning",
        expected=government_warning[:50] + "...",
        actual="Extracted text contains warning" if warning_status != "FAIL" else "Not found/Incorrect",
        status=warning_status,
        confidence=confidence,
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
