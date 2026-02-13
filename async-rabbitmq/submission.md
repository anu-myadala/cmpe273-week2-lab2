# Part B: Async Messaging with RabbitMQ — Submission

## 1. Backlog and Recovery Logs

### Inventory stopped, 10 orders published while down:

```
=== Backlog Drain Test ===

1) Stopping inventory_service...
[+] stop 1/1
 ✔ Container async-rabbitmq-inventory_service-1 Stopped                                1.2s

2) Publishing 10 orders while inventory_service is down...
   Order 1 published
   Order 2 published
   Order 3 published
   Order 4 published
   Order 5 published
   Order 6 published
   Order 7 published
   Order 8 published
   Order 9 published
   Order 10 published
```

### Inventory restarted, backlog drained:

```
5) Restarting inventory_service...
[+] start 2/2
 ✔ Container async-rabbitmq-rabbitmq-1          Healthy                                0.5s
 ✔ Container async-rabbitmq-inventory_service-1 Started                                0.2s

6) Waiting for backlog to drain...
   Messages remaining in inventory_order_queue: 0

7) Checking inventory_service logs for processed orders...
inventory_service-1  | [InventoryService] Processing order order-066aa2b7: 1x burger
inventory_service-1  | [InventoryService] Reserved 1x burger, remaining: 99
inventory_service-1  | [InventoryService] Processing order order-d5bbcfe2: 1x burger
inventory_service-1  | [InventoryService] Reserved 1x burger, remaining: 98
inventory_service-1  | [InventoryService] Processing order order-3eaf8926: 1x burger
inventory_service-1  | [InventoryService] Reserved 1x burger, remaining: 97
inventory_service-1  | [InventoryService] Processing order order-9f75ac04: 1x burger
inventory_service-1  | [InventoryService] Reserved 1x burger, remaining: 96
inventory_service-1  | [InventoryService] Processing order order-67a7751e: 1x burger
inventory_service-1  | [InventoryService] Reserved 1x burger, remaining: 95
inventory_service-1  | [InventoryService] Processing order order-14c602b3: 1x burger
inventory_service-1  | [InventoryService] Reserved 1x burger, remaining: 94
inventory_service-1  | [InventoryService] Processing order order-c8e0b1f2: 1x burger
inventory_service-1  | [InventoryService] Reserved 1x burger, remaining: 93
inventory_service-1  | [InventoryService] Processing order order-1ace2d20: 1x burger
inventory_service-1  | [InventoryService] Reserved 1x burger, remaining: 92
inventory_service-1  | [InventoryService] Processing order order-05355a74: 1x burger
inventory_service-1  | [InventoryService] Reserved 1x burger, remaining: 91
inventory_service-1  | [InventoryService] Processing order order-9e262d3f: 1x burger
inventory_service-1  | [InventoryService] Reserved 1x burger, remaining: 90
```

Because the queue is durable, RabbitMQ held onto all 10 orders even though InventoryService was completely offline. As soon as it came back up and reconnected, it chewed through the backlog right away, you can see the remaining stock count going from 99 down to 90. No messages were lost.

## 2. Idempotency Demonstration

### Duplicate message was correctly rejected:

```
inventory_service-1  | [InventoryService] Processing order order-553d95cc: 1x pizza
inventory_service-1  | [InventoryService] Reserved 1x pizza, remaining: 99
inventory_service-1  | [InventoryService] Duplicate order order-553d95cc, skipping (idempotent)
```

Here I published the same `OrderPlaced` event for `order-553d95cc` twice. The first time it went through fine and reserved 1 pizza (stock dropped to 99). The second time, it got caught as a duplicate and was just skipped — so stock stayed at 99 instead of incorrectly going to 98.

### Idempotency Strategy

The approach is pretty straightforward. InventoryService keeps a `processed_orders` set in memory that stores every `order_id` it has already handled. When a new message comes in, it checks whether that order ID is already in the set. If it is, the message just gets acknowledged and thrown away. If not, inventory gets reserved and the order ID gets added to the set.

This works well for our use case since RabbitMQ gives us at-least-once delivery meaning a message might show up more than once, but we won't miss any. The tradeoff is that this set lives in memory, so it resets if the service restarts. In a real production setup you'd want to track processed IDs in a database instead so they survive restarts.

## 3. Dead Letter Queue (DLQ) / Poison Message Handling

### Malformed message routed to DLQ:

```
inventory_service-1  | [InventoryService] Malformed message, rejecting to DLQ: b'THIS IS NOT VALID JSON {{{'

4) Checking dead_letter_queue for the rejected message...
   Messages in dead_letter_queue: 1

5) Reading message from DLQ...
   DLQ content: [{"payload_bytes":26,"redelivered":false,"exchange":"dlx",
   "routing_key":"","message_count":0,"properties":{"delivery_mode":2,
   "headers":{"x-death":[{"count":1,"exchange":"order_events",
   "queue":"inventory_order_queue","reason":"rejected","routing-keys":[""],
   "time":1770761210}],"x-first-death-exchange":"order_events",
   "x-first-death-queue":"inventory_order_queue",
   "x-first-death-reason":"rejected"}},
   "payload":"THIS IS NOT VALID JSON {{{","payload_encoding":"string"}]
```

I sent a garbage string that can't be parsed as JSON. When InventoryService tries to decode it and fails, it nacks the message with `requeue=False` so it doesn't keep bouncing back into the main queue. Since I set up the `inventory_order_queue` with a dead-letter exchange (`dlx`), the rejected message gets routed over to `dead_letter_queue` automatically. That way bad messages don't block everything, but they're still sitting there if we need to look at them later to figure out what went wrong.
