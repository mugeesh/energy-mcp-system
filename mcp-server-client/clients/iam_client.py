import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class IAMClient:
    """IAM API client using the caller's JWT.

    The frontend sends ``Authorization: Bearer <token>`` on every request; the
    client injects it into MCP tool calls. No username/password login is used.
    """

    def __init__(self, auth_token=None):
        self.base_url = os.getenv("IAM_URL")
        if not self.base_url:
            raise ValueError("IAM_URL is not configured")

        token = (auth_token or os.getenv("AUTH_TOKEN") or "").strip()
        if not token:
            raise ValueError(
                "No IAM token supplied. The frontend must send "
                "'Authorization: Bearer <token>' with every /chat request."
            )

        if not token.startswith("Bearer "):
            token = "Bearer " + token
        self.token = token
        logger.info("IAMClient: using caller JWT (len: %d)", len(self.token))

    def get_headers(self):
        return {
            "Content-Type": "application/json",
            "authorization": self.token,
        }

    def get_all_users(self):
        try:
            response = requests.get(
                f"{self.base_url}/users",
                headers=self.get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            logger.info(
                "✅ get_all_users succeeded: %d users returned",
                len(response.json()),
            )
            return response
        except Exception as e:
            logger.error("❌ get_all_users failed: %s", e)
            if hasattr(e, "response") and e.response is not None:
                logger.error("Response body: %s", e.response.text)
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
            logger.info(
                "✅ get_all_sites succeeded: %d sites returned",
                len(response.json()),
            )
            return response
        except Exception as e:
            logger.error("❌ get_all_sites failed: %s", e)
            if hasattr(e, "response") and e.response is not None:
                logger.error("Response body: %s", e.response.text)
            raise
