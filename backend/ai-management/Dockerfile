# Use official Python image
FROM python:3.10

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for YOLOv8)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies globally (not in venv)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt && pip install ultralytics

# Copy your code
COPY . .

# Expose backend port
EXPOSE 5001

# Run your backend (adjust as needed)
CMD ["python", "main.py"]