# syntax=docker/dockerfile:1
# Сборка 1: frontend (React + Vite) -> статические файлы
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
# Необязательный секрет extra_ca — корневой сертификат прокси с TLS-инспекцией (в образ не попадает):
#   docker build --secret id=extra_ca,src=/path/ca.crt .
RUN --mount=type=secret,id=extra_ca \
    if [ -f /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Сборка 2: backend (FastAPI) + собранный SPA на одном домене
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    DATABASE_URL=sqlite:////data/deanate.db \
    FRONTEND_DIST=/app/frontend/dist \
    COOKIE_SECURE=true \
    TRUST_PROXY_HEADERS=true
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN --mount=type=secret,id=extra_ca \
    if [ -f /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi; \
    pip install -r requirements.txt && useradd --create-home --uid 10001 app && mkdir -p /data
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)" || exit 1
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
