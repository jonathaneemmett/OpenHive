import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { isInitializeRequest } from '@modelcontextprotocol/sdk/types.js';
import express from 'express';
import { randomUUID } from 'node:crypto';
import { buildServer } from './server.js';

const args = process.argv.slice(2);
const transportArg = args.includes('--transport')
	? args[args.indexOf('--transport') + 1]
	: 'stdio';

async function startStdio() {
	const server = buildServer();
	const transport = new StdioServerTransport();
	await server.connect(transport);
	console.error('MCP server running on stdio');
}

async function startHttp() {
	const app = express();
	app.use(express.json());

	const transports = new Map<string, StreamableHTTPServerTransport>();

	app.post('/mcp', async (req, res) => {
		const sessionId = req.headers['mcp-session-id'] as string | undefined;

		if (sessionId && transports.has(sessionId)) {
			const transport = transports.get(sessionId)!;
			await transport.handleRequest(req, res, req.body);
		} else if (!sessionId && isInitializeRequest(req.body)) {
			const transport = new StreamableHTTPServerTransport({
				sessionIdGenerator: () => randomUUID(),
				onsessioninitialized: (id) => {
					transports.set(id, transport);
				},
			});
			transport.onclose = () => {
				if (transport.sessionId) transports.delete(transport.sessionId);
			};
			const server = buildServer();
			await server.connect(transport);
			await transport.handleRequest(req, res, req.body);
		} else {
			res.status(400).json({ error: 'Bad Request: no valid session' });
		}
	});

	app.get('/mcp', async (req, res) => {
		const sessionId = req.headers['mcp-session-id'] as string | undefined;
		if (!sessionId || !transports.has(sessionId)) {
			res.status(400).send('Invalid session');
			return;
		}
		await transports.get(sessionId)!.handleRequest(req, res);
	});

	app.delete('/mcp', async (req, res) => {
		const sessionId = req.headers['mcp-session-id'] as string | undefined;
		if (!sessionId || !transports.has(sessionId)) {
			res.status(400).send('Invalid session');
			return;
		}
		await transports.get(sessionId)!.handleRequest(req, res);
	});

	app.listen(3000, () => {
		console.error('MCP server running on http://localhost:3000/mcp');
	});
}

if (transportArg === 'http') {
	startHttp();
} else {
	startStdio();
}
