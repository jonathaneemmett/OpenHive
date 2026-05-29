
from typing import Annotated

from pydantic import Field


def register(mcp):
    @mcp.tool()
    async def echo(
        message: Annotated[str, Field(description="The message to echo back")],
    ) -> str:
        """Echo the input message back to the caller."""
        return message
