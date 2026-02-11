FROM python:3.11-slim

WORKDIR /app

# Copy common module
COPY common/ /app/common/

# Copy service files
COPY async-rabbitmq/inventory_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY async-rabbitmq/inventory_service/*.py ./

CMD ["python", "consumer.py"]
