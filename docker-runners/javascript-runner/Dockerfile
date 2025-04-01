FROM node:14-slim

WORKDIR /app

# Install common Node.js libraries that might be needed
RUN npm install express axios

# Copy the entrypoint.js file to a different location to avoid conflicts with mounted volumes
COPY entrypoint.js /app/entrypoint.js

# Create function directory where user code will be mounted
RUN mkdir -p /function

ENTRYPOINT ["node", "/app/entrypoint.js"]