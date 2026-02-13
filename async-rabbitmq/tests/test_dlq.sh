#!/bin/bash
# Test: Send a malformed message and show it lands in the Dead Letter Queue.
#
# Usage: Run from the async-rabbitmq/ directory:
#   docker compose up -d --build
#   bash tests/test_dlq.sh

set -e

RABBIT_API="http://localhost:15672/api"

echo "=== Dead Letter Queue (DLQ) Test ==="

echo ""
echo "1) Publishing a malformed (non-JSON) message to order_events..."
curl -s -u guest:guest -X POST "$RABBIT_API/exchanges/%2F/order_events/publish" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {"delivery_mode": 2},
    "routing_key": "",
    "payload": "THIS IS NOT VALID JSON {{{",
    "payload_encoding": "string"
  }' > /dev/null
echo "   Malformed message published"

echo ""
echo "2) Waiting for inventory_service to reject the message..."
sleep 5

echo ""
echo "3) Checking inventory_service logs..."
docker compose logs --tail=10 inventory_service

echo ""
echo "4) Checking dead_letter_queue for the rejected message..."
DLQ_COUNT=$(curl -s -u guest:guest "$RABBIT_API/queues/%2F/dead_letter_queue" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('messages', 0))")
echo "   Messages in dead_letter_queue: $DLQ_COUNT"

echo ""
echo "5) Reading message from DLQ..."
RESULT=$(curl -s -u guest:guest -X POST "$RABBIT_API/queues/%2F/dead_letter_queue/get" \
  -H "Content-Type: application/json" \
  -d '{"count": 1, "ackmode": "ack_requeue_true", "encoding": "auto"}')
echo "   DLQ content: $RESULT"

echo ""
echo "=== DLQ Test Complete ==="
echo "Expected: Malformed message rejected by InventoryService and routed to dead_letter_queue."
