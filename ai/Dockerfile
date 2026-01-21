FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster pip
RUN pip install uv

# Copy pyproject.toml first for caching
COPY ai/pyproject.toml ai/uv.lock* ./ai/

# Install dependencies from pyproject.toml
RUN cd ai && uv pip install --system -e . || pip install -e .

# Copy application code
COPY . .

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command - run all services
CMD ["python", "-m", "ai.main"]
