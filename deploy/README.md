# Cloud deploy — AaaS demo

This directory holds the reverse-proxy config and environment template
for the Docker-based cloud demo. The actual Compose file lives at the
repo root (`docker-compose.yml`).

## Quick start — local Docker

```bash
# From the repo root, with Docker Desktop running:
cp deploy/.env.example .env          # tweak AAAS_DOMAIN if needed
docker compose up --build
```

Once the four services report healthy (TTS takes ~2 minutes on a cold
volume because it downloads 150 MB of MMS weights), open:

- <http://localhost/demo/> — tenant demo landing page
- <http://localhost/admin/> — operator dashboard
- <http://localhost/exam/> — accessible mock exam module
- <http://localhost/docs> — OpenAPI docs for the gateway

The seed API keys (visible in
`services/gateway/app/main.py :: _seed_dev_repository`) are:

| Tenant              | Key                                          |
| ------------------- | -------------------------------------------- |
| Utkal University    | `aaas_live_00000000000000000000000000000000` |
| Jajpur Collectorate | `aaas_live_11111111111111111111111111111111` |
| BSE Odisha          | `aaas_live_22222222222222222222222222222222` |

## Deploying to a real host

1. Point DNS at the server (A / AAAA record for `demo.aaas.cloud`).
2. Open ports 80 and 443 on the firewall — Caddy needs both for the
   ACME HTTP-01 challenge.
3. Edit `.env`:

   ```env
   AAAS_DOMAIN=demo.aaas.cloud
   AAAS_ENV=prod
   ```

4. `docker compose up -d --build`

Caddy will provision a Let's Encrypt certificate automatically within a
minute of boot. Check `docker logs aaas-caddy-1` if it doesn't.

## Switching on the real ML engines

The default Compose stack runs the **mock** engines for STT and
Translate, because they're zero-weight and deterministic — perfect for
CI, automated demos, and low-memory hosts. To flip either service to
its real backend, set the corresponding build-arg + runtime env-var
before starting:

```env
# .env
STT_ENGINE_EXTRA=indic
STT_ENGINE=indic_wav2vec

TRANSLATE_ENGINE_EXTRA=indic
TRANSLATE_ENGINE=indictrans2
```

Then:

```bash
docker compose build stt translate
docker compose up -d stt translate
```

First boot downloads the weights (~500 MB for IndicWav2Vec, ~1 GB for
IndicTrans2 distilled-200M) into the named volume, so subsequent
restarts are fast.

## Resource budget

| Service   | RAM (idle) | RAM (loaded) | Disk (image) | Notes                  |
| --------- | ---------- | ------------ | ------------ | ---------------------- |
| gateway   | 120 MB     | 180 MB       | 150 MB       | async, httpx pool      |
| tts       | 400 MB     | 1.2 GB       | 1.6 GB       | PyTorch + VITS weights |
| stt       | 100 MB     | 100 MB       | 140 MB       | mock; +800 MB if Indic |
| translate | 90 MB      | 90 MB        | 130 MB       | mock; +1.6 GB if Indic |
| caddy     | 25 MB      | 25 MB        | 60 MB        |                        |

A 4 GB / 2 vCPU droplet will happily host the full stack in mock mode.
For the real-model config, size up to 8 GB.

## Logs

All services log structured JSON to stdout. Caddy logs access too. For
a local dev loop, `docker compose logs -f gateway` is your friend; for
a real deploy, ship stdout to whatever log-aggregator you already
operate (we do **not** prescribe one).
