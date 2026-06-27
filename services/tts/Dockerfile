# syntax=docker/dockerfile:1.9
#
# AaaS TTS service — Meta MMS-TTS (ory/hin/eng), CPU-only (torch CPU).
#
# Model weights (~150 MB each, ~450 MB total when all three languages
# are pre-fetched) land in /models on first boot. For a zero-network
# cloud deploy, bind-mount a pre-warmed volume or run
# `python bundle/prefetch_model.py` on the host and COPY the result in.

FROM python:3.12-slim AS builder
WORKDIR /build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1
# CPU-only torch wheels are much smaller than the default CUDA ones.
RUN pip install --prefix=/install --index-url https://download.pytorch.org/whl/cpu \
      "torch>=2.4"
COPY pyproject.toml README.md ./
COPY app/ ./app/
RUN pip install --prefix=/install .

FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.title="aaas-tts" \
      org.opencontainers.image.source="https://github.com/subarnarekha/aaas" \
      org.opencontainers.image.licenses="Apache-2.0"

RUN apt-get update \
 && apt-get install -y --no-install-recommends libsndfile1 curl \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1001 aaas && \
    useradd  --system --uid 1001 --gid 1001 --create-home aaas

COPY --from=builder /install /usr/local
WORKDIR /app
COPY --chown=aaas:aaas app/ ./app/
RUN mkdir -p /models && chown aaas:aaas /models

USER aaas
EXPOSE 8001
ENV PYTHONUNBUFFERED=1 \
    MODEL_CACHE_DIR=/models \
    HF_HOME=/models/hf \
    AAAS_TTS_PORT=8001
HEALTHCHECK --interval=10s --timeout=5s --start-period=120s --retries=6 \
    CMD curl -fsS http://localhost:8001/readyz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
