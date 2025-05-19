"""
FreightFlow – GPT-4.1 snapshot risk agent (Phase 7, final, robust)
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from openai import OpenAIError
import backoff

from agents import Agent, Runner, ModelSettings, function_tool

log = logging.getLogger(__name__)


@function_tool
def get_live_hazards() -> list:
    """
    Return a lightweight list of hazards from the most-recent *.geojson file.
    Each item only contains the fields GPT actually needs:
        { "type": "Crash", "coordinates": [lon, lat] }
    """
    files = sorted(Path("data/hazards").glob("*.geojson"))
    if not files:
        return []
    try:
        raw = json.loads(files[-1].read_text()).get("features", [])
        slim = [
            {
                "type": f["properties"].get("type", ""),
                "coordinates": f["geometry"]["coordinates"],
            }
            for f in raw
        ]
        return slim
    except Exception as exc:
        log.warning("Failed to parse hazard snapshot: %s", exc)
        return []



risk_agent = Agent(
    name="RiskAgent",
    instructions=(
        "You are FreightFlow's Risk Agent.\n"
        "The user supplies an encoded `polyline`.\n"
        "You can call the tool `get_live_hazards()` to fetch live hazards.\n"
        "Return JSON **exactly** with keys:\n"
        '{"delay_prob": float (0-1), '
        '"avoid_coords": [[lon,lat]…], '
        '"explain": str}'
    ),
    tools=[get_live_hazards],
    model="gpt-4.1-2025-04-14",          
    model_settings=ModelSettings(temperature=0.2),
)


def _safe_hazards() -> list:
    try:
        return get_live_hazards()          # ← FunctionTool is callable
    except Exception as exc:
        log.warning("hazard tool failure: %s", exc)
        return []


@backoff.on_exception(
    backoff.expo, OpenAIError, max_tries=4,
    giveup=lambda e: getattr(e, "http_status", 500) != 429
)
def _call_gpt_sync(msg):
    return Runner.run_sync(risk_agent, [msg])


def classify_delay_prob(polyline: str) -> dict:
    """
    Returns {"delay_prob": 0-1, …}. Falls back to legacy rule engine on:
      − missing / test API key
      − any GPT error (incl. 429 after 4 back-off retries)
    """
    from backend.agents import risk as rule_risk

    key = os.getenv("OPENAI_API_KEY", "")
    if not key or key.lower().startswith("test"):
        return rule_risk.classify_delay_prob(polyline, {"features": _safe_hazards()})

    
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    try:
        msg = {"role": "user", "content": json.dumps({"polyline": polyline})}
        result = _call_gpt_sync(msg)
        log.info("Risk handled by GPT-4.1")
        return result.final_output
    except (OpenAIError, Exception) as exc:
        log.warning("GPT fallback: %s", exc)
        return rule_risk.classify_delay_prob(polyline, {"features": _safe_hazards()})