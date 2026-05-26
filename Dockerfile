# Stage 1: Build the Angular frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ .
RUN npm run build -- --configuration=production

# Stage 2: Build the FastAPI backend and integrate frontend
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy AS base

RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install backend requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY backend/ .

# Copy the compiled Angular frontend from the build stage into backend's static directory
COPY --from=frontend-build /app/dist/frontend/browser ./static

# Configure ownership and non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
