#!/usr/bin/env bash
# 🩺 Сторож сервера (cron каждые 5 минут). Упавший бот сам сообщить не может — поэтому проверяем снаружи:
#   • контейнеры db / redis / web / bot запущены и не перезапускаются по кругу;
#   • сайт/API отвечает на 127.0.0.1:8000;
#   • диск не забит (≥ DISK_WARN %).
# Сломалось → сообщение в Telegram (ALERT_CHAT_ID или BACKUP_CHAT_ID из .env) и попытка поднять (`compose up -d`).
# Пишем только при СМЕНЕ состояния: «❌ упало» один раз, потом «✅ снова работает» — без спама каждые 5 минут.
#
# Установка (один раз):  crontab -e  →
#   */5 * * * * cd /root/yashilqullarbot && ./scripts/healthcheck.sh >> backups/health.log 2>&1
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
STATE=backups/.health_state
DISK_WARN="${DISK_WARN:-90}"
DC="${DC:-docker compose}"                       # для тестов можно подменить
CURL="${CURL:-curl}"

env_get() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r' | sed -e 's/^["'\'']//' -e 's/["'\'']$//'; }
TOKEN="$(env_get BOT_TOKEN)"
CHAT="$(env_get ALERT_CHAT_ID)"; [ -z "$CHAT" ] && CHAT="$(env_get BACKUP_CHAT_ID)"

tg() { [ -n "$TOKEN" ] && [ -n "$CHAT" ] && $CURL -sS --max-time 20 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
         --data-urlencode "chat_id=${CHAT}" --data-urlencode "text=$1" >/dev/null 2>&1 || true; }

problems=()
for svc in db redis web bot; do
  st="$($DC ps --format '{{.Service}} {{.State}}' 2>/dev/null | awk -v s="$svc" '$1==s{print $2}')"
  if [ "$st" != "running" ]; then
    problems+=("$svc: ${st:-нет контейнера}")
  fi
done
code="$($CURL -s -o /dev/null -m 10 -w '%{http_code}' http://127.0.0.1:8000/ 2>/dev/null || true)"
case "$code" in 000|5??|"") problems+=("сайт/API не отвечает (HTTP ${code:-000})");; esac
disk="$(df -P / | awk 'NR==2{gsub("%","",$5); print $5}')"
[ "${disk:-0}" -ge "$DISK_WARN" ] && problems+=("диск заполнен на ${disk}%")

now="$(date '+%d.%m %H:%M')"
prev="$(cat "$STATE" 2>/dev/null || echo ok)"
if [ ${#problems[@]} -eq 0 ]; then
  if [ "$prev" != "ok" ]; then
    tg "✅ Yashil Qo'llar: всё снова работает ($now)"
    echo "[$now] recovered"
  fi
  echo ok > "$STATE"
  exit 0
fi

summary="$(printf '%s; ' "${problems[@]}")"
if [ "$prev" != "$summary" ]; then             # новая или другая проблема — сообщаем один раз
  tg "❌ Yashil Qo'llar ($now): ${summary%; }
Пробую поднять: docker compose up -d. Логи: docker compose logs --tail=50 bot web"
  echo "[$now] $summary"
fi
echo "$summary" > "$STATE"
# пробуем поднять упавшее (тома с данными не трогаются)
if printf '%s' "$summary" | grep -qE '(db|redis|web|bot):|не отвечает'; then
  $DC up -d >/dev/null 2>&1 || true
fi
exit 1
