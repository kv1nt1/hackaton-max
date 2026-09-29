#!/bin/sh
# Выполняется контейнером postgres один раз, при первом создании тома.
# 1) если есть data/DataBase.backup — восстанавливаем его (custom-формат или plain SQL);
# 2) иначе применяем sql/01..08 по порядку.
set -eu

BACKUP=/seed/data/DataBase.backup
SQL_DIR=/seed/sql

psql_strict() { psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" "$@"; }
psql_loose()  { psql -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" "$@"; }

if [ -s "$BACKUP" ]; then
  echo "[init] восстанавливаю дамп $BACKUP"
  if head -c 5 "$BACKUP" | grep -q PGDMP; then
    pg_restore --no-owner --no-privileges \
      --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" "$BACKUP" \
      || echo "[init] pg_restore завершился с предупреждениями (часто безвредны), проверяю результат"
  else
    psql_loose -f "$BACKUP"
  fi

  # Дамп мог быть сделан до появления таблиц бронирований — донакатываем 07 и 08.
  # Ошибки «already exists» здесь ожидаемы и безвредны.
  for f in "$SQL_DIR"/07_*.sql "$SQL_DIR"/08_*.sql; do
    [ -e "$f" ] || continue
    echo "[init] применяю $f"
    psql_loose -f "$f"
  done
else
  echo "[init] дампа нет, применяю схему из $SQL_DIR"
  for f in "$SQL_DIR"/*.sql; do
    echo "[init] применяю $f"
    psql_strict -f "$f"
  done
fi

TABLES=$(psql_strict -tAc "select count(*) from information_schema.tables where table_schema='public'")
if [ "$TABLES" -eq 0 ]; then
  echo "[init] ОШИБКА: в схеме public нет таблиц" >&2
  exit 1
fi
echo "[init] готово, таблиц в public: $TABLES"
