import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { registerEchoTool } from './tools/echo.js';

export function buildServer(): McpServer {
	const server = new McpServer({
		name: 'nodejs-mcp',
		version: '1.0.0',
	});

	registerEchoTool(server);

	return server;
}
