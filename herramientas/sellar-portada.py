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

    # EL NUMERO SE CUENTA DE LOS ARCHIVOS, NO DE LA LISTA DE LA PAGINA. La lista
    # se escribe a mano y lleva tambien las fuentes que estan conectadas pero
    # todavia no entregaron dato —UCDP mientras espera su credencial—. Contar
    # renglones anunciaba fuentes que el lector no puede consultar. Se cuentan
    # las fuentes DISTINTAS que dejaron archivo, que es la misma cuenta que hace
    # la tabla del README: un solo numero, calculado en un solo lugar.
    nombres = set()
    for archivo in sorted(DATOS.glob("*.json")):
        try:
            d = json.loads(archivo.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — un archivo ilegible no infla la cuenta
            continue
        fuente = (d.get("procedencia") or {}).get("fuente")
        if fuente:
            nombres.add(fuente if isinstance(fuente, str) else fuente.get("nombre", ""))
    fuentes = len({n for n in nombres if n})
    renglones = lista.group(1).count("['")
    if renglones != fuentes:
        print(f"[sellar-portada] la lista de la página tiene {renglones} renglones y "
              f"hay {fuentes} fuentes con dato: se sella con {fuentes}.", file=sys.stderr)

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
        # La portada corta lo dice con OTRA redaccion, y por eso se le escapaba:
        # decia «de quince fuentes publicas» cuando ya eran veintisiete. Escrito
        # ademas con LETRAS, que envejece igual y encima no se puede sellar.
        (r'(Se recolecta solo, todos los días, de )\d+( fuentes públicas)',
         rf'\g<1>{f}\g<2>'),
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

    # LA TABLA CUENTA ARCHIVOS; EL TITULO TIENE QUE CONTAR FUENTES. ACNUR deja
    # dos archivos —el corte del ano y la serie historica— y la tabla decia «34
    # fuentes» cuando eran 33. Sobrestimar la cantidad de fuentes en un registro
    # cuya promesa es la trazabilidad es el peor lado para equivocarse.
    distintas = len({f for _, f, _, _, _ in filas if f})

    cuerpo = [
        f"{MARCA_INICIO}",
        "",
        f"**{distintas} fuentes en servicio**, en {len(filas)} archivos de datos: hay "
        "fuentes que dejan más de un archivo. Esta tabla no se escribe: la calcula "
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
        print(f"[sellar-portada] README.md: tabla rehecha con {distintas} fuentes "
              f"en {len(filas)} archivos")
    return len(filas)


def _versionarTarjeta(ruta: Path, c: dict) -> int:
    """Le pone version a la direccion de la tarjeta, para que las redes la relean.

    LinkedIn, X, Facebook y WhatsApp GUARDAN la miniatura la primera vez que
    alguien comparte el enlace y no vuelven a pedirla. Se puede rehacer la imagen
    y seguir mostrandose la vieja durante semanas.

    La version no es un numero inventado: son LAS PROPIAS CIFRAS de la tarjeta.
    Cuando entra un colector, la direccion cambia sola y las redes van a buscar
    la imagen nueva. Cuando no cambia nada, la direccion tampoco: no se fuerza
    una recarga porque si.
    """
    texto = ruta.read_text(encoding="utf-8")
    version = f'{c["estados"]}-{c["indicadores"]}-{c["fuentes"]}'
    nuevo, n = re.subn(
        r'(siwa-compartir\.png)(\?v=[0-9-]+)?"',
        rf'\g<1>?v={version}"', texto)
    if n and nuevo != texto:
        ruta.write_text(nuevo, encoding="utf-8")
        print(f"[sellar-portada] {ruta.relative_to(RAIZ)}: tarjeta versionada como "
              f"v={version} "
              f"({n} direcciones)")
    return n


def _revisarTarjeta(c: dict) -> bool:
    """Avisa cuando la tarjeta de compartir quedó con cifras viejas.

    LA TARJETA NO SE PUEDE REDIBUJAR ACA. Es un PNG y hace falta Pillow, que el
    robot no tiene ni va a tener: el registro se sostiene sobre biblioteca
    estándar. Pero SI se puede comprobar que está al día, porque quien la dibuja
    deja al lado un archivo con las cifras que usó.

    Es exactamente el problema de la portada, un escalón más lejos: la tarjeta
    decía «71 indicadores · 15 fuentes» cuando ya eran 69 y 27, y es LA PRIMERA
    COSA que ve quien recibe el enlace compartido. Nadie lo notó porque una
    imagen no se relee.
    """
    testigo = RAIZ / "sitio" / "marca" / "siwa-compartir.json"
    if not testigo.exists():
        print("[sellar-portada] AVISO: la tarjeta de compartir no dejó testigo de "
              "sus cifras; no se puede saber si está al día.", file=sys.stderr)
        return False
    try:
        d = json.loads(testigo.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — un testigo ilegible es un testigo ausente
        return False

    viejas = {k: d.get(k) for k in ("estados", "indicadores", "fuentes")}
    nuevas = {k: c[k] for k in ("estados", "indicadores", "fuentes")}
    if viejas == nuevas:
        return True
    difiere = ", ".join(f"{k}: la tarjeta dice {viejas[k]} y son {nuevas[k]}"
                        for k in nuevas if viejas[k] != nuevas[k])
    print(f"[sellar-portada] AVISO: LA TARJETA DE COMPARTIR QUEDO VIEJA ({difiere}). "
          "Es la primera imagen que ve quien recibe el enlace. Se rehace con: "
          "python herramientas/tarjeta-compartir.py", file=sys.stderr)
    return False


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
    for ruta in (SITIO, PORTADA):
        if ruta.exists():
            _versionarTarjeta(ruta, c)
    _revisarTarjeta(c)
    print(f"[sellar-portada] {c['indicadores']} indicadores · {c['fuentes']} fuentes · "
          f"{c['estados']} Estados · {total} lugares en total")
    return 1 if enTodas else 0


if __name__ == "__main__":
    raise SystemExit(sellar())
