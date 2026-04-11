#!/usr/bin/env python3
import json
import logging
import os
import signal
import sys
import time
from typing import Any, Dict

import pika
from site_lookup import SiteLookUp

from ollama.ollama_api import OllamaAPI
from rabbitmq.rabbitMqClient import RabbitMqClient

# --- Configuration & Logging ---
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "energy_request_queue")
SITE_MAPPING_FILE = "site_mapping.json"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("EnergyMCPServer")


class EnergyMCPServer:
    def __init__(self):
        self.site_lookup = SiteLookUp()
        self.ollama_client = OllamaAPI()
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
        site_list = "\n".join(
            [
                f"- {s['title']} [ID: {s['id']}]"
                for s in self.site_lookup.list_all_sites()
            ]
        )
        ai_data = self.ollama_client.get_ai_extraction(query, site_list)
        logger.debug(f"your query :{query}")
        logger.debug(f"AI response {ai_data}")
        # ai_data = {'day': '8', 'site_id': '468473'}
        site_id = ai_data.get("site_id")
        site_info = self.site_lookup.get_site_details(site_id)
        is_valid = self.check_site_id_valid(site_info, query)
        if is_valid:
            day = ai_data.get("day")
            date_filter = self.site_lookup.parse_date_range(day)
            energy_data = self.site_lookup.get_energy_consumption(
                site_id=site_id,
                from_date=date_filter["from"],
                to_date=date_filter["to"],
            )
            return {
                "site_id": site_id,
                "site_title": site_info["title"],
                "period": date_filter["description"],
                "data": energy_data,
            }
        else:
            return {
                "error": f"Site id not found from your question {query} , please give me the correct query"
            }

    def check_site_id_valid(self, site_info: dict, query: str):
        if site_info:
            site_title = site_info["title"].lower()
            title_words = [w for w in site_title.split() if len(w) > 3]
            is_valid = any(word in query.lower() for word in title_words)
            if is_valid:
                return True
            else:
                return False
        else:
            return False

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
                body=response,
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
                    queue=RABBITMQ_QUEUE, on_message_callback=self.on_request
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

    #testing only
    # query = "can you give energy consumption for the site E2E Validation-flagged-breakers  site last 8 days"
    # server.parse_query(query)
