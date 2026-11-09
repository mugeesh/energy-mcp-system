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

# --- Preflight: the host bootstrap runs only on first boot ------------------
# If cloud-init failed (or the instance predates the bootstrap), Docker will be
# missing here and `docker compose up` fails with a cryptic error.
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Docker is not installed on this host." >&2
  echo "   user_data/cloud-init only runs on first boot. Install it with:" >&2
  echo "     sudo bash $(pwd)/deploy/user_data.sh" >&2
  echo "   Then log out and back in (so the 'docker' group applies) and re-run this script." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "❌ The Docker Compose plugin is missing." >&2
  echo "   Install it with: sudo bash $(pwd)/deploy/user_data.sh" >&2
  exit 1
fi

# Compose v5 shells out to buildx for `compose build`; AL2023's bundled buildx
# (0.12) is too old and fails with "requires buildx 0.17.0 or later".
if ! docker buildx version >/dev/null 2>&1; then
  echo "❌ The Docker buildx plugin is missing." >&2
  echo "   Install it with: sudo bash $(pwd)/deploy/user_data.sh" >&2
  exit 1
fi

buildx_version="$(docker buildx version 2>/dev/null | sed -n 's/.*buildx v\{0,1\}\([0-9][0-9]*\)\.\([0-9][0-9]*\).*/\1.\2/p' | head -n1)"
if [ -z "$buildx_version" ]; then
  echo "❌ Could not determine the buildx version." >&2
  echo "   Reinstall it with: sudo bash $(pwd)/deploy/user_data.sh" >&2
  exit 1
fi
bx_major="${buildx_version%%.*}"
bx_minor="${buildx_version#*.}"
if [ "$bx_major" -eq 0 ] && [ "$bx_minor" -lt 17 ]; then
  echo "❌ buildx ${buildx_version} is too old; Compose v5 needs >= 0.17.0." >&2
  echo "   Upgrade it with: sudo bash $(pwd)/deploy/user_data.sh" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "❌ Cannot talk to the Docker daemon." >&2
  echo "   Log out and back in after the install so your user joins the 'docker' group," >&2
  echo "   or run: sudo usermod -aG docker \$USER && newgrp docker" >&2
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
