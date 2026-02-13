#!/bin/bash
# Test: Re-deliver the same OrderPlaced message twice and ensure no double reserve.
#
# Usage: Run from the async-rabbitmq/ directory:
#   docker compose up -d --build
#   bash tests/test_idempotency.sh

set -e

BASE_URL="http://localhost:8001"
RABBIT_API="http://localhost:15672/api"

echo "=== Idempotency Test ==="

echo ""
echo "1) Publishing a single order..."
RESPONSE=$(curl -s -X POST "$BASE_URL/order" \
  -H "Content-Type: application/json" \
  -d '{"item": "pizza", "qty": 1}')
ORDER_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['order_id'])")
echo "   Created order: $ORDER_ID"

echo ""
echo "2) Waiting for inventory to process..."
sleep 3

echo ""
echo "3) Re-publishing the same OrderPlaced event (duplicate) via RabbitMQ Management API..."
PAYLOAD=$(python3 -c "
import json, time
msg = json.dumps({
    'event': 'OrderPlaced',
    'order_id': '$ORDER_ID',
    'item': 'pizza',
    'qty': 1,
    'timestamp': time.time()
})
body = {
    'properties': {'delivery_mode': 2},
    'routing_key': '',
    'payload': msg,
    'payload_encoding': 'string'
}
print(json.dumps(body))
")

curl -s -u guest:guest -X POST "$RABBIT_API/exchanges/%2F/order_events/publish" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" > /dev/null
echo "   Duplicate message published"

echo ""
echo "4) Waiting for inventory to process duplicate..."
sleep 3

echo ""
echo "5) Checking inventory_service logs for idempotency handling..."
docker compose logs --tail=15 inventory_service

echo ""
echo "=== Idempotency Test Complete ==="
echo "Expected: Second message skipped with 'Duplicate order ... skipping' log."
