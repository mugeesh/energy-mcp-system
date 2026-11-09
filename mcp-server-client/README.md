# mcp-server-client

Python project containing the Energybox IAM MCP server and a DeepSeek-powered
MCP client / FastAPI backend.

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
cd mcp-server-client
uv sync
```

Copy `../.env.example` to `../.env` and set `DEEPSEEK_API_KEY` plus the IAM
values.

## Run the FastAPI backend

```bash
uv run python main.py
# or
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Endpoints: `POST /chat`, `GET /health`, `GET /tools`, `POST /clear_history`.

## Run the MCP server

stdio (what the client spawns by default):

```bash
cd mcp_server
uv run python server.py
```

streamable HTTP:

```bash
MCP_TRANSPORT=streamable-http MCP_HTTP_HOST=0.0.0.0 MCP_HTTP_PORT=8001 \
  uv run python server.py
# endpoint: http://localhost:8001/mcp
```

## Run the interactive client

```bash
MCP_TRANSPORT=stdio uv run python -m mcp_client.client
```

## MCP client configuration (Cursor / OpenCode / Claude Desktop)

```json
{
  "mcpServers": {
    "energybox": {
      "command": "uv",
      "args": ["--directory", "/Users/mugeesh/git2/iam-mcp/mcp-server-client/mcp_server", "run", "server.py"],
      "env": {
        "IAM_URL": "https://iam.staging.energybox.com",
        "AUTH_TOKEN": "Bearer <token>"
      }
    }
  }
}
```

## Environment

See [`../.env.example`](../.env.example). The important ones:

- `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`
- `MCP_TRANSPORT` (`stdio` / `streamable-http`), `MCP_SERVER_URL`
- `IAM_URL`, `ts_api_url`
- `AUTH_TOKEN` (local stdio only; HTTP uses the frontend Bearer token)
