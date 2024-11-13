# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p databases prompts

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default to running combined mode using run_combined.py
CMD ["python", "run_combined.py"]

# Alternative commands for running individual processes:
# Web only: CMD ["python", "web.py"]
# Worker only: CMD ["python", "bot.py"]
