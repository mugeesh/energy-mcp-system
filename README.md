# iam-mcp

Energybox IAM + energy assistant built from two parts:

- **MCP server** (`mcp-server-client/mcp_server/`) — exposes site, energy
  consumption and user lookups as MCP tools. Speaks stdio locally and
  streamable HTTP in Docker.
- **MCP client** (`mcp-server-client/mcp_client/` + `main.py`) — a FastAPI
  service that connects to the MCP server, calls **DeepSeek**
  (`deepseek-chat`) for tool calling, and exposes `/chat`, `/health`,
  `/tools` and `/clear_history` to the Next.js UI.

```
iam-mcp/
├── mcp-server-client/     # Python: MCP server + DeepSeek client + FastAPI
│   ├── mcp_server/        # FastMCP server (stdio / streamable-http)
│   ├── mcp_client/        # DeepSeek agent + MCP client
│   ├── clients/           # IAM + time-series HTTP clients
│   ├── main.py            # FastAPI app (:8000)
│   └── Dockerfile         # shared image for both compose services
├── energy-mcp-ui/         # Next.js chat UI (:3000)
├── deploy/                # Terraform + remote deploy script
├── mcp-test/              # separate iam-mcp site-ID server (reference)
├── docker-compose.yml     # MCP server (:8001) + client (:8000)
└── .env.example           # copy to .env, add DEEPSEEK_API_KEY
```

## Quick start (local, stdio)

```bash
cp .env.example .env          # add DEEPSEEK_API_KEY + IAM credentials
cd mcp-server-client
uv sync
uv run python main.py         # FastAPI on http://localhost:8000
```

The client spawns `mcp_server/server.py` over stdio automatically. For the
interactive CLI instead:

```bash
cd mcp-server-client
MCP_TRANSPORT=stdio uv run python -m mcp_client.client
```

## Docker Compose

```bash
cp .env.example .env          # add DEEPSEEK_API_KEY
docker compose up -d --build
```

| Service | URL | Notes |
| --- | --- | --- |
| `mcp-client` | http://localhost:8000 | FastAPI (`/chat`, `/health`, `/tools`) |
| `mcp-server` | http://127.0.0.1:8001/mcp | streamable HTTP, used by the client |

Check it:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/tools
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | — | DeepSeek API key (required) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible base URL |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model used for tool calling |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `MCP_SERVER_URL` | `http://127.0.0.1:8001/mcp` | Used in HTTP mode |
| `MCP_SERVER_PATH` | `mcp-server-client/mcp_server` | Used in stdio mode |
| `IAM_URL` | staging IAM | IAM base URL |
| `AUTH_TOKEN` | — | Local stdio fallback only; HTTP uses the FE Bearer token |
| `ts_api_url` | — | Time-series / energy API base URL |
| `CORS_ALLOW_ORIGINS` | localhost:3000 | UI origins |

## UI (runs locally)

The UI is **not** part of the Docker/deploy stack. Run it on your laptop and
point it at the client:

```bash
cd energy-mcp-ui
npm install
NEXT_PUBLIC_MCP_BACKEND_SERVER_URL=http://localhost:8000 npm run dev
# against a deployed client:
# NEXT_PUBLIC_MCP_BACKEND_SERVER_URL=http://<ec2-public-ip>:8080 npm run dev
```

## Deploy

The `deploy/` folder contains Terraform for an EC2 `t3.micro` plus a
`remote-deploy.sh` that runs **the MCP server and client** with Compose. The
Next.js UI stays local. See [`deploy/README.md`](deploy/README.md).

## Notes

- The client injects the caller's JWT into MCP tool calls; the LLM never sees
  the token.
- The server keeps a separate IAM session per token.
- `mcp-test/` is left in place as the earlier standalone site-ID MCP server.
