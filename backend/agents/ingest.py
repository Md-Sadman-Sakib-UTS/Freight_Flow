"""
FreightFlow – hazard ingest agent
Grabs TfNSW live-hazard feed and snapshots to data/hazards/.
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import logging
import os
import time

import httpx
from dotenv import load_dotenv

# ───────────────────────── Config ─────────────────────────
load_dotenv()
API_KEY  = os.getenv("TFNSW_API_KEY")
FEED_URL = "https://api.transport.nsw.gov.au/v1/live/hazards/incident/open"
OUT_DIR  = Path("data/hazards")
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# ───────────────────────── TfNSW fetcher ──────────────────
def _fetch_from_api() -> list:
    """Hit TfNSW and return a *list* of hazard features."""
    if not API_KEY:
        raise RuntimeError("TFNSW_API_KEY not set")
    hdrs = {"Authorization": f"apikey {API_KEY}", "Accept": "application/json"}
    data = httpx.get(FEED_URL, headers=hdrs, timeout=20).json()

    # TfNSW sometimes returns a FeatureCollection, sometimes a raw list
    if isinstance(data, dict) and "features" in data:
        return data["features"]
    if isinstance(data, list):
        return data
    raise RuntimeError("Unexpected TfNSW payload structure")

# ─────────────────── Public helper (test can patch) ───────
def fetch_hazards():
    """
    Return either:
      • a raw *list* of features (preferred), or
      • a GeoJSON FeatureCollection *dict* with 'features' key.

    By default this calls the live API, but the pytest suite monkey-patches
    this symbol with a fixture.
    """
    return _fetch_from_api()

# ───────────────────────── Snapshot writer ─────────────────
def snapshot() -> None:
    """
    Call `fetch_hazards()` and write ONE timestamped snapshot file.
    Handles both raw-list and FeatureCollection inputs.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)   # allows monkey-patched OUT_DIR
    payload = fetch_hazards()

    # Normalise to features list
    features = payload["features"] if isinstance(payload, dict) else payload

    ts  = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    out = OUT_DIR / f"{ts}.geojson"
    out.write_text(json.dumps({"type": "FeatureCollection", "features": features}))

    logging.info("Saved %s (%d hazards)", out.name, len(features))

# ───────────────────────── CLI / test entry ───────────────
def main():
    """Single-shot snapshot – pytest calls this."""
    snapshot()

# ───────────────────────── Main loop (prod) ───────────────
if __name__ == "__main__":
    logging.info("Ingest loop running — Ctrl-C to stop")
    try:
        while True:
            try:
                snapshot()
            except Exception as exc:
                logging.error("Fetch failed – %s", exc)
                time.sleep(60)    # quick retry on error
            else:
                time.sleep(900)   # 15 min between successful pulls
    except KeyboardInterrupt:
        logging.info("Stopped by user")

