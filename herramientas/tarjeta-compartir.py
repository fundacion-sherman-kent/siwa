"""Genera la tarjeta que se ve cuando alguien comparte SIWA.

NO forma parte del robot. Es una herramienta local que se corre a mano cuando
cambia la identidad o cambian las cifras, y deja el resultado en
`sitio/marca/siwa-compartir.png`. El sitio publicado sigue sin dependencias:
lo unico que viaja es el PNG ya generado.

    python herramientas/tarjeta-compartir.py

Necesita Pillow, que se instala solo en la maquina de quien la corre.
La tipografia de la casa es Inter; si no esta instalada usa Segoe UI, que es la
mas parecida de las que trae Windows. En una tarjeta de 1200x630 la diferencia
no se aprecia, pero queda dicho.
"""

from __future__ import annotations

import json
import pathlib

from PIL import Image, ImageDraw, ImageFont

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "sitio" / "marca" / "siwa-compartir.png"
LOGO = RAIZ / "sitio" / "marca" / "fusk-logo-nombre-color.png"

ANCHO, ALTO = 1200, 630          # la medida que piden LinkedIn, X y WhatsApp
NAVY = (0, 18, 30)
NARANJA = (251, 101, 0)
BLANCO = (255, 255, 255)
TENUE = (125, 144, 168)
CLARO = (199, 210, 224)

FUENTES = [
    ("Inter", "Inter-Bold.ttf", "Inter-Regular.ttf"),
    ("Segoe UI", "segoeuib.ttf", "segoeui.ttf"),
    ("Arial", "arialbd.ttf", "arial.ttf"),
]


def _tipografia():
    """La de la casa si esta; si no, la mas parecida que haya."""
    for nombre, negrita, normal in FUENTES:
        try:
            ImageFont.truetype(negrita, 12)
            return nombre, negrita, normal
        except OSError:
            continue
    raise RuntimeError("No se encontro ninguna tipografia utilizable")


def _cifras() -> str:
    """Las cifras salen de los datos, no de la memoria de quien escribe."""
    carpeta = RAIZ / "datos" / "publico"
    indicadores, fuentes = 0, 0
    for archivo in sorted(carpeta.glob("*.json")):
        if archivo.name == "desplazamiento-serie.json":
            continue
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        indicadores += len(datos.get("indicadores") or [])
        fuentes += 1
    return f"33 Estados   ·   {indicadores} indicadores   ·   {fuentes} fuentes"


def dibujar() -> pathlib.Path:
    nombre, negrita, normal = _tipografia()
    lienzo = Image.new("RGB", (ANCHO, ALTO), NAVY)
    pincel = ImageDraw.Draw(lienzo)

    # Filete naranja arriba: es la marca de la casa antes que cualquier texto.
    pincel.rectangle([0, 0, ANCHO, 9], fill=NARANJA)

    # Retícula tenue al fondo, que da profundidad sin competir con el texto.
    for x in range(0, ANCHO, 60):
        pincel.line([(x, 9), (x, ALTO)], fill=(0, 26, 42), width=1)
    for y in range(9, ALTO, 60):
        pincel.line([(0, y), (ANCHO, y)], fill=(0, 26, 42), width=1)

    # El logotipo es a color y sobre navy no se lee. El manual de identidad
    # resuelve el caso de la misma manera para toda marca sobre fondo oscuro:
    # NO se recolorea, se apoya en una placa blanca con sus colores intactos.
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        alto_logo = 62
        logo = logo.resize((int(logo.width * alto_logo / logo.height), alto_logo),
                           Image.LANCZOS)
        margen = 20
        placa = (76, 56, 76 + logo.width + margen * 2, 56 + alto_logo + margen * 2)
        pincel.rounded_rectangle(placa, radius=12, fill=BLANCO)
        lienzo.paste(logo, (76 + margen, 56 + margen), logo)

    titulo = ImageFont.truetype(negrita, 148)
    bajada = ImageFont.truetype(normal, 34)
    pie = ImageFont.truetype(negrita, 25)
    sello = ImageFont.truetype(normal, 21)

    # «SIWA» con espaciado ancho: la palabra funciona como sello, no como frase.
    x, y = 76, 214
    for letra in "SIWA":
        pincel.text((x, y), letra, font=titulo, fill=BLANCO)
        x += pincel.textlength(letra, font=titulo) + 26

    pincel.text((82, 390), "Reporte de situación de América Latina y el Caribe",
                font=bajada, fill=CLARO)

    pincel.line([(80, 462), (232, 462)], fill=NARANJA, width=4)
    pincel.text((80, 486), _cifras(), font=pie, fill=BLANCO)
    pincel.text((80, 528),
                "Datos públicos calificados con doctrina de inteligencia.",
                font=sello, fill=TENUE)
    pincel.text((80, 560), "Acceso libre y gratuito.", font=sello, fill=TENUE)

    pincel.rectangle([0, ALTO - 6, ANCHO, ALTO], fill=NARANJA)

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    lienzo.save(SALIDA, "PNG", optimize=True)
    return SALIDA


if __name__ == "__main__":
    ruta = dibujar()
    print(f"[tarjeta] {ruta} · {ruta.stat().st_size / 1024:.0f} KB")
