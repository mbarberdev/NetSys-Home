# NetSys-Home — single-image build.
# Stage 1 builds the React frontend; stage 2 installs the FastAPI backend
# with the prebuilt static bundle copied in. Result is one container that
# serves the API and the UI on port 5000.

# ── Stage 1: Frontend build ──────────────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build


# ── Stage 2: Backend runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# Train the classifier at build time so the image is self-contained
WORKDIR /app/backend
RUN python3 -m classifier.train

EXPOSE 5000
CMD ["python3", "app.py"]
