# ---- base image ----
    FROM python:3.8-slim

    # Prevent Python from writing .pyc files and allow stdout/stderr to appear immediately
    ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1
    
    # Where *inside* the container your code will live
    WORKDIR /app
    
    # ---- OS‑level build deps you already needed ----
    RUN apt-get update && apt-get install -y --no-install-recommends \
            git libopenjp2-7-dev build-essential zlib1g-dev libjpeg-dev \
        && rm -rf /var/lib/apt/lists/*
    
    # ---- Python deps ----
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    # ---- (optional) copy the project ----
    # If you plan to mount the source code from your host (see docker‑compose.yml
    # below) you can omit this.  It’s handy for CI/CD builds, though.
    # COPY . .
    
    # ---- default command ----
    CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
    