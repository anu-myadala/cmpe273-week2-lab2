# Campus Food Ordering - Communication Models Lab

A comprehensive implementation of a campus food ordering system in three different communication paradigms to understand trade-offs between synchronous, asynchronous, and streaming architectures.

## 📋 Overview

This project demonstrates three different architectural approaches for implementing the same food ordering workflow:

1. **Synchronous REST** - Direct HTTP calls between services
2. **Asynchronous RabbitMQ** - Message queue-based communication
3. **Streaming Kafka** - Event streaming platform

Each implementation handles the same business logic (order → inventory → notification) but showcases different trade-offs in terms of latency, coupling, scalability, and complexity.

## 🎯 Learning Objectives

- Understand **synchronous vs asynchronous** communication patterns
- Learn **message queuing** with RabbitMQ (idempotency, DLQ, resilience)
- Explore **event streaming** with Kafka (replay, partitions, consumer groups)
- Analyze **trade-offs**: latency, coupling, scalability, complexity
- Practice **Docker containerization** and **microservices** patterns
- Implement **real-world testing** scenarios (failures, delays, load)

## 🏗️ Architecture Overview

### Part A: Synchronous REST

```
Client → OrderService → InventoryService → NotificationService
         (waits)        (waits)           (returns)
         
Total Latency = Sum of all services
```

**Characteristics:**
- Simple request-response pattern
- Immediate feedback
- Tight coupling (cascading failures)
- Latency = sum of all services

### Part B: Async RabbitMQ

```
Client → OrderService → RabbitMQ → InventoryService → RabbitMQ → NotificationService
         (202)          (queue)     (consumer)         (queue)     (consumer)
         
Client Latency = Order service only (~15ms)
Processing happens asynchronously
```

**Characteristics:**
- Loose coupling via message queues
- Resilient (messages persist during outages)
- Idempotency (duplicate detection)
- Dead Letter Queue (poison message handling)

### Part C: Streaming Kafka

```
Client → Producer → Kafka → [Inventory Consumer, Analytics Consumer, ...]
         (202)      (log)    (independent groups)
         
Multiple consumers process same events independently
Full event replay capability
```

**Characteristics:**
- High throughput (1000+ events/second)
- Event sourcing & replay
- Multiple independent consumers
- Horizontal scalability

## 📊 Comparison Table

| Aspect | Sync REST | Async (RabbitMQ) | Streaming (Kafka) |
|--------|-----------|------------------|-------------------|
| **Response Time** | Slow (sum of all) | Fast (202) | Fast (202) |
| **Client Latency (P50)** | 2040ms | 15ms | 12ms |
| **Throughput** | ~50/s | ~500-1000/s | ~1000-5000/s |
| **Latency Impact** | Cascading | Isolated | Isolated |
| **Failure Recovery** | Immediate fail | Retry + DLQ | Replay |
| **Coupling** | Tight | Loose | Loose |
| **Scalability** | Vertical | Horizontal | Massive Horizontal |
| **Complexity** | Low | Medium | High |
| **Data Replay** | No | Limited | Full |
| **Memory Required** | 2GB | 4GB | 8GB+ |
| **Infrastructure** | Docker | Docker + RabbitMQ | Docker + Kafka + Zookeeper |
| **Best For** | Simple CRUD | Workflows | High-volume + Analytics |

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (latest versions)
- **Python 3.11+** (for running tests)
- **8GB RAM** minimum (for Kafka; 2-4GB for others)
- **Available Ports**: See each part's README

### Part A: Synchronous REST

```bash
cd sync-rest
docker-compose up --build

# In another terminal
cd tests
python test_baseline.py
python test_delay.py
python test_failure.py
```

**Ports:** 8001 (Order), 8002 (Inventory), 8003 (Notification)

### Part B: Async RabbitMQ

```bash
cd async-rabbitmq
docker compose up -d --build

# In another terminal (from async-rabbitmq/ directory)
bash tests/test_backlog_drain.sh
bash tests/test_idempotency.sh
bash tests/test_dlq.sh
```

**Ports:** 8001 (Order), 5672 (RabbitMQ), 15672 (Management UI)

**RabbitMQ UI:** http://localhost:15672 (guest/guest)

### Part C: Streaming Kafka

```bash
cd streaming-kafka
docker-compose up --build

# Wait 60 seconds for Kafka initialization

# In another terminal
cd tests
python produce_10k.py
python test_lag.py
python test_replay.py
```

**Ports:** 8201 (Producer), 9092 (Kafka), 2181 (Zookeeper)

## 📁 Repository Structure

