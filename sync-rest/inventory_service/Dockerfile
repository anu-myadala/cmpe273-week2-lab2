FROM python:3.11-slim

WORKDIR /app

COPY sync-rest/inventory_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sync-rest/inventory_service/app.py .

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8002/health', timeout=2)" || exit 1

CMD ["python", "app.py"]
