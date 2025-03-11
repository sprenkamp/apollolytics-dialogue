# Dockerfile
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install ffmpeg (includes ffprobe) required by pydub
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Create a directory for logs inside /app (this directory will be mounted from the host)
RUN mkdir -p logs

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expose port 8000 to allow access to the FastAPI app
EXPOSE 8080

# Default AWS configuration (use environment variables to override)
ENV AWS_REGION=eu-north-1
ENV DYNAMODB_TABLE=apollolytics_dialogues


# Command to run FastAPI using Uvicorn
CMD ["uvicorn", "backend.ws_speech:app", "--host", "0.0.0.0", "--port", "8080"]
