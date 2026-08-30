"""Sismos de América Latina y el Caribe — Servicio Geológico de los EEUU.

Fuente: USGS, servicio FDSN de eventos. Registro primario oficial.

Calificación: fiabilidad `A` (registro oficial de la agencia que mide).
Credibilidad `2`: es fuente única y no admite segunda fuente independiente,
circunstancia que se declara conforme a `doctrina/fuentes.md` §2 ter. Una nota
de prensa que reproduzca el mismo registro no sería corroboración.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import comun

FUENTE = "USGS — United States Geological Survey"
URL_BASE = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# Marco de recolección: América Latina y el Caribe.
LATITUD_MIN, LATITUD_MAX = -57.0, 33.0
LONGITUD_MIN, LONGITUD_MAX = -118.0, -34.0

MAGNITUD_MINIMA = 4.0
DIAS = 7


def recolectar():
    desde = (datetime.now(timezone.utc) - timedelta(days=DIAS)).strftime("%Y-%m-%d")
    url = (
        f"{URL_BASE}?format=geojson"
        f"&starttime={desde}"
        f"&minmagnitude={MAGNITUD_MINIMA}"
        f"&minlatitude={LATITUD_MIN}&maxlatitude={LATITUD_MAX}"
        f"&minlongitude={LONGITUD_MIN}&maxlongitude={LONGITUD_MAX}"
        f"&orderby=time"
    )

    crudo = comun.pedir(url)

    registros = []
    for rasgo in crudo.get("features", []):
        propiedades = rasgo.get("properties", {})
        coordenadas = rasgo.get("geometry", {}).get("coordinates", [None, None, None])
        milisegundos = propiedades.get("time")
        registros.append(
            {
                "id": rasgo.get("id"),
                "momento": (
                    datetime.fromtimestamp(milisegundos / 1000, tz=timezone.utc).isoformat(
                        timespec="seconds"
                    )
                    if milisegundos
                    else None
                ),
                "magnitud": propiedades.get("mag"),
                "escala": propiedades.get("magType"),
                "lugar": propiedades.get("place"),
                "longitud": coordenadas[0],
                "latitud": coordenadas[1],
                "profundidad_km": coordenadas[2],
                "url_evento": propiedades.get("url"),
            }
        )

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=(
            "Registro primario de la agencia que mide. Fuente única por naturaleza "
            "de la materia: no existe segunda fuente independiente. Declarado "
            "conforme a doctrina/fuentes.md §2 ter."
        ),
    )

    return comun.escribir(
        colector="sismos",
        capa="publico",
        fuente=FUENTE,
        url_fuente=url,
        calificacion=calificacion,
        registros=registros,
        vacios=[
            f"Solo eventos de magnitud {MAGNITUD_MINIMA} o mayor.",
            f"Ventana de {DIAS} días corridos.",
            "El marco es un rectángulo geográfico: puede incluir eventos oceánicos "
            "fuera de las aguas jurisdiccionales de los 33 Estados del padrón.",
        ],
    )


if __name__ == "__main__":
    comun.correr("sismos", recolectar)
