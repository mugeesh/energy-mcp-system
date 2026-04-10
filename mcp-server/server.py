#!/usr/bin/env python3
"""
MCP Server for Energy Consumption API
Listens for RPC requests and processes them using RabbitMQ.
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime

import pika

from rabbitmq.rabbitMqClient import RabbitMqClient

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class SiteManager:
    pass


class EnergyMCPServer:
    def __init__(self):
        self.site_manager = SiteManager()
        self.rabbitmq = RabbitMqClient()
        self.request_queue = os.getenv("RABBITMQ_QUEUE", "energy_request_queue")

        self.site_lookup = {}
        self.site_names = []

        self.load_site_mapping()

        # Graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def load_site_mapping(self):
        """Load site mapping from JSON"""
        try:
            with open("site_mapping.json", "r") as f:
                data = json.load(f)

            for site in data.get("sites", []):
                site_id = site["site_id"]
                main_name = site["name"].strip().lower()

                self.site_lookup[main_name] = site_id
                self.site_names.append(site["name"])

                for alias in site.get("aliases", []):
                    self.site_lookup[alias.strip().lower()] = site_id

            logger.info(f"Loaded {len(self.site_lookup)} site mappings")

        except Exception as e:
            logger.error(f"Failed to load site_mapping.json: {e}")
            raise

    def lookup_site_id(self, site_name: str):
        if not site_name:
            return None

        name_lower = site_name.strip().lower()

        if name_lower in self.site_lookup:
            return self.site_lookup[name_lower]

        for stored_name, site_id in self.site_lookup.items():
            if name_lower in stored_name or stored_name in name_lower:
                logger.info(f"Partial match: '{site_name}' → '{stored_name}'")
                return site_id

        return None

    def get_energy_consumption(self, site_id: str, site_name: str):
        logger.info(f"Fetching energy data for {site_name} (ID: {site_id})")

        mock_data = {
            "HK-001": {"consumption": 1250, "unit": "MWh", "date": "2024-01-15"},
            "SG-002": {"consumption": 890, "unit": "MWh", "date": "2024-01-15"},
            "LD-003": {"consumption": 2100, "unit": "MWh", "date": "2024-01-15"},
        }

        return mock_data.get(
            site_id,
            {
                "consumption": "N/A",
                "unit": "kWh",
                "error": "No data available for this site",
            },
        )

    def process_query(self, query: str) -> dict:
        """
        Process natural language query for energy consumption

        Examples:
        - "energy consumption of E2E Validation-flagged-breakers for last 7 days"
        - "show me energy usage for site 469904 today"
        - "energy consumption of Hong Kong site for yesterday"
        """
        query_lower = query.lower()

        # Extract site name
        # Look for patterns like "of X for" or "for site X"
        site_name = None

        # Pattern 1: "of [site name] for"
        if " of " in query_lower:
            parts = query_lower.split(" of ")
            if len(parts) > 1:
                site_part = parts[1]
                if " for " in site_part:
                    site_name = site_part.split(" for ")[0].strip()
                elif " yesterday" in site_part:
                    site_name = site_part.split(" yesterday")[0].strip()
                elif " today" in site_part:
                    site_name = site_part.split(" today")[0].strip()
                elif " last " in site_part:
                    site_name = site_part.split(" last ")[0].strip()
                else:
                    site_name = site_part.strip()

        # Pattern 2: "for site [name]"
        if not site_name and " for site " in query_lower:
            parts = query_lower.split(" for site ")
            if len(parts) > 1:
                site_part = parts[1]
                if " for " in site_part:
                    site_name = site_part.split(" for ")[0].strip()
                else:
                    site_name = site_part.strip()

        # Pattern 3: Just extract any site-like name (simple approach)
        if not site_name:
            # Remove common phrases
            cleaned = query_lower.replace("energy consumption of ", "")
            cleaned = cleaned.replace("energy usage of ", "")
            cleaned = cleaned.replace("show me ", "")
            cleaned = cleaned.replace("get ", "")

            # Split by common separators
            for separator in [" for ", " yesterday", " today", " last "]:
                if separator in cleaned:
                    site_name = cleaned.split(separator)[0].strip()
                    break

            if not site_name:
                site_name = cleaned.strip()

        # Parse date range
        date_range = self.site_manager.parse_date_range(query_lower)

        # Find site ID
        site_id = self.site_manager.find_site_id(site_name)

        if not site_id:
            # Try to extract numeric ID directly
            import re

            numbers = re.findall(r"\b\d{5,6}\b", query)
            if numbers:
                site_id = numbers[0]

        if not site_id:
            return {
                "error": f"Site '{site_name}' not found",
                "available_sites": self.site_manager.list_all_sites()[
                    :10
                ],  # Show first 10
            }

        # Get energy consumption
        energy_data = self.site_manager.get_energy_consumption(
            site_id, date_range["from"], date_range["to"]
        )

        # Get site details
        site_details = self.site_manager.get_site_details(site_id)

        return {
            "query": query,
            "site": {
                "id": site_id,
                "name": site_details["title"] if site_details else site_name,
                "city": site_details.get("city") if site_details else None,
                "country": site_details.get("country") if site_details else None,
            },
            "period": date_range["description"],
            "energy_consumption": energy_data,
            "timestamp": datetime.now().isoformat(),
        }


def on_request(self, ch, method, props, body):
    """Handle incoming RPC requests"""
    try:
        request = json.loads(body)
        query = request.get("query", "")

        logger.info(f"Processing query: {query}")

        # Process the query
        result = self.process_query(query)

        # Send reply using RabbitMqClient
        self.rabbitmq.reply(
            reply_to=props.reply_to, correlation_id=props.correlation_id, body=result
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"Sents response for query")
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        error_response = {"error": str(e)}
        ch.basic_publish(
            exchange="",
            routing_key=props.reply_to,
            properties=pika.BasicProperties(correlation_id=props.correlation_id),
            body=json.dumps(error_response),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)


def _send_error(self, ch, method, props, error_msg: str):
    """Safely send error response and acknowledge message"""
    try:
        self.rabbitmq.reply(
            reply_to=props.reply_to,
            correlation_id=props.correlation_id,
            body={"error": error_msg},
        )
    except Exception as reply_error:
        logger.warning(f"Failed to send error reply: {reply_error}")

    # Always acknowledge the message to prevent redelivery loops
    try:
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as ack_error:
        logger.warning(f"Failed to ack message: {ack_error}")


def start(self):
    """Start server with reconnection logic"""
    logger.info("Starting Energy MCP Server...")

    while True:
        try:
            self.rabbitmq.connect()
            self.rabbitmq.declare_queue(self.request_queue)
            self.rabbitmq.basic_qos(prefetch_count=1)

            self.rabbitmq.channel.basic_consume(
                queue=self.request_queue,
                on_message_callback=self.on_request,
                auto_ack=False,
            )

            logger.info(f"Server listening on queue: {self.request_queue}")
            self.rabbitmq.channel.start_consuming()

        except (
            pika.exceptions.AMQPConnectionError,
            pika.exceptions.AMQPChannelError,
        ) as e:
            logger.warning(f"Connection lost: {e}. Reconnecting in 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Shutdown requested.")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(5)

    self.shutdown()


def shutdown(self, *args):
    logger.info("Shutting down server...")
    self.rabbitmq.close()
    sys.exit(0)


if __name__ == "__main__":
    server = EnergyMCPServer()
    server.start()
