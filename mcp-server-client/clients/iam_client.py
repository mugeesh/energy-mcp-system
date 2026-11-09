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

    Every IAM route lives under a versioned prefix (``/api/v1/sites``,
    ``/api/v1/users``, ``/api/v1/auth/login``). Hitting ``/sites`` without the
    prefix returns a Tomcat 404, so the prefix is applied here and can be
    overridden with ``IAM_API_PREFIX``.
    """

    DEFAULT_API_PREFIX = "/api/v1"

    def __init__(self, auth_token=None):
        base_url = (os.getenv("IAM_URL") or "").strip().rstrip("/")
        if not base_url:
            raise ValueError("IAM_URL is not configured")

        prefix = (os.getenv("IAM_API_PREFIX", self.DEFAULT_API_PREFIX) or "").strip()
        if prefix and not prefix.startswith("/"):
            prefix = "/" + prefix
        self.base_url = base_url + prefix.rstrip("/")

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

    def _get(self, path: str, **params):
        """GET an IAM endpoint and return the decoded JSON body."""
        url = f"{self.base_url}{path}"
        try:
            response = requests.get(
                url,
                params=params or None,
                headers=self.get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            detail = ""
            if e.response is not None:
                try:
                    payload = e.response.json()
                    detail = payload.get("message") or payload.get("error") or ""
                except ValueError:
                    detail = (e.response.text or "").strip()[:300]
            logger.error("❌ GET %s failed: HTTP %s %s", url, status, detail)
            raise RuntimeError(
                f"IAM API GET {url} failed (HTTP {status})"
                + (f": {detail}" if detail else "")
            ) from e
        except Exception as e:
            logger.error("❌ GET %s failed: %s", url, e)
            raise

    @staticmethod
    def _as_items(payload):
        """Normalize a list or a paginated envelope into a plain list."""
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("content", "items", "data", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        raise RuntimeError(
            f"Unexpected IAM response shape: {type(payload).__name__}"
        )

    def get_all_users(self):
        users = self._as_items(self._get("/users"))
        logger.info("✅ get_all_users succeeded: %d users returned", len(users))
        return users

    def get_all_sites(self):
        sites = self._as_items(
            self._get("/sites", sensorTypesAnd="false", siblings="true")
        )
        logger.info("✅ get_all_sites succeeded: %d sites returned", len(sites))
        return sites
