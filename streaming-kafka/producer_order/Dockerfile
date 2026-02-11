FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for confluent-kafka
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy common module
COPY common/ /app/common/

# Copy service files
COPY streaming-kafka/producer_order/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY streaming-kafka/producer_order/*.py ./

EXPOSE 8201

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8201/health', timeout=2)" || exit 1

CMD ["python", "app.py"]
