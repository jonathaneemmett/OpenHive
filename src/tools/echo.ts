import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';

export function registerEchoTool(server: McpServer) {
	server.registerTool(
		'echo',
		{
			title: 'Echo',
			description: 'Returns the input message back to the caller',
			inputSchema: z.object({
				message: z.string().describe('The message to echo back'),
			}),
		},
		async ({ message }) => ({
			content: [{ type: 'text', text: message }],
		}),
	);
}
