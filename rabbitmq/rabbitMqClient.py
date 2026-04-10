# common/rabbitmq_client.py
import json
import logging
import os

import pika
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RabbitMqClient:
    def __init__(self):
        self.connection = None
        self.channel = None

        self.host = os.getenv("RABBITMQ_HOST", "localhost")
        self.port = int(os.getenv("RABBITMQ_PORT", 5672))
        self.user = os.getenv("RABBITMQ_USER", "admin")
        self.password = os.getenv("RABBITMQ_PASS")
        self.heartbeat = int(os.getenv("RABBITMQ_HEARTBEAT", 600))

        if not self.password:
            raise ValueError("RABBITMQ_PASS environment variable is required")

    def connect(self):
        """Connect to RabbitMQ (idempotent - safe to call multiple times)"""
        if self.connection and self.connection.is_open:
            return

        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=self.heartbeat,
                blocked_connection_timeout=300,
                connection_attempts=5,
                retry_delay=5,
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            logger.info(f"✅ Connected to RabbitMQ at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"❌ RabbitMQ connection failed: {e}")
            raise

    def declare_queue(self, queue_name: str, durable: bool = True):
        if not self.channel:
            self.connect()
        self.channel.queue_declare(queue=queue_name, durable=durable)

    def basic_qos(self, prefetch_count: int = 1):
        if self.channel:
            self.channel.basic_qos(prefetch_count=prefetch_count)

    def close(self):
        if self.connection and not self.connection.is_closed:
            try:
                self.connection.close()
                logger.info("RabbitMQ connection closed.")
            except Exception as e:
                logger.warning(f"Error while closing connection: {e}")

    # Add these methods inside the RabbitMqClient class

    def publish(
        self,
        queue: str,
        body: dict | str | bytes,
        correlation_id: str = None,
        reply_to: str = None,
    ):
        """Low-level publish with common properties"""
        if not self.channel:
            self.connect()

        if isinstance(body, dict):
            body = json.dumps(body)

        if isinstance(body, str):
            body = body.encode("utf-8")

        properties = pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,  # make message persistent
            correlation_id=correlation_id,
            reply_to=reply_to,
        )

        self.channel.basic_publish(
            exchange="", routing_key=queue, properties=properties, body=body
        )
        logger.debug(
            f"Published to '{queue}' | corr_id: {correlation_id[:8] if correlation_id else 'N/A'}"
        )

    def reply(self, reply_to: str, correlation_id: str, body: dict | str | bytes):
        """
        Send RPC reply back to the client.
        This is the server-side counterpart of publish().
        """
        if not self.channel:
            self.connect()

        if isinstance(body, dict):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode("utf-8")

        properties = pika.BasicProperties(
            correlation_id=correlation_id, delivery_mode=2
        )

        self.channel.basic_publish(
            exchange="", routing_key=reply_to, properties=properties, body=body
        )
        logger.debug(
            f"Replied to correlation_id: {correlation_id[:8] if correlation_id else 'N/A'}"
        )
