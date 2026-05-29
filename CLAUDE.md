# OpenHive - Python MCP Server

## Project Overview

OpenHive is a Python MCP (Model Context Protocol) server. MCP is a protocol that enables AI models to interact with external tools and data sources through a standardized interface.

## Tech Stack

- **Language:** Python 3.11+
- **MCP SDK:** `mcp` (official Python SDK from Anthropic)
- **Package Manager:** `uv` (preferred) or `pip`
- **Project Config:** `pyproject.toml` (no `setup.py` or `requirements.txt`)
- **Formatting:** `ruff format`
- **Linting:** `ruff check`
- **Type Checking:** `mypy` with strict mode

## Project Structure

```
openhive/
  __init__.py
  server.py          # MCP server entry point
  tools/             # Tool implementations (one file per tool or domain)
    __init__.py
  resources/         # MCP resource implementations
    __init__.py
  prompts/           # MCP prompt templates
    __init__.py
tests/
  __init__.py
pyproject.toml
CLAUDE.md
```

## MCP Server Conventions

### Server Setup

- Use `mcp.server.FastMCP` for the server (high-level API), not the low-level `Server` class
- Define the server instance in `server.py` as the single entry point
- Register tools using the `@mcp.tool()` decorator
- Register resources using `@mcp.resource()` decorator
- Register prompts using `@mcp.prompt()` decorator

### Tool Design

- Each tool function must have a clear, descriptive docstring -- this becomes the tool description shown to the AI model
- Use type hints on all parameters -- the MCP SDK uses these to generate the JSON schema
- Use `Annotated[type, Field(description="...")]` for parameter descriptions
- Keep tool functions focused: one tool = one action
- Return plain strings for simple results; return structured data as JSON strings
- Handle errors gracefully and return informative error messages rather than raising exceptions
- Avoid side effects where possible; tools should be predictable and idempotent when practical

### Resource Design

- Use URI templates for dynamic resources (e.g., `resource://items/{id}`)
- Return appropriate MIME types
- Resources are for read-only data exposure; use tools for actions

### Example Tool Pattern

```python
from mcp.server import FastMCP
from pydantic import Field
from typing import Annotated

mcp = FastMCP("openhive")

@mcp.tool()
async def my_tool(
    param: Annotated[str, Field(description="Description of param")],
    optional_param: Annotated[int, Field(description="Optional with default")] = 10,
) -> str:
    """Short description of what this tool does.

    Longer description with usage details if needed.
    """
    # Implementation
    return "result"
```

## Python Conventions

### General

- Use `async`/`await` for I/O-bound operations
- Prefer `pathlib.Path` over `os.path`
- Use f-strings for string formatting
- Use dataclasses or Pydantic models for structured data
- Use `logging` module, not `print()`, for diagnostics
- Use `typing` annotations on all function signatures

### Naming

- `snake_case` for functions, methods, variables, and modules
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants
- Prefix private/internal names with `_`

### Error Handling

- Catch specific exceptions, never bare `except:`
- Use custom exception classes for domain-specific errors
- Log errors with context before re-raising or returning error messages

### Dependencies

- Pin dependencies in `pyproject.toml` with minimum versions (e.g., `mcp>=1.0`)
- Keep dependencies minimal -- only add what's truly needed
- Use `uv` for dependency management and virtual environments

## Commands

```bash
# Install dependencies
uv sync

# Run the server (stdio transport for Claude Desktop / Claude Code)
uv run mcp run openhive/server.py

# Run the server (SSE transport for HTTP)
uv run mcp run openhive/server.py --transport sse

# Inspect the server interactively
uv run mcp dev openhive/server.py

# Format code
uv run ruff format .

# Lint code
uv run ruff check --fix .

# Type check
uv run mypy openhive/

# Run tests
uv run pytest
```

## Testing

- Use `pytest` with `pytest-asyncio` for async tests
- Test tools in isolation by calling the function directly
- Use `mcp.ClientSession` for integration tests against the running server
- Mock external services; never make real API calls in tests
- Aim for test coverage on all tool functions

## Git Conventions

- Write concise commit messages in imperative mood (e.g., "Add search tool")
- One logical change per commit
- Do not commit `.env`, secrets, or virtual environment directories
