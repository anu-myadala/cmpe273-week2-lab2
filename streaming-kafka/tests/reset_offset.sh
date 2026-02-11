#!/bin/bash
# Reset consumer offset for replay testing

echo "Resetting consumer group offsets to earliest..."

docker exec streaming_kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group analytics-group \
  --reset-offsets \
  --to-earliest \
  --topic order-events \
  --execute

docker exec streaming_kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group analytics-group \
  --reset-offsets \
  --to-earliest \
  --topic inventory-events \
  --execute

echo "Offset reset complete!"
echo "Analytics consumer will now reprocess all events from the beginning."
