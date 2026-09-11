#!/bin/bash
# Sirve el espejo descargado con el servidor HTTP de Python.
# Necesario porque abrir los archivos directamente con file:// no resuelve
# los index.html de cada carpeta ni las rutas raíz-relativas ("/...").
#
# Uso: ./serve.sh <carpeta-del-sitio> [puerto]

set -euo pipefail

ROOT="${1:?Uso: serve.sh <carpeta-del-sitio> [puerto]}"
PORT="${2:-8000}"

cd "$ROOT"
echo "Sirviendo $ROOT en http://localhost:$PORT/"
python3 -m http.server "$PORT"
