FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# In Docker, MCP client modules are copied to /app/clients/ via docker-compose build context
# Create __init__.py if clients dir exists (Docker) or use sys.path (local dev)
RUN mkdir -p /app/clients && touch /app/clients/__init__.py

EXPOSE 8010

HEALTHCHECK --interval=10s --timeout=5s --retries=3 --start-period=15s \
  CMD curl -f http://localhost:8010/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
