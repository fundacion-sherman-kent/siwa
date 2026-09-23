# -*- coding: utf-8 -*-
"""Argentina — muertes en accidentes viales por provincia (SNIC).

POR QUÉ EXISTE
--------------
La vista de Territorio (`sitio/subnacional.html`) tiene un eje "muertes que no
son delito" que hoy está en 0 Estados. El mismo CSV del SNIC que ya leen
`subnacional_homicidios.py` y `subnacional_robos.py`
(`https://cloud-snic.minseg.gob.ar/Bases/SNIC/snic-provincias.csv`) trae, entre
sus categorías, "Muertes en accidentes viales" — confirmado en vivo el
23/9/2026 (34 categorías en total en esa corrida). Costo de descarga cero: es
el mismo archivo, otro filtro de columna.

QUÉ ES Y QUÉ NO
---------------
Es un RECUENTO DE VÍCTIMAS de accidentes de tránsito, por provincia y año. NO
ES DELITO: no se suma ni se compara con homicidios o robos, que están en otra
categoría del CSV. Sirve para poblar el eje "muertes que no son delito", no el
de seguridad/criminalidad.
"""
from __future__ import annotations

import collections
import csv
import io
from pathlib import Path

import comun
import estado_reciente as er
import geo

COLECTOR = "subnacional_viales"
CAPA = "publico"
_CATEGORIA = "Muertes en accidentes viales"


def argentina() -> dict:
    filas = list(csv.reader(io.StringIO(er.pedir(er.SNIC_PROVINCIAS).decode("utf-8-sig", "replace")),
                            delimiter=";"))
    cab = [c.strip('"') for c in filas[0]]
    i = {c: n for n, c in enumerate(cab)}
    por = collections.defaultdict(dict)
    for f in filas[1:]:
        if len(f) < len(cab) or f[i["codigo_delito_snic_nombre"]].strip('"') != _CATEGORIA:
            continue
        try:
            por[f[i["provincia_nombre"]].strip('"')][int(f[i["anio"]])] = \
                int(float(f[i["cantidad_victimas"]]))
        except (ValueError, KeyError):
            continue
    return {"unidad": "provincia", "por_unidad": dict(por), "en_curso": None,
            "organismo": "Ministerio de Seguridad — SNIC (Argentina)", "licencia": "CC BY 4.0",
            "nota": "Recuento de VÍCTIMAS de accidentes viales, por provincia. NO ES DELITO: no se "
                    "suma ni se compara con homicidios o robos, que son otra categoría del mismo CSV."}


def construir() -> Path:
    nombres = {p["iso"]: p["pais"] for p in geo.padron()}
    bloques = {p["iso"]: p.get("bloque") for p in geo.padron()}
    dato = argentina()
    por = dato["por_unidad"]
    if not por:
        raise RuntimeError("Argentina: el SNIC no devolvió 'Muertes en accidentes viales'")
    anios = sorted({a for s in por.values() for a in s})
    ultimo = anios[-1] if anios else None
    unidades = [{"nombre": u,
                 "ultimo": {"anio": ultimo, "valor": s.get(ultimo)} if ultimo in s else None,
                 "serie": [{"anio": a, "valor": v} for a, v in sorted(s.items())]}
                for u, s in sorted(por.items())]
    registro = {"iso": "ARG", "pais": nombres.get("ARG", "Argentina"), "bloque": bloques.get("ARG"),
                "nombre_unidad": dato["unidad"], "cuantas": len(unidades),
                "organismo": dato["organismo"], "licencia": dato["licencia"],
                "nota": dato.get("nota"), "en_curso": dato.get("en_curso"),
                "unidades": unidades}
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="Muertes en accidentes viales por provincia — Ministerio de Seguridad, SNIC (Argentina)",
        url_fuente="https://www.argentina.gob.ar/seguridad/estadisticascriminales/bases-de-datos",
        calificacion=comun.calificar(
            "A", 2, False,
            "Registro administrativo oficial (SNIC), mismo archivo que homicidios y robos por "
            "unidad. Credibilidad 2: el nombre de la unidad todavía no se cotejó contra un padrón "
            "geográfico común, y es la única fuente para esta materia (sin segunda fuente que "
            "corrobore por provincia)."),
        registros=[registro],
        vacios=[
            "ES RECUENTO POR UNIDAD, NO TASA: sin la población de cada provincia no se calcula tasa.",
            "NO ES DELITO: es un accidente de tránsito. No se suma ni se compara con homicidios o "
            "robos, que son otra categoría del mismo CSV.",
            "SOLO ARGENTINA (24 provincias): el resto de la región no tiene, hoy, un archivo "
            "equivalente ya leído por SIWA con este mismo costo de descarga cero.",
            "UNA SOLA FUENTE: no hay segunda fuente que corrobore por provincia (regla de casa, "
            "doctrina/fuentes.md §2 ter) — se publica igual, rotulado como oficial única.",
        ],
        extra={"resumen": {"estados_con_desglose": 1,
                           "unidades_totales": len(unidades),
                           "es_prototipo": True,
                           "capa_subnacional": "APAGADA — este dato alimenta la vista preliminar de "
                                                "Territorio, no el mapa de opacidad de los 33",
                           "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
