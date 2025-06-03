# Use official Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install pip and poetry
RUN pip install --upgrade pip

# Copy project files
COPY pyproject.toml .
COPY . .

# Install project dependencies
RUN pip install --no-cache-dir .

# Set default environment variables (can be overridden at runtime)
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE ${PORT}

# Use JSON array form for CMD to handle signals properly
CMD ["sh", "-c", "uvicorn src.main:app --host $HOST --port $PORT"]