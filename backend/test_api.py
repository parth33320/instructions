import requests
import json
import os
from main import parse_alcohol_content

def test_abv_parsing():
    """
    Unit test for the alcohol content parsing logic.
    Ensures both numeric value and full phrase are correctly captured.
    """
    test_cases = [
        # (input_text, expected_numeric, expected_phrase)
        ("CRISP LAGER ALC. 4.2% BY VOL.", 4.2, "ALC. 4.2% BY VOL."),
        ("VODKA 80 PROOF 750ML", 80.0, "80 PROOF"),
        ("ALC 13.5% BY VOLUME WINE", 13.5, "ALC 13.5% BY VOLUME"),
        ("RESERVE SHIRAZ 14.5% ALC/VOL", 14.5, "14.5% ALC/VOL"),
        ("ALC 13.5% BY VOL", 13.5, "ALC 13.5% BY VOL"),
        ("40% ALC./VOL.", 40.0, "40% ALC./VOL."),
        ("90 PROOF", 90.0, "90 PROOF")
    ]

    print("\nRunning ABV Parsing Unit Tests...")
    all_passed = True
    for text, exp_val, exp_phrase in test_cases:
        matches = parse_alcohol_content(text)

        # Check if expected value and phrase are matched
        match_found = False
        for m in matches:
            val = float(m["value"])
            phrase = m["phrase"]
            if abs(val - exp_val) < 0.01 and phrase.upper() == exp_phrase.upper():
                match_found = True
                break

        if match_found:
            print(f"✅ PASS: '{text}' -> Found {exp_val} in '{exp_phrase}'")
        else:
            found_desc = ", ".join([f"{m['value']} in '{m['phrase']}'" for m in matches])
            print(f"❌ FAIL: '{text}' -> Expected {exp_val} in '{exp_phrase}', but found {found_desc}")
            all_passed = False

    return all_passed

def test_analyze_endpoint():
    url = "http://127.0.0.1:8000/analyze"
    image_path = "sample_label.png"

    if not os.path.exists(image_path):
        print(f"Error: {image_path} not found")
        return

    data = {
        "brand_name": "OLD TOM DISTILLERY",
        "abv": "45%",
        "government_warning": "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems."
    }

    with open(image_path, "rb") as f:
        files = {"file": f}
        try:
            response = requests.post(url, data=data, files=files)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Response Body:")
                print(json.dumps(response.json(), indent=2))
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Failed to connect to backend: {e}")

if __name__ == "__main__":
    # Run unit tests first
    abv_passed = test_abv_parsing()

    if abv_passed:
        print("\nAll ABV parsing unit tests passed! Proceeding to endpoint test...")
        test_analyze_endpoint()
    else:
        print("\nABV parsing unit tests failed. Skipping endpoint test.")
