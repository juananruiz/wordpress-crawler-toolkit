#!/bin/bash
# Descarga un espejo estático de un sitio (pensado para WordPress) con wget.
# Resumible: se puede interrumpir y volver a lanzar sin perder lo ya descargado
# (usa --no-clobber). Incluye timeouts para no quedarse colgado en una petición
# si el servidor va lento.
#
# Uso: ./mirror.sh <url> <directorio-destino>
# Ejemplo: ./mirror.sh https://ejemplo.com ./salida

set -euo pipefail

URL="${1:?Uso: mirror.sh <url> <directorio-destino>}"
DEST="${2:?Uso: mirror.sh <url> <directorio-destino>}"

command -v wget >/dev/null 2>&1 || {
  echo "wget no está instalado. En macOS: brew install wget" >&2
  exit 1
}

nice -n 15 wget \
  --mirror \
  --convert-links \
  --adjust-extension \
  --page-requisites \
  --no-parent \
  --no-clobber \
  -e robots=off \
  --timeout=30 \
  --tries=3 \
  --waitretry=5 \
  --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -P "$DEST" \
  "$URL"

echo ""
echo "Descarga terminada (o interrumpida) en: $DEST"
echo "Si el proceso se cortó a mitad, vuelve a ejecutar este mismo comando para reanudar."
echo "Siguiente paso: ./normalize.sh <directorio-del-sitio-descargado> <dominio>"
