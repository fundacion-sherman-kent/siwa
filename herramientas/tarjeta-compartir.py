"""Genera la tarjeta que se ve cuando alguien comparte SIWA.

NO forma parte del robot. Es una herramienta local que se corre a mano cuando
cambian la identidad o las cifras, y deja el resultado en
`sitio/marca/siwa-compartir.png`. El sitio publicado sigue sin dependencias: lo
único que viaja es el PNG ya dibujado.

    python herramientas/tarjeta-compartir.py

POR QUÉ SE REHÍZO
-----------------
La tarjeta anterior decía **«71 indicadores · 15 fuentes»** cuando ya eran 69 y
27. No era un error de cálculo —la herramienta siempre sacó las cifras de los
datos— sino de **cadencia**: se dibujó una vez y nadie volvió a correrla, porque
está fuera del robot. Y es la primera cosa que ve quien recibe el enlace.

Es el mismo problema que el de la portada, con un agravante: la portada la
recalcula el robot en cada corrida; **una imagen no puede recalcularse sin
Pillow, que el robot no tiene**. La solución no es meter la dependencia en el
robot: es dejar al lado del PNG un archivo con las cifras que se usaron para
dibujarlo, de modo que el sellador —que sí corre siempre y solo necesita la
biblioteca estándar— **compare y avise cuando la tarjeta quedó vieja**.

LAS CIFRAS SALEN DE UN SOLO LUGAR
---------------------------------
Antes la tarjeta contaba por su cuenta y el sellador de la portada por la suya.
Coincidían, pero por casualidad: dos recuentos independientes de lo mismo se
separan tarde o temprano, y entonces la tarjeta diría una cosa y la página otra.
Acá se importa el recuento del sellador. **Una sola fuente de verdad.**

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
    """Las mismas que sella la portada. No se cuenta dos veces lo mismo."""
    ruta = RAIZ / "herramientas" / "sellar-portada.py"
    spec = importlib.util.spec_from_file_location("sellar", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo._cifras()


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

    # El testigo, para que el sellador pueda avisar cuando esto quede viejo.
    TESTIGO.write_text(json.dumps(
        {"estados": c["estados"], "indicadores": c["indicadores"],
         "fuentes": c["fuentes"],
         "como_se_rehace": "python herramientas/tarjeta-compartir.py"},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return SALIDA


if __name__ == "__main__":
    ruta = dibujar()
    print(f"[tarjeta] {ruta.relative_to(RAIZ)} · {ruta.stat().st_size / 1024:.0f} KB")
    print(f"[tarjeta] testigo: {TESTIGO.relative_to(RAIZ)}")
