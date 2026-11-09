#!/usr/bin/env python3
"""
IAM / Energy MCP Agent backed by DeepSeek.

- Connects to the MCP server over stdio (default) or streamable HTTP
- Uses DeepSeek's OpenAI-compatible chat completions API for tool calling
- Injects the caller's JWT into MCP tool calls on the backend (never shown to the LLM)
- Keeps each /chat request stateless
"""

import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult
from openai import AsyncOpenAI

load_dotenv()

# ========================= CONFIG =========================
_PROJECT_ROOT = Path(__file__).resolve().parents[1]

# MCP transport: "stdio" (spawn server.py locally) or "streamable-http" (URL).
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH", str(_PROJECT_ROOT / "mcp_server"))
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")

# DeepSeek (OpenAI-compatible API)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2"))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("IAMMCPAgent")


class EnergyMCPAgent:
    """MCP + DeepSeek agent (kept as ``EnergyMCPAgent`` for API compatibility)."""

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools: List[Dict] = []
        self.messages: List[Dict] = []
        self._connected = False
        self.current_token: Optional[str] = None
        self.max_history = int(os.getenv("MCP_MAX_HISTORY", 12))
        self._llm: Optional[AsyncOpenAI] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------
    def _llm_client(self) -> AsyncOpenAI:
        if self._llm is None:
            if not DEEPSEEK_API_KEY:
                raise RuntimeError(
                    "DEEPSEEK_API_KEY is not set. Add it to the environment or .env file."
                )
            self._llm = AsyncOpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
        return self._llm

    # ------------------------------------------------------------------
    # MCP connection
    # ------------------------------------------------------------------
    async def connect(self) -> None:
        """Connect to the MCP server and load its tools."""
        if self._connected:
            return

        logger.info("🔌 Connecting to MCP Server (%s)...", MCP_TRANSPORT)
        read, write = await self._open_transport()

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.session.initialize()

        tools_response = await self.session.list_tools()
        self.tools = [self._mcp_tool_to_openai(t) for t in tools_response.tools]

        self._connected = True
        logger.info("✅ Connected. Loaded %d MCP tools.", len(self.tools))

    async def _open_transport(self):
        """Return (read, write) for the configured MCP transport."""
        if MCP_TRANSPORT in {"http", "streamable-http", "streamable_http"}:
            from mcp.client.streamable_http import streamablehttp_client

            transport = await self.exit_stack.enter_async_context(
                streamablehttp_client(MCP_SERVER_URL)
            )
            # streamablehttp_client yields (read, write, get_session_id)
            return transport[0], transport[1]

        process_env = os.environ.copy()
        if self.current_token:
            process_env["AUTH_TOKEN"] = self.current_token

        server_params = StdioServerParameters(
            command=os.getenv("MCP_SERVER_COMMAND", "uv"),
            args=["--directory", MCP_SERVER_PATH, "run", "server.py"],
            env=process_env,
        )
        return await self.exit_stack.enter_async_context(stdio_client(server_params))

    def _mcp_tool_to_openai(self, mcp_tool) -> Dict:
        """Convert an MCP tool into an OpenAI/DeepSeek function schema.

        ``auth_token`` is deliberately hidden from the LLM; it is injected on the
        backend for every tool call.
        """
        schema = {
            "type": "function",
            "function": {
                "name": mcp_tool.name,
                "description": mcp_tool.description
                or f"Execute the {mcp_tool.name} tool",
                "parameters": mcp_tool.inputSchema
                or {"type": "object", "properties": {}, "required": []},
            },
        }
        params = schema["function"].get("parameters", {})
        properties = params.get("properties", {})
        required = params.get("required", [])

        if "auth_token" in properties:
            del properties["auth_token"]
        if "auth_token" in required:
            required.remove("auth_token")
        return schema

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute an MCP tool and return a clean Python/JSON result."""
        if not self.session:
            await self.connect()

        try:
            result: CallToolResult = await self.session.call_tool(
                name=tool_name, arguments=arguments
            )

            if result.structuredContent:
                return (
                    result.structuredContent.get("result")
                    or result.structuredContent
                )

            if result.content:
                texts = [
                    block.text.strip()
                    for block in result.content
                    if hasattr(block, "text") and block.text
                ]
                if len(texts) == 1:
                    try:
                        return json.loads(texts[0])
                    except (json.JSONDecodeError, TypeError):
                        return texts[0]
                return [
                    json.loads(text) if text.startswith("{") else text
                    for text in texts
                ]
            return None

        except Exception as exc:  # noqa: BLE001 - surface error to the LLM
            logger.error("Tool call failed [%s]: %s", tool_name, exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    async def chat(
        self,
        user_query: str,
        history: Optional[List[Dict]] = None,
        token: Optional[str] = None,
    ) -> str:
        """Per-request stateless chat — no global history pollution."""
        self.current_token = token

        if not self._connected:
            await self.connect()

        messages: List[Dict] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful IAM and energy data assistant. "
                    "Use the available tools to answer questions about sites, "
                    "energy consumption and users. "
                    "Be concise, accurate, and professional. "
                    "If you need information, call the appropriate tool."
                ),
            }
        ]

        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_query})
        self._trim_history(messages)

        max_steps = int(os.getenv("MCP_MAX_STEPS", 8))
        llm = self._llm_client()

        for step in range(max_steps):
            logger.info("Thinking (step %d)...", step + 1)

            response = await llm.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=messages,
                tools=self.tools or None,
                temperature=DEEPSEEK_TEMPERATURE,
            )
            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            assistant_message: Dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
            }
            if tool_calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ]
            messages.append(assistant_message)

            if not tool_calls:
                final_content = message.content or "No response generated."
                logger.debug("✅ Final Answer:\n%s", final_content)
                return final_content

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except (json.JSONDecodeError, TypeError):
                    arguments = {}
                if not isinstance(arguments, dict):
                    arguments = {}

                # Secure token injection: the LLM never sees or supplies this.
                tool_arguments = dict(arguments)
                if token:
                    tool_arguments["auth_token"] = token

                logger.info("   → Calling tool: %s", tool_name)
                tool_result = await self._call_tool(tool_name, tool_arguments)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False),
                    }
                )

        logger.warning("⚠️ Max steps reached.")
        return "Sorry, I couldn't complete the request after multiple steps."

    def _trim_history(self, messages: List[Dict]) -> None:
        """Trim in-place: keep the system prompt plus recent messages."""
        if len(messages) <= self.max_history:
            return

        system_prompt = next(
            (msg for msg in messages if msg.get("role") == "system"), None
        )
        if system_prompt is None:
            system_prompt = {"role": "system", "content": "You are a helpful assistant."}

        messages[:] = [system_prompt] + messages[-(self.max_history - 1):]
        logger.debug("History trimmed to %d messages", len(messages))

    async def clear_all_history(self) -> Dict[str, Any]:
        """No-op kept for API compatibility.

        Chat history is supplied by the client on every request, so the agent
        holds no conversation state to clear.
        """
        self.messages.clear()
        return {"status": "Done", "cleared": 0}

    async def close(self) -> None:
        """Clean shutdown."""
        if self.exit_stack:
            await self.exit_stack.aclose()
        if self._llm is not None:
            await self._llm.close()
        self._connected = False
        logger.info("👋 IAM MCP Agent shutdown.")


# ====================== Interactive Mode ======================
async def main():
    async with EnergyMCPAgent() as agent:
        print("\n" + "═" * 80)
        print("⚡ IAM / ENERGY AI AGENT  →  DeepSeek + MCP")
        print("═" * 80)
        print("Examples:")
        print("   • List all sites")
        print("   • Show energy for Mugeesh Site last 10 days")
        print("   • Who is mugeesh husain?")
        print("Type 'quit' to exit.\n")

        while True:
            try:
                query = input("You: ").strip()
                if query.lower() in ["quit", "exit", "bye", "q"]:
                    break
                if query:
                    reply = await agent.chat(query, token=os.getenv("AUTH_TOKEN"))
                    print("\nAssistant:", reply, "\n")
            except KeyboardInterrupt:
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("Error: %s", exc, exc_info=True)

    print("\nGoodbye!")


if __name__ == "__main__":
    asyncio.run(main())
