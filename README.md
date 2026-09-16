# wp-mirror-toolkit

Herramientas para descargar un espejo estático navegable de un sitio
WordPress (o similar) con `wget`, y dejarlo listo para servirlo en local
corrigiendo los problemas de enlaces que `wget` deja por el camino.

Nace de descargar y arreglar una copia local de un sitio WordPress real
(muchas páginas, plugins de Elementor, sliders, formularios...). El flujo
manual llevó a varios problemas repetidos que estos scripts automatizan.

## Por qué no basta con `wget --mirror --convert-links`

- **`--convert-links` solo se aplica al final de un rastreo completo.** Si el
  proceso se corta (falla de red, memoria, o lo paras tú), los enlaces se
  quedan apuntando al dominio original y el espejo no es navegable en local.
- **`--adjust-extension` puede duplicar la extensión** en assets con query
  string de cache-busting (`estilo.css?ver=1.2.3` se guarda a veces como
  `estilo.css?ver=1.2.3.css`), y el HTML no se actualiza para apuntar ahí.
- **wget guarda el `?` de la query string literalmente en el nombre de
  archivo** (`jquery.min.js?ver=3.7.1` es el nombre real en disco). Ningún
  servidor HTTP puede servir eso bien, porque siempre interpreta el `?` como
  inicio de la query string de la petición, no como parte del nombre.
- **Un rastreo recursivo se puede interrumpir a medias**, dejando páginas
  enlazadas entre sí pero con huecos: la página A enlaza a B, y B a C, pero
  el rastreo se cortó antes de llegar a C.

## Requisitos

- `wget` (macOS: `brew install wget`)
- `curl`
- `python3` (solo librería estándar, no hace falta instalar nada más)

## Flujo de trabajo

### Con un solo comando

`run.sh` encadena descarga + normalización + auditoría + descarga de páginas
que falten, **una sola vez**, y al final te dice cuántas páginas rotas
quedan. Si quedan páginas rotas en cascada (ver más abajo), te da el mismo
comando para volver a lanzarlo — no repite el ciclo solo, así siempre ves qué
está pasando en cada vuelta.

```bash
./scripts/run.sh https://ejemplo.com ./salida
# si al final dice que quedan páginas rotas, se repite tal cual:
./scripts/run.sh https://ejemplo.com ./salida
# cuando ya no queden páginas rotas:
./scripts/serve.sh ./salida/www.ejemplo.com 8000
```

### Paso a paso (si prefieres ir viendo cada fase)

```bash
# 1. Descarga inicial (resumible: se puede volver a lanzar igual si se corta)
./scripts/mirror.sh https://ejemplo.com ./salida

# 2. Corrige los tres problemas de enlaces de wget descritos arriba
./scripts/normalize.sh ./salida/www.ejemplo.com www.ejemplo.com

# 3. Detecta qué falta (páginas nunca descargadas, imágenes rotas...)
./scripts/audit_links.py --root ./salida/www.ejemplo.com --out broken.json

# 4. Descarga puntualmente las páginas que faltan directamente del sitio real
#    (mucho más rápido que repetir el rastreo completo)
./scripts/fetch_missing.py --root ./salida/www.ejemplo.com \
    --domain www.ejemplo.com --in broken.json --category pages

# 5. Vuelve a normalizar (las páginas nuevas también pueden tener enlaces
#    absolutos o assets con el problema de la query string)
./scripts/normalize.sh ./salida/www.ejemplo.com www.ejemplo.com

# 6. Repite 3-5: cada tanda de páginas nuevas puede revelar más páginas que
#    tampoco existían (ver "Por qué hay que iterar" más abajo). Cuando
#    audit_links.py ya no encuentra páginas nuevas (solo imágenes, si has
#    decidido dejarlas), está terminado.

# 7. Sirve el resultado en local
./scripts/serve.sh ./salida/www.ejemplo.com 8000
# abre http://localhost:8000/
```

### Por qué hay que iterar el paso 3-5

