# infra/minio

Dev MinIO runs alongside other services via Docker Compose. The `minio-init`
sidecar in `docker-compose.yml` creates these buckets automatically:

| Bucket         | Purpose                                |
| -------------- | -------------------------------------- |
| `aaas-audio`   | Transient STT/TTS audio uploads        |
| `aaas-docs`    | OCR / document adapter uploads         |
| `aaas-models`  | Large model artefacts (not checked in) |

## Manual access

- Web console: <http://localhost:9001>
- Access key: `aaas-dev`
- Secret key: `aaas-dev-secret`

## Production

Use a managed S3-compatible store in a region inside India (AWS Mumbai,
GCP Mumbai, or a CERT-In empanelled DC). Never keep keys hardcoded as they
are in this dev setup.
