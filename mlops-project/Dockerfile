FROM python:3.10

# Install necessary packages
RUN apt-get update && apt-get install -y git

# Set environment variable to suppress Git warnings
ENV GIT_PYTHON_REFRESH=quiet

# Set the working directory
WORKDIR /app

# Copy your project files
COPY . .

# Install Python dependencies
RUN pip install -r requirements.txt

# Command to run your application
CMD ["python", "src/train.py"]

