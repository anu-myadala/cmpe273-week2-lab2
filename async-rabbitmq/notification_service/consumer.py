"""
RabbitMQ Consumer for NotificationService
Consumes InventoryReserved events and sends notifications
"""
import pika
import json
import logging
import os
import time

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class NotificationConsumer:
    def __init__(self):
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
        self.rabbitmq_port = int(os.getenv('RABBITMQ_PORT', '5672'))
        self.rabbitmq_user = os.getenv('RABBITMQ_USER', 'guest')
        self.rabbitmq_password = os.getenv('RABBITMQ_PASSWORD', 'guest')
        self.exchange_name = 'inventory'
        self.queue_name = 'inventory-events'
        self.connection = None
        self.channel = None
        self.notifications_sent = 0
        
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
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='topic',
                durable=True
            )
            
            # Declare DLQ
            self.channel.queue_declare(
                queue='inventory-events-dlq',
                durable=True
            )
            
            # Declare main queue
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': 'dlx',
                    'x-dead-letter-routing-key': 'inventory-events-dlq'
                }
            )
            
            # Bind queue to exchange - only listen for InventoryReserved events
            self.channel.queue_bind(
                exchange=self.exchange_name,
                queue=self.queue_name,
                routing_key='inventory.reserved'
            )
            
            # Set prefetch count
            self.channel.basic_qos(prefetch_count=10)
            
            logger.info(f"Connected to RabbitMQ at {self.rabbitmq_host}:{self.rabbitmq_port}")
            logger.info(f"Listening on queue: {self.queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def process_message(self, ch, method, properties, body):
        """Process incoming inventory events"""
        try:
            # Parse message
            try:
                event = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            event_type = event.get('event_type')
            order_id = event.get('order_id')
            user_id = event.get('user_id', 'unknown')
            
            if not order_id:
                logger.error(f"Missing order_id in message: {event}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            # Only process InventoryReserved events (filtered by routing key binding)
            if event_type == 'InventoryReserved':
                logger.info(f"Processing notification for order {order_id}")
                
                # Send notification
                item = event.get('item', 'unknown')
                quantity = event.get('quantity', 1)
                
                notification_message = (
                    f"Dear {user_id}, your order #{order_id} for {quantity}x {item} "
                    f"has been confirmed and inventory has been reserved."
                )
                
                # Simulate sending notification (email, SMS, push, etc.)
                logger.info(f"[NOTIFICATION SENT] {notification_message}")
                self.notifications_sent += 1
                
                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            else:
                # Skip other event types
                logger.debug(f"Skipping event type: {event_type}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Reject and requeue for retry
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
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
            logger.info(f"Sent {self.notifications_sent} notifications")
            logger.info("Consumer stopped")
        except Exception as e:
            logger.error(f"Error stopping consumer: {e}")


def main():
    """Main entry point"""
    consumer = NotificationConsumer()
    
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
