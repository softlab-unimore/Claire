# Use official Python 3.12.4 slim image
FROM python:3.12.4-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

RUN python manage.py collectstatic --noinput

# Expose port for Gunicorn
EXPOSE 8003

# Default command
CMD ["gunicorn", "Claire.wsgi:application", "--bind", "0.0.0.0:8003", "--timeout", "60"]
