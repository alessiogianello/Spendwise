# Single-image demo build: the Flutter web client is compiled in a first
# stage and served by the FastAPI backend from the same origin.

# --- stage 1: Flutter web build -------------------------------------------
FROM debian:bookworm-slim AS web
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl unzip xz-utils zip ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Pinned to the version the project is developed with (see frontend/README.md).
ARG FLUTTER_VERSION=3.44.8
RUN git clone --depth 1 --branch ${FLUTTER_VERSION} https://github.com/flutter/flutter.git /flutter
ENV PATH="/flutter/bin:${PATH}"
RUN flutter config --no-analytics --enable-web && flutter precache --web

WORKDIR /src
COPY frontend/pubspec.yaml frontend/pubspec.lock ./
RUN flutter pub get
COPY frontend/ ./
RUN flutter build web --release

# --- stage 2: backend + static files ----------------------------------------
FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /src/build/web ./static

# Render (and most PaaS) inject PORT; 8000 is the local default.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
