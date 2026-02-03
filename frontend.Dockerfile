FROM node:20-alpine

WORKDIR /frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY frontend/ .

# Build arg for API URL (needed at build time for NEXT_PUBLIC_* vars)
ARG NEXT_PUBLIC_API_URL=http://localhost:4000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build the application
RUN npm run build

# Expose port
EXPOSE 3010

# Run the application
CMD ["npm", "start"]
