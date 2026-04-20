# services/

Backend microservices. Each service is independently deployable.

| Planned service     | Phase | Stack                                 |
| ------------------- | ----- | ------------------------------------- |
| `gateway/`          | 1     | Go — API gateway (auth, routing)      |
| `stt/`              | 1     | Python FastAPI — Whisper / IndicWhisper |
| `tts/`              | 1     | Python FastAPI — Piper / IndicTTS     |
| `translate/`        | 2     | Python FastAPI — IndicTrans2          |
| `screen-reader/`    | 2     | Python FastAPI — VLM alt-text, ARIA   |
| `exam-engine/`      | 3     | Go — exam delivery + accommodations   |
| `content-adapter/`  | 2     | Python FastAPI — OCR, simplification  |
| `admin-api/`        | 1     | Node.js Fastify — tenant CRUD, audit  |

Each service ships its own Dockerfile, OpenAPI spec, and SLO doc under `services/<name>/`.
