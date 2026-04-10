#!/usr/bin/env python3
"""
MCP Server for Energy Consumption API
Listens for requests and processes them
"""
import sys
import time

import pika
import json
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
from rabbitmq.rabbitMqClient import RabbitMqClient
import signal

load_dotenv()
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnergyMCPServer:
    def __init__(self):
        self.rabbitmq_client = RabbitMqClient()
        self.rabbitmq = RabbitMqClient()
        self.request_queue = os.getenv('RABBITMQ_QUEUE', 'energy_request_queue')
        self.site_lookup = {}
        self.site_names = []
        self.site_data = None
        # load sites
        self.load_site_mapping()

        # Graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def load_site_mapping(self):
        """Load site mapping"""
        try:
            with open('site_mapping.json', 'r') as f:
                data = json.load(f)

            for site in data.get('sites', []):
                site_id = site['site_id']
                main_name = site['name'].strip().lower()

                self.site_lookup[main_name] = site_id
                self.site_names.append(site['name'])

                for alias in site.get('aliases', []):
                    self.site_lookup[alias.strip().lower()] = site_id

            logger.info(f"Loaded {len(self.site_lookup)} site mappings")
        except Exception as e:
            logger.error(f"Failed to load site_mapping.json: {e}")
            raise

    def lookup_site_id(self, site_name):
        """Convert site name to site_id using fuzzy matching"""
        site_name_lower = site_name.lower()

        # Try exact match first
        if site_name_lower in self.site_lookup:
            return self.site_lookup[site_name_lower]

        # Try partial match
        for name, site_id in self.site_lookup.items():
            if site_name_lower in name or name in site_name_lower:
                return site_id

        return None

    def get_energy_consumption(self, site_id, site_name):
        """
        Call your actual API or return mock data
        Replace this with your real API call
        """
        logger.info(f"Fetching energy data for {site_name} (ID: {site_id})")

        # Option 1: Call your real API (uncomment when ready)
        # response = requests.get(
        #     f"https://your-domain.com/api/{site_id}/energyconsumption",
        #     timeout=10
        # )
        # return response.json()

        # Option 2: Mock data for testing
        mock_data = {
            "HK-001": {"consumption": 1250, "unit": "MWh", "date": "2024-01-15"},
            "SG-002": {"consumption": 890, "unit": "MWh", "date": "2024-01-15"},
            "LD-003": {"consumption": 2100, "unit": "MWh", "date": "2024-01-15"}
        }

        return mock_data.get(site_id, {
            "consumption": "N/A",
            "unit": "kWh",
            "error": "No data available"
        })

    def on_request(self, ch, method, props, body):
        try:
            request = json.loads(body)
            site_name = request.get('site_name', '').strip()

            logger.info(f"Processing request for site: {site_name}")

            site_id = self.lookup_site_id(site_name)

            if not site_id:
                response = {
                    "error": f"Site '{site_name}' not found",
                    "available_sites": self.site_names[:15]
                }
            else:
                energy_data = self.get_energy_consumption(site_id, site_name)
                response = {
                    "site_name": site_name,
                    "site_id": site_id,
                    "consumption": energy_data,
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                }

            # Send reply
            ch.basic_publish(
                exchange='',
                routing_key=props.reply_to,
                properties=pika.BasicProperties(correlation_id=props.correlation_id),
                body=json.dumps(response)
            )

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            try:
                ch.basic_publish(
                    exchange='',
                    routing_key=props.reply_to,
                    properties=pika.BasicProperties(correlation_id=props.correlation_id),
                    body=json.dumps({"error": str(e)})
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception:
                pass  # best effort

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            # Send error response
            ch.basic_publish(
                exchange='',
                routing_key=props.reply_to,
                properties=pika.BasicProperties(
                    correlation_id=props.correlation_id
                ),
                body=json.dumps({"error": str(e)})
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def start(self):
        logger.info("Starting Energy MCP Server...")

        while True:
            try:
                self.rabbitmq.connect()
                self.rabbitmq.declare_queue(self.request_queue)
                self.rabbitmq.basic_qos(prefetch_count=1)

                self.rabbitmq.channel.basic_consume(
                    queue=self.request_queue,
                    on_message_callback=self.on_request
                )

                logger.info(f"Server listening on queue: {self.request_queue}")
                self.rabbitmq.channel.start_consuming()
            except (pika.exceptions.AMQPConnectionError, pika.exceptions.AMQPChannelError) as e:
                logger.warning(f"Connection lost: {e}. Reconnecting in 5s...")
                time.sleep(5)
            except KeyboardInterrupt:
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
