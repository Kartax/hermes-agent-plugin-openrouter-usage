"""OpenRouter Usage — Dashboard Backend API.

Mounted at /api/plugins/openrouter-usage/ by the dashboard plugin system.
Fetches usage data from OpenRouter's /api/v1/key and /api/v1/activity endpoints.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query

_log = logging.getLogger(__name__)

router = APIRouter()

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _resolve_api_key() -> str:
    """Read the OpenRouter API key from env or .env file."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key

    hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
    env_path = os.path.join(hermes_home, ".env")
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    var, val = line.split("=", 1)
                    if var.strip() == "OPENROUTER_API_KEY":
                        return val.strip().strip("\"'")
    except FileNotFoundError:
        pass
    return ""


def _resolve_management_key() -> str:
    """Read the OpenRouter Management API key if set."""
    key = os.environ.get("OPENROUTER_MANAGEMENT_API_KEY", "")
    if key:
        return key
    hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
    env_path = os.path.join(hermes_home, ".env")
    try:
        with open(env_path) as f:
            for line in f:
                if "OPENROUTER_MANAGEMENT_API_KEY" in line and "=" in line:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        val = parts[1].strip().strip("\"' \t\n")
                        if val:
                            return val
    except FileNotFoundError:
        pass
    return ""


def _api_get(path: str, api_key: str = None) -> dict:
    """Make a GET request to the OpenRouter API."""
    if not api_key:
        api_key = _resolve_api_key()
    if not api_key:
        return {"error": "OPENROUTER_API_KEY not found"}

    url = f"{OPENROUTER_BASE}/{path.lstrip('/')}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "Hermes-Agent/openrouter-usage-plugin")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        _log.error("OpenRouter HTTP %s: %s", e.code, body)
        return {"error": f"HTTP {e.code}: {body[:200]}"}
    except urllib.error.URLError as e:
        _log.error("OpenRouter connection error: %s", e)
        return {"error": f"unreachable: {e.reason}"}
    except json.JSONDecodeError as e:
        return {"error": f"invalid JSON: {e}"}


PERIOD_SECONDS = {"1h": 3600, "24h": 86400, "7d": 604800}


@router.get("/usage")
async def get_usage(period: str = Query("24h", regex="^(24h|7d)$")):
    """Fetch OpenRouter usage summary for the given period."""
    key_data = _api_get("key")
    if "error" in key_data and "data" not in key_data:
        return {"error": key_data["error"]}

    data_root = key_data.get("data", key_data)
    credits_data = _api_get("credits")
    cd = credits_data.get("data", credits_data) if "error" not in credits_data else {}

    result = {
        "label": str(data_root.get("label", "Default Key"))[:30],
        "is_free_tier": data_root.get("is_free_tier", False),
        "usage_total": round(float(data_root.get("usage", 0) or 0), 6),
        "usage_daily": round(float(data_root.get("usage_daily", 0) or 0), 6),
        "usage_weekly": round(float(data_root.get("usage_weekly", 0) or 0), 6),
        "usage_monthly": round(float(data_root.get("usage_monthly", 0) or 0), 6),
        "total_credits": round(float(cd.get("total_credits", 0) or 0), 2),
        "total_usage": round(float(cd.get("total_usage", 0) or 0), 6),
        "remaining": round(max(0, float(cd.get("total_credits", 0) or 0) - float(cd.get("total_usage", 0) or 0)), 2),
        "period": period,
    }
    return result


