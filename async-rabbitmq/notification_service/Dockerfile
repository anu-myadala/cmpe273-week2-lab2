FROM python:3.11-slim

WORKDIR /app

COPY async-rabbitmq/notification_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY async-rabbitmq/notification_service/*.py ./

CMD ["python", "consumer.py"]
