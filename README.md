
setup steps
1. uv init
2. uv venv
3. source .venv/bin/activate
4. uv add pika 
5. uv add pika requests 
6. uv add pika python-dotenv

### run on local PC
1. uv run mcp-client/client.py
2. uv run python -m mcp-server.server
3. uv run ollama_api.py


📚 Next Steps
Once this works, you can:


Add PostgreSQL instead of JSON file

Dockerize everything with docker-compose

Add Ollama for natural language processing

Build a web frontend
