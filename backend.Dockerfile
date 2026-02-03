FROM python:3.11-slim

WORKDIR /backend

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Expose port
EXPOSE 4000

# Run the application (use asyncio loop for gremlinpython compatibility)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "4000", "--reload", "--loop", "asyncio"]
