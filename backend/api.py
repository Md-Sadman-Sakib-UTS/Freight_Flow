from pathlib import Path
import json
import os

import httpx
from fastapi import FastAPI, Body, HTTPException
from fastapi.staticfiles import StaticFiles


from backend.agents import ingest                      
from backend.agents import risk_agent as gpt_risk      
from backend.agents import risk as rule_risk          
from backend.agents import cost                        
from backend import kpi                                

app = FastAPI(title="FreightFlow API")


@app.get("/api/hazards")
def latest_hazards():
    snaps = sorted(ingest.OUT_DIR.glob("*.geojson"))
    if not snaps:
        raise HTTPException(503, "No hazard snapshots yet")
    return json.loads(snaps[-1].read_text())

@app.get("/api/shipments/{ship_id}")
def get_shipment(ship_id: str):
    coords = [[151.195, -33.85], [151.205, -33.85]]  
    return {"route": {"type": "LineString", "coordinates": coords},
            "risk":  {"delay_prob": 0.8}}

@app.post("/api/risk")
def ad_hoc_risk(body: dict = Body(...)):
    poly = body["polyline"]
    if "hazards" in body:      
        return rule_risk.classify_delay_prob(poly, body["hazards"])
    return gpt_risk.classify_delay_prob(poly)


@app.get("/api/route-options")
def route_options(fromLon: float, fromLat: float, toLon: float, toLat: float):
    mbx = os.getenv("VITE_MAPBOX_TOKEN")
    url = (
        "https://api.mapbox.com/directions/v5/mapbox/driving/"
        f"{fromLon},{fromLat};{toLon},{toLat}"
    )
    params = {
        "alternatives": "true",
        "overview": "full",
        "geometries": "polyline",
        "access_token": mbx,
    }
    resp = httpx.get(url, params=params, timeout=20).json()["routes"][:3]

    routes = []
    for r in resp:
        distance_km = r["distance"] / 1000
        eta_min     = r["duration"] / 60
        cost_aud    = cost.estimate_cost(distance_km, eta_min)
        risk        = gpt_risk.classify_delay_prob(r["geometry"])
       
        if isinstance(risk, str):
            try:
                risk = json.loads(risk)
            except Exception:
                risk = {"delay_prob": 0.5, "avoid_coords": [], "explain": "parse error"}

        routes.append(
            {
                "polyline":    r["geometry"],
                "distance_km": round(distance_km, 2),
                "eta_min":     round(eta_min, 1),
                "cost_aud":    round(cost_aud, 2),
                "risk":        risk,
            }
        )

   
    chosen = min(routes, key=lambda x: (x["risk"]["delay_prob"], x["eta_min"]))

    baseline_cost = routes[0]["cost_aud"]
    saved = max(0, baseline_cost - chosen["cost_aud"])

    kpi.bump_routes(chosen["risk"]["delay_prob"] > 0.7, saved)

    return {
        "original":     routes[0],
        "chosen":       chosen,
        "alternatives": routes,
        "saved_aud":    round(saved, 2),
    }


@app.get("/api/kpi")
def kpi_snapshot():
    return kpi.snapshot()


app.mount(
    "/",
    StaticFiles(directory=Path("frontend/dist"), html=True),
    name="frontend",
)
