# Common Utilities

This directory contains shared utility functions used across all three communication model implementations.

## Module: `ids.py`

Provides consistent ID generation and timestamp handling for all services.

### Functions

#### `generate_order_id() -> str`
Generates a unique order ID using UUID4.

**Returns:** String representation of UUID4

**Example:**
```python
from common.ids import generate_order_id

order_id = generate_order_id()
# Returns: "550e8400-e29b-41d4-a716-446655440000"
```

#### `generate_event_id() -> str`
Generates a unique event ID using UUID4.

**Returns:** String representation of UUID4

**Example:**
```python
from common.ids import generate_event_id

event_id = generate_event_id()
# Returns: "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
```

#### `current_timestamp() -> str`
Generates ISO-8601 formatted timestamp in UTC with 'Z' suffix.

**Returns:** ISO-8601 timestamp string

**Example:**
```python
from common.ids import current_timestamp

timestamp = current_timestamp()
# Returns: "2026-02-10T14:30:00.123456Z"
```

#### `parse_timestamp(ts_str: str) -> datetime`
Parses ISO-8601 timestamp string back to datetime object.

**Arguments:**
- `ts_str`: ISO-8601 formatted timestamp string

**Returns:** datetime object in UTC timezone

**Example:**
```python
from common.ids import parse_timestamp

dt = parse_timestamp("2026-02-10T14:30:00.123456Z")
# Returns: datetime(2026, 2, 10, 14, 30, 0, 123456, tzinfo=timezone.utc)
```

## Usage

To use these utilities in your service:

1. Ensure the common module is in your Python path
2. Import the required functions:

```python
import sys
sys.path.append('/app/common')

from ids import generate_order_id, current_timestamp

# Generate an order
order = {
    "order_id": generate_order_id(),
    "timestamp": current_timestamp(),
    "user_id": "user123",
    "item": "Burger",
    "quantity": 2
}
```

## Testing

Test the utilities:

```python
from common.ids import generate_order_id, generate_event_id, current_timestamp, parse_timestamp

# Test ID generation
order_id = generate_order_id()
assert len(order_id) == 36  # UUID4 format with dashes

# Test timestamp
ts = current_timestamp()
assert ts.endswith('Z')
assert 'T' in ts

# Test parsing
dt = parse_timestamp(ts)
assert dt.tzinfo is not None
```
