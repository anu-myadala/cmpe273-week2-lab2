"""
Kafka Consumer for Analytics
Consumes from multiple topics and computes real-time metrics
"""
from confluent_kafka import Consumer, KafkaError
import json
import logging
import os
import signal
import time

from metrics import MetricsCalculator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class AnalyticsConsumer:
    def __init__(self):
        self.kafka_broker = os.getenv('KAFKA_BROKER', 'kafka:9092')
        self.group_id = 'analytics-group'
        self.topics = ['order-events', 'inventory-events']
        self.running = True
        self.metrics = MetricsCalculator()
        self.metrics_interval = 10  # Log metrics every 10 seconds
        self.last_metrics_time = time.time()

        # Optional throttling for lag demos
        # Set PROCESSING_DELAY_MS to slow down per-message processing.
        try:
            self.processing_delay_ms = int(os.getenv('PROCESSING_DELAY_MS', '0'))
        except ValueError:
            self.processing_delay_ms = 0
        
        # Consumer configuration
        consumer_config = {
            'bootstrap.servers': self.kafka_broker,
            'group.id': self.group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False  # Manual commit for replay capability
        }
        
        self.consumer = Consumer(consumer_config)
        self.consumer.subscribe(self.topics)
        
        logger.info(f"Analytics consumer initialized")
        logger.info(f"Consuming from: {', '.join(self.topics)}")
        logger.info(f"Group ID: {self.group_id}")
    
    def process_message(self, msg):
        """Process an event and update metrics"""
        try:
            # Parse message
            event = json.loads(msg.value().decode('utf-8'))
            
            event_type = event.get('event_type')
            timestamp = event.get('timestamp')
            
            # Add to metrics
            self.metrics.add_event(event_type, timestamp)
            
            # Log periodically
            current_time = time.time()
            if current_time - self.last_metrics_time >= self.metrics_interval:
                metrics = self.metrics.get_metrics()
                logger.info(f"=== METRICS ===")
                logger.info(f"  Orders/min: {metrics['orders_per_minute']}")
                logger.info(f"  Total orders: {metrics['total_orders']}")
                logger.info(f"  Reserved: {metrics['reserved_orders']}")
                logger.info(f"  Failed: {metrics['failed_orders']}")
                logger.info(f"  Success rate: {metrics['success_rate_percent']}%")
                logger.info(f"  Failure rate: {metrics['failure_rate_percent']}%")
                logger.info(f"  Throughput: {metrics['throughput_events_per_second']} events/s")
                logger.info(f"===============")
                
                # Save to file
                self.metrics.save_to_file()
                
                self.last_metrics_time = current_time
            
            # Simulate slower consumer if requested
            if self.processing_delay_ms > 0:
                time.sleep(self.processing_delay_ms / 1000.0)

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
                    # Commit offset manually (for replay capability)
                    self.consumer.commit(msg)
                else:
                    logger.warning(f"Failed to process message")
        
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            self.stop()
    
    def stop(self):
        """Stop consumer and save final metrics"""
        logger.info("Stopping consumer...")
        self.running = False
        
        # Save final metrics
        metrics = self.metrics.get_metrics()
        logger.info(f"\n=== FINAL METRICS ===")
        logger.info(f"  Total orders: {metrics['total_orders']}")
        logger.info(f"  Reserved: {metrics['reserved_orders']}")
        logger.info(f"  Failed: {metrics['failed_orders']}")
        logger.info(f"  Success rate: {metrics['success_rate_percent']}%")
        logger.info(f"  Failure rate: {metrics['failure_rate_percent']}%")
        logger.info(f"  Elapsed: {metrics['elapsed_seconds']}s")
        logger.info(f"  Avg throughput: {metrics['throughput_events_per_second']} events/s")
        logger.info(f"=====================\n")
        
        self.metrics.save_to_file()
        
        # Close consumer
        self.consumer.close()
        logger.info("Consumer stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    if hasattr(signal_handler, 'consumer'):
        signal_handler.consumer.running = False


def main():
    """Main entry point"""
    consumer = AnalyticsConsumer()
    
    # Register signal handlers
    signal_handler.consumer = consumer
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start consuming
    consumer.start()


if __name__ == '__main__':
    main()
