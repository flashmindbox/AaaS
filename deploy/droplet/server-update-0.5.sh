#!/bin/bash
# AaaS server update for extension 0.5.0: extension tenant key, no access
# logs, 30-day translation-cache purge. Safe to re-run.
set -e
# extension tenant key for the gateway
sed -i 's#^Environment=AAAS_ENV=prod$#Environment=AAAS_ENV=prod EXTENSION_API_KEY=aaas_live_ae7b43dd188349aa99b6e71cc8dd6b18#' /etc/systemd/system/aaas-gateway.service
# no access logs (they would record visitor IPs)
for s in gateway tts stt translate; do
  grep -q -- '--no-access-log' /etc/systemd/system/aaas-$s.service || sed -i "s#^ExecStart=\(.*\)\$#ExecStart=\1 --no-access-log#" /etc/systemd/system/aaas-$s.service
done
# 30-day purge of the translation cache
DEBIAN_FRONTEND=noninteractive apt-get install -yq sqlite3 >/dev/null
cat > /etc/systemd/system/aaas-cache-purge.service <<'UNIT'
[Unit]
Description=Empty the AaaS translation cache

[Service]
Type=oneshot
User=aaas
ExecStart=/usr/bin/sqlite3 /opt/aaas/system/services/translate/cache/translations.sqlite3 "DELETE FROM tr; VACUUM;"
UNIT
cat > /etc/systemd/system/aaas-cache-purge.timer <<'UNIT'
[Unit]
Description=Empty the AaaS translation cache every 30 days

[Timer]
OnCalendar=*-*-01 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now aaas-cache-purge.timer
# start fresh: clears the test translations made during setup
systemctl start aaas-cache-purge.service
systemctl restart aaas-tts aaas-stt aaas-translate
sleep 3
systemctl restart aaas-gateway
for p in 8000/healthz 8001/readyz 8002/readyz 8003/readyz; do
  for i in $(seq 60); do curl -sf -m 2 127.0.0.1:$p >/dev/null && break; sleep 2; done
  echo "$p $(curl -s -o /dev/null -w %{http_code} 127.0.0.1:$p)"
done
grep -h ExecStart /etc/systemd/system/aaas-gateway.service /etc/systemd/system/aaas-translate.service
grep -h EXTENSION_API_KEY /etc/systemd/system/aaas-gateway.service | cut -c1-60
systemctl list-timers aaas-cache-purge.timer --no-pager | head -2
