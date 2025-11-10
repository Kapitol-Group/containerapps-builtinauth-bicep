# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build

WORKDIR /frontend

# Accept build arguments for Vite environment variables
ARG VITE_ENTRA_CLIENT_ID
ARG VITE_ENTRA_TENANT_ID
ARG VITE_SHAREPOINT_BASE_URL
ARG VITE_BACKEND_API_URL=/api

# Set them as environment variables for the build process
ENV VITE_ENTRA_CLIENT_ID=$VITE_ENTRA_CLIENT_ID
ENV VITE_ENTRA_TENANT_ID=$VITE_ENTRA_TENANT_ID
ENV VITE_SHAREPOINT_BASE_URL=$VITE_SHAREPOINT_BASE_URL
ENV VITE_BACKEND_API_URL=$VITE_BACKEND_API_URL

# Copy frontend package files
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend with frontend static files
FROM python:3.12

WORKDIR /code

# Copy entity store client first
COPY backend/entity-store-transformation-client ./entity-store-transformation-client

# Copy requirements and install dependencies
COPY backend/requirements.txt .

RUN pip3 install -r requirements.txt

# Copy rest of backend code
COPY backend/ .

# Copy built frontend from previous stage
COPY --from=frontend-build /frontend/build ./frontend_build

EXPOSE 50505

ENTRYPOINT ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
