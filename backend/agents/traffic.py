def route_passes_traffic(route_polyline: str, traffic_features, radius=0.001) -> bool:
    """Returns True if the route passes near a live traffic jam/incident."""
    import polyline
    for lat, lon in polyline.decode(route_polyline):
        for feat in traffic_features:
            hx, hy = feat["geometry"]["coordinates"]
            # You may want to check 'type' property for 'Jam', 'Incident', etc.
            if abs(lon - hx) < radius and abs(lat - hy) < radius:
                return True
    return False