@router.get("/activity")
async def get_activity(period: str = Query("24h", regex="^(24h|7d)$")):
    """Fetch OpenRouter activity log (only works with Management Key).

    Returns data aggregated by (date, model, provider).
    """
    try:
        mgmt_key = _resolve_management_key()
        if not mgmt_key:
            return {
                "error": "Management Key required",
                "hint": "Set OPENROUTER_MANAGEMENT_API_KEY in ~/.hermes/.env and restart dashboard",
            }

        activity_data = _api_get("activity", api_key=mgmt_key)
        if "error" in activity_data:
            return {"error": activity_data["error"]}

        data_list = []
        if isinstance(activity_data, list):
            data_list = activity_data
        elif isinstance(activity_data, dict) and "data" in activity_data:
            data_list = activity_data["data"]

        if not data_list:
            return {
                "total_requests": 0, "total_prompt_tokens": 0,
                "total_completion_tokens": 0, "total_tokens": 0,
                "total_cost": 0, "period": period,
                "top_models": [], "recent_entries": [],
            }

        # Date-based cutoff — data is aggregated by DAY, so use generous windows
        now = datetime.now(timezone.utc)
        if period == "1h":
            # No hourly data — show today
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "24h":
            # Show today + yesterday
            cutoff = (now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1))
        else:
            # Show last 7 days
            cutoff = (now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6))

        recent = []
        for entry in data_list:
            date_str = entry.get("date", "")
            if not date_str:
                continue
            try:
                entry_dt = datetime.fromisoformat(date_str.strip())
                if entry_dt.tzinfo is None:
                    entry_dt = entry_dt.replace(tzinfo=timezone.utc)
                if entry_dt >= cutoff:
                    recent.append(entry)
            except (ValueError, TypeError):
                continue

        total_requests = sum(e.get("requests", 0) or 0 for e in recent)
        total_prompt = sum(int(e.get("prompt_tokens", 0) or 0) for e in recent)
        total_comp = sum(int(e.get("completion_tokens", 0) or 0) for e in recent)
        total_cost = sum(float(e.get("usage", 0) or 0) for e in recent)

        model_stats = {}
        for e in recent:
            m = e.get("model", e.get("model_permaslug", "?"))
            if m not in model_stats:
                model_stats[m] = {"requests": 0, "tokens": 0, "cost": 0.0}
            model_stats[m]["requests"] += int(e.get("requests", 0) or 0)
            model_stats[m]["tokens"] += int(e.get("prompt_tokens", 0) or 0) + int(e.get("completion_tokens", 0) or 0)
            model_stats[m]["cost"] += float(e.get("usage", 0) or 0)

        top_models = sorted(
            [{"model": m, **s} for m, s in model_stats.items()],
            key=lambda x: -x["cost"],
        )[:10]

        # Aggregate recent entries by (date, model) — OpenRouter splits by provider
        merged = {}
        for e in recent:
            key = (str(e.get("date", ""))[:10], e.get("model", "?"))
            if key not in merged:
                merged[key] = {
                    "date": key[0],
                    "model": key[1],
                    "requests": 0, "prompt_tokens": 0,
                    "completion_tokens": 0, "total_tokens": 0,
                    "cost": 0.0, "providers": [],
                }
            m = merged[key]
            m["requests"] += int(e.get("requests", 0) or 0)
            m["prompt_tokens"] += int(e.get("prompt_tokens", 0) or 0)
            m["completion_tokens"] += int(e.get("completion_tokens", 0) or 0)
            m["total_tokens"] += int(e.get("prompt_tokens", 0) or 0) + int(e.get("completion_tokens", 0) or 0)
            m["cost"] += float(e.get("usage", 0) or 0)
            prov = e.get("provider_name", "")
            if prov and prov not in m["providers"]:
                m["providers"].append(prov)

        # Sort by date desc, cost desc
        last_entries = sorted(
            merged.values(),
            key=lambda x: (x["date"], -x["cost"]),
            reverse=True,
        )[:15]

        # Round costs
        for e in last_entries:
            e["cost"] = round(e["cost"], 6)

        return {
            "total_requests": total_requests,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_comp,
            "total_tokens": total_prompt + total_comp,
            "total_cost": round(total_cost, 6),
            "period": period,
            "note": "Data is aggregated by (date, model, provider). Hourly granularity not available.",
            "top_models": top_models,
            "recent_entries": last_entries,
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        _log.error("get_activity crashed: %s\n%s", e, tb)
        return {
            "error": f"Server error: {e}",
            "detail": str(e),
        }