```
cmpe273-comm-models-lab/
├── README.md                           # This file
├── common/
│   ├── README.md                        # Common utilities docs
│   └── ids.py                           # Shared ID/timestamp generation
│
├── sync-rest/                           # Part A: Synchronous REST
│   ├── README.md                        # Setup & architecture
│   ├── RESULTS.md                       # Test results & analysis
│   ├── docker-compose.yml
│   ├── order_service/                   # Port 8001
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app.py
│   ├── inventory_service/               # Port 8002
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app.py
│   ├── notification_service/            # Port 8003
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app.py
│   └── tests/
│       ├── README.md
│       ├── test_baseline.py             # Baseline latency
│       ├── test_delay.py                # Delay injection
│       └── test_failure.py              # Failure injection
│
├── async-rabbitmq/                      # Part B: Async RabbitMQ
│   ├── submission.md                    # Test results & analysis
│   ├── docker-compose.yml
│   ├── broker/
│   │   └── README.md                    # Exchange/queue topology docs
│   ├── order_service/                   # Port 8001
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app.py
│   ├── inventory_service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app.py
│   ├── notification_service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app.py
│   └── tests/
│       ├── test_backlog_drain.sh        # Service outage & recovery
│       ├── test_idempotency.sh          # Duplicate detection
│       └── test_dlq.sh                  # Poison message handling
│
└── streaming-kafka/                     # Part C: Streaming Kafka
    ├── README.md                        # Setup & architecture
    ├── RESULTS.md                       # Test results & analysis
    ├── docker-compose.yml
    ├── producer_order/                  # Port 8201
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── app.py
    │   └── producer.py
    ├── inventory_consumer/
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── consumer.py
    ├── analytics_consumer/
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── consumer.py
    │   └── metrics.py
    └── tests/
        ├── README.md
        ├── produce_10k.py               # High volume test
        ├── test_lag.py                  # Consumer lag test
        ├── test_replay.py               # Event replay test
        └── reset_offset.sh              # Offset reset script
```

## 🔧 Technology Stack

**Languages & Frameworks:**
- Python 3.11
- Flask (REST APIs)
- Pika (RabbitMQ client)
- confluent-kafka-python (Kafka client)

**Infrastructure:**
- Docker & Docker Compose
- RabbitMQ 3.12 with management plugin
- Apache Kafka 3.6 (Confluent 7.5.0)
- Zookeeper 3.8

**Testing:**
- Python requests library
- Custom latency measurement
- CSV/JSON export for results

## 📖 Detailed Documentation

Each part has comprehensive documentation:

### Part A: Synchronous REST
- **[sync-rest/README.md](sync-rest/README.md)** - Architecture, setup, API specs
- **[sync-rest/RESULTS.md](sync-rest/RESULTS.md)** - Test results, latency analysis, trade-offs
- **[sync-rest/tests/README.md](sync-rest/tests/README.md)** - Test instructions

### Part B: Async RabbitMQ
- **[async-rabbitmq/submission.md](async-rabbitmq/submission.md)** - Backlog recovery, idempotency, DLQ analysis
- **[async-rabbitmq/broker/README.md](async-rabbitmq/broker/README.md)** - Exchange/queue topology docs

### Part C: Streaming Kafka
- **[streaming-kafka/README.md](streaming-kafka/README.md)** - Architecture, Kafka config, setup
- **[streaming-kafka/RESULTS.md](streaming-kafka/RESULTS.md)** - Throughput, replay, scaling analysis
- **[streaming-kafka/tests/README.md](streaming-kafka/tests/README.md)** - Test instructions

## 🧪 Testing Summary

### Synchronous REST Tests

| Test | What It Shows | Key Insight |
|------|---------------|-------------|
| Baseline | Normal latency (~30ms) | Fast when all services healthy |
| Delay | Cascading delays (+2000ms) | Downstream delays affect all callers |
| Failure | Immediate failures (100%) | One service down = entire flow fails |

### Async RabbitMQ Tests

| Test | What It Shows | Key Insight |
|------|---------------|-------------|
| Backlog Drain | Messages queue during outages, drain on restart | No message loss, durable queues preserve messages |
| Idempotency | Duplicate detection via in-memory set | Safe to retry, at-least-once delivery |
| DLQ | Malformed message routed to dead letter queue | Bad messages don't block queue, available for inspection |

### Streaming Kafka Tests

| Test | What It Shows | Key Insight |
|------|---------------|-------------|
| 10K Volume | High throughput (~2000/s) | Batch API critical, scales linearly |
| Lag | Backpressure handling | Lag builds then drains, no loss |
| Replay | Event sourcing | Deterministic reprocessing |

## 💡 Key Concepts

### Synchronous vs Asynchronous

**Synchronous:**
```python
result = call_service_1()  # Wait
result = call_service_2()  # Wait
return result              # Finally return
```
- Client waits for entire chain
- Latency = sum of all services
- Simple but brittle

