FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install uv

# Copy dependency files and README first
COPY pyproject.toml README.md ./

# Copy app folder for hatch to find packages
COPY app ./app

# Install dependencies (not editable mode)
RUN uv pip install . --system

# Copy remaining files
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
