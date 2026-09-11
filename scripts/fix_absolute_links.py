#!/usr/bin/env python3
"""
Convierte enlaces absolutos (https://dominio/...) a rutas raíz-relativas (/...)
en todos los .html y .css de un espejo descargado con wget.

Por qué hace falta: wget solo reescribe los enlaces con --convert-links al
FINALIZAR un rastreo completo. Si el proceso se interrumpe (falla de red,
falta de memoria, lo paras tú a propósito...), esa conversión nunca se aplica
y todos los enlaces internos se quedan apuntando al dominio original — lo cual
impide navegar el espejo en local.

Es seguro volver a ejecutarlo: si ya no quedan enlaces absolutos, no hace nada.

Uso:
    ./fix_absolute_links.py --root <carpeta-del-sitio> --domain www.ejemplo.com
"""
import argparse
import os
import re


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="Carpeta raíz del sitio descargado (donde está el index.html)")
    ap.add_argument("--domain", required=True, help="Dominio a limpiar, p.ej. www.ejemplo.com")
    ap.add_argument("--extensions", default=".html,.css", help="Extensiones a procesar, separadas por comas (default: .html,.css)")
    args = ap.parse_args()

    exts = tuple(e.strip() for e in args.extensions.split(","))
    pattern = re.compile(r"https?://" + re.escape(args.domain) + r"/?")

    changed = 0
    for dirpath, _dirs, files in os.walk(args.root):
        for f in files:
            if not f.endswith(exts):
                continue
            fp = os.path.join(dirpath, f)
            try:
                with open(fp, "r", encoding="utf-8", errors="surrogateescape") as fh:
                    content = fh.read()
            except OSError as e:
                print(f"AVISO: no se pudo leer {fp}: {e}")
                continue
            new_content = pattern.sub("/", content)
            if new_content != content:
                with open(fp, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(new_content)
                changed += 1

    print(f"Archivos modificados: {changed}")


if __name__ == "__main__":
    main()
