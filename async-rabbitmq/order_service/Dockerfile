FROM python:3.11-slim

WORKDIR /app

# Copy common module
COPY common/ /app/common/

# Copy service files
COPY async-rabbitmq/order_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY async-rabbitmq/order_service/*.py ./

EXPOSE 8101

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8101/health', timeout=2)" || exit 1

CMD ["python", "app.py"]
