# backend/agents/cost.py
FUEL_PER_KM_AUD = 0.25
DRIVER_PER_HOUR_AUD = 50

def estimate_cost(distance_km: float, eta_min: float, toll: float = 0.0) -> float:
    return distance_km * FUEL_PER_KM_AUD + (eta_min / 60) * DRIVER_PER_HOUR_AUD + toll