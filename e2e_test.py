import requests
import os
import json
import time

def run_e2e_test():
    base_url = "http://127.0.0.1:8000"
    image_path = "sample_label.png"

    print("--- Starting End-to-End Test ---")

    # 1. Test Root
    try:
        resp = requests.get(f"{base_url}/")
        print(f"Root endpoint: {resp.status_code}")
    except Exception as e:
        print(f"Error connecting to backend: {e}")
        return

    # 2. Test Single Analysis
    print("\nTesting /analyze (Single)...")
    data = {
        "brand_name": "OLD TOM DISTILLERY",
        "abv": "45%",
        "government_warning": "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems."
    }

    start_time = time.time()
    with open(image_path, "rb") as f:
        files = {"file": f}
        resp = requests.post(f"{base_url}/analyze", data=data, files=files)
    end_time = time.time()

    duration = end_time - start_time
    print(f"Duration: {duration:.2f}s")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"Overall Status: {result['overall_status']}")
        for res in result['results']:
            print(f"  - {res['field']}: {res['status']} ({res['message']})")

    if duration < 5.0:
        print("✅ SPEED REQUIREMENT MET (< 5s)")
    else:
        print("❌ SPEED REQUIREMENT FAILED (> 5s)")

    # 3. Test Discrepancy Detection
    print("\nTesting /analyze (Single with mismatching Brand Name)...")
    data["brand_name"] = "WRONG BRAND"
    with open(image_path, "rb") as f:
        files = {"file": f}
        resp = requests.post(f"{base_url}/analyze", data=data, files=files)

    if resp.status_code == 200:
        result = resp.json()
        print(f"Overall Status: {result['overall_status']}")
        brand_res = next(r for r in result['results'] if r['field'] == 'Brand Name')
        print(f"  - Brand Name: {brand_res['status']} (Expected: WRONG BRAND, Found: {brand_res['actual']})")
        if brand_res['status'] == "FAIL":
            print("✅ DISCREPANCY DETECTED CORRECTLY")

    print("\n--- End-to-End Test Complete ---")

if __name__ == "__main__":
    run_e2e_test()
