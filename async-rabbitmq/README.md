# Async Architecture with RabbitMQ

This implementation demonstrates a campus food ordering system using asynchronous message queuing with RabbitMQ. Services communicate via message queues, providing decoupling, resilience, and eventual consistency.

## Architecture

```
┌──────────────┐
│    Client    │
└──────┬───────┘
       │ POST /order (202 Accepted)
       ▼
┌─────────────────┐         ┌──────────────────┐
│  OrderService   │────────>│   RabbitMQ       │
│  - Accept order │ publish │   - orders       │
│  - Save local   │         │     exchange     │
│  - Return 202   │         │   - order-events │
└─────────────────┘         │     queue        │
                            └────┬─────────────┘
                                 │ consume
                                 ▼
                          ┌─────────────────────┐
                          │ InventoryService    │
                          │ - Check inventory   │
                          │ - Idempotency check │
                          │ - Reserve/Fail      │
                          └──────┬──────────────┘
                                 │ publish
                                 ▼
                          ┌──────────────────┐
                          │   RabbitMQ       │
                          │   - inventory    │
                          │     exchange     │
                          │   - inventory-   │
                          │     events queue │
                          └────┬─────────────┘
                               │ consume (filtered)
                               ▼
                        ┌─────────────────────┐
                        │ NotificationService │
                        │ - Send alerts       │
                        └─────────────────────┘
```

### Message Flow

1. Client sends order → OrderService
2. OrderService saves order locally + publishes event → RabbitMQ
3. OrderService returns 202 immediately (async)
4. InventoryService consumes event from queue
5. InventoryService checks idempotency
6. InventoryService reserves inventory
7. InventoryService publishes result → RabbitMQ
8. NotificationService consumes InventoryReserved events
9. NotificationService sends notification

**Key Difference from Sync**: Client gets immediate 202 response, processing happens asynchronously in background.

## Services

### OrderService (Port 8101)

REST API that accepts orders and publishes events.

**Endpoints:**
- `GET /health` - Health check
- `POST /order` - Create order (returns 202 immediately)
- `GET /orders` - List all orders
- `GET /orders/{order_id}` - Get specific order

**POST /order Request:**
```json
{
  "user_id": "string",
  "item": "string",
  "quantity": 1
}
```

**Response (202 Accepted):**
```json
{
  "order_id": "uuid",
  "status": "accepted",
  "message": "Order received and being processed",
  "timestamp": "ISO-8601"
}
```

**Event Published:**
```json
{
  "event_id": "uuid",
  "event_type": "OrderPlaced",
  "order_id": "uuid",
  "timestamp": "ISO-8601",
  "user_id": "string",
  "item": "string",
  "quantity": 1
}
```

### InventoryService (Consumer)

Background consumer that processes orders.

**Functionality:**
- Consumes from `order-events` queue
- Checks event_id for duplicates (idempotency)
- Simulates inventory check (90% success rate)
- Reserves inventory on success
- Publishes InventoryReserved or InventoryFailed event
- Handles poison messages (sends to DLQ)

**Idempotency:**
```python
if event_id in processed_events:
    logger.info("Duplicate detected, skipping")
    ack_message()
    return

# Process event...
processed_events.add(event_id)
ack_message()
```

**Events Published:**
```json
{
  "event_id": "uuid",
  "event_type": "InventoryReserved|InventoryFailed",
  "order_id": "uuid",
  "timestamp": "ISO-8601",
  "user_id": "string",
  "item": "string",
  "quantity": 1
}
```

### NotificationService (Consumer)

Background consumer that sends notifications.

**Functionality:**
- Consumes from `inventory-events` queue
- Filters for InventoryReserved events only
- Sends notifications (logs to console)
- Acknowledges messages

## RabbitMQ Topology

### Exchanges

1. **orders** (topic exchange, durable)
   - Receives OrderPlaced events from OrderService

2. **inventory** (topic exchange, durable)
   - Receives InventoryReserved/Failed events from InventoryService

3. **dlx** (dead letter exchange, topic, durable)
   - Receives rejected/failed messages

### Queues

1. **order-events** (durable)
   - Binds to: `orders` exchange, routing key: `order.placed`
   - Consumed by: InventoryService
   - DLQ: Configured with x-dead-letter-exchange
   - Prefetch: 10

2. **inventory-events** (durable)
   - Binds to: `inventory` exchange, routing key: `inventory.reserved`
   - Consumed by: NotificationService
   - Prefetch: 10

3. **order-events-dlq** (dead letter queue, durable)
   - Receives: Rejected messages from order-events
   - Purpose: Store poison messages for debugging

### Routing Keys

- `order.placed` - OrderPlaced events
- `inventory.reserved` - InventoryReserved events
- `inventory.failed` - InventoryFailed events
- `order-events-dlq` - DLQ routing

## Configuration

### Environment Variables

**OrderService:**
- `PORT` - Service port (default: 8101)
- `RABBITMQ_HOST` - RabbitMQ hostname
- `RABBITMQ_PORT` - RabbitMQ port (default: 5672)
- `RABBITMQ_USER` - Username (default: guest)
- `RABBITMQ_PASSWORD` - Password (default: guest)

