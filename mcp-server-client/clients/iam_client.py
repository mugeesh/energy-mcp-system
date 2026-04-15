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

    def __init__(self, auth_token=None):
        self.base_url = os.getenv("IAM_URL")
        self.username = os.getenv("IAM_USERNAME")
        self.password = os.getenv("IAM_PASSWORD")
        if auth_token:
            token_str = auth_token.strip()
            if not token_str.startswith("Bearer "):
                self.token = "Bearer " + token_str
            else:
                self.token = token_str
            logger.info(f"IAMClient: Using provided JWT token (len: {len(self.token)})")
        else:
            logger.info("IAMClient: No token provided → logging in with credentials")
            self.token = self.get_token_iam()
        logger.debug(f"Final Authorization header will be: {self.token[:80]}...")

    def get_token_iam(self):
        """Only used when no token is passed from frontend"""
        try:
            headers = {"Content-Type": "application/json"}
            payload = {"email": self.username, "password": self.password}

            response = requests.post(
                f"{self.base_url}/auth/login",
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()

            access_token = response.json().get("accessToken")
            if not access_token:
                raise ValueError("Login response did not contain accessToken")

            return "Bearer " + access_token

        except Exception as e:
            logger.error(f"Failed to get token via login: {e}")
            raise

    def get_headers(self):
        if not getattr(self, 'token', None):
            raise ValueError("No authentication token available in IAMClient")
        return {
            "Content-Type": "application/json",
            "authorization": self.token
        }

    # Your other methods stay almost the same
    def get_all_users(self):
        try:
            response = requests.get(
                f"{self.base_url}/users",
                headers=self.get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            logger.info(f"✅ get_all_users succeeded: {len(response.json())} users returned")
            return response
        except Exception as e:
            logger.error(f"❌ get_all_users failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response body: {e.response.text}")
            raise

    def get_all_sites(self):
        try:
            response = requests.get(
                f"{self.base_url}/sites",
                params={"sensorTypesAnd": "false", "siblings": "true"},
                headers=self.get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            logger.info(f"✅ get_all_sites succeeded: {len(response.json())} users returned")
            return response
        except Exception as e:
            logger.error(f"❌ get_all_users failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response body: {e.response.text}")
            raise
