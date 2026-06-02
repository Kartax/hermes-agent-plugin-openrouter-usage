# Hermes Agent Plugin: OpenRouter Usage

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hermes Plugin](https://img.shields.io/badge/Hermes-Plugin-blue)](https://hermes-agent.nousresearch.com)

A Hermes Agent plugin that shows your **OpenRouter usage and activity** — available credits, daily spend, and detailed request/token/cost logs — directly in the Hermes dashboard and via a CLI tool.

## Features

- **Dashboard tab** — real-time view of credits, spend, top models, and recent activity
- **CLI tool** (`openrouter_usage`) — query usage from any Hermes session
- **Management Key support** — unlocks per-request activity logs with model-level breakdown
- **No external dependencies** — uses only Python stdlib (`urllib`)

<img width="1320" height="796" alt="image" src="https://github.com/user-attachments/assets/75f8d6ec-e660-427f-bdb9-9909efd4c806" />


## Requirements

- [Hermes Agent](https://hermes-agent.nousresearch.com) (v1.x or later)
- A [OpenRouter API key](https://openrouter.ai/keys)

## Installation

```bash
hermes plugins install Kartax/hermes-agent-plugin-openrouter-usage
```

After installation, restart your Hermes session (`/reset`) or restart the dashboard for the dashboard tab to appear.

## Configuration

Add these to your `~/.hermes/.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | **Yes** | Your OpenRouter API key (for credits & spend) |
| `OPENROUTER_MANAGEMENT_API_KEY` | No | Management Key for activity logs (recommended) |

> **Where to get keys:** https://openrouter.ai/keys

## Usage

### CLI Tool

In any Hermes session, ask:

> "Zeig mir mein OpenRouter usage"
> "How many tokens did I use in the last 7 days?"
> "OpenRouter usage this week"

The agent will call `openrouter_usage` and return a formatted overview.

### Dashboard

Once installed and the management key is configured:

1. Start the Hermes dashboard: `hermes dashboard`
2. Open the **OpenRouter Usage** tab in the sidebar
3. See at a glance: available credits, spend today, top models by cost, and a detailed activity table

![Dashboard Preview](https://img.shields.io/badge/dashboard-BarChart3-green)

## License

MIT — see [LICENSE](LICENSE).
