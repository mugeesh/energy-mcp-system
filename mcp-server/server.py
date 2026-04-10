#!/usr/bin/env python3
import json
import logging
import os
import re
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any

import pika
from rabbitmq.rabbitMqClient import RabbitMqClient
from site_lookup import SiteLookUp

# --- Configuration & Logging ---
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "energy_request_queue")
SITE_MAPPING_FILE = "site_mapping.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("EnergyMCPServer")


class EnergyMCPServer:
    def __init__(self):
        self.site_lookup = SiteLookUp()
        self.rabbitmq = RabbitMqClient()
        self.is_running = True

        # Handle process signals
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_exit(self, signum, frame):
        logger.info("Shutdown signal received.")
        self.is_running = False
        self.rabbitmq.close()
        sys.exit(0)

    def parse_query(self, query: str) -> Dict[str, Any]:
        """Processes natural language query to find site and fetch energy data."""
        # 1. Parse the Date Range first
        # This uses your SiteLookUp logic for "yesterday", "last 7 days", etc.
        date_info = self.site_lookup.parse_date_range(query)

        # 2. Extract the Site Name/Subject
        # Logic: Strip prefixes and date markers to isolate the site name
        subject = re.sub(r'^(get|show me|energy (consumption|usage) of)\s+', '', query, flags=re.IGNORECASE)
        # Remove the date portion from the subject so it doesn't confuse the lookup
        subject = re.split(r'\s+(for|last|yesterday|today)\b', subject, flags=re.IGNORECASE)[0].strip()

        # 3. Find the Site ID
        site_id = self.site_lookup.find_site_id(subject or query)

        if not site_id:
            # Get a few real site names for suggestions
            all_sites = self.site_lookup.list_all_sites()
            suggestions = [s['title'] for s in all_sites[:5]]
            return {
                "error": f"Could not identify site from query: '{subject}'",
                "suggestions": suggestions
            }

        # 4. Get the Data
        # We pass the parsed from/to dates into the API call
        energy_data = self.site_lookup.get_energy_consumption(
            site_id=site_id,
            from_date=date_info["from"],
            to_date=date_info["to"]
        )

        # 5. Fetch site details for a richer response
        site_details = self.site_lookup.get_site_details(site_id)

        return {
            "query": query,
            "site": {
                "id": site_id,
                "title": site_details.get("title") if site_details else subject,
                "city": site_details.get("city") if site_details else "N/A"
            },
            "period": date_info["description"],
            "data": energy_data,
            "timestamp": datetime.now().isoformat()
        }

    def on_request(self, ch, method, props, body):
        """Standard RabbitMQ RPC callback."""
        try:
            data = json.loads(body)
            query = data.get("query", "")
            logger.info(f"RPC Request: {query}")

            response = self.parse_query(query)
            # {'data': {'energy': 503.15, 'unit': 'kWh'}, 'period': 'last 7 days (default)', 'query': "'E2E Validation-flagged-breaker", 'site': {'city': 'Hong Kong', 'id': '474154', 'title': 'E2E Validation'}, 'timestamp': '2026-04-10T18:10:16.122645'}


            self.rabbitmq.reply(
                reply_to=props.reply_to,
                correlation_id=props.correlation_id,
                body=response
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Callback error: {e}")
            self._send_error(ch, method, props, str(e))

    def _send_error(self, ch, method, props, error_msg: str):
        try:
            err_body = json.dumps({"error": error_msg})
            ch.basic_publish(
                exchange="",
                routing_key=props.reply_to,
                properties=pika.BasicProperties(correlation_id=props.correlation_id),
                body=err_body,
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Critical failure sending error response: {e}")

    def start(self):
        """Main loop with reconnection logic."""
        logger.info(f"Energy MCP Server starting on queue: {RABBITMQ_QUEUE}")

        while self.is_running:
            try:
                self.rabbitmq.connect()
                self.rabbitmq.declare_queue(RABBITMQ_QUEUE)
                self.rabbitmq.channel.basic_qos(prefetch_count=1)
                self.rabbitmq.channel.basic_consume(
                    queue=RABBITMQ_QUEUE,
                    on_message_callback=self.on_request
                )
                self.rabbitmq.channel.start_consuming()
            except (pika.exceptions.AMQPError, Exception) as e:
                if not self.is_running:
                    break
                logger.warning(f"Connection lost ({e}). Retrying in 5 seconds...")
                time.sleep(5)

if __name__ == "__main__":
    server = EnergyMCPServer()
    server.start()
