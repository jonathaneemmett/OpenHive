# OpenHive

A self-hosted AI assistant MCP server built with Python.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
```

## Running the Server

### Interactive Inspector (for testing)

```bash
uv run mcp dev openhive/server.py
```

### Stdio Transport (for Claude Desktop / Claude Code)

```bash
uv run mcp run openhive/server.py
```

### SSE Transport (HTTP)

```bash
uv run mcp run openhive/server.py --transport sse
```

## Available Tools

- **echo** — Echoes a message back to the caller
