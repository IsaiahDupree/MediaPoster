FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# ffmpeg for video processing, libpq-dev for postgres
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5555

# Run the application
# Using reload for development as implied by usage context
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5555", "--reload"]
