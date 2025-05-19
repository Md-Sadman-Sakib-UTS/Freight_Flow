def route_passes_hazard(route_polyline: str, hazard_features, radius=0.001) -> bool:
    """Returns True if the route passes near any known hazard."""
    import polyline
    for lat, lon in polyline.decode(route_polyline):
        for feat in hazard_features:
            hx, hy = feat["geometry"]["coordinates"]
            if abs(lon - hx) < radius and abs(lat - hy) < radius:
                return True
    return False