"""
Kafka Producer for OrderService
Publishes order events to Kafka
"""
from confluent_kafka import Producer
import json
import logging
import os

logger = logging.getLogger(__name__)


class OrderProducer:
    def __init__(self):
        self.kafka_broker = os.getenv('KAFKA_BROKER', 'kafka:9092')
        self.topic = 'order-events'
        
        # Producer configuration
        self.config = {
            'bootstrap.servers': self.kafka_broker,
            'client.id': 'order-producer',
            'acks': 'all',  # Wait for all replicas
            'retries': 3,
            'max.in.flight.requests.per.connection': 1  # Ensure ordering
        }
        
        self.producer = Producer(self.config)
        logger.info(f"Kafka producer initialized: {self.kafka_broker}")
    
    def delivery_callback(self, err, msg):
        """Callback for message delivery reports"""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")
    
    def produce_event(self, event):
        """
        Produce an event to Kafka
        
        Args:
            event: Dictionary containing event data
        """
        try:
            # Convert event to JSON
            value = json.dumps(event).encode('utf-8')
            key = event.get('order_id', '').encode('utf-8')
            
            # Produce message
            self.producer.produce(
                topic=self.topic,
                key=key,
                value=value,
                callback=self.delivery_callback
            )
            
            # Trigger callbacks
            self.producer.poll(0)
            
            return True
            
        except Exception as e:
            logger.error(f"Error producing event: {e}")
            return False
    
    def produce_batch(self, events):
        """
        Produce multiple events in batch
        
        Args:
            events: List of event dictionaries
        """
        try:
            for event in events:
                value = json.dumps(event).encode('utf-8')
                key = event.get('order_id', '').encode('utf-8')
                
                self.producer.produce(
                    topic=self.topic,
                    key=key,
                    value=value,
                    callback=self.delivery_callback
                )
            
            # Wait for all messages to be delivered
            self.producer.flush()
            
            logger.info(f"Batch of {len(events)} events produced")
            return True
            
        except Exception as e:
            logger.error(f"Error producing batch: {e}")
            return False
    
    def close(self):
        """Close producer and flush pending messages"""
        try:
            remaining = self.producer.flush(timeout=10)
            if remaining > 0:
                logger.warning(f"{remaining} messages were not delivered")
            logger.info("Producer closed")
        except Exception as e:
            logger.error(f"Error closing producer: {e}")
