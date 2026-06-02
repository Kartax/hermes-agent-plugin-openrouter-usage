"""OpenRouter Usage — Tool Handlers.

Fetches usage data from OpenRouter's /api/v1/key and /api/v1/activity endpoints.
Uses only stdlib (urllib) — no external dependencies required.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

_log = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
PERIOD_SECONDS = {"24h": 86400, "7d": 604800}


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


def _api_get(path: str) -> dict:
    """Make a GET request to the OpenRouter API and return parsed JSON."""
    api_key = _resolve_api_key()
    if not api_key:
        return {"error": "OPENROUTER_API_KEY not found in environment or .env file"}

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
        return {"error": f"OpenRouter API error {e.code}: {body}"}
    except urllib.error.URLError as e:
        _log.error("OpenRouter connection error: %s", e)
        return {"error": f"OpenRouter unreachable: {e.reason}"}
    except json.JSONDecodeError as e:
        _log.error("OpenRouter non-JSON response: %s", e)
        return {"error": f"Invalid JSON from OpenRouter: {e}"}


def _format_credits(n: float) -> str:
    """Format credit amount nicely."""
    if n >= 1_000_000:
        return f"${n / 1_000_000:,.2f}M"
    if n >= 1_000:
        return f"${n / 1_000:,.2f}K"
    return f"${n:.6f}".rstrip("0").rstrip(".")


def openrouter_usage(args: dict, **kwargs) -> str:
    """Handler: fetch OpenRouter usage data.

    Shows key-level usage credits and credit balance.
    The 'period' parameter adjusts what time window is highlighted.
    """
    period = args.get("period", "24h")

    # ── 1. Fetch key info ──
    key_data = _api_get("key")
    if "error" in key_data and "data" not in key_data:
        return json.dumps({"error": key_data["error"]})

    data_root = key_data.get("data", key_data)

    label = data_root.get("label", "Default Key")[:30]
    usage_total = float(data_root.get("usage", 0) or 0)
    usage_daily = float(data_root.get("usage_daily", 0) or 0)
    usage_weekly = float(data_root.get("usage_weekly", 0) or 0)
    usage_monthly = float(data_root.get("usage_monthly", 0) or 0)
    is_free = data_root.get("is_free_tier", False)

    # ── 2. Fetch credits ──
    credits_data = _api_get("credits")
    if "error" not in credits_data:
        cd = credits_data.get("data", credits_data)
        total_credits = float(cd.get("total_credits", 0) or 0)
        total_usage = float(cd.get("total_usage", 0) or 0)
    else:
        total_credits = 0
        total_usage = 0

    remaining = max(0, total_credits - total_usage) if total_credits else 0

    # ── 3. Build response ──
    lines = []
    lines.append("OpenRouter Usage")
    lines.append("─" * 40)
    lines.append(f"  Key:       {label}")
    lines.append(f"  Tier:      {'Free' if is_free else 'Pay-as-you-go'}")
    lines.append("")

    # Credits summary
    lines.append("Credits:")
    lines.append(f"  Purchased:  ${total_credits:,.2f}" if total_credits else "")
    lines.append(f"  Used:       ${total_usage:,.6f}" if total_usage else "")
    lines.append(f"  Remaining:  ${remaining:,.2f}" if total_credits else "")

    lines.append("")
    lines.append("Usage (in $):")

    lines.append(f"  Daily:   ${usage_daily:.6f}")
    lines.append(f"  Weekly:  ${usage_weekly:.6f}")
    lines.append(f"  Monthly: ${usage_monthly:.6f}")
    lines.append(f"  Total:   ${usage_total:.6f}")

    # ── 4. Try activity log (management key only) ──
    activity = _api_get("activity")
    if isinstance(activity, dict) and "error" not in activity:
        data_list = []
        if isinstance(activity, list):
            data_list = activity
        elif isinstance(activity, dict) and "data" in activity:
            data_list = activity["data"]

        if isinstance(data_list, list) and len(data_list) > 0:
            # Date-based cutoff
            now = datetime.now(timezone.utc)
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if period == "7d":
                cutoff = cutoff - __import__("datetime").timedelta(days=6)
            elif period == "1h":
                pass  # show today

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

            total_req = sum(e.get("requests", 0) or 0 for e in recent)
            total_prompt = sum(int(e.get("prompt_tokens", 0) or 0) for e in recent)
            total_comp = sum(int(e.get("completion_tokens", 0) or 0) for e in recent)
            total_cost = sum(float(e.get("usage", 0) or 0) for e in recent)

            lines.append("")
            lines.append("Activity (detailed):")
            lines.append(f"  Requests:     {total_req}")
            lines.append(f"  Prompt tok:   {total_prompt:,}")
            lines.append(f"  Completion t: {total_comp:,}")
            lines.append(f"  Total tokens: {total_prompt + total_comp:,}")
            lines.append(f"  Total cost:   ${total_cost:.6f}")

            # Top models
            model_stats = {}
            for e in recent:
                m = e.get("model", "?")
                short = m.split("/")[-1] if "/" in m else m
                if short not in model_stats:
                    model_stats[short] = {"requests": 0, "tokens": 0, "cost": 0.0}
                model_stats[short]["requests"] += int(e.get("requests", 0) or 0)
                model_stats[short]["tokens"] += int(e.get("prompt_tokens", 0) or 0) + int(e.get("completion_tokens", 0) or 0)
                model_stats[short]["cost"] += float(e.get("usage", 0) or 0)

            top = sorted(model_stats.items(), key=lambda x: -x[1]["cost"])[:5]
            if top:
                lines.append("")
                lines.append("  Top models:")
                for name, stats in top:
                    lines.append(f"    {name}: {stats['requests']} req / {stats['tokens']:,} tok / ${stats['cost']:.4f}")

            # Last entries (aggregated by date+model)
            merged = {}
            for e in recent:
                k = (str(e.get("date", ""))[:10], e.get("model", "?"))
                if k not in merged:
                    merged[k] = {"date": k[0], "model": k[1].split("/")[-1], "tokens": 0, "cost": 0.0}
                merged[k]["tokens"] += int(e.get("prompt_tokens", 0) or 0) + int(e.get("completion_tokens", 0) or 0)
                merged[k]["cost"] += float(e.get("usage", 0) or 0)

            sorted_entries = sorted(merged.values(), key=lambda x: (x["date"], -x["cost"]), reverse=True)[:5]
            if sorted_entries:
                lines.append("")
                lines.append(f"  Last entries:")
                for e in sorted_entries:
                    lines.append(f"    • {e['date']} | {e['model']:20s} | {e['tokens']:>7,} tok | ${e['cost']:.4f}")

    else:
            # No management key
            lines.append("")
            lines.append("  \u2139 For request/token-level activity, create a Management Key")
            lines.append("    at https://openrouter.ai/keys and set OPENROUTER_MANAGEMENT_API_KEY.")

    return json.dumps(
        {
            "result": "\n".join(line for line in lines if line),
            "usage_total": round(usage_total, 6),
            "usage_daily": round(usage_daily, 6),
            "usage_weekly": round(usage_weekly, 6),
            "usage_monthly": round(usage_monthly, 6),
            "total_credits": round(total_credits, 2),
            "remaining_credits": round(remaining, 2),
            "period": period,
            "has_management_key": isinstance(activity, dict)
            and "error" not in activity,
        }
    )
