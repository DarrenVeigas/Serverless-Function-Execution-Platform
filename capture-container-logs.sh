#!/bin/bash
# Run this script to capture detailed logs from a running container

# Get the container ID from docker ps (assumes your container name contains "function")
CONTAINER_ID=$(docker ps | grep "function" | awk '{print $1}')

if [ -z "$CONTAINER_ID" ]; then
  echo "No function container found running"
  exit 1
fi

echo "Capturing logs from container $CONTAINER_ID"

# Capture logs with timestamps
docker logs -t $CONTAINER_ID > container_logs.txt

# Inspect container details
docker inspect $CONTAINER_ID > container_inspect.json

echo "Logs saved to container_logs.txt"
echo "Container details saved to container_inspect.json"
