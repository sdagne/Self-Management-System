import requests
import time

BASE_URL = "http://localhost:8001/api/counters"

SERVICE_TYPES = [
    "document_legalization",
    "land_registration",
    "passport_renewal",
    "business_license",
]

COUNTERS_TO_CREATE = 100

for number in range(1, COUNTERS_TO_CREATE + 1):
    payload = {
        "counter_number": number,
        "counter_name": f"Counter {number}",
        "service_types": SERVICE_TYPES,
        "staff_name": f"Staff {number}"
    }

    try:
        response = requests.post(BASE_URL, json=payload)
    except requests.RequestException as exc:
        print(f"[{number}] Failed to reach server: {exc}")
        continue

    if response.ok:
        print(f"[{number}] Created {payload['counter_name']}")
    elif response.status_code == 400 and response.json().get("detail") == "Counter number already exists":
        print(f"[{number}] Already exists")
    else:
        print(f"[{number}] Unexpected response {response.status_code}: {response.text}")

    time.sleep(0.05)

