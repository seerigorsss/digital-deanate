#!/bin/sh
# Готовит постоянное хранилище /data и запускает приложение без root-прав, если это возможно.
set -e
mkdir -p /data
if [ "$(id -u)" = "0" ]; then
  chown -R app:app /data 2>/dev/null || true
  if setpriv --reuid=app --regid=app --init-groups sh -c 'test -w /data'; then
    exec setpriv --reuid=app --regid=app --init-groups "$@"
  fi
  echo "WARNING: /data недоступен для записи пользователю app — запуск от root" >&2
fi
exec "$@"
