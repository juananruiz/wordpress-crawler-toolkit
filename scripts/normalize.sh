#!/bin/bash
# Aplica las tres correcciones de enlaces, en el orden correcto, sobre un
# espejo ya descargado (o parcialmente descargado). Seguro de repetir.
#
# Uso: ./normalize.sh <carpeta-del-sitio> <dominio>
# Ejemplo: ./normalize.sh ./salida/www.ejemplo.com www.ejemplo.com

set -euo pipefail

ROOT="${1:?Uso: normalize.sh <carpeta-del-sitio> <dominio>}"
DOMAIN="${2:?Uso: normalize.sh <carpeta-del-sitio> <dominio>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== 1/3 Enlaces absolutos -> raíz-relativos =="
python3 "$HERE/fix_absolute_links.py" --root "$ROOT" --domain "$DOMAIN"

echo ""
echo "== 2/3 Extensiones duplicadas en assets con query string =="
python3 "$HERE/fix_duplicate_extensions.py" --root "$ROOT"

echo ""
echo "== 3/3 Query strings literales en nombres de archivo (CSS/JS) =="
python3 "$HERE/strip_query_strings.py" --root "$ROOT"

echo ""
echo "Normalización completa. Siguiente paso: ./audit_links.py --root \"$ROOT\" --out broken.json"
