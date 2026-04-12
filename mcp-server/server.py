#!/usr/bin/env python3
import logging
import os
import sys
from typing import Any, Dict, Optional, List
from site_lookup import SiteLookUp
from user_lookup import UserLookUp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Constants
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "energy_request_queue")

# Production logging format
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/Users/mugeesh/git2/POC/MCP/energy-mcp-system/server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("EnergyMCPServer")

mcp = FastMCP(name="Energy MCP Production Ready")
site_lookup: Optional[SiteLookUp] = None
user_lookup: Optional[UserLookUp] = None


def get_site_lookup() -> SiteLookUp:
    """Lazy initialization so the server starts instantly."""
    global site_lookup
    if site_lookup is None:
        logger.info("Initializing SiteLookUp...")
        site_lookup = SiteLookUp()
    return site_lookup


@mcp.tool()
def list_all_sites() -> List[Dict]:
    """Return all available Energybox sites with basic info.
    Use this when the user asks to see all sites or doesn't know the exact name."""
    sm = get_site_lookup()
    return sm.list_all_sites()


@mcp.tool()
def search_sites(query: str) -> List[Dict]:
    """Search for sites by name, partial name, or ID.
    Returns matching sites with title and ID. Use when the exact site name is unclear."""
    sm = get_site_lookup()
    sites = sm.list_all_sites()
    query = query.lower().strip()

    matches = []
    for site in sites:
        title = site["title"].lower()
        if query in title or site["id"] == query:
            matches.append(site)
    logger.debug(f'site match :{matches}')
    return matches


@mcp.tool()
def get_site_details(site_identifier: str) -> Dict:
    """Get full details of a site (city, country, status, etc.)."""
    sm = get_site_lookup()
    site_id = sm.find_site_id(site_identifier)
    if not site_id:
        return {"error": "Site not found"}
    return sm.get_site_details(site_id) or {"error": "Details not available"}


@mcp.tool()
def get_energy_consumption(site_identifier: str, days: int = 7) -> Dict[str, Any]:
    """Get energy consumption for a site.
    Args:
        site_identifier: Site name (e.g. "Marcus Test", "Mugeesh Site") OR site ID
        days: Number of days to look back (default 7). Use 0 for today only.
    """
    sm = get_site_lookup()

    # Use your existing smart lookup
    site_id = sm.find_site_id(site_identifier)
    if not site_id:
        return {
            "error": f"Site '{site_identifier}' not found. Try list_all_sites() or search_sites() first."
        }

    site_info = sm.get_site_details(site_id)
    if not site_info:
        return {"error": "Site details not found"}

    date_filter = sm.parse_date_range(days)
    energy_data = sm.get_energy_consumption(
        site_id=site_id,
        from_date=date_filter["from"],
        to_date=date_filter["to"]
    )

    return {
        "site_title": site_info["title"],
        "site_id": site_id,
        "period": date_filter["description"],
        "data": energy_data,
    }




@mcp.tool()
def list_all_users() -> List[Dict]:
    """Return all available Energybox users with basic info.
    Use this when the user asks to see all sites or doesn't know the exact name."""
    sm = get_user_lookup()
    return sm.list_all_users()


@mcp.tool()
def search_users(query: str) -> List[Dict]:
    """Search for users by name, partial name, or ID.
    Returns matching users with name and ID. Use when the exact name is unclear."""
    sm = get_user_lookup()
    users = sm.list_all_users()
    query = query.lower().strip()

    matches = []
    for user in users:
        name = user["name"].lower()
        if query in name or user["id"] == query:
            matches.append(user)
    logger.debug(f'user match :{matches}')
    return matches


@mcp.tool()
def get_user_details(user_identifier: str) -> Dict:
    """Get full details of a user (name, email, position, contacts , role etc.)."""
    user_memory = get_user_lookup()
    site_id = user_memory.find_user_id(user_identifier)
    if not site_id:
        return {"error": "User not found"}
    return user_memory.get_user_details(site_id) or {"error": "Details not available"}

def get_user_lookup() -> UserLookUp:
    """Lazy initialization so the server starts instantly."""
    global user_lookup
    if user_lookup is None:
        logger.info("Initializing UserLookUp...")
        user_lookup = UserLookUp()
    return user_lookup



def main():
    # Initialize and run the server
    logger.info("🚀 Starting Energy MCP Server (stdio transport)")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
