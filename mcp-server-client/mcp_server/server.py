#!/usr/bin/env python3
"""IAM / Energy MCP server.

Exposes site, energy-consumption and user lookups over MCP.

Transport is selected with ``MCP_TRANSPORT``:
  - ``stdio`` (default): spawn with ``uv run server.py`` (local MCP clients)
  - ``streamable-http``: serve ``/mcp`` for Docker / remote clients

The server never holds a shared user token. Every tool accepts an optional
``auth_token`` argument (injected by the client on the backend) and falls back
to the IAM username/password login only when no token is supplied.
"""

import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from site_lookup import SiteLookUp
from user_lookup import UserLookUp

# Load the project-root .env when run directly (Docker supplies env instead).
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
MCP_HTTP_HOST = os.getenv("MCP_HTTP_HOST", "0.0.0.0")
MCP_HTTP_PORT = int(os.getenv("MCP_HTTP_PORT", "8001"))
MCP_HTTP_PATH = os.getenv("MCP_HTTP_PATH", "/mcp")
MCP_STATELESS_HTTP = os.getenv("MCP_STATELESS_HTTP", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# stdio uses stdout for the MCP protocol, so logs go to stderr + a file.
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("server.log"), logging.StreamHandler()],
)
logger = logging.getLogger("IAMMCPServer")

mcp = FastMCP(
    name="IAM MCP Production Ready",
    host=MCP_HTTP_HOST,
    port=MCP_HTTP_PORT,
    streamable_http_path=MCP_HTTP_PATH,
    stateless_http=MCP_STATELESS_HTTP,
)

# Cache one lookup object per caller token so users never share API sessions.
_site_lookups: Dict[str, SiteLookUp] = {}
_user_lookups: Dict[str, UserLookUp] = {}


def _resolve_token(auth_token: Optional[str]) -> Optional[str]:
    """Per-request token wins; AUTH_TOKEN is a local stdio fallback only."""
    token = (auth_token or os.getenv("AUTH_TOKEN") or "").strip()
    return token or None


def _cache_key(auth_token: Optional[str]) -> str:
    return auth_token.strip() if auth_token else "__default__"


def _token_fingerprint(key: str) -> str:
    """Non-reversible token id, safe to log."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def get_site_lookup(auth_token: Optional[str] = None) -> SiteLookUp:
    """Lazy, per-token initialization so the server starts instantly."""
    auth_token = _resolve_token(auth_token)
    key = _cache_key(auth_token)
    if key not in _site_lookups:
        logger.info("Initializing SiteLookUp for token %s", _token_fingerprint(key))
        _site_lookups[key] = SiteLookUp(auth_token)
    return _site_lookups[key]


def get_user_lookup(auth_token: Optional[str] = None) -> UserLookUp:
    """Lazy, per-token initialization so the server starts instantly."""
    auth_token = _resolve_token(auth_token)
    key = _cache_key(auth_token)
    if key not in _user_lookups:
        logger.info("Initializing UserLookUp for token %s", _token_fingerprint(key))
        _user_lookups[key] = UserLookUp(auth_token)
    return _user_lookups[key]


# ---------------------------------------------------------------------------
# Site tools
# ---------------------------------------------------------------------------
@mcp.tool()
def list_all_sites(auth_token: Optional[str] = None) -> List[Dict]:
    """Return all available Energybox sites with basic info.

    Use this when the user asks to see all sites or doesn't know the exact name.
    """
    sm = get_site_lookup(auth_token)
    return sm.list_all_sites()


@mcp.tool()
def search_sites(query: str, auth_token: Optional[str] = None) -> List[Dict]:
    """Search for sites by name, partial name, or ID.

    Returns matching sites with title and ID. Use when the exact site name is
    unclear.
    """
    sm = get_site_lookup(auth_token)
    sites = sm.list_all_sites()
    query = query.lower().strip()

    matches = []
    for site in sites:
        title = site["title"].lower()
        if query in title or str(site["id"]) == query:
            matches.append(site)
    logger.debug("site match: %s", matches)
    return matches


@mcp.tool()
def get_site_details(
    site_identifier: str, auth_token: Optional[str] = None
) -> Dict:
    """Get full details of a site (city, country, status, etc.)."""
    sm = get_site_lookup(auth_token)
    site_id = sm.find_site_id(site_identifier)
    if not site_id:
        return {"error": "Site not found"}
    return sm.get_site_details(site_id) or {"error": "Details not available"}


@mcp.tool()
def get_energy_consumption(
    site_identifier: str,
    days: int = 7,
    auth_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Get energy consumption for a site.

    Args:
        site_identifier: Site name (e.g. "Marcus Test", "Mugeesh Site") OR site ID
        days: Number of days to look back (default 7).
        auth_token: Injected by the backend, never supplied by the LLM.
    """
    sm = get_site_lookup(auth_token)

    site_id = sm.find_site_id(site_identifier)
    if not site_id:
        return {
            "error": (
                f"Site '{site_identifier}' not found. "
                "Try list_all_sites() or search_sites() first."
            )
        }

    site_info = sm.get_site_details(site_id)
    if not site_info:
        return {"error": "Site details not found"}

    date_filter = sm.parse_date_range(days)
    energy_data = sm.get_energy_consumption(
        site_id=site_id,
        from_date=date_filter["from"],
        to_date=date_filter["to"],
    )

    return {
        "site_title": site_info["title"],
        "site_id": site_id,
        "period": date_filter["description"],
        "data": energy_data,
    }


# ---------------------------------------------------------------------------
# User tools
# ---------------------------------------------------------------------------
@mcp.tool()
def list_all_users(auth_token: Optional[str] = None) -> List[Dict]:
    """Return all available Energybox users with basic info."""
    sm = get_user_lookup(auth_token)
    return sm.list_all_users()


@mcp.tool()
def search_users(query: str, auth_token: Optional[str] = None) -> List[Dict]:
    """Search for users by name, partial name, or ID.

    Returns matching users with name and ID. Use when the exact name is unclear.
    """
    sm = get_user_lookup(auth_token)
    users = sm.list_all_users()
    query = query.lower().strip()

    matches = []
    for user in users:
        name = user["name"].lower()
        if query in name or str(user["id"]) == query:
            matches.append(user)
    logger.debug("user match: %s", matches)
    return matches


@mcp.tool()
def get_user_details(
    user_identifier: str, auth_token: Optional[str] = None
) -> Dict:
    """Get full details of a user (name, email, position, contacts, role, etc.)."""
    user_memory = get_user_lookup(auth_token)
    user_id = user_memory.find_user_id(user_identifier)
    if not user_id:
        return {"error": "User not found"}
    return user_memory.get_user_details(user_id) or {"error": "Details not available"}


def main():
    logger.info("🚀 Starting IAM MCP Server (transport=%s)", MCP_TRANSPORT)
    if MCP_TRANSPORT in {"http", "streamable-http", "streamable_http"}:
        logger.info(
            "MCP endpoint: http://%s:%s%s",
            MCP_HTTP_HOST,
            MCP_HTTP_PORT,
            MCP_HTTP_PATH,
        )
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
