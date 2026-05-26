#!/usr/bin/env sh
set -eu

CLICKHOUSE_URL="${CLICKHOUSE_URL:-http://localhost:8123}"
CLICKHOUSE_DB="${CLICKHOUSE_DB:-default}"
CSV="${CSV:-$(dirname "$0")/../data/tutorial_flights.csv}"

DB_PARAM="database=${CLICKHOUSE_DB}"

# Idempotente: pula se a tabela já tem dados
EXISTING=$(curl -s "$CLICKHOUSE_URL/?${DB_PARAM}&query=SELECT%20count()%20FROM%20flights" 2>/dev/null || echo "0")
if echo "$EXISTING" | grep -qE '^[0-9]+$' && [ "$EXISTING" -gt "0" ]; then
  echo "flights já possui $EXISTING linhas — pulando import."
  exit 0
fi

echo "Criando banco $CLICKHOUSE_DB..."
curl -sf "$CLICKHOUSE_URL/" --data "CREATE DATABASE IF NOT EXISTS ${CLICKHOUSE_DB}"

echo "Criando tabela flights..."
curl -sf "$CLICKHOUSE_URL/?${DB_PARAM}" --data "DROP TABLE IF EXISTS flights"
curl -sf "$CLICKHOUSE_URL/?${DB_PARAM}" --data "
CREATE TABLE flights (
    \`Department\`              String,
    \`Cost\`                    Float64,
    \`Travel Class\`            String,
    \`Ticket Single or Return\` String,
    \`Airline\`                 String,
    \`Travel Date\`             Date,
    \`Origin ICAO\`             String,
    \`Origin Name\`             String,
    \`Origin Municipality\`     String,
    \`Origin Region\`           String,
    \`Origin Country\`          String,
    \`Origin Latitude\`         Nullable(Float64),
    \`Origin Longitude\`        Nullable(Float64),
    \`Destination ICAO\`        String,
    \`Destination Name\`        String,
    \`Destination Region\`      String,
    \`Destination Country\`     String,
    \`Destination Latitude\`    Nullable(Float64),
    \`Destination Longitude\`   Nullable(Float64),
    \`Distance\`                Float64
) ENGINE = MergeTree()
ORDER BY \`Travel Date\`
"

echo "Importando $CSV..."
sed 's|"#N/A"|\\N|g' "$CSV" | \
    curl -sf "$CLICKHOUSE_URL/?${DB_PARAM}&query=INSERT%20INTO%20flights%20FORMAT%20CSVWithNames" \
         --data-binary @-

COUNT=$(curl -sf "$CLICKHOUSE_URL/?${DB_PARAM}&query=SELECT%20count()%20FROM%20flights")
echo "$COUNT linhas importadas."
