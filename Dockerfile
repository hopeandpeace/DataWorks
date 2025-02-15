# Use an official lightweight Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for OCR, curl, git, etc.
RUN apt-get update && apt-get install -y \
    curl \
    git \
    tesseract-ocr \
    libtesseract-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy all files from your project to the container
COPY . .

# Install all Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8000 as specified in the project
EXPOSE 8000

# Command to run your FastAPI application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
