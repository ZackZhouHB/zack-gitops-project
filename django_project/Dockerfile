# Use Python 3.13 for Django 5.2 compatibility
FROM python:3.13-slim

# Prevent Python from writing .pyc files and allow stdout/stderr to appear immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libopenjp2-7-dev \
    build-essential \
    zlib1g-dev \
    libjpeg-dev \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker layer cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port on which Django will run
EXPOSE 8000

# Run Django server on container start
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
