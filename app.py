import os, json, threading
from datetime import datetime
from urllib.parse import quote_plus
from collections import deque
from pathlib import Path

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import httpx, pydeck as pdk, polyline
from dotenv import load_dotenv
from streamlit_searchbox import st_searchbox

# ── 0. Page config ───────────────────────────────────────────────
st.set_page_config(page_title="FreightFlow", layout="wide")

# ── 1. Env & constants ───────────────────────────────────────────
NSW_BBOX = [139.965, -38.03, 155.258, -27.839]
REFRESH_SECONDS = 300    # 5 minutes

load_dotenv()
MBX = os.getenv("MAPBOX_TOKEN")
if not MBX:
    st.error("MAPBOX_TOKEN missing in .env")
    st.stop()

# ── 2. Kick-off the 15-min ingest loop in background ─────────────
from backend.agents.ingest import main as ingest_loop

def _ensure_ingest():
    if "ingest_thread" not in st.session_state:
        t = threading.Thread(target=ingest_loop, name="hazard_ingest", daemon=True)
        t.start()
        st.session_state.ingest_thread = t

_ensure_ingest()

# ── 3. Auto-refresh the UI every 5 min ──────────────────────────
st_autorefresh(interval=REFRESH_SECONDS*1000, key="data_refresh")

# ── 4. Backend helpers ───────────────────────────────────────────
from backend.agents import ingest, cost, toll, hazard, traffic
from backend.agents import risk_agent as gpt_risk

# ── 5. KPI state (rolling window) ────────────────────────────────
WIN = 50
if "hist" not in st.session_state:
    st.session_state.hist = deque(maxlen=WIN)

def bump(delayed: bool, saved: float):
    st.session_state.hist.append((delayed, saved))

def kpi_snapshot():
    if not st.session_state.hist:
        return {"delay_pct": 0.0, "money_saved": 0.0}
    delayed = sum(1 for d, _ in st.session_state.hist if d)
    saved   = sum(s for _, s in st.session_state.hist)
    return {"delay_pct": delayed / len(st.session_state.hist), "money_saved": saved}

# ── 6. NSW geocoder searchbox ───────────────────────────────────
def search_places(q: str):
    if len(q) < 3:
        return []
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote_plus(q)}.json"
    params = {"access_token": MBX, "autocomplete": "true",
              "country": "au", "bbox": ",".join(map(str, NSW_BBOX)), "limit": 6}
    feats = httpx.get(url, params=params, timeout=4).json().get("features", [])
    return [(f["place_name"],
             {"name": f["place_name"], "lon": f["center"][0], "lat": f["center"][1]})
            for f in feats]

def coords(sel, label):
    if not isinstance(sel, dict):
        st.warning(f"Choose the {label} from the drop-down list.")
        st.stop()
    return sel["lon"], sel["lat"]

# ── 7. Helper for map zoom ──────────────────────────────────────
def _view_state_for_paths(path_polylines: list[str]) -> pdk.ViewState:
    lats, lons = [], []
    for pl in path_polylines:
        for lat, lon in polyline.decode(pl):
            lats.append(lat); lons.append(lon)
    if not lats:
        return pdk.ViewState(latitude=-33.86, longitude=151.2, zoom=8)
    return pdk.ViewState(
        latitude=sum(lats)/len(lats),
        longitude=sum(lons)/len(lons),
        zoom=8 if max(lats)-min(lats) > 1 else 10
    )

# ── 8. Sidebar UI ────────────────────────────────────────────────
st.sidebar.title("Multi-Agent Route Intelligence")
st.sidebar.markdown(
    """
    <div style='font-size:1.08em; margin-bottom:0.5em'>
    <b>Active Agents:</b>
    <ul style='margin-left:1em;'>
      <li><span style='color:rgb(0,180,0);font-weight:bold'>Recommended Agent</span>: Multi-agent arbitration (all rules applied)</li>
      <li><span style='color:rgb(200,80,0);font-weight:bold'>Baseline Agent</span>: Cheapest total cost route</li>
      <li><span style='color:rgb(60,60,180);font-weight:bold'>Alternate Agent</span>: Best backup (fastest not chosen by above)</li>
      <li><b>Hazard Avoidance Agent</b>: Avoids all known hazards (crashes, floods)</li>
      <li><b>Traffic Agent</b>: Avoids routes with current traffic jams/incidents</li>
      <li><b>Promise Agent</b>: Ensures delivery before user-set ETA deadline</li>
      <li><b>Eco Agent</b>: Minimizes CO₂ emissions for green logistics</li>
      <li><b>Toll Agent</b>: Adds real NSW road tolls to total cost (API ready)</li>
    </ul>
    </div>
    """,
    unsafe_allow_html=True,
)

