# syntax=docker/dockerfile:1.9
#
# AaaS gateway — multi-stage build.
#
# Build context is the repo root (see docker-compose.yml), because the
# gateway also serves the widget + demo sites + exam + admin as static
# files so everything stays same-origin. Keeping a single origin side-
# steps CORS + cookie headaches and matches how the bundled USB demo
# runs too.

FROM python:3.12-slim AS builder
WORKDIR /build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1
COPY services/gateway/pyproject.toml services/gateway/README.md ./
COPY services/gateway/app/ ./app/
RUN pip install --prefix=/install .

FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.title="aaas-gateway" \
      org.opencontainers.image.source="https://github.com/subarnarekha/aaas" \
      org.opencontainers.image.licenses="Apache-2.0"

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1001 aaas && \
    useradd  --system --uid 1001 --gid 1001 --create-home aaas

COPY --from=builder /install /usr/local
WORKDIR /app
COPY --chown=aaas:aaas services/gateway/app/ ./app/
# Static assets — gateway _mount_demo_assets picks them up from
# /app/apps/... (walks up from main.py looking for an apps/ sibling).
COPY --chown=aaas:aaas apps/widget/dist/ ./apps/widget/dist/
COPY --chown=aaas:aaas apps/demo-sites/  ./apps/demo-sites/
COPY --chown=aaas:aaas apps/exam/        ./apps/exam/
COPY --chown=aaas:aaas apps/admin/       ./apps/admin/

USER aaas
EXPOSE 8000
ENV PYTHONUNBUFFERED=1
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