**InventoryService:**
- Same RabbitMQ connection settings

**NotificationService:**
- Same RabbitMQ connection settings

### RabbitMQ Settings

- Port: 5672 (AMQP)
- Management UI: 15672
- Default credentials: guest/guest
- Persistence: Enabled
- Message delivery mode: 2 (persistent)
- Manual acknowledgment: Enabled
- Prefetch count: 10

## Building and Running

### Prerequisites
- Docker and Docker Compose
- 4GB RAM minimum
- Ports 5672, 8101, 15672 available

### Start Services

```bash
cd async-rabbitmq
docker-compose up --build
```

Services will start in order:
1. RabbitMQ (wait for healthy)
2. OrderService
3. InventoryService (consumer)
4. NotificationService (consumer)

### Verify Services

```bash
# Check OrderService
curl http://localhost:8101/health

# Check RabbitMQ Management UI
# Open browser: http://localhost:15672
# Login: guest/guest
```

### Create an Order

```bash
curl -X POST http://localhost:8101/order \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "item": "Burger",
    "quantity": 2
  }'
```

Response (immediate):
```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "Order received and being processed",
  "timestamp": "2026-02-11T00:00:00.000000Z"
}
```

### Check Order Status

```bash
curl http://localhost:8101/orders/550e8400-e29b-41d4-a716-446655440000
```

### List All Orders

```bash
curl http://localhost:8101/orders
```

### Monitor Processing

```bash
# Watch inventory service process orders
docker logs -f async_inventory_service

# Watch notifications
docker logs -f async_notification_service

# Check RabbitMQ Management UI
# http://localhost:15672 → Queues tab
```

## Running Tests

See [tests/README.md](tests/README.md) for detailed test instructions.

Quick start:

```bash
pip install requests pika

cd tests
python test_resilience.py
python test_idempotency.py
python test_dlq.py
```

## RabbitMQ Management UI

Access at http://localhost:15672 (guest/guest)

**Useful views:**
- **Queues**: Monitor message counts, rates
- **Exchanges**: View topology
- **Connections**: Active consumers
- **Channels**: Message flow

**Key metrics:**
- Ready: Messages waiting to be consumed
- Unacked: Messages being processed
- Total: Total messages in queue

## Stopping Services

```bash
docker-compose down
```

Clean up volumes and data:
```bash
docker-compose down -v
```

## Key Characteristics

### Advantages ✓

1. **Decoupling** - Services don't need to know about each other
2. **Resilience** - Messages queue if consumer is down
3. **Scalability** - Can scale consumers independently
4. **Async Response** - Client gets immediate 202, doesn't wait
5. **Retry Logic** - Built-in message redelivery
6. **Backpressure** - Prefetch count prevents overload
7. **DLQ** - Poison messages don't block queue

### Disadvantages ✗

1. **Complexity** - More moving parts (RabbitMQ)
2. **Eventual Consistency** - Order accepted ≠ order completed
3. **Debugging** - Harder to trace across services
4. **Message Order** - Not guaranteed without special config
5. **Infrastructure** - Requires RabbitMQ cluster
6. **Monitoring** - Need to watch queues, consumers

## When to Use Async/RabbitMQ

### ✓ Good Use Cases

1. **Workflows** - Multi-step processes that can be async
2. **High Volume** - Need to handle traffic spikes
3. **Background Jobs** - Long-running tasks
4. **Microservices** - Decoupling services
5. **Event-Driven** - Publish-subscribe patterns
6. **Resilience** - Can't afford to lose requests

### ✗ Avoid When

1. **Immediate Results** - Client needs synchronous response
2. **Simple CRUD** - Overhead not justified
3. **Strong Consistency** - Need ACID transactions
4. **Low Complexity** - Don't need decoupling

## Troubleshooting

### Service won't connect to RabbitMQ
- Wait 30s for RabbitMQ to fully start
- Check: `docker logs async_rabbitmq`
- Verify network: `docker network inspect async-rabbitmq_async-network`

### Messages not processing
- Check consumer logs: `docker logs async_inventory_service`
- Check queue in UI: http://localhost:15672
- Verify queue bindings in RabbitMQ

### High message backlog
- Scale consumers: `docker-compose up --scale inventory_service=3`
- Check consumer performance
- Increase prefetch_count

### Poison messages
- Check DLQ: http://localhost:15672 → order-events-dlq
- View message content in UI
- Fix data format and republish

## Comparison with Sync REST

| Aspect | Sync REST | Async RabbitMQ |
|--------|-----------|----------------|
| Response | Immediate result | 202 Accepted |
| Latency | Sum of all services | Service independent |
| Failure | Entire chain fails | Messages queue |
| Coupling | Tight | Loose |
| Scalability | Limited | High |
| Consistency | Strong | Eventual |
| Complexity | Low | Medium |
| Debugging | Easy | Harder |

## Further Reading

- RabbitMQ documentation: https://www.rabbitmq.com/documentation.html
- Compare with sync-rest/RESULTS.md for sync vs async trade-offs
- Compare with streaming-kafka/RESULTS.md for streaming benefits
