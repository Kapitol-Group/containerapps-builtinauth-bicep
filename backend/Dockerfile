# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend with frontend static files
FROM python:3.12

WORKDIR /code

COPY backend/requirements.txt .

RUN pip3 install -r requirements.txt

COPY backend/ .

RUN pip3 install -e ./entity-store-transformation-client

# Copy built frontend from previous stage
COPY --from=frontend-build /frontend/build ./frontend_build

EXPOSE 50505

ENTRYPOINT ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]