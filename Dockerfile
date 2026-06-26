# Stage 1: Build React frontend
FROM node:20-slim AS frontend-builder
ARG NPM_REGISTRY
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -n "$NPM_REGISTRY" ]; then npm config set registry "$NPM_REGISTRY"; fi && npm install
COPY frontend/ ./
RUN if [ -n "$NPM_REGISTRY" ]; then npm config set registry "$NPM_REGISTRY"; fi && npm run build

# Stage 2: Production image
FROM python:3.12-slim

ARG APT_MIRROR
RUN if [ -n "$APT_MIRROR" ]; then \
      sed -i "s|http://deb.debian.org|${APT_MIRROR}|g; s|http://security.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list 2>/dev/null || true; \
    fi

# Chromium system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdbus-1-3 libdrm2 libxkbcommon0 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libx11-xcb1 libfontconfig1 libx11-6 \
    libxcb1 libxext6 libxshmfence1 \
	    libglib2.0-0 libgtk-3-0 libpangocairo-1.0-0 libcairo-gobject2 \
	    libgdk-pixbuf-2.0-0 libxss1 libxtst6 fonts-liberation \
	    libgl1-mesa-dri libegl-mesa0 \
	    procps ca-certificates \
	    && rm -rf /var/lib/apt/lists/*

# Playwright system deps (matches test-infra)
RUN pip install --no-cache-dir playwright && playwright install-deps chromium 2>/dev/null || true && pip uninstall -y playwright

# Windows core fonts (Arial, Times New Roman, Verdana, etc.)
RUN echo "deb ${APT_MIRROR:-http://deb.debian.org}/debian trixie contrib" >> /etc/apt/sources.list.d/contrib.list \
    && echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections \
    && apt-get update && apt-get install -y --no-install-recommends ttf-mscorefonts-installer \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY backend/requirements.txt /app/backend/
ARG PIP_INDEX_URL
RUN if [ -n "$PIP_INDEX_URL" ]; then export PIP_EXTRA_INDEX_URL="$PIP_INDEX_URL"; fi && pip install --no-cache-dir -r /app/backend/requirements.txt

# Backend code
COPY backend/ /app/backend/

# Frontend build from stage 1
COPY --from=frontend-builder /build/dist /app/frontend/dist

# Pre-download CloakBrowser binary
RUN python -c "from cloakbrowser.download import ensure_binary; ensure_binary()"

EXPOSE 8080
ENV DATA_DIR=/data

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/status')" || exit 1

VOLUME /data

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
