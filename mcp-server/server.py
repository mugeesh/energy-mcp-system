#!/usr/bin/env python3
import logging
import os
import sys
from typing import Any, Dict, Optional, List
from site_lookup import SiteLookUp
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from mcp.server.fastmcp import FastMCP

# --- Configuration & Logging ---
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "energy_request_queue")
SITE_MAPPING_FILE = "site_mapping.json"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("EnergyMCPServer")

mcp = FastMCP(
    name="Energy MCP"
)

site_lookup: Optional[SiteLookUp] = None

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
def get_energy_consumption(site_identifier: str, days: int = 7) -> Dict[str, Any]:
    """Get energy consumption for a site.
    Args:
        site_identifier: Site name (e.g. "E2E Validation-flagged-breakers", "Mugeesh Site") OR site ID
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
def get_site_details(site_identifier: str) -> Dict:
    """Get full details of a site (city, country, status, etc.)."""
    sm = get_site_lookup()
    site_id = sm.find_site_id(site_identifier)
    if not site_id:
        return {"error": "Site not found"}
    return sm.get_site_details(site_id) or {"error": "Details not available"}

def main():
    logger.info("🚀 Starting Energy MCP Server (stdio transport)")
    mcp.run(transport="stdio")   # This is the standard for Claude Desktop


if __name__ == "__main__":
    main()
