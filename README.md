# AI-Powered Alcohol Label Verification App

This prototype assists TTB Compliance Agents by automatically verifying alcohol beverage labels against application data using AI-powered OCR and fuzzy matching logic.

## Features

- **Automated Verification**: Checks Brand Name, Alcohol Content (ABV/Proof), and the Government Health Warning Statement.
- **High Performance**: End-to-end analysis typically completes in under 5 seconds.
- **Offline OCR**: Uses `EasyOCR` locally to ensure functionality even behind restrictive government firewalls (no cloud ML dependencies).
- **Nuanced Matching**: Uses fuzzy logic for brand names and strict pattern matching for legal requirements like the Government Warning.
- **Batch Processing**: Support for uploading multiple labels simultaneously for rapid review.
- **"Mother-Proof" UI**: Simple, clean interface designed for varying levels of technical expertise.

## Project Structure

- `backend/`: FastAPI Python application handling OCR and verification logic.
- `frontend/`: Next.js App Router application with Tailwind CSS.
- `sample_label.png`: A synthetically generated label for testing.

## Setup & Installation

### Backend

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:8000`.

### Frontend

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   The application will be available at `http://localhost:3000`.

## Technical Approach

### 1. OCR Extraction
We use **EasyOCR**, an open-source OCR library that runs locally. This choice was specifically made based on stakeholder feedback regarding network restrictions and speed requirements. EasyOCR provides a good balance between accuracy and performance.

### 2. Verification Logic
- **Brand Name**: Uses `fuzzywuzzy` (Levenshtein distance) to allow for minor variations in capitalization or punctuation (e.g., "STONE'S THROW" vs "Stone's Throw") while still flagging significant mismatches.
- **Alcohol Content**: Uses regex patterns to identify various formats of ABV and Proof. It extracts numerical values and compares them against the expected values.
- **Government Warning**: Implements strict normalization and searching. It checks for the exact phrase "GOVERNMENT WARNING:" in all caps and ensures the subsequent required text is present with high accuracy.

### 3. Frontend Design
Built with **Next.js** and **Tailwind CSS**, the UI focuses on clarity:
- Clear **PASS/FAIL** status indicators.
- Side-by-side comparison of "Expected" vs "Actual" data.
- Batch upload capability to handle peak season volume.

## Assumptions & Trade-offs

- **Batch Logic**: In this prototype, batching sends multiple individual requests to the `/analyze` endpoint. In a production system, this could be optimized into a single bulk endpoint or background task queue.
- **Font Availability**: The synthetic label generator assumes common system fonts; if unavailable, it falls back to defaults.
- **Image Quality**: While AI improves robustness, extremely low-resolution or blurry images may still fail OCR extraction.

## Testing

An end-to-end test script is provided in the root directory:
```bash
python e2e_test.py
```
This script verifies the API's correctness and ensures it meets the <5s speed requirement.
