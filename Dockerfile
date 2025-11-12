FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Redis
RUN apt-get update && apt-get install -y \
    gcc \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Copy and set permissions for start script
COPY start.sh .
RUN chmod +x start.sh

# Expose port for FastAPI
EXPOSE 8000

# Default command - run start script
CMD ["./start.sh"]
