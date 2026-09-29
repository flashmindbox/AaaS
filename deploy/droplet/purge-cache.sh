#!/bin/sh
exec /usr/bin/sqlite3 /opt/aaas/system/services/translate/cache/translations.sqlite3 \
  "DELETE FROM tr; ATTACH '/opt/aaas/system/services/translate/cache/translations.seed.sqlite3' AS seed; INSERT OR IGNORE INTO tr SELECT * FROM seed.tr; DETACH seed; VACUUM;"
