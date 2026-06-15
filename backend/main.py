from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio
import uvicorn
import pytesseract
from PIL import Image, ImageEnhance
import io
import re
import math
from rapidfuzz import fuzz  # ← DROP-IN REPLACEMENT: rapidfuzz is 5-10x faster than fuzzywuzzy, same API

app = FastAPI(title="TTB Label Verification API")

# --- PERF FIX #1: Global thread pool for OCR ---
# pytesseract is synchronous/CPU-bound. Running it directly in an async
# FastAPI endpoint blocks the entire event loop. Offloading to a thread pool
# lets FastAPI handle other requests while OCR runs.
_executor = ThreadPoolExecutor(max_workers=2)

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


# --- PERF FIX #2: Pre-warm Tesseract on startup ---
# Tesseract loads its LSTM model the very first time it is called in a process.
# On Render this costs 2-4 seconds on the first real request. Running a dummy
# call at startup shifts that cost to container bring-up (which nobody is
# waiting on yet) and makes every subsequent request faster.
@app.on_event("startup")
async def warmup_tesseract():
    loop = asyncio.get_event_loop()
    dummy = Image.new("L", (100, 40), color=255)
    await loop.run_in_executor(
        _executor,
        lambda: pytesseract.image_to_string(dummy, config="--oem 1 --psm 11"),
    )


@app.get("/")
async def root():
    return {"message": "TTB Label Verification API is running"}


# --- PERF FIX #3: Image pre-processing pipeline ---
# Tesseract accuracy and speed both improve when fed a clean grayscale image
# at ~300 DPI. Large colour images (>1600px wide) force Tesseract to process
# unnecessary data; scaling them down and boosting contrast first is faster
# AND more accurate.
def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    # 1. Grayscale — Tesseract does not need colour; stripping it reduces data.
    image = image.convert("L")

    # 2. Resize — cap at 1600px wide. Labels are high-contrast text so
    #    downsampling loses nothing meaningful and halves OCR time on large scans.
    MAX_WIDTH = 1600
    if image.width > MAX_WIDTH:
        ratio = MAX_WIDTH / image.width
        image = image.resize(
            (MAX_WIDTH, int(image.height * ratio)), Image.LANCZOS
        )

    # 3. Contrast boost — makes text edges crisper, reduces Tesseract errors.
    image = ImageEnhance.Contrast(image).enhance(2.0)

    return image


# --- PERF FIX #4: Optimised Tesseract config ---
# --oem 1   → LSTM engine only (skip legacy engine, ~20% faster)
# --psm 11  → Sparse text mode: finds all text regardless of layout.
#             Perfect for labels where brand name / ABV / warning are in
#             completely different zones. Avoids slow page-segmentation passes.
_TESS_CONFIG = "--oem 1 --psm 11"


def _run_ocr(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, config=_TESS_CONFIG)


def verify_government_warning(full_text: str, expected_warning: str):
    def normalize(t):
        return re.sub(r"\s+", " ", t).strip().upper()

    expected_norm = normalize(expected_warning)
    full_norm = normalize(full_text)

    manual_note = " (Note: Manually verify visual font-weight on physical label)"

    if not re.search(r"GOVERNMENT\s+WARNING", full_text, re.IGNORECASE):
        return "FAIL", "'GOVERNMENT WARNING:' header not found.", 0.0
    if not re.search(r"GOVERNMENT\s+WARNING\s*:", full_text):
        return "FAIL", "Missing colon or not in all caps.", 0.5

    score = fuzz.token_set_ratio(expected_norm, full_norm)
    if score >= 95:
        return "PASS", "Found with high accuracy." + manual_note, 1.0
    if score >= 85:
        return "WARNING", "Wording might have minor discrepancies." + manual_note, 0.8
    return "FAIL", f"Wording mismatch. Match score: {score}%", 0.5


