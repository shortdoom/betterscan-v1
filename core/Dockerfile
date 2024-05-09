# docker build -t bscan-demo1.01 .
# docker run -p 8080:8080 bscan-demo1
# 	-(you need to bind to 0.0.0.0 for es/flask because 127.0.0.1 is on it's internal net)
# 	- starts a new container each time
# 		- docker start -ai <container_with_flask_app> to restart in interactive mode
# docker exec -it <container> bash

# Use the official Python image as base
FROM python:3.10.7-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git

# Set the working directory in the container
WORKDIR /app

# Copy the entire contents of the core/engine directory into the container
COPY . .

# Copy requirements file separately to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expose port 5000 to the outside world
# NOTE: Only local environment
# EXPOSE 5000

# Install all solc versions (gigs of data!)
# RUN python install_solc_versions.py

# Command to run the Flask application
# NOTE: Only local environment
# CMD ["python", "app.py"]

# Command to run the Flask application
CMD ["gunicorn", "-b", ":8080", "app:app", "--workers", "1", "--threads", "8", "--timeout", "0"]