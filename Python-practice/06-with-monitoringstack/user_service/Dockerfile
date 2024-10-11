# Dockerfile-user

# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir flask prometheus_flask_exporter pygelf requests

# Make port 5001 available to the world outside this container
EXPOSE 5001

# Define environment variable
ENV FLASK_APP=user_service.py

# Run user_service.py when the container launches
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
