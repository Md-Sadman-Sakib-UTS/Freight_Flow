import json
from pathlib import Path
from typing import List, Tuple
from polyline import decode as poly_decode
from geopy.distance import geodesic

MAJOR_TYPES = {"Crash", "Flood"}
DIST_THRESHOLD_KM = 1.0

def _polyline_to_coords(polyline: str) -> List[Tuple[float, float]]:
    """Decode an encoded polyline to a list of (lat, lon) tuples."""
    return [(lat, lon) for lat, lon in poly_decode(polyline)]

def _closest_distance_km(waypoints, hazard_coords) -> float:
    """Return min-distance (km) from any waypoint to any hazard point."""
    return min(
        geodesic(wp, hz).km for wp in waypoints for hz in hazard_coords
    )

def classify_delay_prob(polyline: str, hazards: dict) -> dict:
    waypoints = _polyline_to_coords(polyline)
    avoid = []

    for feat in hazards.get("features", []):
        if feat["properties"].get("type") not in MAJOR_TYPES:
            continue
        hz_coords = [(feat["geometry"]["coordinates"][1],
                      feat["geometry"]["coordinates"][0])]
        if _closest_distance_km(waypoints, hz_coords) <= DIST_THRESHOLD_KM:
            avoid.extend(hz_coords)

    delay_prob = 0.8 if avoid else 0.2
    explain = (
        f"{len(avoid)} major hazard(s) within {DIST_THRESHOLD_KM} km of route"
        if avoid else "No major hazards near route"
    )
    return {
        "delay_prob": delay_prob,
        "avoid_coords": avoid,
        "explain": explain,
    }


if __name__ == "__main__":
    import argparse, pprint
    p = argparse.ArgumentParser()
    p.add_argument("polyline_file")
    p.add_argument("hazards_geojson")
    args = p.parse_args()

    poly = Path(args.polyline_file).read_text().strip()
    hazards = json.loads(Path(args.hazards_geojson).read_text())
    pprint.pp(classify_delay_prob(poly, hazards))
