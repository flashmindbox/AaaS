# Deploying AaaS on a Linux server

How the DigitalOcean droplet (`aaas-blr1`, Ubuntu 24.04, 8 vCPU / 16 GB) is set up.
The Windows bundle's `.venv` folders, `system/python` and `system/tesseract` don't
run on Linux; the code and model folders do.

## Layout on the server

```
/opt/aaas/system/            same layout as C:\SUBARNAREKHA\system
  apps/                      widget, demo sites, admin console, privacy page
  services/<svc>/app         service code
  services/<svc>/models      model weights (copied from the laptop — the
                             ai4bharat models are gated on Hugging Face)
  services/<svc>/.venv       built on the server (see below)
```

Owned by the `aaas` system user. Every service listens on 127.0.0.1 only; Caddy
serves HTTPS on 443 and the firewall allows only 22/80/443.

## Build the Python environments

Python 3.14 via `uv`, one environment per service (translate pins
`transformers 4.57.6`, stt/tts use `5.12.1`), CPU-only PyTorch:

```bash
cd /opt/aaas/system/services
for s in gateway tts stt translate; do
  uv venv --python 3.14 $s/.venv
  [ -f /opt/aaas/torch-$s.txt ] && uv pip install -p $s/.venv -r /opt/aaas/torch-$s.txt \
      --index-url https://download.pytorch.org/whl/cpu
  uv pip install -p $s/.venv -r /opt/aaas/requirements-$s.txt
done
```

System packages: `tesseract-ocr libsndfile1 sqlite3 caddy`.

## Files here

| File | Goes to |
|---|---|
| `requirements-*.txt`, `torch-*.txt` | `/opt/aaas/` |
| `systemd/*` | `/etc/systemd/system/` |
| `purge-cache.sh` | `/opt/aaas/purge-cache.sh` (monthly: empties the translation cache, restores the demo-site seed) |
| `Caddyfile.example` | `/etc/caddy/Caddyfile` (fill in the admin password hash) |
| `server-update-0.5.sh` | one-off update script from extension 0.5.0 (safe to re-run) |
| `tests/feature-test.sh` | end-to-end check of every feature against the public URL |
| `tests/load_test.py` | translation throughput test (`python load_test.py [base-url]`) |

The gateway unit sets `EXTENSION_API_KEY`, which seeds the browser extension's
tenant; `START-DEMO.bat` sets the same key for the offline laptop.

## Redeploy code

```bash
cd system
tar --exclude=__pycache__ -czf - services/*/app apps | \
  ssh aaas-do 'tar -xzf - -C /opt/aaas/system && chown -R aaas:aaas /opt/aaas/system \
    && systemctl restart aaas-gateway aaas-tts aaas-stt aaas-translate'
```