def parse_alcohol_content(text: str):
    suffix = r"(?:\s*(?:ALC\.?\/VOL\.?\.?|%\s*ALC\.?\/VOL\.?\.?|%\s*BY\s*VOLUME|%\s*BY\s*VOL\.?|%\s*VOLUME|%\s*VOL\.?|BY\s*VOLUME|BY\s*VOL\.?|VOLUME|VOL\.?|PROOF|%))"
    prefix = r"(?:(?:ALCOHOL|ALC\.?)\s*)"
    pattern = r"(?:" + prefix + r"(\d+(?:\.\d+)?)(?:" + suffix + r")?)|(?:(\d+(?:\.\d+)?)" + suffix + r")"
    matches = []
    for m in re.finditer(pattern, text, re.IGNORECASE):
        value = m.group(1) if m.group(1) else m.group(2)
        if value:
            matches.append({"value": value, "phrase": m.group(0).strip()})
    return matches


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_label(
    file: UploadFile = File(...),
    brand_name: str = Form(...),
    abv: str = Form(...),
    government_warning: str = Form(...),
):
    contents = await file.read()
    raw_image = Image.open(io.BytesIO(contents))

    # Pre-process then OCR — runs in thread pool, does not block event loop
    processed = preprocess_for_ocr(raw_image)
    loop = asyncio.get_event_loop()
    full_text = await loop.run_in_executor(_executor, _run_ocr, processed)

    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
    results = []

    # 1. Brand Name (fuzzy)
    best_score, best_match = 0, ""
    for line in lines:
        s = fuzz.token_set_ratio(brand_name.upper(), line.upper())
        if s > best_score:
            best_score, best_match = s, line
    # Also check full text in case brand is split across lines
    full_score = fuzz.token_set_ratio(brand_name.upper(), full_text.upper())
    if full_score > best_score:
        best_score, best_match = full_score, "See extracted text"

    brand_status = "PASS" if best_score >= 90 else ("WARNING" if best_score >= 80 else "FAIL")
    results.append(VerificationResult(
        field="Brand Name",
        expected=brand_name,
        actual=best_match if brand_status != "FAIL" else "Not clearly found",
        status=brand_status,
        confidence=best_score / 100.0,
        message=f"Match score: {best_score}%",
    ))

    # 2. Alcohol Content (regex) — single pass on full_text is sufficient;
    #    the per-line loop in the original was redundant since full_text
    #    contains every line already.
    abv_matches = parse_alcohol_content(full_text)
    expected_nums = re.findall(r"(\d+(?:\.\d+)?)", abv)

    abv_status, abv_actual, abv_conf = "FAIL", "None found", 0.0
    if abv_matches:
        phrases = list({m["phrase"] for m in abv_matches})
        values = [m["value"] for m in abv_matches]
        abv_actual = ", ".join(phrases)
        match_found = any(
            math.isclose(float(e), float(a), abs_tol=0.1)
            for e in expected_nums
            for a in values
            if _is_float(e) and _is_float(a)
        )
        abv_status = "PASS" if match_found else "FAIL"
        abv_conf = 1.0 if match_found else 0.5

    results.append(VerificationResult(
        field="Alcohol Content",
        expected=abv,
        actual=abv_actual,
        status=abv_status,
        confidence=abv_conf,
        message=f"Found potential values: {abv_actual}",
    ))

    # 3. Government Warning
    w_status, w_msg, w_conf = verify_government_warning(full_text, government_warning)
    results.append(VerificationResult(
        field="Government Warning",
        expected=government_warning[:50] + "...",
        actual="Extracted text contains warning" if w_status != "FAIL" else "Not found/Incorrect",
        status=w_status,
        confidence=w_conf,
        message=w_msg,
    ))

    overall = "PASS"
    if any(r.status == "FAIL" for r in results):
        overall = "FAIL"
    elif any(r.status == "WARNING" for r in results):
        overall = "WARNING"

    return AnalysisResponse(
        filename=file.filename,
        overall_status=overall,
        results=results,
        extracted_text=full_text,
    )


def _is_float(v):
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


@app.post("/batch")
async def batch_analyze(
    files: List[UploadFile] = File(...),
    brand_name: str = Form(...),
    abv: str = Form(...),
    government_warning: str = Form(...),
):
    tasks = [analyze_label(f, brand_name, abv, government_warning) for f in files]
    batch_results = await asyncio.gather(*tasks)
    return {"batch_results": batch_results}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
