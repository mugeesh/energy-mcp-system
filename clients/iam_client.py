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


class IAMClient:

    def __init__(self):
        self.base_url = os.getenv("iam_url")
        self.username = os.getenv("iam_username")
        self.password = os.getenv("iam_password")
        self.user_token = None
        self.token = self.get_token_iam()

    def get_token_iam(self):
        try:
            header_in = {"Content-Type": "application/json"}
            payload = {"email": self.username, "password": self.password}
            iam_return = requests.post(
                self.base_url + "/auth/login",
                data=json.dumps(payload),
                headers=header_in,
            )
            self.user_token = iam_return.json().get("accessToken")
            return "Bearer " + self.user_token
        except Exception as e:
            logging.error("Error fetching access token: " + str(e))

    def get_user_by_id(self, user_id):
        try:
            iam_response = requests.get(
                self.base_url + f"/users/{user_id}", headers=self.get_headers()
            )
            return iam_response
        except Exception as e:
            logging.error("Error fetching access token: " + str(e))

    def get_all_sites(self):
        try:
            iam_response = requests.get(
                f"{self.base_url}/sites",
                params={"sensorTypesAnd": "false", "siblings": "true"},
                headers=self.get_headers(),
                timeout=30,
            )
            iam_response.raise_for_status()
            return iam_response
        except Exception as e:
            logging.error("Error fetching access token: " + str(e))

    def get_all_users(self):
        try:
            iam_response = requests.get(
                f"{self.base_url}/users",
                headers=self.get_headers(),
                timeout=30,
            )
            iam_response.raise_for_status()
            return iam_response
        except Exception as e:
            logging.error("Error fetching access token: " + str(e))

    def get_headers(self):
        return {"Content-Type": "application/json", "authorization": self.token}
