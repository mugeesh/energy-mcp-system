#!/usr/bin/env python3
"""
Clean MCP Client with High-Level RPC - FIXED
"""

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime

# Fixed import - use consistent naming
from rabbitmq.rabbitMqClient import RabbitMqClient

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class EnergyMCPClient:
    def __init__(self):
        self.rabbitmq = RabbitMqClient()
        self.request_queue = os.getenv("RABBITMQ_QUEUE", "energy_request_queue")
        self.responses = {}  # correlation_id -> response
        self.callback_queue = "amq.rabbitmq.reply-to"

        self.setup_rabbitmq()

    def setup_rabbitmq(self):
        """Initialize connection and start listening for replies"""
        self.rabbitmq.connect()

        self.rabbitmq.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True,
        )
        logger.info("MCP Client ready - using Direct Reply-To")

    # ==================== FIXED CALLBACK ====================
    def on_response(self, ch, method, props, body):
        """Handle incoming response from server - CORRECT SIGNATURE"""
        correlation_id = props.correlation_id if props else None

        if correlation_id and correlation_id in self.responses:
            try:
                self.responses[correlation_id] = json.loads(body)
                logger.debug(f"Response received for {correlation_id[:8]}...")
            except Exception as e:
                logger.warning(f"Failed to parse response: {e}")
                self.responses[correlation_id] = {"error": "Invalid response format"}
        else:
            logger.warning(
                f"Received response with unknown correlation_id: {correlation_id}"
            )

    # =========================================================

    def call(self, site_name: str, timeout: int = 30) -> dict:
        """
        High-level RPC method
        """
        if not site_name or not str(site_name).strip():
            return {"error": "Site name is required"}

        correlation_id = str(uuid.uuid4())
        self.responses[correlation_id] = None

        request = {
            "site_name": str(site_name).strip(),
            "request_time": datetime.now().isoformat(),
        }

        try:
            self.rabbitmq.publish(
                queue=self.request_queue,
                body=request,  # dict is handled inside publish()
                correlation_id=correlation_id,
                reply_to=self.callback_queue,
            )

            logger.info(f"RPC call sent for site: '{site_name}'")

            # Wait for response
            start_time = time.time()
            while self.responses[correlation_id] is None:
                self.rabbitmq.connection.process_data_events(time_limit=0.1)

                if time.time() - start_time > timeout:
                    logger.error(f"RPC timeout for '{site_name}' after {timeout}s")
                    self.responses.pop(correlation_id, None)
                    return {"error": f"Timeout after {timeout} seconds"}

                time.sleep(0.05)

            response = self.responses.pop(correlation_id)
            return response

        except Exception as e:
            logger.exception(f"RPC call failed for '{site_name}'")
            self.responses.pop(correlation_id, None)
            return {"error": f"RPC failed: {str(e)}"}

    def close(self):
        self.rabbitmq.close()
        logger.info("MCP Client closed")


# ====================== CLI ======================


def interactive_mode():
    client = EnergyMCPClient()
    print("\n" + "=" * 60)
    print("🌍 Energy MCP Client - High-Level RPC")
    print("=" * 60)

    try:
        while True:
            site = input("\n🔍 Enter site name (or 'quit'): ").strip()
            if site.lower() in ["quit", "exit", "q"]:
                break
            if not site:
                continue

            print(f"📡 Sending request for '{site}'...")
            result = client.call(site)

            print("\n" + "-" * 50)
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                if "available_sites" in result:
                    print(f"Available: {', '.join(result.get('available_sites', []))}")
            else:
                cons = result.get("consumption", {})
                print(f"✅ Site       : {result.get('site_name')}")
                print(f"📌 Site ID    : {result.get('site_id')}")
                print(f"⚡ Consumption: {cons.get('consumption')} {cons.get('unit')}")
                print(f"📅 Date       : {cons.get('date')}")
            print("-" * 50)

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    finally:
        client.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        client = EnergyMCPClient()
        try:
            resp = client.call(sys.argv[1])
            print(json.dumps(resp, indent=2))
        finally:
            client.close()
    else:
        interactive_mode()
