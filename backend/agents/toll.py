import httpx
import os
from dotenv import load_dotenv
load_dotenv()

TOLL_API_URL = "https://api.transport.nsw.gov.au/v1/toll-calculator/price"
TOLL_API_KEY = os.getenv("TFNSW_API_KEY")

def get_toll_price(origin: tuple, destination: tuple, vehicle_type: str = "car", waypoints=None) -> float:
    if not TOLL_API_KEY:
        raise RuntimeError("TFNSW_API_KEY not set")
    headers = {
        "Authorization": f"apikey {TOLL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "start": {"lat": origin[1], "lon": origin[0]},
        "end": {"lat": destination[1], "lon": destination[0]},
        "vehicleType": vehicle_type
    }
    if waypoints:  
        payload["waypoints"] = waypoints
    print("Toll payload:", payload)
    try:
        resp = httpx.post(TOLL_API_URL, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("totalToll", 0.0)
    except httpx.HTTPStatusError as exc:
        print(f"Toll API error {exc.response.status_code}: {exc.response.text}")
        return 0.0
    except Exception as exc:
        print(f"Toll API general error: {exc}")
        return 0.0

if __name__ == "__main__":
    origin = (150.9083, -33.7667) 
    destination = (151.1799, -33.9399)  
    toll_value = get_toll_price(origin, destination, vehicle_type="car")
    print("Toll price (AUD):", toll_value)