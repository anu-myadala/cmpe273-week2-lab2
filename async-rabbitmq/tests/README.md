# Async RabbitMQ Tests

This directory contains automated tests for the async RabbitMQ implementation.

## Prerequisites

- Docker and Docker Compose installed
- Services running: `docker-compose up -d`
- Python 3.11+ with dependencies: `pip install requests pika`

## Tests

### 1. Resilience Test (`test_resilience.py`)

Tests message queueing and resilience when consumers are unavailable.

**What it does:**
1. Publishes 50 orders while all services are running
2. Stops InventoryService
3. Publishes 50 more orders (these queue up in RabbitMQ)
4. Waits 60 seconds
5. Restarts InventoryService
6. Monitors backlog draining
7. Verifies all 100 orders were processed

**How to run:**
```bash
cd async-rabbitmq/tests
python test_resilience.py
```

**Expected output:**
- All 100 orders should be created
- Messages queue in RabbitMQ when consumer is down
- Consumer processes backlog after restart
- No message loss

**Key Learning:**
- Demonstrates decoupling - producer works even when consumer is down
- Shows message persistence in RabbitMQ
- Illustrates graceful handling of service outages

### 2. Idempotency Test (`test_idempotency.py`)

Verifies that duplicate events are detected and not processed twice.

**What it does:**
1. Creates an event with specific event_id
2. Publishes event to RabbitMQ
3. Re-publishes same event (duplicate)
4. Publishes again (third time)
5. Checks logs for duplicate detection

**How to run:**
```bash
cd async-rabbitmq/tests
python test_idempotency.py
```

**Expected output:**
- Event processed once
- Duplicate events detected and skipped
- "Duplicate event detected" messages in logs

**To verify:**
```bash
docker logs async_inventory_service | grep -i duplicate
docker logs async_inventory_service | grep <event_id>
```

**Key Learning:**
- Event_id tracking prevents duplicate processing
- Critical for at-least-once delivery semantics
- Prevents double-charging, double-reservations, etc.

### 3. DLQ Test (`test_dlq.py`)

Tests poison message handling and dead letter queue routing.

**What it does:**
1. Sends malformed JSON message
2. Verifies message is rejected and routed to DLQ
3. Sends 10 valid messages
4. Verifies valid messages process normally
5. Checks DLQ contents

**How to run:**
```bash
cd async-rabbitmq/tests
python test_dlq.py
```

**Expected output:**
- Poison message rejected and sent to DLQ
- Valid messages process successfully
- Service continues running normally

**To verify:**
1. Check service logs:
```bash
docker logs async_inventory_service | grep -i "invalid json"
```

2. Check RabbitMQ Management UI:
   - Navigate to http://localhost:15672 (guest/guest)
   - Go to Queues tab
   - Look for `order-events-dlq` queue
   - Should have 1+ message

3. View DLQ messages:
   - Click on `order-events-dlq`
   - Click "Get messages"
   - See the poison message content

**Key Learning:**
- DLQ isolates problem messages
- Prevents poison messages from blocking queue
- Allows debugging without losing messages
- Service continues processing valid messages

## Running All Tests

Run all tests in sequence:

```bash
cd async-rabbitmq/tests
python test_resilience.py
python test_idempotency.py
python test_dlq.py
```

## Monitoring Tools

### RabbitMQ Management UI
- URL: http://localhost:15672
- Credentials: guest/guest
- Use to monitor:
  - Queue depths
  - Message rates
  - Consumer status
  - Exchanges and bindings

### Docker Logs
```bash
# View all logs
docker logs async_order_service
docker logs async_inventory_service
docker logs async_notification_service

# Follow logs in real-time
docker logs -f async_inventory_service

# Search logs
docker logs async_inventory_service | grep "duplicate"
docker logs async_inventory_service | grep "DLQ"
```

### Queue Inspection
```bash
# Check queue depths
docker exec async_rabbitmq rabbitmqctl list_queues name messages

# Check exchanges
docker exec async_rabbitmq rabbitmqctl list_exchanges

# Check bindings
docker exec async_rabbitmq rabbitmqctl list_bindings
```

## Interpreting Results

### Resilience Test
- **Good:** All 100 orders processed, no loss during outage
- **Shows:** Message persistence and queueing
- **Benefit:** Services can be deployed independently

### Idempotency Test
- **Good:** Event processed once, duplicates detected
- **Shows:** Safe to retry/replay messages
- **Benefit:** Exactly-once semantics with at-least-once delivery

### DLQ Test
- **Good:** Poison message isolated, service continues
- **Shows:** Error isolation and handling
- **Benefit:** One bad message doesn't break entire system

## Troubleshooting

### Services won't start
```bash
docker-compose down
docker-compose up --build
```

### RabbitMQ connection errors
- Wait 30 seconds after starting RabbitMQ
- Check RabbitMQ is healthy: `docker ps`
- Check logs: `docker logs async_rabbitmq`

### Messages not processing
- Check consumer is running: `docker ps`
- Check logs: `docker logs async_inventory_service`
- Check queue depth in RabbitMQ UI
- Verify exchange/queue bindings

## Cleanup

Stop services:
```bash
cd ..
docker-compose down
```

Clean up volumes:
```bash
docker-compose down -v
```
