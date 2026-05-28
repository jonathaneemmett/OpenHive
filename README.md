# NodeJsMCP

A simple Node.js/TypeScript MCP (Model Context Protocol) server with stdio and HTTP transports.

## Prerequisites

- Node.js (v18+)
- npm

## Setup

```bash
npm install
```

## Build

```bash
npm run build
```

## Run

### stdio mode (default)

```bash
npm start
```

### HTTP mode

```bash
npm start -- --transport http
```

Server starts at `http://localhost:3000/mcp`.

## Development

```bash
# Run with tsx (no build step)
npm run dev

# Run in HTTP mode
npm run dev -- --transport http

# Watch for changes
npm run watch
```

## Tools

| Tool | Description |
|------|-------------|
| `echo` | Returns the input message back to the caller |
