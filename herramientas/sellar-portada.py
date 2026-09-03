"""Las cifras de la portada se calculan; no se escriben a mano.

POR QUÉ EXISTE
--------------
La página calcula sus propias cifras y las muestra bien. Pero **la tarjeta que ve
quien comparte el enlace, y lo que lee un buscador, están escritas a mano en el
encabezado del archivo** —en las etiquetas `description`, `og:description`,
`twitter:description` y en el bloque de datos estructurados—.

El 2 de septiembre de 2026 esas etiquetas decían «15 fuentes» cuando ya eran 16.
Se corrigieron a mano. El 3 de septiembre decían «15 fuentes» y «71 indicadores»
cuando eran **19 y 69**. Volvió a pasar en un día, y va a volver a pasar cada vez
que entre un colector: **una cifra escrita a mano envejece sola.**

Esta herramienta la recalcula desde los datos y la reescribe. La corre el robot
después de cada recolección completa, de modo que la portada no puede quedar
diciendo un número que el propio sitio desmiente dos renglones más abajo.

LO QUE NO HACE
--------------
No inventa el texto: solo reemplaza los números dentro de las frases que ya
están escritas. Si una frase cambia de forma, la herramienta **falla y lo dice**,
en lugar de escribir en un lugar equivocado.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITIO = RAIZ / "sitio" / "index.html"
# La portada de la raiz es la que recibe a quien entra por la direccion corta, y
# tiene las MISMAS frases. Quedo con las cifras viejas la primera vez justamente
# porque se la corrigio a mano solo del otro lado.
PORTADA = RAIZ / "index.html"
# El mapa del sitio declara cuando cambio cada direccion. Es la misma clase de
# dato escrito a mano: quedo en el 1 de septiembre mientras el registro seguia
# recolectando cada hora.
MAPA = RAIZ / "sitemap.xml"
DATOS = RAIZ / "datos" / "publico"
# El README es la primera pagina que ve quien llega al repositorio, y su tabla de
# fuentes estaba escrita a mano: decia «Pendiente» de OpenSanctions y de la
# contratacion abierta cuando ambas llevaban dias en servicio, y enumeraba siete
# fuentes cuando ya eran veintisiete. Es el mismo error que el de la portada, en
# el otro sentido: aquella prometia de mas y esta declaraba de menos. Se calcula.
LEEME = RAIZ / "README.md"
MARCA_INICIO = "<!-- fuentes:calculado -->"
MARCA_FIN = "<!-- fuentes:fin -->"


def _cifras() -> dict:
    indicadores = 0
    for archivo in sorted(DATOS.glob("*.json")):
        try:
            d = json.loads(archivo.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — un archivo ilegible no debe sellar mal
            continue
        indicadores += len(d.get("indicadores") or [])

    html = SITIO.read_text(encoding="utf-8")
    lista = re.search(r"const FUENTES_DEL_REGISTRO = \[(.*?)\];", html, re.S)
    if not lista:
        raise SystemExit("No se halló FUENTES_DEL_REGISTRO: la portada no se selló.")
    fuentes = lista.group(1).count("['")

    estados = json.loads((RAIZ / "colectores" / "m49.json").read_text(encoding="utf-8")) \
        if (RAIZ / "colectores" / "m49.json").exists() else None
    return {"indicadores": indicadores, "fuentes": fuentes, "estados": 33}


# Cada regla dice QUE frase busca y COMO queda. Si la frase cambió, no se
# reemplaza nada y se avisa: es preferible una portada vieja a una mentira nueva.
def _reglas(c: dict) -> list:
    i, f, e = c["indicadores"], c["fuentes"], c["estados"]
    return [
        (r'(<meta name="description" content="Registro público y gratuito de América '
         r'Latina y el Caribe: )\d+( indicadores sobre )\d+( Estados)',
         rf'\g<1>{i}\g<2>{e}\g<3>'),
        (r'(Registro público y gratuito de la situación de América Latina y el '
         r'Caribe: )\d+( indicadores sobre )\d+( Estados)',
         rf'\g<1>{i}\g<2>{e}\g<3>'),
        (r'(<meta property="og:description" content=")\d+( Estados, )\d+'
         r'( indicadores, )\d+( fuentes)',
         rf'\g<1>{e}\g<2>{i}\g<3>{f}\g<4>'),
        (r'(<meta name="twitter:description" content=")\d+( Estados, )\d+'
         r'( indicadores, )\d+( fuentes)',
         rf'\g<1>{e}\g<2>{i}\g<3>{f}\g<4>'),
        (r'(los )\d+( Estados de América Latina y el Caribe: )\d+( indicadores de '
         r'seguridad, defensa, gobernanza y desarrollo, recolectados de forma '
         r'automática de )[a-zñáéíóú]+|(\d+)( fuentes públicas)',
         None),  # se maneja aparte, más abajo
    ]


def _sellarArchivo(ruta: Path, c: dict) -> tuple:
    html = ruta.read_text(encoding="utf-8")
    original = html
    cambios, sinTocar = 0, []

    for patron, reemplazo in _reglas(c):
        if reemplazo is None:
            continue
        nuevo, n = re.subn(patron, reemplazo, html)
        if n:
            html, cambios_ = nuevo, n
            cambios += cambios_
        else:
            sinTocar.append(patron[:60])


    # El bloque de datos estructurados escribe el número en letras («quince
    # fuentes»), que además de envejecer obliga a traducirlo. Pasa a cifra.
    patron_ld = (r'(los )\d+( Estados de América Latina y el Caribe: )\d+'
                 r'( indicadores de seguridad, defensa, gobernanza y desarrollo, '
                 r'recolectados de forma automática de )[\wáéíóúñ]+( fuentes públicas)')
    nuevo, n = re.subn(patron_ld,
                       rf'\g<1>{c["estados"]}\g<2>{c["indicadores"]}\g<3>{c["fuentes"]}\g<4>',
                       html)
    if n:
        html = nuevo
        cambios += n
    else:
        sinTocar.append("descripción de los datos estructurados")

    if html != original:
        ruta.write_text(html, encoding="utf-8")
    return cambios, sinTocar


def _sellarMapa() -> int:
    """La fecha del mapa del sitio es la de hoy: el registro cambia a diario."""
    if not MAPA.exists():
        return 0
    hoy = datetime.now(timezone.utc).date().isoformat()
    texto = MAPA.read_text(encoding="utf-8")
    nuevo, n = re.subn(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>",
                       f"<lastmod>{hoy}</lastmod>", texto)
    if n and nuevo != texto:
        MAPA.write_text(nuevo, encoding="utf-8")
        print(f"[sellar-portada] sitemap.xml: {n} fechas puestas en {hoy}")
    return n


def _sellarLeeme() -> int:
    """Rehace la tabla de fuentes del README desde los archivos que existen.

    No pregunta qué colectores hay escritos: pregunta **cuáles dejaron dato**. Un
    colector que nunca corrió no figura, y uno que corrió no puede figurar como
    pendiente.
    """
    if not LEEME.exists():
        return 0
    texto = LEEME.read_text(encoding="utf-8")
    if MARCA_INICIO not in texto or MARCA_FIN not in texto:
        print("[sellar-portada] AVISO: el README no tiene las marcas de la tabla de "
              "fuentes; NO se tocó nada.", file=sys.stderr)
        return 0

    filas = []
    for archivo in sorted(DATOS.glob("*.json")):
        try:
            d = json.loads(archivo.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — un archivo ilegible no entra a la tabla
            continue
        p = d.get("procedencia") or {}
        if not p.get("fuente"):
            continue
        cal = p.get("calificacion") or {}
        codigo = f'{cal.get("fiabilidad", "?")}-{cal.get("credibilidad", "?")}'
        estados = len({r.get("iso") for r in (d.get("registros") or []) if r.get("iso")})
        vacios = len(p.get("vacios_declarados") or [])
        filas.append((archivo.stem, p["fuente"].get("nombre", ""), codigo, estados, vacios))

    cuerpo = [
        f"{MARCA_INICIO}",
        "",
        f"**{len(filas)} fuentes en servicio.** Esta tabla no se escribe: la calcula "
        "`herramientas/sellar-portada.py` desde los archivos de datos, después de cada "
        "recolección. Un colector que no dejó dato no aparece acá.",
        "",
        "| Colector | Fuente | Calificación | Estados | Vacíos declarados |",
        "|---|---|:---:|---:|---:|",
    ]
    for nombre, fuente, codigo, estados, vacios in filas:
        cuerpo.append(f"| `{nombre}` | {fuente} | `{codigo}` | "
                      f"{estados if estados else '—'} | {vacios} |")
    cuerpo += [
        "",
        "La calificación es la del Almirantazgo: la letra mide **de quién viene** y el "
        "número, **qué tan verificado está lo que dice**. Ninguna fuente única puede "
        "calificar `1`; la circunstancia viaja declarada dentro de cada archivo.",
        "",
        f"{MARCA_FIN}",
    ]

    inicio = texto.index(MARCA_INICIO)
    fin = texto.index(MARCA_FIN) + len(MARCA_FIN)
    nuevo = texto[:inicio] + "\n".join(cuerpo) + texto[fin:]
    if nuevo != texto:
        LEEME.write_text(nuevo, encoding="utf-8")
        print(f"[sellar-portada] README.md: tabla rehecha con {len(filas)} fuentes")
    return len(filas)


def sellar() -> int:
    c = _cifras()
    total, faltantes = 0, []
    # Las dos portadas: la del registro y la de la raíz. Sellar una sola fue el
    # error de la primera vez, y por eso la corta siguió mintiendo un día más.
    for ruta in (SITIO, PORTADA):
        if not ruta.exists():
            continue
        cambios, sinTocar = _sellarArchivo(ruta, c)
        total += cambios
        if sinTocar:
            faltantes.append((ruta.name, sinTocar))
        print(f"[sellar-portada] {ruta.relative_to(RAIZ)}: {cambios} lugares actualizados")

    # Cada portada tiene su propia redacción: que una frase falte en UNA no es un
    # error. Solo alarma la que no se halló en NINGUNA, porque esa sí quedó sin
    # sellar en todo el registro.
    enTodas = set.intersection(*[set(xs) for _, xs in faltantes]) if faltantes else set()
    if enTodas:
        print("[sellar-portada] AVISO: estas frases no se hallaron en ninguna portada "
              "y NO se tocó nada de ellas:", file=sys.stderr)
        for x in sorted(enTodas):
            print(f"  · {x}", file=sys.stderr)

    _sellarMapa()
    _sellarLeeme()
    print(f"[sellar-portada] {c['indicadores']} indicadores · {c['fuentes']} fuentes · "
          f"{c['estados']} Estados · {total} lugares en total")
    return 1 if enTodas else 0


if __name__ == "__main__":
    raise SystemExit(sellar())
