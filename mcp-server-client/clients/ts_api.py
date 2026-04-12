import json
import logging
import os

import requests
from dotenv import load_dotenv

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class TSApi:

    def __init__(self, iam_token):
        self.ts_api_url = os.getenv("ts_api_url")
        self.iam_token = iam_token

    def get_energy_consumption_by_site_id(self, site_id, from_date, to_date):
        try:
            url = f"{self.ts_api_url}/energy/site/{site_id}/consumption"
            params = {"from": from_date, "to": to_date}
            logger.info(
                f"Fetching energy data for site {site_id} from {from_date} to {to_date}"
            )
            response = requests.get(
                url, params=params, headers=self.get_headers(), timeout=30
            )
            response.raise_for_status()
            return response
        except Exception as e:
            logging.error("Error fetching access token: " + str(e))

    def get_headers(self):
        return {"Content-Type": "application/json", "authorization": self.iam_token}
