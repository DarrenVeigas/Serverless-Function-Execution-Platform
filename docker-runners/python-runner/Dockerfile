FROM python:3.9-slim

WORKDIR /app

# Install common Python libraries that might be needed
RUN pip install fastapi uvicorn requests numpy pandas

# Copy the entrypoint.py file to a different location to avoid conflicts with mounted volumes
COPY entrypoint.py /app/entrypoint.py

# Create function directory where user code will be mounted
RUN mkdir -p /function

ENTRYPOINT ["python", "/app/entrypoint.py"]