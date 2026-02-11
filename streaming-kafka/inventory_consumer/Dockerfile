FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy common module
COPY common/ /app/common/

# Copy service files
COPY streaming-kafka/inventory_consumer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY streaming-kafka/inventory_consumer/*.py ./

CMD ["python", "consumer.py"]
