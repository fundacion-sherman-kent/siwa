# -*- coding: utf-8 -*-
"""OCR para SIWA — leer el dato que sólo viene en infografía o PDF de imagen.

POR QUÉ EXISTE
--------------
Muchas fuentes subnacionales publican el dato SOLO como infografía o PDF escaneado
(los «grado 2»: el observatorio de Santa Fe, los boletines de varias policías del
Caribe y Centroamérica). Una persona lo lee; un programa, no. Este módulo le da al
robot la capacidad de leer esas imágenes con OCR abierto (Tesseract), con un
preprocesado de OpenCV que mejora el reconocimiento.

CÓMO SE USA
-----------
    import ocr
    if ocr.disponible():
        texto = ocr.leer(imagen_bytes)      # o ocr.leer_url("https://…/infografia.png")
        numeros = ocr.numeros_junto_a(texto, "Rosario")

DEGRADACIÓN ELEGANTE
--------------------
Si Tesseract/OpenCV no están instalados (el robot base es de biblioteca estándar),
`disponible()` devuelve False y nada se rompe: el colector que lo use declara que
no pudo leer, como cualquier otro vacío. El OCR se instala solo en el paso del
robot que lo necesita (apt `tesseract-ocr` + pip `pytesseract opencv-python-headless
Pillow numpy`), no en todo el robot.

LO QUE NO HACE
--------------
No adivina. El OCR de una infografía tiene error; por eso lo que sale se trata como
DATO A CONFIRMAR contra la fuente nacional (regla de las dos fuentes), no como cifra
oficial directa. Y lo que no se pudo leer con confianza se declara, no se rellena.
"""
from __future__ import annotations

import io
import re
import urllib.request

# Español + inglés: la mayoría de las infografías de la región están en uno u otro.
IDIOMAS = "spa+eng"


def disponible() -> bool:
    """True sólo si están Tesseract y sus envoltorios de Python."""
    try:
        import pytesseract  # noqa: F401
        import PIL  # noqa: F401
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001 — falta el binario o el paquete: no está disponible
        return False


def _preprocesar(imagen_bytes: bytes) -> "Image.Image":
    """Escala de grises, aumento de tamaño y umbral: sube mucho el acierto del OCR."""
    from PIL import Image
    img = Image.open(io.BytesIO(imagen_bytes)).convert("L")
    # Agrandar las chicas: Tesseract lee mejor con texto grande.
    if max(img.size) < 1600:
        f = 1600 / max(img.size)
        img = img.resize((int(img.size[0] * f), int(img.size[1] * f)))
    try:
        import cv2
        import numpy as np
        arr = np.array(img)
        arr = cv2.bilateralFilter(arr, 5, 40, 40)
        arr = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 31, 10)
        return Image.fromarray(arr)
    except Exception:  # noqa: BLE001 — sin OpenCV, se usa la imagen en gris igual
        return img


def leer(imagen_bytes: bytes) -> str:
    """Texto reconocido en una imagen. Requiere `disponible()`; si no, devuelve ''."""
    if not disponible():
        return ""
    import pytesseract
    try:
        return pytesseract.image_to_string(_preprocesar(imagen_bytes), lang=IDIOMAS)
    except Exception:  # noqa: BLE001
        return ""


def leer_url(url: str, espera: int = 40) -> str:
    """Baja una imagen o PDF-imagen y la lee. Los PDF se rasterizan si hay poppler."""
    cab = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")}
    with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=espera) as r:
        crudo = r.read()
    if crudo[:4] == b"%PDF":
        try:
            from pdf2image import convert_from_bytes
            paginas = convert_from_bytes(crudo, dpi=200)
            partes = []
            for p in paginas:
                buf = io.BytesIO()
                p.save(buf, format="PNG")
                partes.append(leer(buf.getvalue()))
            return "\n".join(partes)
        except Exception:  # noqa: BLE001 — sin poppler no se rasteriza; se declara vacío
            return ""
    return leer(crudo)


def numeros_junto_a(texto: str, etiqueta: str, ventana: int = 40) -> list[int]:
    """Números que aparecen cerca de una etiqueta (p. ej. el nombre de un departamento).

    Devuelve los enteros hallados en la ventana de caracteres alrededor de cada
    aparición de la etiqueta. Es una AYUDA para el que codifica el colector, no una
    extracción definitiva: siempre se coteja el resultado contra la fuente nacional.
    """
    out = []
    low = texto.lower()
    et = etiqueta.lower()
    i = low.find(et)
    while i >= 0:
        tramo = texto[max(0, i - ventana): i + len(etiqueta) + ventana]
        for n in re.findall(r"\d[\d.\s]{0,7}\d|\d", tramo):
            try:
                out.append(int(n.replace(".", "").replace(" ", "")))
            except ValueError:
                continue
        i = low.find(et, i + 1)
    return out


if __name__ == "__main__":
    import sys
    print("OCR disponible:", disponible())
    if disponible() and len(sys.argv) > 1:
        print(leer_url(sys.argv[1])[:2000])