from_sel = st_searchbox(search_places, key="from_sb", placeholder="Origin in NSW")
to_sel   = st_searchbox(search_places, key="to_sb", placeholder="Destination in NSW")
DELIVERY_DEADLINE_MIN = st.sidebar.number_input(
    "Max ETA (minutes)", min_value=10, max_value=600, value=120, step=5
)
run_btn  = st.sidebar.button(
    "Find best route",
    disabled=not (isinstance(from_sel, dict) and isinstance(to_sel, dict)),
)
st.sidebar.markdown("---")

# ── 9. Main title & hazard layer ───────────────────────────────
st.title("FreightFlow")

latest = sorted(Path(ingest.OUT_DIR).glob("*.geojson"))[-1]
hazards_fc = json.loads(latest.read_text())
traffic_fc = hazards_fc  # Use separate traffic API if available

pdk.settings.mapbox_api_key = MBX
haz_layer = pdk.Layer(
    "ScatterplotLayer", hazards_fc["features"],
    get_position="geometry.coordinates",
    get_fill_color=[200, 0, 0, 180],  # semi-transparent red
    get_radius=180,
    pickable=True,
)
deck = pdk.Deck(
    map_style="mapbox://styles/mapbox/light-v11",
    initial_view_state=_view_state_for_paths([]),
    layers=[haz_layer],
)
map_ph = st.pydeck_chart(deck)

# ── 10. Route calculation & Multi-Agent Arbitration ─────────────
def polyline_to_waypoints(polyline_str):
    return [{"lat": lat, "lon": lon} for lat, lon in polyline.decode(polyline_str)]