**Asynchronous:**
```python
publish_event()            # Don't wait
return "202 Accepted"      # Return immediately
# Processing happens in background
```
- Client gets immediate response
- Processing decoupled
- Resilient but complex

### Message Queues vs Event Streams

**Message Queues (RabbitMQ):**
- Messages consumed and removed
- Work distribution (one consumer gets each message)
- Good for workflows and task queues

**Event Streams (Kafka):**
- Events persist in log (retained)
- Multiple consumers read same events
- Good for analytics and event sourcing

### Idempotency

Processing the same message multiple times produces same result:

```python
# Non-idempotent (BAD)
balance += 100  # Replay = double credit!

# Idempotent (GOOD)
if event_id not in processed:
    balance += 100
    processed.add(event_id)
```

### Event Replay

Reprocessing historical events from beginning:

```bash
# Reset Kafka consumer offset
kafka-consumer-groups --reset-offsets --to-earliest

# Consumer replays all events
# Useful for: bug fixes, new analytics, disaster recovery
```

## 🎓 When to Use Each Pattern

### Use Synchronous REST When:
✓ Simple CRUD operations
✓ Need immediate result
✓ 1-2 services in chain
✓ Low complexity requirement
✓ Internal APIs

### Use Async RabbitMQ When:
✓ Multi-step workflows
✓ Need resilience to outages
✓ Can tolerate eventual consistency
✓ Want loose coupling
✓ Background jobs

### Use Streaming Kafka When:
✓ High volume (1000+ events/s)
✓ Need event replay
✓ Multiple consumers of same data
✓ Event sourcing pattern
✓ Real-time analytics

## 🔬 Results Summary

### Latency Comparison (Client Perspective)

| Metric | Sync REST | Async RabbitMQ | Streaming Kafka |
|--------|-----------|----------------|-----------------|
| P50 | 2040ms | 15ms | 12ms |
| P95 | 2080ms | 25ms | 20ms |
| P99 | 2100ms | 35ms | 30ms |

### Throughput Comparison

| Pattern | Single Request | Batch | Notes |
|---------|----------------|-------|-------|
| Sync REST | ~50/s | N/A | Blocking |
| Async RabbitMQ | ~500/s | ~1000/s | Message broker |
| Streaming Kafka | ~100/s | ~2000-5000/s | Batch critical |

### Failure Behavior

| Scenario | Sync | Async | Streaming |
|----------|------|-------|-----------|
| Service down | ✗ Entire flow fails | ✓ Messages queue | ✓ Messages queue |
| Network blip | ✗ Request lost | ✓ Retry | ✓ Persist & retry |
| High load | ✗ Timeout/fail | ✓ Backpressure | ✓ Lag & catch up |

## 🚨 Common Issues & Solutions

### Services won't start
```bash
# Check Docker resources
docker system df
docker system prune -a  # Clean up

# Check port conflicts
lsof -i :8001  # Check if port in use
```

### RabbitMQ connection issues
```bash
# Wait for RabbitMQ to be ready (30s)
docker logs async_rabbitmq

# Check management UI
open http://localhost:15672
```

### Kafka won't start
```bash
# Kafka needs 8GB RAM
# Check Docker memory settings

# Wait 60s for initialization
docker logs streaming_kafka

# Verify Zookeeper is up
docker logs streaming_zookeeper
```

### Tests fail
```bash
# Ensure services are running
docker ps

# Check service health
curl http://localhost:8001/health  # Sync
curl http://localhost:8101/health  # Async
curl http://localhost:8201/health  # Kafka

# Check logs
docker-compose logs --tail=50
```

## 📚 Further Reading

### Synchronous REST
- REST API Design Best Practices
- Timeout strategies
- Circuit breaker pattern

### Asynchronous Messaging
- RabbitMQ documentation: https://www.rabbitmq.com/documentation.html
- Message queue patterns
- Eventual consistency

### Event Streaming
- Kafka documentation: https://kafka.apache.org/documentation/
- Event sourcing pattern
- CQRS (Command Query Responsibility Segregation)

### General Microservices
- Microservices Patterns (Chris Richardson)
- Domain-Driven Design (Eric Evans)
- Building Microservices (Sam Newman)

## 🤝 Contributing

This is a lab project. Feel free to:
- Report issues
- Suggest improvements
- Add new test scenarios
- Enhance documentation

## 📄 License

MIT License - feel free to use for learning and education.

## 👥 Authors

- CMPE 273 - Enterprise Distributed Systems
- San Jose State University

---

**Note:** This project is for educational purposes to demonstrate different communication patterns in distributed systems. Production systems would include additional considerations: security, monitoring, logging, deployment automation, service mesh, etc.
