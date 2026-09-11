#!/usr/bin/env python3
"""
Descarga directamente del sitio real las rutas que audit_links.py marcó como
rotas, sin relanzar un rastreo recursivo completo (mucho más rápido cuando
solo faltan unas pocas decenas/cientos de páginas).

Nota importante: como cada página nueva puede enlazar a otras páginas que
todavía no existen en el espejo, normalmente hace falta repetir el ciclo
"auditar -> descargar lo que falte" varias veces hasta que ya no aparezca
nada nuevo (ver README).

Uso:
    ./fetch_missing.py --root <carpeta-del-sitio> --domain www.ejemplo.com \
        --in broken.json --category pages
"""
import argparse
import json
import os
import subprocess


def fetch(path, root, base_url, timeout):
    if path.endswith("/"):
        dest = os.path.join(root, path.lstrip("/"), "index.html")
    else:
        dest = os.path.join(root, path.lstrip("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    url = base_url + path
    try:
        r = subprocess.run(
            ["curl", "-s", "-L", "-o", dest, "-w", "%{http_code}", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 10,
        )
        code = r.stdout.strip()
    except subprocess.TimeoutExpired:
        code = "timeout"

    if code == "200":
        return "ok"
    if os.path.exists(dest) and (code != "200"):
        # limpiar cuerpo de error (páginas 404 personalizadas, etc.)
        os.remove(dest)
    return code


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="Carpeta raíz del sitio descargado")
    ap.add_argument("--domain", required=True, help="Dominio del sitio real, p.ej. www.ejemplo.com")
    ap.add_argument("--in", dest="in_file", required=True, help="JSON de audit_links.py")
    ap.add_argument("--category", choices=["pages", "images", "both"], default="pages",
                     help="Qué categoría del JSON descargar (default: pages)")
    ap.add_argument("--timeout", type=int, default=20, help="Timeout por petición en segundos (default: 20)")
    args = ap.parse_args()

    with open(args.in_file, encoding="utf-8") as fh:
        data = json.load(fh)

    categories = ["pages", "images"] if args.category == "both" else [args.category]
    todo = sorted({p for cat in categories for p in data.get(cat, {})})

    base_url = f"https://{args.domain}"
    results = {"ok": [], "notfound": [], "error": []}
    for i, path in enumerate(todo, 1):
        status = fetch(path, args.root, base_url, args.timeout)
        if status == "ok":
            results["ok"].append(path)
        elif status == "404":
            results["notfound"].append(path)
        else:
            results["error"].append((path, status))
        if i % 20 == 0:
            print(f"  {i}/{len(todo)}...")

    print(f"\nOK: {len(results['ok'])}")
    print(f"404 (no existen tampoco en el sitio real): {len(results['notfound'])}")
    print(f"Errores: {len(results['error'])}")
    for p, c in results["error"]:
        print(f"  {c}  {p}")

    out_file = os.path.splitext(args.in_file)[0] + "_fetch_results.json"
    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    print(f"\nResultados guardados en {out_file}")
    print("Siguiente paso: vuelve a ejecutar normalize.sh para limpiar los enlaces de las páginas nuevas,")
    print("luego audit_links.py otra vez por si aparecen más huecos en cascada.")


if __name__ == "__main__":
    main()
