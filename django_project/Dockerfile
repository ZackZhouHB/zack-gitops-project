# Use a lighter Python base image
FROM python:3.9-alpine

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies in a single layer
RUN apk update && apk add --no-cache \
    git \
    build-base \
    zlib-dev \
    libjpeg-turbo-dev \
    curl \
    bash \
    && rm -rf /var/cache/apk/*

# Copy only the requirements file first to leverage Docker layer cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set environment variables for Django
ENV PYTHONUNBUFFERED 1

# Expose the port on which Django will run
EXPOSE 8000

# Run Django server on container start
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
