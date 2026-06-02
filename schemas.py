OPENROUTER_USAGE = {
    "name": "openrouter_usage",
    "description": (
        "Fetch OpenRouter usage and activity statistics. "
        "Returns available credits, daily spend, and if a Management Key is configured, "
        "detailed activity with requests, tokens, costs, and top models. "
        "Use this when the user asks about OpenRouter usage, costs, token consumption, "
        "or wants to see their API activity."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "enum": ["24h", "7d"],
                "description": "Time period: '24h' (today + yesterday) or '7d' (last 7 days). Default: '24h'.",
            },
        },
        "required": [],
    },
}