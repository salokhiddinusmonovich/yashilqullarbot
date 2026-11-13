#!/usr/bin/env bash
# Деплой на сервере (его запускает GitHub Actions по SSH после зелёных тестов, можно и руками):
#   бэкап → git pull (только fast-forward) → пересборка bot + web → проверка, что оба живы.
# Не поднялись — откат на прошлый коммит и пересборка. Миграции НЕ запускаются (см. docker-compose.yml).
# Лог: backups/deploy.log
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
exec > >(tee -a backups/deploy.log) 2>&1
exec 9>backups/.deploy.lock
flock -n 9 || { echo "⏳ деплой уже идёт — выходим"; exit 0; }

echo "=== деплой $(date '+%F %T') ==="
before=$(git rev-parse HEAD)

./scripts/backup.sh || { echo "❌ бэкап не удался — деплой остановлен"; exit 1; }

git fetch --quiet origin main
if ! git merge --ff-only --quiet origin/main; then
  echo "❌ на сервере есть свои изменения/коммиты — git pull без слияния невозможен, разберитесь руками (git status)"
  exit 1
fi
after=$(git rev-parse HEAD)
echo "код: ${before:0:7} → ${after:0:7}"

healthy() {
  local code="000"
  for _ in $(seq 1 30); do                      # web: gunicorn поднимается ~10–20 c (collectstatic)
    code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/ || true)
    [ "$code" != "000" ] && break
    sleep 2
  done
  [ "$code" = "000" ] && { echo "❌ web не отвечает"; docker compose logs --tail=40 web; return 1; }
  sleep 15                                      # бот: падение сразу после старта видно за эти секунды
  local st
  st=$(docker inspect -f '{{.State.Status}}' yashilqollar-bot 2>/dev/null || echo missing)
  [ "$st" != "running" ] && { echo "❌ бот: $st"; docker compose logs --tail=40 bot; return 1; }
  if docker compose logs --since 30s bot 2>&1 | grep -q "Traceback"; then
    echo "❌ бот пишет ошибки"; docker compose logs --tail=40 bot; return 1
  fi
  echo "✅ web: HTTP $code · бот: $st"
}

docker compose up -d --build bot web
if healthy; then
  echo "✅ готово: ${after:0:7}"
  exit 0
fi

echo "↩ откат на ${before:0:7}"
git reset --keep "$before"
docker compose up -d --build bot web
healthy && echo "↩ откатились, работает старая версия" || echo "‼️ после отката тоже не работает — нужен человек"
exit 1
