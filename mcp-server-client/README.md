setup steps

1. uv init
2. uv venv
3. source .venv/bin/activate
4. uv add pika
5. uv add pika requests
6. uv add pika python-dotenv
7. uv add mcp ollama
8. uv add fastapi
7. uv sync

### run on local PC

1. uv run mcp-client/client.py
2. uv run python -m mcp-server.server
3. uv run ollama_api.py

###TEST


📚 Next Steps
Once this works, you can:

Add PostgreSQL instead of JSON file

Dockerize everything with docker-compose

Add Ollama for natural language processing

Build a web frontend

#### curser Apps

# MCP

on visual studio code

```
{
    "servers": {
        "energy-mcp": {
            "command": "/usr/local/bin/uv",
            "args": [
                "--directory",
                "/Users/mugeesh/git2/POC/MCP/energy-mcp-system/mcp-server",
                "run",
                "server.py"
            ],
            "env": {
                "LOG_LEVEL": "debug"
            }
        }
    }
}
check logs
cd /Users/mugeesh/Library/Application Support/Code/logs/20260409T151803/window8
tail -f mcpServer.mcp.config.usrlocal.energy-mcp.log

```
```
{
  "mcpServers": {
    "energy-mcp": {
      "command": "/usr/local/bin/uv",
      "args": [
        "--directory",
        "/Users/mugeesh/git2/POC/MCP/energy-mcp-system/mcp-server",
        "run",
        "server.py"
      ]
    }
  }
}
```
# check logs
```/Users/mugeesh/Library/Application Support/Cursor/logs/20260411T113943/window3/exthost/anysphere.cursor-mcp```


### set ENV
```
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASS=password123
TIKA_SERVER_URL=http://localhost:9998
MY_API_KEY=sk-abc123xyz
# IAM
iam_username=
iam_password=
iam_url=
# ts api
ts_api_url=

```
