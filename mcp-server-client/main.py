# backend/app/main.py
from contextlib import asynccontextmanager
from operator import index
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mcp_client.client import \
    EnergyMCPAgent  # Adjust import if your path is different

# Global agent instance
agent: Optional[EnergyMCPAgent] = None


# Lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    # Startup
    print("🚀 Starting Energy MCP Agent...")
    agent = EnergyMCPAgent()
    await agent.connect()
    print("✅ Energy MCP Agent + MCP Server connected successfully")
    yield
    # Shutdown
    if agent:
        await agent.close()
    print("👋 Energy MCP Agent shutdown")


app = FastAPI(title="Energy MCP Agent API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict]] = None


class ChatResponse(BaseModel):
    content: str
    toolCalls: Optional[List[Dict]] = None


class HealthResponse(BaseModel):
    status: str
    agent_ready: bool
    mcp_server_connected: bool
    available_tools: List[str]
    message: str


# ====================== MAIN ENDPOINTS ======================


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not agent:
        raise HTTPException(status_code=503, detail="Agent is not initialized yet")

    try:
        final_content = await agent.chat(request.message)

        return ChatResponse(
            content=final_content,
            toolCalls=[],  # TODO: Enhance later to return actual tool calls
        )

    except Exception as e:
        print(f"Error in /chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health", response_model=HealthResponse)
async def health():
    """Detailed health check with tools list"""
    if not agent:
        return HealthResponse(
            status="unhealthy",
            agent_ready=False,
            mcp_server_connected=False,
            available_tools=[],
            message="Agent not initialized",
        )

    try:
        # Get list of tools from the agent
        tool_names = [tool["function"]["name"] for tool in agent.ollama_tools]
        # or alternatively: [t.name for t in agent.tools] if you have raw tools

        return HealthResponse(
            status="healthy",
            agent_ready=True,
            mcp_server_connected=True,
            available_tools=tool_names,
            message="All systems operational",
        )
    except Exception as e:
        return HealthResponse(
            status="degraded",
            agent_ready=True,
            mcp_server_connected=False,
            available_tools=[],
            message=f"Partial failure: {str(e)}",
        )


@app.get("/tools")
async def list_tools():
    """Return all available MCP tools"""
    if not agent or not hasattr(agent, "ollama_tools"):
        return {"tools": [], "count": 0, "message": "Agent not ready"}

    tools_list = [
        {
            "index": idx,
            "name": tool["function"]["name"],
            "description": tool["function"].get("description", ""),
        }
        for idx, tool in enumerate(agent.ollama_tools)
    ]
    return {
        "tools": tools_list,
        "count": len(tools_list),
        "message": "Available tools from MCP server",
    }


@app.post("/clear_history")
async def clear_history():
    """Detailed clear history"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent is not initialized yet")
    try:
        return await agent.clear_all_history()
    except Exception as e:
        print(f"Error in /clearHistory endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Optional: Simple root endpoint
@app.get("/")
async def root():
    return {
        "name": "Energy MCP Agent API",
        "version": "1.0",
        "endpoints": ["/chat", "/health", "/tools"],
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
