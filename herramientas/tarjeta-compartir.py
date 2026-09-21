"""Genera la tarjeta que se ve cuando alguien comparte SIWA.

Corre SOLA, dentro del robot (`.github/workflows/recolectar.yml`, paso
"Redibujar la tarjeta de compartir"), después de que el catálogo público
escribe `cuantos_portada` en `datos/publico/indice.json`. También se puede
correr a mano, por ejemplo después de tocar la identidad visual:

    python herramientas/tarjeta-compartir.py

Deja el resultado en `sitio/marca/siwa-compartir.png` (y una tarjeta por país
y por zona en `sitio/marca/tarjetas/`). El sitio publicado sigue sin
dependencias en tiempo de lectura: lo único que viaja es el PNG ya dibujado.

POR QUÉ SE REHÍZO (2/9/2026) Y POR QUÉ SE VOLVIÓ A TOCAR (21/9/2026)
------------------------------------------------------------------------
La tarjeta original decía **«71 indicadores · 15 fuentes»** cuando ya eran 69 y
27. No era un error de cálculo —la herramienta siempre sacó las cifras de los
datos— sino de **cadencia**: se dibujaba una vez y nadie la volvía a correr,
porque vivía fuera del robot y había que acordarse. Y es la primera cosa que
ve quien recibe el enlace.

La primera corrección (2/9/2026) dejó el `.png` a mano pero agregó un testigo
(`siwa-compartir.json`) para que `sellar-portada.py` -que sí corre siempre y
solo necesita la biblioteca estándar- avisara cuando la tarjeta había quedado
vieja. Fue una mejora a medias: avisaba, pero no se redibujaba sola, y para el
21/9/2026 la tarjeta seguía diciendo **174 indicadores · 60 fuentes** con el
registro ya en 237 y 73 -el aviso quedó sonando en los logs del robot durante
semanas y nadie lo redibujó a mano-.

La segunda corrección (21/9/2026) invierte esa decisión: Pillow **sí** entra al
robot, pero SOLO en el paso que dibuja la tarjeta, no en el resto -es el mismo
patrón que ya usan `sipri.yml` y `wjp.yml` para sus propias dependencias sueltas
(`openpyxl`, `pypdf`, etc.): un `pip install` de una línea, en el único paso
que la necesita, y nada más del robot pasa a depender de ella. El testigo
(`siwa-compartir.json`) se conserva: sigue sirviendo para quien la corre a mano
y para que `sellar-portada.py` -que corre ANTES, sin Pillow- detecte una
tarjeta vieja si por lo que sea el paso del robot no llegó a correr.

LAS CIFRAS SALEN DE UN SOLO LUGAR
---------------------------------
Antes la tarjeta contaba por su cuenta, y después importó el cálculo de
`sellar-portada.py` -que a su vez lo reháce por su cuenta, leyendo archivo por
archivo-. Coincidían, pero eran dos implementaciones separadas del mismo
número: exactamente el tipo de duplicación que esta casa ya pagó (es la razon
por la que esta herramienta se rehizo la primera vez, ver arriba). Desde el
21/9/2026 hay un lugar publicado y único para este número:
`datos/publico/indice.json` -> `cuantos_portada`, que escribe
`herramientas/indice-datos.py`. Esta herramienta LEE ESE CAMPO, no lo recalcula.
No puede leerlo de `sellar-portada.py` -que corre ANTES que `indice-datos.py`
en el robot, para tener margen de sellar el HTML antes del último generador- así
que esta sí tiene que ir DESPUÉS de él (ver el paso nuevo en `recolectar.yml`).

LO QUE SE CORRIGIÓ DEL DIBUJO
-----------------------------
- **La tipografía es Inter**, la de la casa, y viaja en el repositorio: antes
  dependía de que estuviera instalada en la máquina y caía en Segoe UI.
- **El logotipo se recorta antes de usarlo.** El archivo trae margen transparente
  —207 px a la izquierda, 184 a la derecha, 132 arriba, 125 abajo—, de modo que
  pedirle 62 px de alto entregaba una marca visible de 43. Se recorta el aire y
  recién entonces se escala: el alto pedido es el alto que se ve.
- **La mitad derecha estaba vacía.** Las tres cifras pasan a una fila que cruza
  la tarjeta entera, con el número grande y el rótulo abajo: es lo que sigue
  legible cuando la miniatura se muestra a 500 px en una lista.
- **Un solo filete naranja.** Había dos, arriba y abajo; el manual manda uno.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

from PIL import Image, ImageDraw, ImageFont

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "sitio" / "marca" / "siwa-compartir.png"
# Al lado del PNG, las cifras con que se lo dibujó. Lo lee el sellador para
# avisar cuando la tarjeta quedó atrasada respecto del registro.
TESTIGO = RAIZ / "sitio" / "marca" / "siwa-compartir.json"
LOGO = RAIZ / "sitio" / "marca" / "fusk-logo-nombre-color.png"
# Inter viaja en el repositorio con su licencia: es la tipografía del manual y
# no puede depender de lo que tenga instalado quien corra la herramienta.
INTER = RAIZ / "herramientas" / "tipografia" / "Inter[opsz,wght].ttf"

ANCHO, ALTO = 1200, 630          # la medida que piden LinkedIn, X y WhatsApp
NAVY = (0, 18, 30)               # el azul de la casa
NARANJA = (251, 101, 0)
BLANCO = (255, 255, 255)
TENUE = (125, 144, 168)
CLARO = (199, 210, 224)
RETICULA = (0, 26, 42)

MARGEN = 76


def _cifras() -> dict:
    """Las cifras publicadas de la portada, LEÍDAS, no recalculadas.

    Única fuente de verdad: `datos/publico/indice.json` -> `cuantos_portada`,
    que escribe `herramientas/indice-datos.py` en cada corrida del robot (el
    último generador, para no anunciar el número de la corrida anterior). Antes
    esta función importaba y ejecutaba `sellar-portada.py` para que recontara los
    archivos por su cuenta: dos cálculos separados del mismo número, que es
    justo el error que obligó a reescribir esta herramienta la primera vez.
    """
    indice = RAIZ / "datos" / "publico" / "indice.json"
    try:
        datos = json.loads(indice.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(
            f"No existe {indice.relative_to(RAIZ)}. Corré antes "
            "herramientas/indice-datos.py (el robot lo hace solo, en cada pasada)."
        )
    c = datos.get("cuantos_portada")
    if not c or not all(k in c for k in ("estados", "indicadores", "fuentes")):
        raise SystemExit(
            f"{indice.relative_to(RAIZ)} no tiene 'cuantos_portada' completo. "
            "Corré antes herramientas/indice-datos.py."
        )
    return {"estados": c["estados"], "indicadores": c["indicadores"], "fuentes": c["fuentes"]}


def _letra(tamanio: int, peso: float = 400.0) -> ImageFont.FreeTypeFont:
    """Inter en el peso pedido. Es una tipografía variable: el peso es un eje."""
    fuente = ImageFont.truetype(str(INTER), tamanio)
    # El eje de tamaño óptico se lleva al máximo: son cuerpos grandes.
    fuente.set_variation_by_axes([32.0, float(peso)])
    return fuente


def _logoRecortado(alto: int) -> Image.Image:
    """Devuelve el logotipo SIN su margen transparente, al alto pedido.

    El archivo trae aire alrededor del dibujo. Escalarlo tal cual hace que el
    alto pedido no sea el alto que se ve: se pedían 62 px y la marca medía 43.
    """
    logo = Image.open(LOGO).convert("RGBA")
    caja = logo.split()[3].getbbox()      # el borde real del dibujo, por su alfa
    if caja:
        logo = logo.crop(caja)
    ancho = max(1, round(logo.width * alto / logo.height))
    return logo.resize((ancho, alto), Image.LANCZOS)


def _texto(pincel, xy, texto, fuente, relleno, espaciado=0):
    """Dibuja, con espaciado entre letras cuando se lo pide, y devuelve el ancho."""
    if not espaciado:
        pincel.text(xy, texto, font=fuente, fill=relleno)
        return pincel.textlength(texto, font=fuente)
    x, y = xy
    for letra in texto:
        pincel.text((x, y), letra, font=fuente, fill=relleno)
        x += pincel.textlength(letra, font=fuente) + espaciado
    return x - espaciado - xy[0]


def dibujar() -> pathlib.Path:
    c = _cifras()
    lienzo = Image.new("RGB", (ANCHO, ALTO), NAVY)
    pincel = ImageDraw.Draw(lienzo)

    # Retícula tenue: da profundidad sin competirle al texto.
    for x in range(0, ANCHO, 60):
        pincel.line([(x, 10), (x, ALTO)], fill=RETICULA, width=1)
    for y in range(10, ALTO, 60):
        pincel.line([(0, y), (ANCHO, y)], fill=RETICULA, width=1)

    # UN filete naranja, arriba. Es la marca de la casa antes que cualquier texto.
    pincel.rectangle([0, 0, ANCHO, 9], fill=NARANJA)

    # El logotipo es a color y sobre navy no se lee. El manual resuelve el caso
    # igual para toda marca sobre fondo oscuro: NO se recolorea, se apoya en una
    # placa blanca con sus colores intactos.
    if LOGO.exists():
        alto_logo = 74
        logo = _logoRecortado(alto_logo)
        aire = 22
        placa = (MARGEN, 44, MARGEN + logo.width + aire * 2, 44 + alto_logo + aire * 2)
        pincel.rounded_rectangle(placa, radius=14, fill=BLANCO)
        lienzo.paste(logo, (MARGEN + aire, 44 + aire), logo)

    # «SIWA» funciona como sello, no como palabra: espaciado ancho y peso alto.
    _texto(pincel, (MARGEN, 182), "SIWA", _letra(144, 800), BLANCO, espaciado=21)

    _texto(pincel, (MARGEN + 4, 352),
           "Reporte de situación de América Latina y el Caribe",
           _letra(36, 400), CLARO)

    # La leyenda va ACA, pegada a su bajada, y no al pie: abajo quedaba a diez
    # pixeles del borde contra setenta y seis de los costados, y encima se
    # confundia con los rotulos de las cifras.
    _texto(pincel, (MARGEN + 4, 404),
           "Datos públicos calificados con doctrina de inteligencia  ·  "
           "Acceso libre y gratuito",
           _letra(21, 400), TENUE)

    pincel.rectangle([MARGEN + 4, 456, MARGEN + 160, 460], fill=NARANJA)

    # LAS TRES CIFRAS, cruzando la tarjeta entera y haciendo de base. Antes iban
    # en un renglón de texto chico contra el margen izquierdo, y la mitad derecha
    # quedaba vacía. El número grande es lo único que sobrevive a una miniatura
    # de 500 px, que es como se ve esto en una lista de novedades.
    columnas = [
        (str(c["estados"]),     "ESTADOS"),
        (str(c["indicadores"]), "INDICADORES"),
        (str(c["fuentes"]),     "FUENTES"),
    ]
    numero, rotulo = _letra(74, 800), _letra(22, 600)
    # Se MIDE el ancho de cada columna y se reparte el sobrante en huecos
    # iguales, de modo que la primera arranque en el margen izquierdo y la
    # última termine en el derecho. Repartiendo a ojo en tres partes quedaban
    # trescientos diez píxeles muertos contra el borde derecho.
    anchos = []
    for cifra, nombre in columnas:
        anchos.append(max(pincel.textlength(cifra, font=numero),
                          pincel.textlength(nombre, font=rotulo)
                          + 2.2 * (len(nombre) - 1)))
    util = ANCHO - (MARGEN + 4) * 2
    hueco = (util - sum(anchos)) / (len(columnas) - 1)
    x = MARGEN + 4
    for (cifra, nombre), ancho in zip(columnas, anchos):
        _texto(pincel, (x, 484), cifra, numero, BLANCO)
        _texto(pincel, (x, 572), nombre, rotulo, TENUE, espaciado=2.2)
        x += ancho + hueco

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    lienzo.save(SALIDA, "PNG", optimize=True)
    dibujarAmbitos(c)

    # El testigo, para que el sellador pueda avisar cuando esto quede viejo.
    TESTIGO.write_text(json.dumps(
        {"estados": c["estados"], "indicadores": c["indicadores"],
         "fuentes": c["fuentes"],
         "como_se_rehace": "python herramientas/tarjeta-compartir.py"},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return SALIDA


# ---- Una tarjeta por pais y por zona ----------------------------------------
#
# Las cuarenta puertas compartian la tarjeta generica: quien recibia el enlace
# de Paraguay veia «SIWA» y tres cifras de la region. Cada ambito tiene ahora la
# suya, con su nombre grande y su zona. puertas.py, que corre en el robot y no
# tiene Pillow, solo mira si el archivo existe.
TARJETAS = RAIZ / "sitio" / "marca" / "tarjetas"


def _sello(t: str) -> str:
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", str(t))
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()


def _ajustar(pincel, texto: str, peso: float, maximo: int, ancho_util: int, minimo: int = 56):
    """La letra mas grande con la que el nombre entra en el ancho util."""
    tamanio = maximo
    while tamanio > minimo:
        fuente = _letra(tamanio, peso)
        if pincel.textlength(texto, font=fuente) <= ancho_util:
            return fuente
        tamanio -= 4
    return _letra(minimo, peso)


def dibujarUna(nombre: str, bajada: str, salida: pathlib.Path, c: dict) -> None:
    lienzo = Image.new("RGB", (ANCHO, ALTO), NAVY)
    pincel = ImageDraw.Draw(lienzo)
    for x in range(0, ANCHO, 60):
        pincel.line([(x, 10), (x, ALTO)], fill=RETICULA, width=1)
    for y in range(10, ALTO, 60):
        pincel.line([(0, y), (ANCHO, y)], fill=RETICULA, width=1)
    pincel.rectangle([0, 0, ANCHO, 9], fill=NARANJA)
    if LOGO.exists():
        alto_logo = 62
        logo = _logoRecortado(alto_logo)
        aire = 18
        placa = (MARGEN, 40, MARGEN + logo.width + aire * 2, 40 + alto_logo + aire * 2)
        pincel.rounded_rectangle(placa, radius=12, fill=BLANCO)
        lienzo.paste(logo, (MARGEN + aire, 40 + aire), logo)
    _texto(pincel, (ANCHO - MARGEN - 190, 60), "SIWA", _letra(58, 800), BLANCO, espaciado=9)

    # El nombre del ambito es lo unico que tiene que sobrevivir a la miniatura.
    util = ANCHO - MARGEN * 2
    fuente = _ajustar(pincel, nombre, 800, 116, util)
    _texto(pincel, (MARGEN, 196), nombre, fuente, BLANCO)
    _texto(pincel, (MARGEN + 4, 342), bajada, _letra(32, 400), CLARO)
    _texto(pincel, (MARGEN + 4, 392),
           "Reporte de situación de América Latina y el Caribe  ·  cada cifra con su fuente y su fecha",
           _letra(21, 400), TENUE)
    pincel.rectangle([MARGEN + 4, 444, MARGEN + 160, 448], fill=NARANJA)

    columnas = [(str(c["estados"]), "ESTADOS"), (str(c["indicadores"]), "INDICADORES"),
                (str(c["fuentes"]), "FUENTES")]
    numero, rotulo = _letra(60, 800), _letra(20, 600)
    anchos = [max(pincel.textlength(ci, font=numero),
                  pincel.textlength(no, font=rotulo) + 2.2 * (len(no) - 1)) for ci, no in columnas]
    hueco = (util - 8 - sum(anchos)) / (len(columnas) - 1)
    x = MARGEN + 4
    for (ci, no), an in zip(columnas, anchos):
        _texto(pincel, (x, 476), ci, numero, BLANCO)
        _texto(pincel, (x, 548), no, rotulo, TENUE, espaciado=2.2)
        x += an + hueco
    salida.parent.mkdir(parents=True, exist_ok=True)
    lienzo.save(salida, "PNG", optimize=True)


def dibujarAmbitos(c: dict) -> None:
    geo_ruta = RAIZ / "colectores" / "geo.py"
    esp = importlib.util.spec_from_file_location("geo", geo_ruta)
    geo = importlib.util.module_from_spec(esp)
    sys_path_antes = list(__import__("sys").path)
    __import__("sys").path.insert(0, str(geo_ruta.parent))
    try:
        esp.loader.exec_module(geo)
    finally:
        __import__("sys").path[:] = sys_path_antes
    padron = geo.padron()
    zonas = sorted({p["bloque"] for p in padron})
    for p in padron:
        dibujarUna(p["pais"], f"Zona {p['bloque']}  ·  uno de los 33 Estados del padrón",
                   TARJETAS / f"{_sello(p['pais'])}.png", c)
    for z in zonas:
        cuantos = sum(1 for p in padron if p["bloque"] == z)
        dibujarUna(z, f"Zona de {cuantos} Estados del padrón de 33", TARJETAS / f"{_sello(z)}.png", c)
    print(f"[tarjetas] {len(padron)} países y {len(zonas)} zonas en {TARJETAS}")


if __name__ == "__main__":
    ruta = dibujar()
    print(f"[tarjeta] {ruta.relative_to(RAIZ)} · {ruta.stat().st_size / 1024:.0f} KB")
    print(f"[tarjeta] testigo: {TESTIGO.relative_to(RAIZ)}")
