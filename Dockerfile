FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
# Railway автоматично встановлює PORT через змінну оточення
CMD python -c "import os; port = os.getenv('PORT', '8000'); import subprocess; subprocess.run(['uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', port])"

