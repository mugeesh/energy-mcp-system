#!/usr/bin/env python3
"""
MCP Client for Energy Consumption API
Sends requests to server and receives responses
"""

import pika
import json
import uuid
import time
from datetime import datetime
import logging
import sys
import os
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnergyMCPClient:
    def __init__(self):
        self.rabbitmq_host = 'localhost'
        self.request_queue = 'energy_request_queue'
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_port =5672
        self.request_queue = 'energy_request_queue'

        # Store responses
        self.responses = {}
        self.connection = None
        self.channel = None
        self.callback_queue = None

        # Connect to RabbitMQ
        self.setup_rabbitmq()
    
    def setup_rabbitmq(self):
        """Setup RabbitMQ connection and callback queue"""
        try:
            credentials = pika.PlainCredentials('admin', 'password123')
            parameters = pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                virtual_host='/',
                credentials=credentials
            )
            # 3. Establish the connection
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Use Direct Reply-To (no queue creation needed)
            self.callback_queue = 'amq.rabbitmq.reply-to'
            
            # Consume from the direct reply-to queue
            self.channel.basic_consume(
                queue=self.callback_queue,
                on_message_callback=self.on_response,
                auto_ack=True
            )
            
            logger.info(f"Connected to RabbitMQ at {self.rabbitmq_host}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def on_response(self, ch, method, props, body):
        """Handle response from server"""
        correlation_id = props.correlation_id
        if correlation_id in self.responses:
            self.responses[correlation_id] = json.loads(body)
            logger.info(f"Received response for request {correlation_id[:8]}")
    
    def get_energy_consumption(self, site_name):
        """
        Send request to get energy consumption for a site
        
        Args:
            site_name: Name of the site (e.g., "Hong Kong", "Singapore")
        
        Returns:
            Response dictionary with energy data
        """
        # Generate unique correlation ID
        correlation_id = str(uuid.uuid4())
        
        # Prepare request
        request = {
            "site_name": site_name,
            "request_time": datetime.now().isoformat()
        }
        
        # Store placeholder for response
        self.responses[correlation_id] = None
        
        # Publish request
        self.channel.basic_publish(
            exchange='',
            routing_key=self.request_queue,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=correlation_id,
                content_type='application/json'
            ),
            body=json.dumps(request)
        )
        
        logger.info(f"Sent request for '{site_name}' (ID: {correlation_id[:8]})")
        
        # Wait for response (with timeout)
        timeout = 100*10  # seconds
        start_time = time.time()
        
        while self.responses[correlation_id] is None:
            # Process incoming messages
            self.connection.process_data_events()
            
            # Check timeout
            if time.time() - start_time > timeout:
                logger.error(f"Timeout waiting for response for {site_name}")
                return {"error": "Request timeout"}
            
            time.sleep(0.1)
        
        # Clean up
        response = self.responses[correlation_id]
        del self.responses[correlation_id]
        
        return response
    
    def close(self):
        """Close connection"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("Connection closed")

def interactive_mode():
    """Run client in interactive mode"""
    client = EnergyMCPClient()
    
    print("\n" + "="*50)
    print("🌱 Energy Consumption MCP Client")
    print("="*50)
    print("\nAvailable sites: Hong Kong, Singapore, London")
    print("Type 'quit' or 'exit' to stop\n")
    
    try:
        while True:
            # Get user input
            site_name = input("\n🔍 Enter site name: ").strip()
            
            if site_name.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
            
            if not site_name:
                print("❌ Please enter a site name")
                continue
            
            # Send request
            print(f"📡 Querying energy consumption for '{site_name}'...")
            response = client.get_energy_consumption(site_name)
            
            # Display response
            print("\n" + "-"*40)
            if "error" in response:
                print(f"❌ Error: {response['error']}")
                if "available_sites" in response:
                    print(f"💡 Available sites: {', '.join(response['available_sites'])}")
            else:
                print(f"✅ Site: {response['site_name']}")
                print(f"📌 Site ID: {response['site_id']}")
                print(f"⚡ Consumption: {response['consumption']['consumption']} {response['consumption']['unit']}")
                print(f"📅 Date: {response['consumption']['date']}")
                print(f"🕐 Query time: {response['timestamp']}")
            print("-"*40)
    
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    finally:
        client.close()

def single_query_mode(site_name):
    """Run a single query"""
    client = EnergyMCPClient()
    try:
        print(f"Querying {site_name}...")
        response = client.get_energy_consumption(site_name)
        print(json.dumps(response, indent=2))
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single query mode
        single_query_mode(sys.argv[1])
    else:
        # Interactive mode
        interactive_mode()
