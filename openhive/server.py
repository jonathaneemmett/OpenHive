import json
import logging
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from mcp.server import FastMCP
from pydantic import Field

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from openhive.events import event_store
from openhive.services import openrouter
from openhive.skills.loader import Skill, discover_skills
from openhive.tools import alerts, dependabot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("openhive")

dependabot.register(mcp)
alerts.register(mcp)


# --- MCP resource: alerts ---


@mcp.resource("openhive://alerts")
def alerts_resource() -> str:
    """Current alerts as a subscribable MCP resource."""
    all_alerts = event_store.list_alerts()
    return json.dumps([a.to_dict() for a in all_alerts], indent=2)


@mcp.resource("openhive://alerts/unread")
def unread_alerts_resource() -> str:
    """Unread alerts only."""
    from openhive.events import AlertStatus

    unread = event_store.list_alerts(status=AlertStatus.UNREAD)
    return json.dumps([a.to_dict() for a in unread], indent=2)


# --- Skills ---


def _register_skill_prompt(skill: Skill) -> None:
    """Register a skill as an MCP prompt."""

    @mcp.prompt(name=skill.name, description=skill.description)
    def skill_prompt() -> str:
        return skill.instructions

    # Rename to avoid decorator collisions
    skill_prompt.__name__ = f"skill_{skill.name}"
    skill_prompt.__qualname__ = f"skill_{skill.name}"


def _load_skills() -> None:
    """Discover and register all skills."""
    skills = discover_skills()
    for skill in skills:
        _register_skill_prompt(skill)
    if skills:
        logger.info("Registered %d skill(s)", len(skills))
    else:
        logger.info("No skills found")


_load_skills()


# --- Built-in tools ---


@mcp.tool()
async def echo(
    message: Annotated[str, Field(description="The message to echo back")],
) -> str:
    """Echo a message back to the caller."""
    return message


@mcp.tool()
async def chat(
    prompt: Annotated[str, Field(description="The prompt to send to the AI model")],
    model: Annotated[
        str | None,
        Field(description="Model ID to use. Uses default if not specified."),
    ] = None,
) -> str:
    """Send a prompt to an AI model via OpenRouter and return the response."""
    try:
        return await openrouter.chat(prompt, model)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def list_models() -> str:
    """List available AI models from OpenRouter."""
    try:
        models = await openrouter.list_models()
        return json.dumps(models, indent=2)
    except Exception as e:
        return f"Error: {e}"


# --- Custom HTTP routes (webhooks, SSE) ---


@mcp.custom_route("/webhooks/github", methods=["POST"])
async def github_webhook(request):
    from openhive.webhooks import handle_github_webhook

    return await handle_github_webhook(request)


@mcp.custom_route("/events", methods=["GET"])
async def events_sse(request):
    from openhive.sse import handle_sse

    return await handle_sse(request)


# --- Server entry point ---


def main() -> None:
    """Run the OpenHive MCP server."""
    logger.info("Starting OpenHive MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
