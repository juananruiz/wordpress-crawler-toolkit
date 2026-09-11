#!/usr/bin/env python3
"""
Escanea todos los enlaces internos (href/src que empiezan por "/") de un
espejo descargado y comprueba cuáles no resuelven a un archivo real en disco.

Separa los resultados en dos grupos:
  - "images": rutas rotas que son assets (imágenes, fuentes, pdf, etc.)
  - "pages":  rutas rotas que son páginas/contenido (todo lo demás)

Ignora rutas dinámicas que nunca van a existir como archivo estático
(wp-json, xmlrpc.php, feeds RSS, admin-ajax) y el visor de PDF embebido
(sus URLs llevan una query string que no corresponde a un archivo real).

Uso:
    ./audit_links.py --root <carpeta-del-sitio> --out broken.json
"""
import argparse
import html
import json
import os
import re
from urllib.parse import unquote, urlsplit

ASSET_EXTS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf", ".css", ".js",
    ".woff", ".woff2", ".eot", ".ttf", ".ico", ".json", ".xml", ".mp4",
    ".zip", ".doc", ".docx", ".xls", ".xlsx",
)

IGNORE_SEGMENTS = ("/wp-json/", "xmlrpc.php", "/feed", "admin-ajax", "pdfjs-viewer-for-elementor")

HREF_RE = re.compile(r'(?:href|src)="(/[^"]*)"')


def build_index(root):
    files, dirs = set(), set()
    for dirpath, _dirs, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        d = "/" + rel_dir if rel_dir else "/"
        if not d.endswith("/"):
            d += "/"
        dirs.add(d)
        for f in filenames:
            files.add("/" + (os.path.join(rel_dir, f) if rel_dir else f))
    return files, dirs


def resolves(path, files, dirs):
    path = path.split("#")[0]
    if path == "":
        return True
    if path in files:
        return True
    d = path if path.endswith("/") else path + "/"
    if d in dirs:
        return (d + "index.html") in files
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="Carpeta raíz del sitio descargado")
    ap.add_argument("--out", default=None, help="Ruta de salida en JSON (si se omite, solo imprime el resumen)")
    ap.add_argument("--show", type=int, default=40, help="Cuántas rutas listar en pantalla por categoría (default: 40)")
    args = ap.parse_args()

    files, dirs = build_index(args.root)

    broken = {}
    total_checked = 0
    for dirpath, _dirs, filenames in os.walk(args.root):
        for f in filenames:
            if not f.endswith(".html"):
                continue
            fp = os.path.join(dirpath, f)
            try:
                with open(fp, "r", encoding="utf-8", errors="surrogateescape") as fh:
                    content = fh.read()
            except OSError:
                continue
            for m in HREF_RE.finditer(content):
                raw = m.group(1)
                url = html.unescape(raw)
                path = unquote(urlsplit(url).path)
                if not path:
                    continue
                if any(seg in path for seg in IGNORE_SEGMENTS):
                    continue
                total_checked += 1
                if not resolves(path, files, dirs):
                    broken.setdefault(path, []).append(fp)

    images = {p: v for p, v in broken.items() if p.lower().endswith(ASSET_EXTS)}
    pages = {p: v for p, v in broken.items() if not p.lower().endswith(ASSET_EXTS)}

    print(f"Enlaces internos comprobados: {total_checked}")
    print(f"Rutas rotas: {len(broken)}  (imágenes/assets: {len(images)}, páginas/otras: {len(pages)})")
    print()
    print("=== Páginas rotas (no-asset) ===")
    for p, v in sorted(pages.items(), key=lambda x: -len(x[1]))[: args.show]:
        print(f"{len(v):4d}x  {p}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"images": images, "pages": pages}, fh, ensure_ascii=False, indent=1)
        print(f"\nGuardado en {args.out}")


if __name__ == "__main__":
    main()
