# syntax=docker/dockerfile:1.9
#
# AaaS Translate service. Source default is AI4Bharat IndicTrans2 (real),
# but the slim Docker image is built without torch unless `--build-arg
# ENGINE_EXTRA=indic` is passed — so the runtime ENV below pins `mock` to
# match the image contents. Rebuild with the extra AND unset
# `AAAS_TRANSLATE_ENGINE` (or set it to `indictrans2`) for a real-engine
# container.

ARG ENGINE_EXTRA=

FROM python:3.12-slim AS builder
ARG ENGINE_EXTRA
WORKDIR /build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1
COPY pyproject.toml README.md ./
COPY app/ ./app/
RUN if [ -n "$ENGINE_EXTRA" ]; then \
      pip install --prefix=/install --index-url https://download.pytorch.org/whl/cpu "torch>=2.4" && \
      pip install --prefix=/install ".[$ENGINE_EXTRA]" ; \
    else \
      pip install --prefix=/install "." ; \
    fi

FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.title="aaas-translate" \
      org.opencontainers.image.source="https://github.com/subarnarekha/aaas" \
      org.opencontainers.image.licenses="Apache-2.0"

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1001 aaas && \
    useradd  --system --uid 1001 --gid 1001 --create-home aaas

COPY --from=builder /install /usr/local
WORKDIR /app
COPY --chown=aaas:aaas app/ ./app/
RUN mkdir -p /models && chown aaas:aaas /models

USER aaas
EXPOSE 8003
ENV PYTHONUNBUFFERED=1 \
    AAAS_TRANSLATE_ENGINE=mock \
    AAAS_TRANSLATE_MODEL_CACHE_DIR=/models \
    AAAS_TRANSLATE_TRANSLATE_PORT=8003 \
    HF_HOME=/models/hf
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8003/readyz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
