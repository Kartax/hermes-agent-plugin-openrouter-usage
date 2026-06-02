"""OpenRouter Usage — Plugin Registration.

Wires the openrouter_usage tool into the Hermes tool system.
"""

import logging

from . import schemas, tools

_log = logging.getLogger(__name__)


def register(ctx):
    """Register the openrouter_usage tool with Hermes."""
    ctx.register_tool(
        name="openrouter_usage",
        toolset="default",
        schema=schemas.OPENROUTER_USAGE,
        handler=tools.openrouter_usage,
    )
    _log.info("openrouter-usage plugin registered")
