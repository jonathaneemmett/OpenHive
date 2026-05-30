import json
import logging
from typing import Annotated

from mcp.server import FastMCP
from pydantic import Field

from openhive.services import openrouter
from openhive.skills.loader import Skill, discover_skills

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("openhive")


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


def main() -> None:
    """Run the OpenHive MCP server."""
    logger.info("Starting OpenHive MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
