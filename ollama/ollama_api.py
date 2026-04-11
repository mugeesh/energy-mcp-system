#!/usr/bin/env python3
"""
Site Manager - Handles site mapping and energy consumption API calls
"""

import json
import logging
import os
import sys

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OllamaAPI:
    def __init__(self):
        self.sites_cache = None
        self.site_lookup = {}
        self.ollama_url = "http://127.0.0.1:11434/api/generate"
        self.model = "qwen3:1.7b"

    def get_ai_extraction(self, query: str, site_list: str):
        """
        Extract site name and date range from a natural language query
        """
        prompt = f"""
            [CONTEXT]
            You are an assistant that matches energy queries to a specific site list.
            VALID SITES: {site_list}
    
            [RULES]
            1. Identify the site ID from the VALID SITES list that matches the Query.
            2. DATE LOGIC: 
               - Convert "weeks" to days (e.g., 2 weeks = 14).
               - Extract "days" as numbers.
               - If no date is mentioned, return "0".
            3. OUTPUT ONLY VALID JSON. No explanation.
    
            [QUERY]
            "{query}"
    
            [JSON STRUCTURE]
            {{
                "site_id": "number",
                "day": "number"
            }}
            """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0,
            "top_p": 0.9,
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=45)
            response.raise_for_status()

            # 1. Get the raw string
            raw_content = response.json().get("response", "").strip()

            if not raw_content:
                logger.error(
                    "AI returned an empty string. Context limit might be reached."
                )
                return {"site_id": "-1", "day": "-1"}
            extracted_json = json.loads(raw_content)
            return {
                "site_id": str(extracted_json.get("site_id", "-1")),
                "day": str(extracted_json.get("day", "-1")),
            }
        except Exception as e:
            logger.error(f"API Request failed: {e}")
            return {"site_id": -1, "day": "-1"}


# Test with your specific query
if __name__ == "__main__":
    ollama_api = OllamaAPI()

    # Test queries
    test_queries = [
        "can you give energy consumption for the site E2E Validation-flagged-breakers  site last 8 days",
        "energy consumption of this site Mugeesh Site last 7 days",
        "give me energy consumption of Mugeesh Site",
        "here is the sitename myrat, give me energy consumption",
        "here is the site Nashville Quality  energy",
        "can you give me the energy consumption of site silent lake last 2 day ago",
        "can you give me consumption of this site fahad for last 2 days",
        "can you give me consumption of this site Dirk for last 2 days",
        "can you give energy consumption for the site Gen I Full Setup last 8 days",
        "can you give energy consumption for the site E2E Validation-flagged-breakers",
        "can you give energy consumption for the site Sam Bulk",
        "please energy consumption of Marcus",
    ]

    site_list = """test-neo4j[ID:987948], __tenacious-sea[ID:995518], Daniel Hub 4DCA[ID:986654], Daniel Hub 4DDD[ID:971411], Energy Accumulated Testing (By Mugeesh)[ID:987080], 
    Holden Test[ID:986219], Fahad Test[ID:961655], __0C:5C:B5:70:00:D5[ID:965626], __02:00:00:00:01:02[ID:30928], "
             "myrat test[ID:984387], _Gen I Full Setup - HK Office[ID:949503], Nashville Quality Office[ID:970822], 
             Test Site -mug[ID:971632], silent-lake Staging Site[ID:971843], __02:00:00:00:01:00[ID:968897], Sam Bulk Upload Test[ID:970232], di Staging[ID:967811], 
             PS Test Site[ID:962677], Marcus Testing[ID:570755], _Gen II Full Setup - HK Office[ID:934726], __SuperHub Proto Fleet testing[ID:914259], Site Name fdsafdsfsda[ID:853936], Energybox Nashville SuperHub - Lively Violet[ID:815864], "
             "Site Name[ID:532479], Energybox Nashville[ID:500214], Pilot Site 1101[ID:492722], Daniel T 1767[ID:488105], Zyanya Integration Test Site (HK#1)[ID:468473], E2E Validation-flagged-breakers[ID:469904], "
             "E2E Validation-Public_API[ID:462740], Mugeesh Site[ID:476821], E2E Validation[ID:474154], Daniel T[ID:468450], #468 SIMULATION [ID:20454], sw: Sam Home[ID:19085], Energybox Cologne[ID:13743], "
             "Dirk's House[ID:11851], Energybox Hongkong[ID:5787]"""

    print("=== Testing AI Extraction ===")
    for query in test_queries:
        result = ollama_api.get_ai_extraction(query, site_list)
        # Use a cleaner print to see progress
        status = "✅" if result["site_id"] != -1 else "❌"
        print(f"{status} Query: {query}")
        print(f"   Match: {result}\n")
