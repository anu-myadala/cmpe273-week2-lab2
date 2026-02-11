# Synchronous REST Architecture

This implementation demonstrates a campus food ordering system using synchronous REST APIs. Services communicate directly via HTTP requests, with each service waiting for responses before proceeding.

## Architecture

```
┌──────────────┐
│    Client    │
└──────┬───────┘
       │ POST /order
       ▼
┌──────────────────┐
│  OrderService    │ (Port 8001)
│  - Create order  │
└──────┬───────────┘
       │ 1. POST /reserve (synchronous)
       ▼
┌──────────────────┐
│ InventoryService │ (Port 8002)
│  - Reserve items │
│  - Fault inject  │
└──────────────────┘
       │
       │ 2. POST /send (synchronous)
       ▼
┌─────────────────────┐
│ NotificationService │ (Port 8003)
│  - Send alerts      │
└─────────────────────┘
```

### Request Flow

1. Client sends order request to OrderService
2. OrderService synchronously calls InventoryService to reserve items
3. If inventory succeeds, OrderService synchronously calls NotificationService
4. OrderService returns final response to client
5. **Total latency = OrderService + InventoryService + NotificationService**

## Services

### OrderService (Port 8001)

Main orchestrator that handles order creation.

**Endpoints:**
- `GET /health` - Health check
- `POST /order` - Create new order

**Request Body:**
```json
{
  "user_id": "string",
  "item": "string",
  "quantity": 1
}
```

**Success Response (200):**
```json
{
  "order_id": "uuid",
  "status": "completed",
  "timestamp": "ISO-8601",
  "user_id": "string",
  "item": "string",
  "quantity": 1
}
```

**Failure Response (500/504):**
```json
{
  "order_id": "uuid",
  "status": "failed",
  "reason": "Inventory service timeout",
  "details": {}
}
```

### InventoryService (Port 8002)

Handles inventory reservation with fault injection capabilities.

**Endpoints:**
- `GET /health` - Health check
- `POST /reserve` - Reserve inventory
- `POST /config` - Configure fault injection

**Reserve Request:**
```json
{
  "order_id": "uuid",
  "item": "string",
  "quantity": 1
}
```

**Config Request:**
```json
{
  "delay_seconds": 0-10,
  "failure_enabled": true/false
}
```

### NotificationService (Port 8003)

Sends order confirmation notifications.

**Endpoints:**
- `GET /health` - Health check
- `POST /send` - Send notification

**Request:**
```json
{
  "order_id": "uuid",
  "user_id": "string",
  "item": "string"
}
```

## Environment Variables

### OrderService
- `PORT` - Service port (default: 8001)
- `INVENTORY_SERVICE_URL` - Inventory service URL
- `NOTIFICATION_SERVICE_URL` - Notification service URL
- `REQUEST_TIMEOUT` - Request timeout in seconds (default: 5)

### InventoryService
- `PORT` - Service port (default: 8002)

### NotificationService
- `PORT` - Service port (default: 8003)

## Building and Running

### Prerequisites
- Docker and Docker Compose
- 2GB RAM minimum
- Ports 8001-8003 available

### Start Services

```bash
cd sync-rest
docker-compose up --build
```

Services will be available at:
- OrderService: http://localhost:8001
- InventoryService: http://localhost:8002
- NotificationService: http://localhost:8003

### Verify Services

```bash
# Check all services are healthy
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Create an Order

```bash
curl -X POST http://localhost:8001/order \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "item": "Burger",
    "quantity": 2
  }'
```

### Configure Fault Injection

Add 2-second delay:
```bash
curl -X POST http://localhost:8002/config \
  -H "Content-Type: application/json" \
  -d '{"delay_seconds": 2, "failure_enabled": false}'
```

Enable failures:
```bash
curl -X POST http://localhost:8002/config \
  -H "Content-Type: application/json" \
  -d '{"delay_seconds": 0, "failure_enabled": true}'
```

Reset to normal:
```bash
curl -X POST http://localhost:8002/config \
  -H "Content-Type: application/json" \
  -d '{"delay_seconds": 0, "failure_enabled": false}'
```

## Running Tests

See [tests/README.md](tests/README.md) for detailed test instructions.

Quick start:

```bash
# Install Python dependencies
pip install requests

# Run all tests
cd tests
python test_baseline.py
python test_delay.py
python test_failure.py
```

## Stopping Services

```bash
docker-compose down
```

Clean up volumes:
```bash
docker-compose down -v
```

## Key Characteristics

### Advantages ✓
- **Simple to understand** - Linear request-response flow
- **Immediate feedback** - Client knows result instantly
- **Easy debugging** - Clear call stack and error propagation
- **Strong consistency** - Operations complete before returning
- **No message broker** - Lower infrastructure complexity

### Disadvantages ✗
- **Cascading delays** - Downstream latency affects all callers
- **Tight coupling** - Services must all be available
- **Cascading failures** - One service down breaks entire flow
- **Limited scalability** - Synchronous waiting wastes resources
- **No retry mechanism** - Failed requests must be retried by client
- **Blocking** - Caller waits for entire chain to complete

## When to Use Synchronous REST

✓ **Good for:**
- Simple CRUD operations
- Immediate result required
- Small number of dependent services (1-2)
- Low latency requirements
- Operations that must complete atomically
- Internal APIs with predictable load

✗ **Avoid for:**
- Long-running operations
- Multiple dependent services (3+)
- High latency tolerance acceptable
- Need for resilience and decoupling
- Variable or unpredictable load
- Operations that can complete asynchronously

## Troubleshooting

### Service won't start
- Check ports 8001-8003 are not in use
- Verify Docker has enough memory (2GB+)
- Check logs: `docker-compose logs <service_name>`

### Timeouts
- Increase `REQUEST_TIMEOUT` environment variable
- Check network connectivity between containers
- Verify services are healthy with `/health` endpoints

### High latency
- Check for configured delays: `curl http://localhost:8002/config`
- Monitor container resources: `docker stats`
- Review service logs for errors

## Architecture Trade-offs

This synchronous REST implementation demonstrates the classic trade-offs:

1. **Simplicity vs Resilience**: Easy to build but brittle under failure
2. **Consistency vs Availability**: Strong consistency but poor availability
3. **Latency Coupling**: All services in the chain contribute to total latency
4. **Error Propagation**: Errors bubble up immediately but take down entire flow

Compare with:
- **Async (RabbitMQ)**: Better resilience, decoupling, but eventual consistency
- **Streaming (Kafka)**: Best for high throughput, replay, but highest complexity
