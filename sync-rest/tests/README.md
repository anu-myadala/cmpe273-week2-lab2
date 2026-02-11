# Synchronous REST Tests

This directory contains automated tests for the synchronous REST implementation.

## Prerequisites

- Docker and Docker Compose installed
- Services running: `docker-compose up -d`
- Python 3.11+ with requests library: `pip install requests`

## Tests

### 1. Baseline Latency Test (`test_baseline.py`)

Measures baseline latency without any fault injection.

**What it does:**
- Sends 100 requests to OrderService
- Measures latency for each request
- Calculates P50, P95, P99 latencies
- Exports results to `baseline_results.csv` and `baseline_latencies.csv`

**How to run:**
```bash
cd sync-rest/tests
python test_baseline.py
```

**Expected output:**
- All requests should succeed (200 OK)
- Latencies should be low (< 100ms typically)
- Results exported to CSV files

### 2. Delay Injection Test (`test_delay.py`)

Demonstrates cascading delay effect in synchronous architecture.

**What it does:**
- Configures 2-second delay in InventoryService
- Sends 100 requests to OrderService
- Measures impact on end-to-end latency
- Resets delay to 0 after test
- Exports results to `delay_results.csv` and `delay_latencies.csv`

**How to run:**
```bash
cd sync-rest/tests
python test_delay.py
```

**Expected output:**
- All requests should succeed but with ~2000ms+ latency
- Shows how downstream delays cascade to clients
- P50 latency should be close to 2000ms + overhead

### 3. Failure Injection Test (`test_failure.py`)

Tests error handling when InventoryService fails.

**What it does:**
- Enables failure injection in InventoryService (returns 500 errors)
- Sends 50 requests to OrderService
- Observes OrderService timeout and error responses
- Disables failure injection after test
- Exports results to `failure_results.csv`

**How to run:**
```bash
cd sync-rest/tests
python test_failure.py
```

**Expected output:**
- All requests should fail with 500 errors from OrderService
- Shows proper error propagation
- Demonstrates tight coupling - one service failure affects entire chain

## Running All Tests

Run all tests in sequence:

```bash
cd sync-rest/tests
python test_baseline.py && \
python test_delay.py && \
python test_failure.py
```

## Interpreting Results

### Baseline Test
- **Good:** P95 < 100ms, all requests succeed
- **Issue:** High latency or failures indicate service problems

### Delay Test
- **Expected:** P50 ≈ 2000ms (configured delay) + network overhead
- **Shows:** In synchronous systems, delays cascade to all callers

### Failure Test
- **Expected:** 100% failure rate when inventory fails
- **Shows:** Tight coupling - one service down = entire flow fails

## Cleanup

After running tests, you can clean up generated CSV files:

```bash
rm *.csv
```

To stop services:

```bash
cd ..
docker-compose down
```
