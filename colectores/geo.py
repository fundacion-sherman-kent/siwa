"""Atribución geográfica de un punto al padrón de los 33 Estados.

Resuelve a qué país del padrón pertenece una coordenada, usando los límites de
Natural Earth que el repositorio guarda en `sitio/geo/paises-alc.geojson`.

Se hace acá, en la recolección, y no en la página: la salida no genera datos
propios (`doctrina/siwa.md` §2). El método —trazado de rayo sobre el anillo
exterior de cada polígono— queda declarado en el archivo de datos.

Sin dependencias externas: solo biblioteca estándar.
"""

from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PADRON_GEO = RAIZ / "sitio" / "geo" / "paises-alc.geojson"

METODO = (
    "Atribución por trazado de rayo sobre los límites de Natural Earth "
    "(escala 1:50 m). Un punto a menos de esa resolución de la costa puede "
    "quedar sin atribuir."
)

_paises: list | None = None


def _cargar() -> list:
    """Lee el padrón una sola vez y precalcula el recuadro de cada país."""
    global _paises
    if _paises is None:
        crudo = json.loads(PADRON_GEO.read_text(encoding="utf-8"))
        _paises = []
        for rasgo in crudo["features"]:
            anillos = _anillos(rasgo["geometry"])
            puntos = [p for anillo in anillos for p in anillo]
            _paises.append(
                {
                    "propiedades": rasgo["properties"],
                    "anillos": anillos,
                    "recuadro": (
                        min(p[0] for p in puntos),
                        min(p[1] for p in puntos),
                        max(p[0] for p in puntos),
                        max(p[1] for p in puntos),
                    ),
                }
            )
    return _paises


def _anillos(geometria: dict) -> list:
    """Devuelve los anillos exteriores, sea polígono simple o múltiple."""
    if geometria["type"] == "Polygon":
        return [geometria["coordinates"][0]]
    if geometria["type"] == "MultiPolygon":
        return [poligono[0] for poligono in geometria["coordinates"]]
    return []


def _dentro(lon: float, lat: float, anillo: list) -> bool:
    """Trazado de rayo: cuenta cruces del borde hacia el este."""
    dentro = False
    cantidad = len(anillo)
    j = cantidad - 1
    for i in range(cantidad):
        xi, yi = anillo[i][0], anillo[i][1]
        xj, yj = anillo[j][0], anillo[j][1]
        if (yi > lat) != (yj > lat):
            corte = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < corte:
                dentro = not dentro
        j = i
    return dentro


def pais_de(lon: float | None, lat: float | None) -> dict | None:
    """País y bloque del padrón que contienen el punto. None si cae afuera."""
    if lon is None or lat is None:
        return None
    for pais in _cargar():
        x0, y0, x1, y1 = pais["recuadro"]
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            continue
        if any(_dentro(lon, lat, anillo) for anillo in pais["anillos"]):
            return pais["propiedades"]
    return None
