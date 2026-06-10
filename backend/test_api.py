import requests
import json
import os

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
    test_analyze_endpoint()
