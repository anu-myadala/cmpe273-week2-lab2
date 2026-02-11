"""
Kafka Consumer for InventoryService
Consumes order events and produces inventory events
"""
from confluent_kafka import Consumer, Producer, KafkaError
import json
import logging
import os
import sys
import signal
import random

sys.path.append('/app/common')
from ids import generate_event_id, current_timestamp

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class InventoryConsumer:
    def __init__(self):
        self.kafka_broker = os.getenv('KAFKA_BROKER', 'kafka:9092')
        self.group_id = 'inventory-group'
        self.input_topic = 'order-events'
        self.output_topic = 'inventory-events'
        self.running = True
        self.inventory = {}  # In-memory inventory
        
        # Consumer configuration
        consumer_config = {
            'bootstrap.servers': self.kafka_broker,
            'group.id': self.group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,  # Manual commit
            'max.poll.interval.ms': 300000
        }
        
        # Producer configuration
        producer_config = {
            'bootstrap.servers': self.kafka_broker,
            'client.id': 'inventory-producer',
            'acks': 'all'
        }
        
        self.consumer = Consumer(consumer_config)
        self.producer = Producer(producer_config)
        
        # Subscribe to input topic
        self.consumer.subscribe([self.input_topic])
        
        logger.info(f"Inventory consumer initialized")
        logger.info(f"Consuming from: {self.input_topic}")
        logger.info(f"Group ID: {self.group_id}")
    
    def process_message(self, msg):
        """Process an order event and produce inventory event"""
        try:
            # Parse message
            event = json.loads(msg.value().decode('utf-8'))
            
            event_type = event.get('event_type')
            order_id = event.get('order_id')
            
            if event_type != 'OrderPlaced':
                logger.debug(f"Skipping non-OrderPlaced event: {event_type}")
                return True
            
            logger.info(f"Processing order {order_id}")
            
            # Extract order details
            payload = event.get('payload', {})
            item = payload.get('item', 'unknown')
            quantity = payload.get('quantity', 1)
            user_id = payload.get('user_id', 'unknown')
            
            # Simulate inventory check (90% success rate)
            success = random.random() > 0.1
            
            if success:
                # Reserve inventory
                self.inventory[order_id] = {
                    'item': item,
                    'quantity': quantity,
                    'reserved_at': current_timestamp()
                }
                
                logger.info(f"Inventory reserved for order {order_id}: {quantity}x {item}")
                
                # Create InventoryReserved event
                response_event = {
                    "event_id": generate_event_id(),
                    "event_type": "InventoryReserved",
                    "order_id": order_id,
                    "timestamp": current_timestamp(),
                    "success": True
                }
                
            else:
                logger.warning(f"Inventory reservation failed for order {order_id}")
                
                # Create InventoryFailed event
                response_event = {
                    "event_id": generate_event_id(),
                    "event_type": "InventoryFailed",
                    "order_id": order_id,
                    "timestamp": current_timestamp(),
                    "success": False,
                    "reason": "Insufficient inventory"
                }
            
            # Produce inventory event
            self.producer.produce(
                topic=self.output_topic,
                key=order_id.encode('utf-8'),
                value=json.dumps(response_event).encode('utf-8')
            )
            self.producer.poll(0)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return False
    
    def start(self):
        """Start consuming messages"""
        logger.info("Starting consumption...")
        
        try:
            while self.running:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f"Reached end of partition")
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                # Process message
                if self.process_message(msg):
                    # Commit offset manually
                    self.consumer.commit(msg)
                else:
                    logger.warning(f"Failed to process message, will retry")
        
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            self.stop()
    
    def stop(self):
        """Stop consumer and close connections"""
        logger.info("Stopping consumer...")
        self.running = False
        
        # Flush producer
        remaining = self.producer.flush(timeout=10)
        if remaining > 0:
            logger.warning(f"{remaining} messages not delivered")
        
        # Close consumer
        self.consumer.close()
        logger.info("Consumer stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    # Set running flag to False
    if hasattr(signal_handler, 'consumer'):
        signal_handler.consumer.running = False


def main():
    """Main entry point"""
    consumer = InventoryConsumer()
    
    # Register signal handlers
    signal_handler.consumer = consumer
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start consuming
    consumer.start()


if __name__ == '__main__':
    main()
