#!/usr/bin/env python3
"""
Site Manager - Handles site mapping and energy consumption API calls
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Add parent directory to path so clients module can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from clients
from clients.iam_client import IAMClient
from clients.ts_api import TSApi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SiteLookUp:
    def __init__(self):
        self.sites_cache = None
        self.site_lookup = {}
        self.last_fetch = None
        self.iam_client = IAMClient()
        self.ts_api = TSApi(self.iam_client.token)
        self.load_sites()

    def load_sites(self, force_refresh=False):
        """Load all sites from Energybox API"""
        if self.sites_cache and not force_refresh:
            return self.sites_cache

        try:
            logger.info("Fetching sites from Energybox API...")
            response = self.iam_client.get_all_sites()
            self.sites_cache = response.json()
            # Build lookup dictionary
            self.site_lookup = {}
            for site in self.sites_cache:
                site_id = str(site["id"])
                site_title = site["title"].lower()

                # Add title mapping
                self.site_lookup[site_title] = site_id

                # Add partial matches for common variations
                words = site_title.split()
                for word in words:
                    if len(word) > 3:  # Only meaningful words
                        self.site_lookup[word] = site_id

                # Add ID mapping directly
                self.site_lookup[site_id] = site_id

            self.last_fetch = datetime.now()
            logger.info(f"Loaded {len(self.sites_cache)} sites")
            return self.sites_cache

        except Exception as e:
            logger.error(f"Failed to load sites: {e}")
            raise

    def find_site_id(self, site_name: str) -> Optional[str]:
        """Find site ID by name or title"""
        if not self.sites_cache:
            self.load_sites()

        site_name_lower = site_name.lower().strip()

        # Try exact match first
        if site_name_lower in self.site_lookup:
            return self.site_lookup[site_name_lower]

        # Try partial match
        for title, site_id in self.site_lookup.items():
            if site_name_lower in title or title in site_name_lower:
                return site_id

        # Try to match by ID if numeric
        if site_name.isdigit():
            return site_name

        return None

    def get_site_details(self, site_id: str) -> Optional[Dict]:
        """Get detailed information for a specific site"""
        if not self.sites_cache:
            self.load_sites()

        for site in self.sites_cache:
            if str(site["id"]) == str(site_id):
                return site
        return None

    def get_energy_consumption(
        self, site_id: str, from_date: str, to_date: str
    ) -> Dict:
        """
        Get energy consumption for a site between dates

        Args:
            site_id: Site ID
            from_date: Start date (ISO format)
            to_date: End date (ISO format)

        Returns:
            Energy consumption data
        """
        try:
            response = self.ts_api.get_energy_consumption_by_site_id(
                site_id, from_date, to_date
            )
            data = response.json()
            return {
                "energy": data["energy"],
                "unit": "kWh",
            }

        except Exception as e:
            logger.error(f"Failed to get energy consumption: {e}")
            return {"error": str(e), "site_id": site_id}

    def parse_date_range(self, day_input: Any) -> Dict:
        # 1. Capture "now" and strip microseconds immediately
        now = datetime.now().replace(microsecond=0)

        try:
            days = int(day_input)
        except ValueError as TypeError:
            days = 7

        if days <= 0:
            days = 7

        # 2. Calculate Start Date (00:00:00)
        from_date = (now - timedelta(days=days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # 3. Use the clean 'now' for the to_date
        to_date = now

        return {
            "from": from_date.isoformat() + "Z",
            "to": to_date.isoformat() + "Z",
            "description": f"last {days} days",
        }

    def list_all_sites(self) -> List[Dict]:
        """Return list of all sites with basic info"""
        if not self.sites_cache:
            self.load_sites()

        return [
            {
                "id": site["id"],
                "title": site["title"],
                "city": site.get("city", "N/A"),
                "country": site.get("country", "N/A"),
                "status": site.get("siteInstallationStatus", "UNKNOWN"),
            }
            for site in self.sites_cache
        ]


if __name__ == "__main__":
    # Test the site manager
    sm = SiteLookUp()
    print("Testing Site Manager...")

    # List sites
    sites = sm.list_all_sites()
    print(f"\nFound {len(sites)} sites:")
    for site in sites[:5]:  # Show first 5
        print(f"  - {site['title']} (ID: {site['id']})")

    # Test finding a site
    test_site = "E2E Validation-flagged-breakers"
    site_id = sm.find_site_id(test_site)
    print(f"\nLooking for '{test_site}': Found ID {site_id}")

    # Test date parsing
    date_range = sm.parse_date_range("last 7 days")
    print(f"\nDate range: {date_range}")