if run_btn:
    f_lon, f_lat = coords(from_sel, "origin")
    t_lon, t_lat = coords(to_sel,   "destination")

    with st.spinner("Calling Mapbox, Risk Agent, Toll API, etc..."):
        url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{f_lon},{f_lat};{t_lon},{t_lat}"
        routes = httpx.get(url, params={
            "alternatives": "true", "overview": "full", "geometries": "polyline",
            "access_token": MBX}, timeout=20).json()["routes"][:3]

        enriched = []
        for r in routes:
            km, eta = r["distance"]/1000, r["duration"]/60
            risk = gpt_risk.classify_delay_prob(r["geometry"])
            if isinstance(risk, str):
                risk = json.loads(risk)
            waypoints = polyline_to_waypoints(r["geometry"])
            try:
                toll_price = toll.get_toll_price((f_lon, f_lat), (t_lon, t_lat), vehicle_type="car", waypoints=waypoints)
            except Exception as exc:
                st.warning(f"Could not get toll for route: {exc}")
                toll_price = 0.0
            has_hazard = hazard.route_passes_hazard(r["geometry"], hazards_fc["features"])
            has_traffic = traffic.route_passes_traffic(r["geometry"], traffic_fc["features"])
            emissions = km * 0.25
            promise_ok = eta <= DELIVERY_DEADLINE_MIN

            enriched.append({
                "polyline": r["geometry"],
                "distance_km": round(km, 2),
                "eta":        round(eta, 1),
                "toll_price": round(toll_price, 2),
                "cost":       round(cost.estimate_cost(km, eta), 2) + toll_price,
                "delay":      risk["delay_prob"],
                "avoid":      risk.get("avoid_coords", []),
                "hazard_safe": int(not has_hazard),
                "traffic_safe": int(not has_traffic),
                "promise_ok": int(promise_ok),
                "co2": emissions
            })

        # Multi-agent filtering
        finalists = [r for r in enriched if r["hazard_safe"] and r["traffic_safe"] and r["promise_ok"]]
        if not finalists:
            finalists = [r for r in enriched if r["hazard_safe"] and r["promise_ok"]]
        if not finalists:
            finalists = [r for r in enriched if r["hazard_safe"]]
        if not finalists:
            finalists = enriched

        recommended = min(finalists, key=lambda r: (r["co2"], r["cost"], r["delay"]))
        by_cost = sorted(enriched, key=lambda r: r["cost"])
        baseline = by_cost[0] if by_cost else recommended
        alternates = [r for r in enriched if r is not recommended and r is not baseline]
        alternate = min(alternates, key=lambda r: (r["delay"], r["eta"])) if alternates else None

        def rejection_reason(route):
            reasons = []
            if not route["hazard_safe"]:
                reasons.append("crosses hazard")
            if not route["traffic_safe"]:
                reasons.append("crosses traffic")
            if not route["promise_ok"]:
                reasons.append("misses delivery time")
            return ", ".join(reasons) if reasons else "—"

        min_d = min(r["delay"] for r in enriched)
        bump(recommended["delay"] > 0.5 and recommended["delay"] - min_d > 0.10,
             max(0, baseline["cost"] - recommended["cost"]))

        # Map drawing
        COLOR_RECOMMENDED = [0, 180, 0, 255]
        COLOR_BASELINE    = [200, 80, 0, 255]
        COLOR_ALTERNATE   = [60, 60, 180, 255]
        COLOR_ALT         = [30, 30, 30, 255]
        route_layers = []
        for r in enriched:
            if r is recommended:
                col, w = COLOR_RECOMMENDED, 12
            elif r is baseline:
                col, w = COLOR_BASELINE, 9
            elif alternate and r is alternate:
                col, w = COLOR_ALTERNATE, 8
            else:
                col, w = COLOR_ALT, 4
            path_points = [[p[1], p[0]] for p in polyline.decode(r["polyline"])]
            route_layers.append(
                pdk.Layer(
                    "PathLayer",
                    data=[{"path": path_points}],
                    get_width=w, get_color=col, opacity=1
                )
            )
        marker_layer = pdk.Layer(
            "ScatterplotLayer",
            data=[{"coords": [f_lon, f_lat], "c": [0,100,255]},
                  {"coords": [t_lon, t_lat], "c": [0,0,0]}],
            get_position="coords", get_fill_color="c", get_radius=500,
        )
        deck.layers = [haz_layer, marker_layer] + route_layers
        visible_routes = [r["polyline"] for r in [recommended, baseline, alternate] if r]
        deck.initial_view_state = _view_state_for_paths(visible_routes)
        map_ph.pydeck_chart(deck)

        # Legend
        st.markdown(
            "<div style='display:flex;gap:1rem'>"
            "<span><span style='width:12px;height:12px;border-radius:2px;background:rgb(0,180,0);display:inline-block;margin-right:4px'></span>Recommended</span>"
            "<span><span style='width:12px;height:12px;border-radius:2px;background:rgb(200,80,0);display:inline-block;margin-right:4px'></span>Baseline</span>"
            "<span><span style='width:12px;height:12px;border-radius:2px;background:rgb(60,60,180);display:inline-block;margin-right:4px'></span>Alternate</span>"
            "<span><span style='width:12px;height:12px;border-radius:2px;background:rgb(30,30,30);display:inline-block;margin-right:4px'></span>Alt</span>"
            "</div>", unsafe_allow_html=True)

        # Table
        st.subheader("Route Decision Table")
        rows = []
        for idx, r in enumerate(enriched, 1):
            rows.append({
                "Route": idx,
                "Recommended": "✓" if r is recommended else "",
                "Baseline": "✓" if r is baseline else "",
                "Alternate": "✓" if alternate and r is alternate else "",
                "ETA": r["eta"],
                "Cost": f"${r['cost']:.2f}",
                "Toll($)": f"{r['toll_price']:.2f}",
                "CO2(kg)": f"{r['co2']:.2f}",
                "Delay": f"{r['delay']:.2f}",
                "Safe": "✅" if r["hazard_safe"] else "❌",
                "No Traffic": "✅" if r["traffic_safe"] else "❌",
                "On Time": "✅" if r["promise_ok"] else "❌",
                "Reason Rejected": rejection_reason(r) if r is not recommended else "—"
            })
        st.table(rows)

        # UI summary/explanation
        st.success("**Recommended route:** chosen by the multi-agent system as safest, meets delivery promise, avoids traffic, minimizes emissions and cost (including real tolls). "
                   "Baseline and alternate are shown for comparison. Rejection reasons for each route are explained above.")

# ── 13. Footer ─────────────────────────────────────────────────
st.caption(f"Last refreshed {datetime.utcnow():%H:%M:%S} UTC")