# backend/kpi.py
data = {"routes": 0, "high_risk": 0, "money_saved": 0.0}

def bump_routes(high_risk: bool, saved: float):
    data["routes"] += 1
    if high_risk:
        data["high_risk"] += 1
    data["money_saved"] += saved

def snapshot():
    if data["routes"] == 0:
        delay_pct = 0
    else:
        delay_pct = data["high_risk"] / data["routes"]
    return {
        "delay_pct": round(delay_pct, 2),
        "money_saved": round(data["money_saved"], 2),
    }
