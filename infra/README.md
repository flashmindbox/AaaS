# infra/

Local development and deployment infrastructure.

- `docker-compose.yml` — dev stack (Postgres, Redis, MinIO, Keycloak)
- `keycloak/realm-aaas.json` — pre-seeded Keycloak realm for dev login
- `postgres/init.sql` — initial schemas and roles
- `minio/` — seeding scripts for dev buckets

Production infra (Terraform modules, Kubernetes manifests, Helm charts)
will live under `infra/terraform/` and `infra/k8s/` starting in Phase 5.
