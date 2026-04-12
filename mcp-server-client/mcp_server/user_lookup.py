#!/usr/bin/env python3
"""
user Manager - Handles user mapping and energy consumption API calls
"""

import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path so clients module can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from clients
from clients.iam_client import IAMClient
from clients.ts_api import TSApi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserLookUp:
    def __init__(self):
        self.last_fetch = None
        self.users_cache = None
        self.user_lookup = {}
        self.iam_client = IAMClient()
        self.ts_api = TSApi(self.iam_client.token)
        self.load_users()

    def load_users(self, force_refresh=False):
        """Load all users from Energybox API"""
        if self.users_cache and not force_refresh:
            return self.users_cache

        try:
            logger.info("Fetching users from Energybox API...")
            response = self.iam_client.get_all_users()
            self.users_cache = response.json()
            # Build lookup dictionary
            self.user_lookup = {}
            for eb_user in self.users_cache:
                user_id = str(eb_user["id"])
                user_full_name = (
                    eb_user["firstName"].lower() + " " + eb_user["lastName"].lower()
                )

                # Add name mapping
                self.user_lookup[user_full_name] = user_id

                # Add partial matches for common variations
                words = user_full_name.split()
                for word in words:
                    if len(word) > 3:  # Only meaningful words
                        self.user_lookup[word] = user_id

                # Add ID mapping directly
                self.user_lookup[user_id] = user_id

            self.last_fetch = datetime.now()
            logger.info(f"Loaded {len(self.users_cache)} users")
            return self.users_cache

        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            raise

    def find_user_id(self, username: str) -> Optional[str]:
        """Find user ID by name or title"""
        if not self.users_cache:
            self.load_users()

        username_lower = username.lower().strip()

        # Try exact match first
        if username_lower in self.user_lookup:
            return self.user_lookup[username_lower]

        # Try partial match
        for title, user_id in self.user_lookup.items():
            if username_lower in title or title in username_lower:
                return eb_user_id

        # Try to match by ID if numeric
        if username.isdigit():
            return username

        return None

    def get_user_details(self, user_id: str) -> Optional[Dict]:
        """Get detailed information for a specific user"""
        if not self.users_cache:
            self.load_users()

        for user in self.users_cache:
            if str(user["id"]) == str(user_id):
                return user
        return None

    def list_all_users(self) -> List[Dict]:
        """Return list of all users with basic info"""
        if not self.users_cache:
            self.load_users()

        return [
            {
                "id": user["id"],
                "name": user["firstName"] + " " + user["lastName"],
                "email": user.get("email", "N/A"),
                "position": user.get("position", "N/A"),
                "contacts": user.get("contacts", "N/A"),
                "role": user.get("role", "N/A"),
                "lastLoginAt": user.get(
                    "lastLoginAt", "UNKNOWN"
                ),  #'2022-02-07T07:46:27.673Z'
            }
            for user in self.users_cache
        ]


if __name__ == "__main__":
    # Test the user manager
    sm = UserLookUp()
    print("Testing user Manager...")

    # List users
    users = sm.list_all_users()
    print(f"\nFound {len(users)} users:")
    for user_info in users[:5]:  # Show first 5
        print(
            f"  - {user_info['name']} (ID: {user_info['id']})  (email: {user_info['email']})  (role: {user_info['role']})"
        )

    # Test finding a user
    test_user = "Mugeesh Husain"
    eb_user_id = sm.find_user_id(test_user)
    print(f"\nLooking for '{test_user}': Found ID {eb_user_id}")
