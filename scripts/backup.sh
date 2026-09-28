#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# 🗄 Ежедневный бэкап Yashil Qo'llar → закрытый Telegram-канал.
#
#   Каждый день:  Postgres (все таблицы: люди, мероприятия, участия…) + Redis
#                 (грязные места, итоги мероприятий, очередь, языки…)
#                 → один архив, зашифрованный паролем → в канал + в backups/ на сервере.
#   По воскресеньям ещё и фото (media/, без миниатюр) — отдельным архивом.
#   На сервере хранятся последние 14 ежедневных и 4 недельных архива.
#   Если что-то сломалось — в канал приходит «❌ Бэкап не удался».
#
# Настройки — в .env (рядом с docker-compose.yml):
#   BOT_TOKEN=...           уже есть (тот же бот)
#   BACKUP_CHAT_ID=-100...  id закрытого канала, бот в нём — админ
#   BACKUP_PASSWORD=...     пароль шифрования. БЕЗ НЕГО БЭКАП НЕ ОТКРЫТЬ — храни отдельно!
#
# Запуск руками:      ./scripts/backup.sh               (--test — только проверить канал, --with-media — и фото)
# По расписанию (cron, 03:00 по Ташкенту = 22:00 UTC):
#   0 22 * * * cd /root/yashilqullarbot && ./scripts/backup.sh >> backups/backup.log 2>&1
#
# Как восстановить (на своём компьютере или сервере):
#   openssl enc -d -aes-256-cbc -pbkdf2 -in backup_XXXX.tar.gz.enc -out b.tar.gz -pass pass:'ПАРОЛЬ'
#   tar xzf b.tar.gz          → db.sql.gz, redis.rdb
#   gunzip -c db.sql.gz | docker compose exec -T db psql -U postgres postgres    # в ПУСТУЮ базу
#   Redis: остановить redis, положить redis.rdb как /data/dump.rdb, убрать appendonlydir, запустить.
# ─────────────────────────────────────────────────────────────────────────────
set -Eeuo pipefail

cd "$(dirname "$0")/.."
DIR=backups
KEEP_DAILY=14
KEEP_WEEKLY=4
TG_LIMIT=$((49 * 1024 * 1024))          # Telegram: боту — файлы до 50 МБ

env_get() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r' | sed -e 's/^["'\'']//' -e 's/["'\'']$//'; }
TOKEN="$(env_get BOT_TOKEN)"
CHAT="$(env_get BACKUP_CHAT_ID)"
PASS="$(env_get BACKUP_PASSWORD)"
DC="${DC:-docker compose}"              # для тестов можно подменить

tg() {  # tg sendMessage|sendDocument  -F ...
  local method=$1; shift
  curl -sS --max-time 120 "https://api.telegram.org/bot${TOKEN}/${method}" -F chat_id="${CHAT}" "$@" \
    | grep -q '"ok":true'
}
human() { numfmt --to=iec --suffix=B "$1" 2>/dev/null || echo "$1 B"; }

fail() {
  local line=$1
  echo "[$(date '+%F %T')] ОШИБКА в строке $line" >&2
  [ -n "$TOKEN" ] && [ -n "$CHAT" ] && tg sendMessage -F text="❌ Бэкап не удался ($(date '+%d.%m %H:%M'), строка $line). Смотри backups/backup.log на сервере." || true
}
trap 'fail $LINENO' ERR

if [ -z "$TOKEN" ] || [ -z "$CHAT" ] || [ -z "$PASS" ]; then
  echo "В .env нужны BOT_TOKEN, BACKUP_CHAT_ID и BACKUP_PASSWORD" >&2
  exit 1
fi

if [ "${1:-}" = "--test" ]; then
  tg sendMessage -F text="✅ Бэкап-бот подключён к каналу. Ночные бэкапы будут приходить сюда." \
    && echo "OK: сообщение в канал отправлено" || { echo "Не получилось: проверь BACKUP_CHAT_ID и что бот — админ канала"; exit 1; }
  exit 0
fi

# один бэкап за раз
exec 9>"/tmp/yashilqollar-backup.lock"
flock -n 9 || { echo "Бэкап уже идёт"; exit 0; }

mkdir -p "$DIR"
chmod 700 "$DIR"
TS="$(date +%F_%H%M)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 1) Postgres — вся база (Django: имя и пользователь — postgres)
$DC exec -T db pg_dump -U postgres postgres | gzip -9 > "$WORK/db.sql.gz"
DB_SIZE=$(stat -c %s "$WORK/db.sql.gz")
[ "$DB_SIZE" -gt 20000 ] || { echo "Дамп базы подозрительно маленький: $DB_SIZE байт"; false; }
USERS=$($DC exec -T db psql -U postgres -d postgres -tAc "select count(*) from app_telegram_tguser" | tr -d '[:space:]')

# 2) Redis — снимок на диск и копия файла
$DC exec -T redis redis-cli SAVE > /dev/null
$DC cp redis:/data/dump.rdb "$WORK/redis.rdb"
REDIS_SIZE=$(stat -c %s "$WORK/redis.rdb")

# 3) Архив + шифрование
export BACKUP_PASS_ENV="$PASS"          # пароль — через окружение, не в командной строке (не виден в ps)
encrypt() { openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_PASS_ENV -out "$1"; }
OUT="$DIR/backup_${TS}.tar.gz.enc"
tar czf - -C "$WORK" db.sql.gz redis.rdb | encrypt "$OUT"
chmod 600 "$OUT"
SIZE=$(stat -c %s "$OUT")

CAPTION="🗄 Бэкап $(date '+%d.%m.%Y %H:%M')
👥 Пользователей: ${USERS}
🐘 База: $(human "$DB_SIZE") · 🧠 Redis: $(human "$REDIS_SIZE")
🔒 Зашифрован (BACKUP_PASSWORD)"
tg sendDocument -F document=@"$OUT" -F caption="$CAPTION"

# 4) По воскресеньям — фото (без миниатюр: они пересоздаются сами)
if [ "$(date +%u)" = "7" ] || [ "${1:-}" = "--with-media" ]; then
  MOUT="$DIR/media_${TS}.tar.gz.enc"
  tar czf - --exclude='media/thumbs' media | encrypt "$MOUT"
  chmod 600 "$MOUT"
  MSIZE=$(stat -c %s "$MOUT")
  if [ "$MSIZE" -lt "$TG_LIMIT" ]; then
    tg sendDocument -F document=@"$MOUT" -F caption="🖼 Фото (media/) — $(human "$MSIZE"), недельный архив"
  else
    tg sendMessage -F text="🖼 Архив фото — $(human "$MSIZE"), больше лимита Telegram (50 МБ). Лежит на сервере: $MOUT. Скачать: scp root@<сервер>:~/yashilqullarbot/$MOUT ."
  fi
fi

# 5) Старые — удаляем
prune() {  # prune <маска> <сколько оставить> — самые новые остаются (файлов может и не быть)
  find "$DIR" -maxdepth 1 -name "$1" -printf '%T@ %p\n' | sort -rn | tail -n +$(($2 + 1)) | cut -d' ' -f2- | xargs -r rm -f --
}
prune 'backup_*.tar.gz.enc' "$KEEP_DAILY"
prune 'media_*.tar.gz.enc' "$KEEP_WEEKLY"

echo "[$(date '+%F %T')] OK: $OUT ($(human "$SIZE")), пользователей: $USERS"
