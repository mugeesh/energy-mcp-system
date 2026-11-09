# backend/app/main.py
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
import os
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import logging
from mcp_client.client import EnergyMCPAgent


# Global agent instance
agent: Optional[EnergyMCPAgent] = None


# Lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    # Startup
    print("🚀 Starting IAM MCP Agent...")
    agent = EnergyMCPAgent()
    await agent.connect()
    print("✅ IAM MCP Agent + MCP Server connected successfully")
    yield
    # Shutdown
    if agent:
        await agent.close()
    print("👋 IAM MCP Agent shutdown")


app = FastAPI(title="IAM MCP Agent API", lifespan=lifespan)

# CORS — comma-separated override via CORS_ALLOW_ORIGINS
_allow_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
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
async def chat(payload: ChatRequest, request: Request):
    if not agent:
        raise HTTPException(status_code=503, detail="Agent is not initialized yet")

    try:
        # Robust Bearer token extraction
        auth_header = request.headers.get("Authorization", "")
        jwt_token = None
        if auth_header.startswith("Bearer "):
            jwt_token = auth_header[7:].strip()
        elif auth_header:
            jwt_token = auth_header.strip()

        if not jwt_token:
            raise HTTPException(
                status_code=401,
                detail="Missing Authorization header. Send 'Authorization: Bearer <token>'.",
            )

        logging.info("Received request with token (length: %d)", len(jwt_token))

        final_content = await agent.chat(
            user_query=payload.message,
            history=payload.history,
            token=jwt_token
        )

        return ChatResponse(
            content=final_content,
            toolCalls=[]
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in /chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
        tool_names = [tool["function"]["name"] for tool in agent.tools]

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
    if not agent or not hasattr(agent, "tools"):
        return {"tools": [], "count": 0, "message": "Agent not ready"}

    tools_list = [
        {
            "index": idx,
            "name": tool["function"]["name"],
            "description": tool["function"].get("description", ""),
        }
        for idx, tool in enumerate(agent.tools)
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
        "name": "IAM MCP Agent API",
        "version": "1.0",
        "endpoints": ["/chat", "/health", "/tools"],
        "status": "running",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
