#!/usr/bin/env python3
"""
Corrige referencias rotas a CSS/JS cuya extensión quedó duplicada al final
por culpa de --adjust-extension de wget.

Por qué hace falta: cuando una URL de asset lleva query string de cache-busting
(p.ej. "estilo.css?ver=1.2.3"), wget a veces guarda el archivo añadiendo la
extensión otra vez al final ("estilo.css?ver=1.2.3.css") para asegurarse de que
el tipo de archivo sea reconocible. El HTML, sin embargo, sigue enlazando a la
ruta original ("estilo.css?ver=1.2.3"), que ya no existe con ese nombre exacto.

Este script detecta esos archivos en disco, construye el mapeo entre la ruta
"lógica" (la que aparece en los enlaces) y la ruta real guardada, y reescribe
las referencias en .html/.css para que apunten al nombre real (incluyendo las
variantes con "&" codificado como entidad HTML, &amp; / &#038;).

Es seguro volver a ejecutarlo.

Uso:
    ./fix_duplicate_extensions.py --root <carpeta-del-sitio>
"""
import argparse
import os
import re


def build_mapping(root):
    # (logical_href, actual_href, ext) — ext es "css" o "js", la extensión duplicada
    entries = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            m = re.search(r"\.(css|js)\?[^/]*\.(css|js)$", f)
            if m and m.group(1) == m.group(2):
                full = os.path.join(dirpath, f)
                logical = full[: -len(m.group(2)) - 1]  # quita la extensión duplicada del final
                logical_href = "/" + os.path.relpath(logical, root)
                actual_href = "/" + os.path.relpath(full, root)
                entries.append((logical_href, actual_href, m.group(2)))
    return entries


def expand_entity_variants(entries):
    # NOTA sobre idempotencia: "logical" es siempre un prefijo exacto de "actual"
    # (actual = logical + "." + ext). Un simple str.replace(logical, actual)
    # también encontraría "logical" dentro de un "actual" ya corregido y le
    # añadiría la extensión otra vez en cada ejecución (bug real detectado y
    # corregido: dejaba ".css.css.css..." tras varias pasadas). Por eso aquí se
    # compila un patrón con "lookahead" negativo que excluye las apariciones que
    # ya llevan la extensión duplicada puesta.
    patterns = []
    for logical, actual, ext in entries:
        variants = [logical]
        if "&" in logical:
            variants.append(logical.replace("&", "&#038;"))
            variants.append(logical.replace("&", "&amp;"))
        for variant_logical in variants:
            variant_actual = actual if variant_logical == logical else variant_logical + "." + ext
            pattern = re.compile(re.escape(variant_logical) + r"(?!\." + re.escape(ext) + r")")
            patterns.append((pattern, variant_actual))
    patterns.sort(key=lambda p: -len(p[0].pattern))
    return patterns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="Carpeta raíz del sitio descargado")
    ap.add_argument("--extensions", default=".html,.css", help="Extensiones a reescribir (default: .html,.css)")
    args = ap.parse_args()
    exts = tuple(e.strip() for e in args.extensions.split(","))

    entries = build_mapping(args.root)
    print(f"Mapeos encontrados: {len(entries)}")
    if not entries:
        return

    patterns = expand_entity_variants(entries)

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
            for pattern, actual in patterns:
                # replacement como función: evita que un "actual" con "\" se
                # interprete como referencia de grupo de regex (p.ej. "\1")
                content, n = pattern.subn(lambda _m, _a=actual: _a, content)
                total_repl += n
            if content != orig:
                with open(fp, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(content)
                changed_files += 1

    print(f"Archivos modificados: {changed_files}, sustituciones aplicadas: {total_repl}")


if __name__ == "__main__":
    main()