Si la descarga inicial se interrumpió, el sitio descargado es un grafo
incompleto: cada página que faltaba y se descarga en el paso 4 puede a su vez
enlazar a páginas que **tampoco** se habían descargado. La auditoría solo ve
los enlaces de las páginas que ya existen en disco, así que cada vuelta del
ciclo revela una capa más. En la práctica converge rápido (unas pocas
iteraciones), especialmente si lo único que queda son páginas de paginación
de categorías (`/category/x/page/N/`), que conviene descargar todas de golpe
en vez de una a una.

## Qué hace cada script

| Script | Qué hace |
|---|---|
| `mirror.sh` | Descarga inicial con `wget --mirror`, resumible, con timeouts. |
| `fix_absolute_links.py` | `https://dominio/...` → `/...` en `.html`/`.css`. |
| `fix_duplicate_extensions.py` | Arregla assets con `.css`/`.js` duplicado al final del nombre. |
| `strip_query_strings.py` | Renombra CSS/JS con `?` literal en el nombre de archivo y corrige referencias. |
| `normalize.sh` | Encadena los tres scripts anteriores, en orden. |
| `audit_links.py` | Escanea todos los `href`/`src` internos y reporta cuáles no existen en disco (separa páginas de imágenes/assets). |
| `fetch_missing.py` | Descarga del sitio real las rutas que `audit_links.py` marcó como rotas. |
| `serve.sh` | `python3 -m http.server` en la carpeta del sitio. |

Todos los scripts de Python son **idempotentes**: se pueden volver a
ejecutar sobre un sitio ya corregido sin que pase nada raro (si no encuentran
nada que arreglar, simplemente no tocan archivos).

## Limitaciones conocidas (no automatizadas)

- **Assets cargados dinámicamente desde JavaScript** (por ejemplo, un
  "worker" de una librería que el propio JS pide en tiempo de ejecución, no
  un `<script src="...">` estático) no los detecta `wget` al rastrear, así
  que no aparecen ni en el espejo ni en la auditoría de enlaces internos
  (porque la auditoría también se basa en `href`/`src` del HTML). Si algo
  deja de funcionar en el navegador aunque su página cargue bien, revisa la
  consola del navegador para ver qué petición falla y descárgala a mano con
  `curl` a la misma ruta relativa dentro del espejo.
- **Enlaces internos inconsistentes que ya existen en el sitio real**
  (por ejemplo, una página que enlaza a una URL antigua que el propio sitio
  redirige con 301 a la URL "buena", en vez de enlazar directamente a la
  buena) no se detectan ni corrigen automáticamente — para el espejo local,
  el contenido en la URL antigua simplemente no existe. Si te encuentras uno,
  compara ambas URLs contra el sitio real (`curl -I` para ver si hay 301) y
  copia el contenido a la ruta que falte.
- **Páginas HTML con query string** (`index.html?p=123`, típico de
  WordPress) se dejan tal cual: normalmente hay muchas variantes de la misma
  base que colisionarían si se les quitara la query, y encima suelen ser
  copias duplicadas de contenido que ya existe en su URL "bonita".
- El PDF/documento en sí referenciado desde una página puede no descargarse
  si el sitio lo carga por JavaScript en vez de un enlace `<a href>` normal
  (mismo caso que el primer punto).

## Advertencia de seguridad al reescribir contenido

Si escribes tu propia variante de estos scripts (o los modificas), ten en
cuenta un fallo real que apareció durante el desarrollo de este toolkit:
`fix_duplicate_extensions.py` mapea una ruta "lógica" a una ruta "real" que
**siempre es la lógica con una extensión añadida al final**
(`...css?ver=X` → `...css?ver=X.css`). Un `str.replace(logica, real)` naíf
encuentra esa misma ruta lógica *dentro* de una ruta ya corregida (porque es
un prefijo exacto) y le vuelve a añadir la extensión — cada ejecución añade
una `.css` más (`...css.css.css...`), corrompiendo silenciosamente cientos de
archivos si se ejecuta el script más de una vez. Aquí está corregido con una
expresión regular con *lookahead* negativo que excluye las apariciones que ya
llevan la extensión puesta. Si tocas ese script, comprueba la idempotencia
ejecutándolo dos veces seguidas y verificando que la segunda vez no modifica
nada.

## Licencia

Uso personal / interno. Ajusta según lo que necesites reutilizar.
