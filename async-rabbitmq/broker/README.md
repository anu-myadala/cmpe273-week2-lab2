# Broker — RabbitMQ

We're using the official `rabbitmq:3-management` Docker image here, so there's no custom broker code in this folder. RabbitMQ just runs as its own service in `docker-compose.yml`.

## Exchanges

All exchanges are fanout, meaning every message gets copied to all bound queues.

- `order_events` — where OrderService publishes `OrderPlaced` events
- `inventory_events` — where InventoryService publishes `InventoryReserved` or `InventoryFailed`
- `dlx` — dead-letter exchange, catches any messages that get rejected or can't be processed

## Queues

- `inventory_order_queue` — bound to `order_events`, consumed by InventoryService. Has a dead-letter exchange (`dlx`) configured so bad messages get routed there instead of blocking the queue.
- `notification_queue` — bound to `inventory_events`, consumed by NotificationService
- `dead_letter_queue` — bound to `dlx`, not consumed by anything automatically. It's just there so we can inspect failed messages later.

## Management UI

RabbitMQ comes with a web dashboard at http://localhost:15672 (login: guest / guest). Useful for checking queue depths, message rates, and bindings while the stack is running.
