#!/bin/bash
# Test: Kill InventoryService for 60s, publish orders, restart, and show backlog drain.
#
# Usage: Run from the async-rabbitmq/ directory:
#   docker compose up -d --build
#   bash tests/test_backlog_drain.sh

set -e

BASE_URL="http://localhost:8001"
RABBIT_API="http://localhost:15672/api"
COMPOSE="docker compose"

echo "=== Backlog Drain Test ==="

echo ""
echo "1) Stopping inventory_service..."
$COMPOSE stop inventory_service

echo ""
echo "2) Publishing 10 orders while inventory_service is down..."
for i in $(seq 1 10); do
  curl -s -X POST "$BASE_URL/order" \
    -H "Content-Type: application/json" \
    -d "{\"item\": \"burger\", \"qty\": 1}" > /dev/null
  echo "   Order $i published"
done

echo ""
echo "3) Checking RabbitMQ queue depth (messages waiting)..."
sleep 2
MESSAGES=$(curl -s -u guest:guest "$RABBIT_API/queues/%2F/inventory_order_queue" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('messages', 0))")
echo "   Messages in inventory_order_queue: $MESSAGES"

echo ""
echo "4) Waiting 10 seconds (simulating downtime)..."
sleep 10

echo ""
echo "5) Restarting inventory_service..."
$COMPOSE start inventory_service

echo ""
echo "6) Waiting for backlog to drain..."
sleep 10

MESSAGES=$(curl -s -u guest:guest "$RABBIT_API/queues/%2F/inventory_order_queue" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('messages', 0))")
echo "   Messages remaining in inventory_order_queue: $MESSAGES"

echo ""
echo "7) Checking inventory_service logs for processed orders..."
$COMPOSE logs --tail=20 inventory_service

echo ""
echo "=== Backlog Drain Test Complete ==="
echo "Expected: All 10 orders processed after restart (0 messages remaining)."
