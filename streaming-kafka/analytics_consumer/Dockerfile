FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

COPY streaming-kafka/analytics_consumer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY streaming-kafka/analytics_consumer/*.py ./

CMD ["python", "consumer.py"]
