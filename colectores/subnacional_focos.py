# -*- coding: utf-8 -*-
"""Focos de calor por unidad de primer orden — eje Riesgo, los 33 de una.

POR QUÉ IMPORTA
---------------
SIWA ya baja los focos de calor de NASA FIRMS como puntos con latitud y longitud, y
los cuenta por país (`focos.py`). Este colector baja un nivel: le pregunta a cada
punto en qué UNIDAD DE PRIMER ORDEN cae (provincia, departamento, estado…), con las
geometrías abiertas de geoBoundaries y un cálculo de punto-en-polígono (Shapely).
Como FIRMS es una fuente global, esto cubre los 33 Estados por igual, sin depender de
que cada país publique nada: es la vía más rápida de sumar una categoría de Riesgo a
todo el mapa subnacional.

CÓMO FUNCIONA
-------------
1. Se baja el mismo conjunto de puntos que `focos.py` (misma clave NASA_FIRMS_MAP_KEY).
2. Cada punto se asigna primero a su país con `geo.pais_de` (rápido, ya existe) y
   después, dentro de ese país, a su unidad ADM1 con Shapely.
3. Las geometrías de geoBoundaries se guardan en `datos/geo/adm1/` la primera vez y
   se reusan: cambian muy de vez en cuando.

LO QUE MIDE Y LO QUE NO
-----------------------
Un foco es una DETECCIÓN de anomalía térmica por satélite, no un incendio confirmado
ni su tamaño. Cuenta presencia de fuego/actividad térmica, no daño. Es RECUENTO por
unidad, no tasa. La ventana es de pocos días (la de FIRMS), no un acumulado anual.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun  # noqa: E402
import focos as firms  # noqa: E402 — reutiliza su descarga de puntos
import geo  # noqa: E402

COLECTOR = "subnacional_focos"
CAPA = "publico"
CACHE = comun.DATOS / "geo" / "adm1"
GEOBOUNDARIES = "https://www.geoboundaries.org/api/current/gbOpen/{iso}/ADM1/"


def _cargar_geometrias(iso: str):
    """[(nombre, poligono_preparado, (minx,miny,maxx,maxy))] de un país, con caché."""
    from shapely.geometry import shape
    from shapely.prepared import prep
    CACHE.mkdir(parents=True, exist_ok=True)
    ruta = CACHE / f"{iso}.geojson"
    if ruta.exists():
        gj = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        meta = json.loads(comun.traer_crudo(GEOBOUNDARIES.format(iso=iso)).decode("utf-8", "replace"))
        url = meta.get("simplifiedGeometryGeoJSON")
        if not url:
            return []
        gj = json.loads(comun.traer_crudo(url).decode("utf-8", "replace"))
        ruta.write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
    out = []
    for f in gj.get("features", []):
        nombre = (f.get("properties") or {}).get("shapeName") or "?"
        try:
            g = shape(f["geometry"])
            out.append((nombre, prep(g), g.bounds))
        except Exception:  # noqa: BLE001 — una unidad rota no voltea al país
            continue
    return out


def construir() -> Path:
    from shapely.geometry import Point
    clave = os.environ.get("NASA_FIRMS_MAP_KEY", "").strip()
    if not clave:
        raise RuntimeError("subnacional_focos: falta NASA_FIRMS_MAP_KEY. NO se anota cero: "
                           "no poder mirar no es haber mirado.")
    puntos = firms._pedir(clave, firms.DIAS)

    nombres = {p["iso"]: p["pais"] for p in geo.padron()}
    bloques = {p["iso"]: p.get("bloque") for p in geo.padron()}
    geoms: dict = {}
    por_unidad: dict = {}
    sin_geometria: set = set()
    fuera = 0

    for f in puntos:
        try:
            lon, lat = float(f["longitude"]), float(f["latitude"])
        except (KeyError, TypeError, ValueError):
            continue
        pais = geo.pais_de(lon, lat)
        if not pais:
            fuera += 1
            continue
        iso = pais["iso"]
        if iso not in geoms:
            geoms[iso] = _cargar_geometrias(iso)
            if not geoms[iso]:
                sin_geometria.add(iso)
        p = Point(lon, lat)
        for nombre, poli, (mnx, mny, mxx, mxy) in geoms[iso]:
            if mnx <= lon <= mxx and mny <= lat <= mxy and poli.contains(p):
                por_unidad.setdefault(iso, {}).setdefault(nombre, 0)
                por_unidad[iso][nombre] += 1
                break

    if not por_unidad:
        raise RuntimeError("subnacional_focos: ningún punto cayó en una unidad "
                           f"(fuera del padrón: {fuera}; sin geometría: {sorted(sin_geometria)})")

    registros = []
    for iso, unidades in sorted(por_unidad.items()):
        lista = [{"nombre": n, "focos": c} for n, c in sorted(unidades.items(), key=lambda x: -x[1])]
        registros.append({
            "iso": iso, "pais": nombres.get(iso, iso), "bloque": bloques.get(iso),
            "nombre_unidad": "unidad de primer orden", "cuantas": len(lista),
            "organismo": "NASA FIRMS (detección satelital) + geoBoundaries (geometrías)",
            "licencia": "NASA (dominio público) + geoBoundaries (CC BY)",
            "unidades": lista,
        })

    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="Focos de calor por unidad de primer orden — NASA FIRMS agregado sobre geoBoundaries ADM1",
        url_fuente="https://firms.modaps.eosdis.nasa.gov/",
        calificacion=comun.calificar(
            "A", 2, False,
            "Detección satelital de NASA cruzada con geometrías abiertas. Credibilidad 2: un foco "
            "es una anomalía térmica detectada, no un incendio confirmado ni su tamaño, y la "
            "asignación a la unidad depende de la precisión de la geometría simplificada."),
        registros=registros,
        vacios=[
            "UN FOCO NO ES UN INCENDIO CONFIRMADO ni mide su tamaño o daño: es una detección de "
            "anomalía térmica por satélite.",
            "ES RECUENTO POR UNIDAD, NO TASA, y en la VENTANA de pocos días de FIRMS, no un año.",
            "La asignación usa la geometría SIMPLIFICADA de geoBoundaries: un punto sobre el límite "
            "puede caer en la unidad vecina. Los puntos fuera de toda unidad no se cuentan.",
        ] + ([f"Sin geometría ADM1 en geoBoundaries: {sorted(sin_geometria)}."] if sin_geometria else []),
        extra={"resumen": {"estados_con_focos_por_unidad": len(registros),
                           "unidades_con_focos": sum(r["cuantas"] for r in registros),
                           "puntos_fuera_del_padron": fuera,
                           "sin_geometria": sorted(sin_geometria),
                           "ventana_dias": firms.DIAS,
                           "es_prototipo": True,
                           "capa_subnacional": "APAGADA — alimenta el prototipo, no el mapa",
                           "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
