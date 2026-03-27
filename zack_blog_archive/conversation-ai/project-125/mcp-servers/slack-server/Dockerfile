FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8003

HEALTHCHECK --interval=10s --timeout=5s --retries=3 --start-period=10s \
  CMD curl -f http://localhost:8003/health || exit 1

CMD ["python", "server.py", "--transport", "http", "--port", "8003"]
