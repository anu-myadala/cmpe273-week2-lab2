"""
RabbitMQ Consumer for InventoryService
Consumes OrderPlaced events and publishes InventoryReserved/Failed events
"""
import pika
import json
import logging
import os
import sys
import time
import random

sys.path.append('/app/common')
from ids import generate_event_id, current_timestamp

from idempotency import IdempotencyTracker

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class InventoryConsumer:
    def __init__(self):
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
        self.rabbitmq_port = int(os.getenv('RABBITMQ_PORT', '5672'))
        self.rabbitmq_user = os.getenv('RABBITMQ_USER', 'guest')
        self.rabbitmq_password = os.getenv('RABBITMQ_PASSWORD', 'guest')
        self.order_exchange = 'orders'
        self.inventory_exchange = 'inventory'
        self.queue_name = 'order-events'
        self.connection = None
        self.channel = None
        self.idempotency_tracker = IdempotencyTracker()
        self.inventory = {}  # Simple in-memory inventory
        
    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_password)
            parameters = pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchanges
            self.channel.exchange_declare(
                exchange=self.order_exchange,
                exchange_type='topic',
                durable=True
            )
            
            self.channel.exchange_declare(
                exchange=self.inventory_exchange,
                exchange_type='topic',
                durable=True
            )
            
            # Declare DLX (Dead Letter Exchange)
            self.channel.exchange_declare(
                exchange='dlx',
                exchange_type='topic',
                durable=True
            )
            
            # Declare DLQ
            self.channel.queue_declare(
                queue='order-events-dlq',
                durable=True
            )
            
            self.channel.queue_bind(
                exchange='dlx',
                queue='order-events-dlq',
                routing_key='order-events-dlq'
            )
            
            # Declare main queue with DLQ configuration
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': 'dlx',
                    'x-dead-letter-routing-key': 'order-events-dlq'
                }
            )
            
            # Bind queue to exchange
            self.channel.queue_bind(
                exchange=self.order_exchange,
                queue=self.queue_name,
                routing_key='order.placed'
            )
            
            # Set prefetch count for backpressure
            self.channel.basic_qos(prefetch_count=10)
            
            logger.info(f"Connected to RabbitMQ at {self.rabbitmq_host}:{self.rabbitmq_port}")
            logger.info(f"Listening on queue: {self.queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def process_message(self, ch, method, properties, body):
        """Process incoming order events"""
        try:
            # Parse message
            try:
                event = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON message: {e}")
                logger.error(f"Message body: {body}")
                # Reject and send to DLQ
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            event_id = event.get('event_id')
            order_id = event.get('order_id')
            
            if not event_id or not order_id:
                logger.error(f"Missing event_id or order_id in message: {event}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            logger.info(f"Processing event {event_id} for order {order_id}")
            
            # Check idempotency
            if self.idempotency_tracker.is_processed(event_id):
                logger.info(f"Duplicate event {event_id} detected, skipping processing")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Simulate inventory check and reservation
            item = event.get('item', 'unknown')
            quantity = event.get('quantity', 1)
            
            # Simulate 10% failure rate for testing
            success = random.random() > 0.1
            
            if success:
                # Reserve inventory
                self.inventory[order_id] = {
                    'item': item,
                    'quantity': quantity,
                    'reserved_at': current_timestamp()
                }
                
                logger.info(f"Inventory reserved for order {order_id}: {quantity}x {item}")
                
                # Publish InventoryReserved event
                response_event = {
                    "event_id": generate_event_id(),
                    "event_type": "InventoryReserved",
                    "order_id": order_id,
                    "timestamp": current_timestamp(),
                    "user_id": event.get('user_id'),
                    "item": item,
                    "quantity": quantity
                }
                
                self.publish_event(response_event, 'inventory.reserved')
                
            else:
                logger.warning(f"Inventory reservation failed for order {order_id}")
                
                # Publish InventoryFailed event
                response_event = {
                    "event_id": generate_event_id(),
                    "event_type": "InventoryFailed",
                    "order_id": order_id,
                    "timestamp": current_timestamp(),
                    "user_id": event.get('user_id'),
                    "item": item,
                    "quantity": quantity,
                    "reason": "Insufficient inventory"
                }
                
                self.publish_event(response_event, 'inventory.failed')
            
            # Mark event as processed
            self.idempotency_tracker.mark_processed(event_id)
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Reject and requeue for retry
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def publish_event(self, event, routing_key):
        """Publish event to inventory exchange"""
        try:
            self.channel.basic_publish(
                exchange=self.inventory_exchange,
                routing_key=routing_key,
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            logger.info(f"Published event {event['event_id']} with routing key '{routing_key}'")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
    
    def start_consuming(self):
        """Start consuming messages"""
        try:
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.process_message,
                auto_ack=False
            )
            
            logger.info("Started consuming messages. Press Ctrl+C to stop.")
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self.stop()
        except Exception as e:
            logger.error(f"Error in start_consuming: {e}")
            self.stop()
    
    def stop(self):
        """Stop consuming and close connection"""
        try:
            if self.channel:
                self.channel.stop_consuming()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info(f"Processed {self.idempotency_tracker.get_processed_count()} unique events")
            logger.info("Consumer stopped")
        except Exception as e:
            logger.error(f"Error stopping consumer: {e}")


def main():
    """Main entry point"""
    consumer = InventoryConsumer()
    
    # Connect with retries
    MAX_RETRIES = 20
    retry_count = 0
    while retry_count < MAX_RETRIES:
        if consumer.connect():
            break
        retry_count += 1
        logger.warning(f"Retrying RabbitMQ connection ({retry_count}/{MAX_RETRIES})...")
        time.sleep(5)
    
    if retry_count >= MAX_RETRIES:
        logger.error("Failed to connect to RabbitMQ after max retries")
        return
    
    # Start consuming
    consumer.start_consuming()


if __name__ == '__main__':
    main()
