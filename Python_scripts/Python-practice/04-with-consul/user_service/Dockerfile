# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install Flask and requests
RUN pip install --no-cache-dir flask requests

# Make port 5001 available to the world outside this container
EXPOSE 5001

# Run user_service.py when the container launches
CMD ["python", "user_service.py"]
