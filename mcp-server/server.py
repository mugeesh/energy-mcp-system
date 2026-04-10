#!/usr/bin/env python3
"""
MCP Server for Energy Consumption API
Listens for requests and processes them
"""

import pika
import json
import requests
import os
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnergyMCPServer:
    def __init__(self):
        self.channel = None
        self.connection = None
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_port =5672
        self.request_queue = 'energy_request_queue'
        self.site_data = None
        self.site_lookup = None
        # Load site mapping from JSON file
        self.load_site_mapping()
        
        # Connect to RabbitMQ
        self.setup_rabbitmq()
    
    def load_site_mapping(self):
        """Load site name to site_id mapping"""
        with open('site_mapping.json', 'r') as f:
            self.site_data = json.load(f)
        
        # Create quick lookup dictionary
        self.site_lookup = {}
        for site in self.site_data['sites']:
            # Add main name
            self.site_lookup[site['name'].lower()] = site['site_id']
            # Add aliases
            for alias in site['aliases']:
                self.site_lookup[alias.lower()] = site['site_id']
        
        logger.info(f"Loaded {len(self.site_lookup)} site mappings")
    
    def setup_rabbitmq(self):
        """Setup RabbitMQ connection and queues"""
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
            
            # Declare the request queue (durable = survives restarts)
            self.channel.queue_declare(queue=self.request_queue, durable=True)
            
            # Only process one message at a time
            self.channel.basic_qos(prefetch_count=1)
            
            logger.info(f"Connected to RabbitMQ at {self.rabbitmq_host}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
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
        """Handle incoming RPC requests"""
        try:
            # Parse request
            request = json.loads(body)
            site_name = request.get('site_name', '')
            
            logger.info(f"Processing request for site: {site_name}")
            
            # Lookup site_id
            site_id = self.lookup_site_id(site_name)
            
            if not site_id:
                # Site not found
                response = {
                    "error": f"Site '{site_name}' not found",
                    "available_sites": list(set([s['name'] for s in self.site_data['sites']]))
                }
            else:
                # Get energy consumption data
                energy_data = self.get_energy_consumption(site_id, site_name)
                response = {
                    "site_name": site_name,
                    "site_id": site_id,
                    "consumption": energy_data,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Send response back to client
            ch.basic_publish(
                exchange='',
                routing_key=props.reply_to,
                properties=pika.BasicProperties(
                    correlation_id=props.correlation_id
                ),
                body=json.dumps(response)
            )
            
            # Acknowledge the request
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
            logger.info(f"Sent response for {site_name} (ID: {site_id})")
            
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
        """Start the server"""
        logger.info(f"Server started. Waiting for requests on queue: {self.request_queue}")
        
        self.channel.basic_consume(
            queue=self.request_queue,
            on_message_callback=self.on_request
        )
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
            self.connection.close()

if __name__ == "__main__":
    server = EnergyMCPServer()
    server.start()
