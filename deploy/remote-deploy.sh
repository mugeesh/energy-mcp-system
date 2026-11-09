#!/usr/bin/env bash
# Run on the EC2 instance from /opt/iam-mcp (the project root).
# Builds and starts the full stack: MCP server + FastAPI/DeepSeek client.
set -euo pipefail

cd "$(dirname "$0")/.."

APP_PORT="${APP_PORT:-8080}"          # host port for the FastAPI client
APP_BIND="${APP_BIND:-0.0.0.0}"       # 127.0.0.1 only when using an SSH tunnel
MCP_SERVER_PORT="${MCP_SERVER_PORT:-8001}"

if [ ! -f .env ]; then
  echo "Missing .env in $(pwd)." >&2
  echo "Create it from .env.example and set DEEPSEEK_API_KEY (and IAM settings)." >&2
  exit 1
fi

export APP_PORT APP_BIND MCP_SERVER_PORT

docker compose up -d --build

echo
echo "Waiting for the client health endpoint..."
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${APP_PORT}/health" >/dev/null 2>&1; then
    echo "✅ Client healthy: http://127.0.0.1:${APP_PORT}/health"
    docker compose ps
    exit 0
  fi
  sleep 2
done

echo "❌ Client did not become healthy. Last logs:" >&2
docker compose logs --tail=80 >&2
exit 1
