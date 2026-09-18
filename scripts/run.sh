#!/bin/bash
# Encadena todo el pipeline: descarga, normaliza enlaces, audita huecos y
# descarga las páginas que falten. Dos modos:
#
#   manual (por defecto) — hace UNA pasada de auditoría+descarga y para. Si
#                           quedan páginas rotas (cascada, ver README "Por qué
#                           hay que iterar"), te da el comando para repetir tú
#                           mismo viendo qué pasa en cada vuelta.
#   auto                 — repite el ciclo auditoría→descarga→normalizar solo,
#                           hasta que no queden páginas rotas o se alcance el
#                           límite de seguridad de iteraciones (evita un bucle
#                           infinito si algo nunca converge).
#
# Uso: ./run.sh [--auto|--manual] <url> <directorio-destino> [dominio]
# Ejemplos:
#   ./run.sh https://ejemplo.com ./salida
#   ./run.sh --auto https://ejemplo.com ./salida

set -euo pipefail

MODE="manual"
MAX_ITER=15

# --- parseo de opciones (--auto/--manual pueden ir en cualquier posición) ---
args=()
for arg in "$@"; do
  case "$arg" in
    --auto) MODE="auto" ;;
    --manual) MODE="manual" ;;
    --mode=auto) MODE="auto" ;;
    --mode=manual) MODE="manual" ;;
    *) args+=("$arg") ;;
  esac
done
set -- "${args[@]:-}"

URL="${1:?Uso: run.sh [--auto|--manual] <url> <directorio-destino> [dominio]}"
DEST="${2:?Uso: run.sh [--auto|--manual] <url> <directorio-destino> [dominio]}"
DOMAIN="${3:-$(echo "$URL" | sed -E 's#^[a-zA-Z]+://##; s#/.*$##')}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$DEST/$DOMAIN"
BROKEN_JSON="$DEST/broken.json"

echo "Modo: $MODE"
echo ""
echo "### Descarga inicial ###"
"$HERE/mirror.sh" "$URL" "$DEST"

echo ""
echo "### Normalizar enlaces ###"
"$HERE/normalize.sh" "$ROOT" "$DOMAIN"

iter=0
while true; do
  iter=$((iter + 1))
  echo ""
  echo "### Auditoría (vuelta $iter) ###"
  python3 "$HERE/audit_links.py" --root "$ROOT" --out "$BROKEN_JSON" --show 15
  PAGES_ROTAS=$(python3 -c "import json; print(len(json.load(open('$BROKEN_JSON'))['pages']))")

  if [ "$PAGES_ROTAS" -eq 0 ]; then
    echo ""
    echo "No quedan páginas rotas (aparte de posibles enlaces ya caídos"
    echo "en el propio sitio real, revisa el detalle de arriba)."
    break
  fi

  if [ "$MODE" = "manual" ]; then
    echo ""
    echo "============================================================"
    echo "Quedan $PAGES_ROTAS páginas rotas (probablemente en cascada: las"
    echo "páginas nuevas que se acaban de traer enlazan a más páginas que"
    echo "todavía no existen). Repite este mismo comando para seguir"
    echo "cerrando huecos:"
    echo ""
    echo "  $0 --manual \"$URL\" \"$DEST\" \"$DOMAIN\""
    echo ""
    echo "O usa --auto para que lo repita él solo hasta converger:"
    echo "  $0 --auto \"$URL\" \"$DEST\" \"$DOMAIN\""
    echo "============================================================"
    exit 0
  fi

  # modo auto: sigue solo
  if [ "$iter" -ge "$MAX_ITER" ]; then
    echo ""
    echo "============================================================"
    echo "Límite de $MAX_ITER vueltas alcanzado sin converger del todo."
    echo "Quedan $PAGES_ROTAS páginas rotas. Puede que el sitio tenga"
    echo "enlaces genuinamente rotos que nunca se van a resolver — revisa"
    echo "$BROKEN_JSON a mano."
    echo "============================================================"
    exit 1
  fi

  echo ""
  echo "### Descargar páginas que faltan ($PAGES_ROTAS) — vuelta $iter ###"
  python3 "$HERE/fetch_missing.py" --root "$ROOT" --domain "$DOMAIN" --in "$BROKEN_JSON" --category pages

  echo ""
  echo "### Renormalizar tras la descarga ###"
  "$HERE/normalize.sh" "$ROOT" "$DOMAIN"
done

echo ""
echo "============================================================"
echo "Las imágenes/assets rotos NO se descargan automáticamente."
echo "Si quieres completarlos también:"
echo "  python3 \"$HERE/fetch_missing.py\" --root \"$ROOT\" --domain \"$DOMAIN\" --in \"$BROKEN_JSON\" --category images"
echo ""
echo "Para servir el sitio en local:"
echo "  $HERE/serve.sh $ROOT 8000"
echo "============================================================"
