#!/usr/bin/env python3
import json
import logging
import os
import sys
import threading
import time
import uuid
from datetime import datetime

# Path adjustment for RabbitMqClient
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rabbitmq.rabbitMqClient import RabbitMqClient

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class EnergyMCPClient:
    def __init__(self):
        self.rabbitmq = RabbitMqClient()
        self.request_queue = os.getenv("RABBITMQ_QUEUE", "energy_request_queue")
        self.responses = {}
        self.callback_queue = "amq.rabbitmq.reply-to"  # Using Direct Reply-To
        self.setup_rabbitmq()

    def setup_rabbitmq(self):
        self.rabbitmq.connect()
        self.rabbitmq.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True,
        )
        logger.info("MCP Client connected via Direct Reply-To")

    def on_response(self, ch, method, props, body):
        corr_id = props.correlation_id
        if corr_id in self.responses:
            try:
                # Store the data and signal the event
                self.responses[corr_id]["data"] = json.loads(body)
                self.responses[corr_id]["event"].set()
            except Exception as e:
                logger.error(f"Failed to parse JSON: {e}")
                self.responses[corr_id]["data"] = {"error": "Invalid JSON response"}
                self.responses[corr_id]["event"].set()

    def call(self, query: str, timeout: int = 30) -> dict:
        if not query.strip():
            return {"error": "Empty query"}

        corr_id = str(uuid.uuid4())
        # Create a thread-safe event for this specific request
        event = threading.Event()
        self.responses[corr_id] = {"event": event, "data": None}

        payload = {"query": query, "timestamp": datetime.now().isoformat()}

        try:
            self.rabbitmq.publish(
                queue=self.request_queue,
                body=payload,
                correlation_id=corr_id,
                reply_to=self.callback_queue,
            )
            logger.info(f"Request sent with correlation_id: {corr_id}")

            # Wait for the event to be set or the timeout to expire
            start_time = time.time()
            while not event.is_set():
                # Crucial: Allow pika to process incoming network packets
                self.rabbitmq.connection.process_data_events(time_limit=0.1)

                if (time.time() - start_time) > timeout:
                    self.responses.pop(corr_id, None)
                    return {"error": "Server timed out waiting for response"}

                # Small sleep to prevent 100% CPU usage while waiting
                time.sleep(0.01)

            # Retrieve the data populated by on_response
            response_entry = self.responses.pop(corr_id)
            return response_entry["data"]

        except Exception as e:
            self.responses.pop(corr_id, None)
            return {"error": f"Connection error: {str(e)}"}

    def close(self):
        self.rabbitmq.close()


def interactive_mode():
    client = EnergyMCPClient()
    print("\n" + "═" * 60)
    print("⚡ ENERGY MCP INTERACTIVE CLI")
    print("═" * 60)

    try:
        while True:
            query = input("\n🔍 Query (e.g. 'E2E Validation' or 'quit'): ").strip()
            if query.lower() in ["quit", "exit", "q"]:
                break
            if not query:
                continue

            print("⏳ Processing...")
            res = client.call(query)

            print("\n" + "─" * 60)
            if "error" in res:
                # Handle the case where site is not found or validation fails
                print(f"❌ ERROR: {res['error']}")
            else:
                energy_data = res.get("data", {})

                print(f"🏢 Site Title:  {res.get('site_title', 'N/A')}")
                print(f"🆔 Site ID:     {res.get('site_id', 'N/A')}")
                print(f"📅 Period:      {res.get('period', 'N/A')}")
                print(f"⚡ Consumption: {energy_data.get('energy', '0.0')} {energy_data.get('unit', 'kWh')}")

            print("─" * 60)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        client.close()


if __name__ == "__main__":
    interactive_mode()
