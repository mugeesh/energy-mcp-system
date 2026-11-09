import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class TSApi:
    """Time-series / energy API client using the caller's IAM JWT."""

    def __init__(self, iam_token):
        # Keep construction non-fatal: site/user lookups must not break just
        # because the energy API is not configured. Validate on first call.
        self.ts_api_url = (os.getenv("ts_api_url") or "").strip().rstrip("/")
        self.iam_token = iam_token

    def get_energy_consumption_by_site_id(self, site_id, from_date, to_date):
        if not self.ts_api_url:
            raise RuntimeError(
                "ts_api_url is not configured. Set it to the time-series API "
                "base URL (e.g. https://ts.staging.energybox.com)."
            )

        url = f"{self.ts_api_url}/energy/site/{site_id}/consumption"
        params = {"from": from_date, "to": to_date}
        logger.info(
            "Fetching energy data for site %s from %s to %s",
            site_id,
            from_date,
            to_date,
        )
        try:
            response = requests.get(
                url, params=params, headers=self.get_headers(), timeout=30
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
            logger.error("❌ Energy API GET %s failed: HTTP %s %s", url, status, detail)
            raise RuntimeError(
                f"Energy API GET {url} failed (HTTP {status})"
                + (f": {detail}" if detail else "")
            ) from e
        except Exception as e:
            logger.error("❌ Energy API GET %s failed: %s", url, e)
            raise

    def get_headers(self):
        return {"Content-Type": "application/json", "authorization": self.iam_token}
