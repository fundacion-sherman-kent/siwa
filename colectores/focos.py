"""Focos de calor — NASA FIRMS, sensor VIIRS.

Materia: **economías ilícitas y control territorial** (eje de seguridad).

Lo que este colector registra es una **anomalía térmica detectada por satélite**.
No es un incendio, no es minería ilegal y no es desmonte: es una firma de calor.
La lectura que la convierte en indicio de ocupación ilegal del territorio la hace
el analista, cruzándola contra concesiones, áreas protegidas y tenencia de la
tierra. El colector no infiere nada y el archivo lo declara.

Requiere clave gratuita de NASA FIRMS, tomada de la variable de entorno
`NASA_FIRMS_MAP_KEY`. La clave nunca se escribe en el repositorio.
"""

from __future__ import annotations

import csv
import io
import os
import urllib.request

import comun
import geo

FUENTE = "NASA FIRMS — VIIRS S-NPP, procesamiento de tiempo casi real"
SENSOR = "VIIRS_SNPP_NRT"
MARCO = "-118,-57,-34,33"          # oeste, sur, este, norte
DIAS = 1
TOPE_MUESTRA = 800                 # puntos que se publican para el mapa

# La escala de confianza de VIIRS es cualitativa: baja, nominal y alta.
CONFIANZA = {"l": "baja", "n": "nominal", "h": "alta"}


def _traer_csv(url: str) -> list[dict]:
    peticion = urllib.request.Request(url, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=180) as respuesta:
        if respuesta.status != 200:
            raise RuntimeError(f"HTTP {respuesta.status} al pedir focos a FIRMS")
        texto = respuesta.read().decode("utf-8")
    if texto.lstrip().lower().startswith("invalid"):
        raise RuntimeError("FIRMS rechazó la clave. Revisar NASA_FIRMS_MAP_KEY.")
    return list(csv.DictReader(io.StringIO(texto)))


def recolectar():
    clave = os.environ.get("NASA_FIRMS_MAP_KEY", "").strip()
    if not clave:
        raise RuntimeError(
            "Falta la clave NASA_FIRMS_MAP_KEY. No se escribe nada: sin clave no "
            "hay dato, y un dato inventado sería peor que ninguno."
        )

    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{clave}/"
        f"{SENSOR}/{MARCO}/{DIAS}"
    )
    crudo = _traer_csv(url)

    # Los de confianza baja no entran: la propia fuente los da por dudosos.
    utiles = [f for f in crudo if f.get("confidence") in ("n", "h")]
    descartados = len(crudo) - len(utiles)

    por_pais: dict[str, dict] = {}
    fuera_del_padron = 0
    muestra = []

    for foco in utiles:
        try:
            lat = float(foco["latitude"])
            lon = float(foco["longitude"])
            potencia = float(foco.get("frp") or 0)
        except (TypeError, ValueError):
            continue

        ubicacion = geo.pais_de(lon, lat)
        if ubicacion is None:
            fuera_del_padron += 1
        else:
            fila = por_pais.setdefault(
                ubicacion["iso"],
                {
                    "iso": ubicacion["iso"],
                    "pais": ubicacion["pais"],
                    "bloque": ubicacion["bloque"],
                    "focos": 0,
                    "confianza_alta": 0,
                    "potencia_radiativa_total": 0.0,
                },
            )
            fila["focos"] += 1
            fila["potencia_radiativa_total"] += potencia
            if foco.get("confidence") == "h":
                fila["confianza_alta"] += 1

        muestra.append(
            {
                "latitud": lat,
                "longitud": lon,
                "potencia_radiativa": potencia,
                "confianza": CONFIANZA.get(foco.get("confidence"), "no declarada"),
                "fecha": foco.get("acq_date"),
                "hora_utc": foco.get("acq_time"),
                "pais": ubicacion["pais"] if ubicacion else None,
                "iso": ubicacion["iso"] if ubicacion else None,
            }
        )

    # La muestra que se publica para el mapa se ordena por potencia radiativa:
    # de todos los focos, los de mayor energía son los que más importan.
    muestra.sort(key=lambda p: p["potencia_radiativa"], reverse=True)
    muestra_publicada = muestra[:TOPE_MUESTRA]

    registros = sorted(por_pais.values(), key=lambda r: r["focos"], reverse=True)
    for fila in registros:
        fila["potencia_radiativa_total"] = round(fila["potencia_radiativa_total"], 1)

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=(
            "Detección instrumental de un sensor satelital, sin intermediación. "
            "Fuente única: la segunda fuente independiente sería otro sensor —VIIRS "
            "NOAA-20 o MODIS— todavía no incorporado. Declarado conforme a "
            "doctrina/fuentes.md §2 ter."
        ),
    )

    vacios = [
        "Lo detectado es una ANOMALÍA TÉRMICA, no un incendio ni una actividad "
        "ilegal. Incluye quema agrícola, incendio forestal, quema de gas en "
        "yacimientos e industria pesada. Atribuirla a minería ilegal o a desmonte "
        "exige cruzarla contra concesiones y áreas protegidas, y eso lo hace el "
        "analista, no este colector.",
        "El sensor no ve bajo cobertura de nubes ni de humo denso: la ausencia de "
        "focos en una zona no prueba que no haya actividad.",
        "La actividad ilegal que no quema —dragado fluvial, socavón, tala selectiva— "
        "no deja firma térmica y por lo tanto no aparece acá en absoluto.",
        f"Ventana de {DIAS} día. Los focos de días anteriores no se acumulan.",
        f"{descartados} focos de confianza baja fueron descartados por indicación de "
        "la propia fuente.",
        (
            f"{fuera_del_padron} focos caen fuera del territorio de los 33 Estados del "
            "padrón y no se computan por país."
        ),
        (
            f"El conteo por país es completo. Para el mapa se publican {len(muestra_publicada)} "
            f"de {len(muestra)} focos, elegidos por mayor potencia radiativa: publicar "
            "el total haría inmanejable el archivo."
        ),
        geo.METODO,
    ]

    return comun.escribir(
        colector="focos",
        capa="publico",
        fuente=FUENTE,
        url_fuente="https://firms.modaps.eosdis.nasa.gov/api/area/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={"muestra_para_mapa": muestra_publicada},
    )


if __name__ == "__main__":
    comun.correr("focos", recolectar)
