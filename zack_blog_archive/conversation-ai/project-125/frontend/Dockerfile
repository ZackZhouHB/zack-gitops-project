FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8502

HEALTHCHECK --interval=10s --timeout=5s --retries=3 --start-period=15s \
  CMD curl -f http://localhost:8502/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0", "--server.headless=true"]
