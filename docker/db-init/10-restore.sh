#!/bin/bash
# Выполняется официальным образом postgres один раз — при создании пустой БД.
set -e

echo ">>> Восстанавливаю дамп в БД '$POSTGRES_DB'..."

# --no-owner/--no-privileges: в дампе владельцем указан пользователь с машины
# разработчика (Postgres.app), в контейнере такой роли нет.
pg_restore --no-owner --no-privileges \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" /seed/DataBase.backup \
    || echo ">>> pg_restore сообщил об ошибках (см. выше), проверяю результат..."

# Проверка: если таблиц нет — падаем, чтобы не поднять бота на пустой БД
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -c "SELECT count(*) AS places FROM places;" \
    -c "SELECT count(*) AS city_nodes FROM city_nodes;"

# В дампе нет таблицы bot_bookings — её создаёт бот-схема из sql/08
echo ">>> Применяю sql/08_bot_bookings.sql..."
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /seed/08_bot_bookings.sql

echo ">>> База готова."
