def estimate_emissions(distance_km: float, emission_factor: float = 0.25) -> float:
    """Estimate emissions in kg CO₂ (default: 0.25 kg/km for car/truck)."""
    return distance_km * emission_factor