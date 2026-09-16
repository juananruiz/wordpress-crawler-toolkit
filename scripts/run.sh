#!/bin/bash
# Encadena todo el pipeline UNA vez: descarga, normaliza enlaces, audita huecos
# y descarga las páginas que falten. No repite el ciclo automáticamente — si al
# final quedan páginas rotas (puede pasar, ver README "Por qué hay que iterar"),
# te lo dice y te da el comando exacto para repetir tú mismo.
#
# Uso: ./run.sh <url> <directorio-destino> [dominio]
# Si no se indica el dominio, se deduce de la URL.
# Ejemplo: ./run.sh https://ejemplo.com ./salida

set -euo pipefail

URL="${1:?Uso: run.sh <url> <directorio-destino> [dominio]}"
DEST="${2:?Uso: run.sh <url> <directorio-destino> [dominio]}"
DOMAIN="${3:-$(echo "$URL" | sed -E 's#^[a-zA-Z]+://##; s#/.*$##')}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$DEST/$DOMAIN"
BROKEN_JSON="$DEST/broken.json"

echo "### 1/4 · Descarga inicial ###"
"$HERE/mirror.sh" "$URL" "$DEST"

echo ""
echo "### 2/4 · Normalizar enlaces ###"
"$HERE/normalize.sh" "$ROOT" "$DOMAIN"

echo ""
echo "### 3/4 · Auditar huecos ###"
python3 "$HERE/audit_links.py" --root "$ROOT" --out "$BROKEN_JSON"

PAGES_ROTAS=$(python3 -c "import json; print(len(json.load(open('$BROKEN_JSON'))['pages']))")

if [ "$PAGES_ROTAS" -gt 0 ]; then
  echo ""
  echo "### 4/4 · Descargar páginas que faltan ($PAGES_ROTAS) ###"
  python3 "$HERE/fetch_missing.py" --root "$ROOT" --domain "$DOMAIN" --in "$BROKEN_JSON" --category pages
  echo ""
  echo "### Renormalizar tras la descarga ###"
  "$HERE/normalize.sh" "$ROOT" "$DOMAIN"
else
  echo ""
  echo "### 4/4 · No hay páginas que descargar, se omite ###"
fi

echo ""
echo "### Auditoría final ###"
python3 "$HERE/audit_links.py" --root "$ROOT" --out "$BROKEN_JSON" --show 15

RESTANTES=$(python3 -c "import json; print(len(json.load(open('$BROKEN_JSON'))['pages']))")

echo ""
echo "============================================================"
if [ "$RESTANTES" -gt 0 ]; then
  echo "Quedan $RESTANTES páginas rotas (probablemente en cascada: las"
  echo "páginas nuevas que se acaban de traer enlazan a más páginas que"
  echo "todavía no existen). Repite este mismo comando para seguir"
  echo "cerrando huecos:"
  echo ""
  echo "  $0 \"$URL\" \"$DEST\" \"$DOMAIN\""
else
  echo "No quedan páginas rotas (aparte de posibles enlaces ya caídos"
  echo "en el propio sitio real, revisa el detalle de arriba)."
fi
echo ""
echo "Las imágenes/assets rotos NO se descargan automáticamente."
echo "Si quieres completarlos también:"
echo "  python3 \"$HERE/fetch_missing.py\" --root \"$ROOT\" --domain \"$DOMAIN\" --in \"$BROKEN_JSON\" --category images"
echo ""
echo "Para servir el sitio en local:"
echo "  \"$HERE/serve.sh\" \"$ROOT\" 8000"
echo "============================================================"
