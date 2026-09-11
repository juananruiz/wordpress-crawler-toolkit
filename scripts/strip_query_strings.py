#!/usr/bin/env python3
"""
Renombra assets CSS/JS que wget guardó con el carácter "?" literalmente en el
nombre de archivo, y corrige las referencias correspondientes en HTML/CSS.

Por qué hace falta: para URLs con query string (p.ej. "jquery.min.js?ver=3.7.1"),
wget guarda el archivo en disco con el "?" incluido tal cual en el nombre. El
problema es que CUALQUIER servidor HTTP interpreta ese "?" como el inicio de
la query string de la petición, no como parte del nombre de archivo — así que
esos ficheros nunca se pueden servir con un servidor HTTP normal (aunque
existan en disco). La solución: renombrar quitando la query string y
actualizar el HTML/CSS para que enlace al nombre limpio.

Se procesan solo archivos .css y .js: para páginas HTML con query string
(p.ej. "index.html?p=123") no se hace nada automáticamente, porque suele haber
muchas variantes de la misma página base que colisionarían al quitarles la
query (ver README, sección "Limitaciones").

Detecta colisiones (dos variantes distintas que, al quitarles la query,
tendrían el mismo nombre) y las deja sin tocar para no perder contenido.

Es seguro volver a ejecutarlo.

Uso:
    ./strip_query_strings.py --root <carpeta-del-sitio>
"""
import argparse
import json
import os
from collections import defaultdict


def find_candidates(root):
    candidates = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if "?" not in f:
                continue
            stripped = f.split("?")[0]
            if stripped.endswith(".css") or stripped.endswith(".js"):
                candidates.append((dirpath, f, stripped))
    return candidates


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="Carpeta raíz del sitio descargado")
    ap.add_argument("--extensions", default=".html,.css", help="Extensiones donde reescribir referencias (default: .html,.css)")
    ap.add_argument("--dry-run", action="store_true", help="Solo mostrar qué se haría, sin tocar nada")
    args = ap.parse_args()
    exts = tuple(e.strip() for e in args.extensions.split(","))

    candidates = find_candidates(args.root)
    by_dir_stripped = defaultdict(list)
    for dirpath, f, stripped in candidates:
        by_dir_stripped[(dirpath, stripped)].append(f)

    renames = []
    mapping = {}
    skipped_collisions = 0
    for (dirpath, stripped), variants in by_dir_stripped.items():
        target_path = os.path.join(dirpath, stripped)
        if len(variants) > 1:
            skipped_collisions += 1
            continue
        old_path = os.path.join(dirpath, variants[0])
        if not os.path.exists(target_path):
            renames.append((old_path, target_path))
        mapping["/" + os.path.relpath(old_path, args.root)] = "/" + os.path.relpath(target_path, args.root)

    print(f"Candidatos: {len(candidates)} | colisiones omitidas: {skipped_collisions} | a renombrar: {len(renames)}")

    if args.dry_run:
        for old, new in renames:
            print(f"  {old} -> {new}")
        return

    for old, new in renames:
        os.rename(old, new)

    pairs = []
    for logical, actual in mapping.items():
        pairs.append((logical, actual))
        if "&" in logical:
            pairs.append((logical.replace("&", "&#038;"), actual.replace("&", "&#038;")))
            pairs.append((logical.replace("&", "&amp;"), actual.replace("&", "&amp;")))
    pairs.sort(key=lambda p: -len(p[0]))

    changed_files = 0
    total_repl = 0
    for dirpath, _dirs, files in os.walk(args.root):
        for f in files:
            if not f.endswith(exts):
                continue
            fp = os.path.join(dirpath, f)
            try:
                with open(fp, "r", encoding="utf-8", errors="surrogateescape") as fh:
                    content = fh.read()
            except OSError:
                continue
            orig = content
            for logical, actual in pairs:
                if logical in content:
                    content = content.replace(logical, actual)
                    total_repl += 1
            if content != orig:
                with open(fp, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(content)
                changed_files += 1

    print(f"Archivos de referencias modificados: {changed_files}, sustituciones: {total_repl}")


if __name__ == "__main__":
    main()
