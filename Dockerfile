# Single-image demo build: the Flutter web client is compiled in a first
# stage and served by the FastAPI backend from the same origin.

# --- stage 1: Flutter web build -------------------------------------------
FROM debian:bookworm-slim AS web
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl unzip xz-utils zip ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Pinned to the version the project is developed with (see frontend/README.md).
ARG FLUTTER_VERSION=3.44.8
# Flutter runs as an unprivileged user: as root, extracting its artifact
# tarballs tries to restore file ownership, which sandboxed builders refuse.
RUN useradd --create-home builder \
    && git clone --depth 1 --branch ${FLUTTER_VERSION} https://github.com/flutter/flutter.git /flutter \
    && chown -R builder:builder /flutter \
    && mkdir /src && chown builder:builder /src
USER builder
ENV PATH="/flutter/bin:${PATH}"
RUN flutter config --no-analytics --enable-web && flutter precache --web

WORKDIR /src
COPY --chown=builder:builder frontend/pubspec.yaml frontend/pubspec.lock ./
RUN flutter pub get
COPY --chown=builder:builder frontend/ ./
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
