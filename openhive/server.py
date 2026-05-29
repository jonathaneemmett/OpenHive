import logging
from typing import Annotated

from mcp.server import FastMCP
from pydantic import Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("openhive")


@mcp.tool()
async def echo(
    message: Annotated[str, Field(description="The message to echo back")],
) -> str:
    """Echo a message back to the caller."""
    return message


def main() -> None:
    """Run the OpenHive MCP server."""
    logger.info("Starting OpenHive MCP server")
    mcp.run()


if __name__ == "__main__":
    main()

