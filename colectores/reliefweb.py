# -*- coding: utf-8 -*-
"""Desastres y crisis declarados por la ONU (ReliefWeb), por país.

POR QUÉ EXISTE
--------------
ReliefWeb es el centro de información humanitaria de la Oficina de Coordinación de
Asuntos Humanitarios de las Naciones Unidas (OCHA). Declara y sigue desastres y
crisis —inundaciones, terremotos, sequías, epidemias, desplazamientos— con fecha,
tipo y país. La Fundación pidió el nombre de aplicación que exige su API y la ONU
lo aprobó el 16/9/2026: «fundacionkent-report-q5v8».

QUÉ PUBLICA
-----------
Un indicador comparable en el eje de desarrollo, categoría de riesgo humanitario,
junto al índice INFORM que ya estaba: la **cantidad de desastres que la ONU
declaró para cada país en los últimos diez años**. Y, como detalle vivo, cuántos
de esos desastres siguen con estado «en curso» hoy.

LO QUE MIDE Y LO QUE NO
-----------------------
Es un recuento de **emergencias declaradas** por un organismo internacional, no
una medida del daño ni de las víctimas. Refleja tanto la exposición real de un
país como la atención internacional que recibió: un Estado chico y poco cubierto
puede tener menos declaraciones que emergencias vivió. Se dice en la cautela.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import comun
import geo

COLECTOR = "reliefweb"
CAPA = "publico"
APPNAME = "fundacionkent-report-q5v8"
BASE = f"https://api.reliefweb.int/v2/disasters?appname={APPNAME}"
ANIOS_VENTANA = 10


def _post(payload: dict) -> dict:
    datos = json.dumps(payload).encode("utf-8")
    pet = urllib.request.Request(
        BASE, data=datos,
        headers={"User-Agent": comun.AGENTE, "Content-Type": "application/json",
                 "Accept": "application/json"})
    ultimo = None
    for intento in range(4):
        try:
            with urllib.request.urlopen(pet, timeout=60) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001 — se reintenta y, si no, se declara
            ultimo = e
            import time
            time.sleep(3 * (intento + 1))
    raise RuntimeError(f"ReliefWeb no respondió: {type(ultimo).__name__}: {str(ultimo)[:140]}")


def _por_pais(payload: dict) -> dict:
    """{iso3 en minúscula: cantidad} desde la faceta de país primario."""
    d = _post(payload)
    facetas = (d.get("embedded", {}).get("facets") or {})
    datos = (facetas.get("primary_country.iso3", {}) or {}).get("data") or []
    return {x["value"]: x["count"] for x in datos if x.get("value")}


def construir() -> Path:
    este = datetime.now(timezone.utc).year
    desde = f"{este - ANIOS_VENTANA + 1}-01-01T00:00:00+00:00"

    ventana = _por_pais({
        "filter": {"field": "date.event", "value": {"from": desde}},
        "facets": [{"field": "primary_country.iso3", "limit": 400}], "limit": 0})
    activos = _por_pais({
        "filter": {"field": "status", "value": "current"},
        "facets": [{"field": "primary_country.iso3", "limit": 400}], "limit": 0})
    if not ventana:
        raise RuntimeError("ReliefWeb no devolvió ningún país con desastres en la ventana")

    registros, cobertura = [], 0
    for p in geo.padron():
        iso3 = p["iso"].lower()
        cuantos = ventana.get(iso3, 0)
        r = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        # Se publica el dato para TODOS: cero desastres declarados es un dato, no un vacío.
        curso = activos.get(iso3, 0)
        r["indicadores"]["desastres_onu"] = {
            "valor": cuantos, "anio": este,
            "activos_hoy": curso,
            "detalle": (f"{curso} con estado «en curso» hoy" if curso
                        else "ninguno en curso hoy"),
        }
        registros.append(r)
        if cuantos:
            cobertura += 1

    medida = {
        "clave": "desastres_onu", "eje": "Desarrollo",
        "rotulo": f"Desastres declarados por la ONU (últimos {ANIOS_VENTANA} años)",
        "unidad": f"desastres declarados en {ANIOS_VENTANA} años", "unidad_singular": "desastre",
        "mas_es_peor": True,
        "origen": "ReliefWeb — Oficina de Coordinación de Asuntos Humanitarios de las Naciones Unidas (OCHA)",
        "cautela": ("Es un recuento de EMERGENCIAS DECLARADAS por la ONU, no del daño ni de las "
                    "víctimas. Refleja la exposición real del país y, a la vez, la atención "
                    "internacional que recibió: un Estado chico o poco cubierto puede tener menos "
                    "declaraciones que emergencias vivió. Cada declaración es un evento —una "
                    "inundación, un terremoto, una epidemia—, no una escala de gravedad."),
    }
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="ReliefWeb — Oficina de Coordinación de Asuntos Humanitarios de las Naciones Unidas (OCHA)",
        url_fuente="https://reliefweb.int/disasters",
        calificacion=comun.calificar(
            "A", 2, False,
            "Organismo de las Naciones Unidas que declara y sigue emergencias humanitarias. "
            "Credibilidad 2 y no 1: la declaración depende de la atención internacional, y la "
            "cobertura de los Estados chicos del Caribe es despareja."),
        registros=registros,
        vacios=[
            "NO ES UNA MEDIDA DEL DAÑO. Es cuántas emergencias declaró la ONU, no cuánta gente "
            "afectaron ni cuánto costaron. Un país con más declaraciones no sufrió necesariamente más.",
            "LA COBERTURA ES DESPAREJA: los Estados chicos y menos cubiertos por la prensa "
            "internacional tienden a tener menos declaraciones que emergencias reales.",
            f"La ventana es de {ANIOS_VENTANA} años, hasta hoy. Un desastre viejo pero de gran "
            "impacto no cuenta si quedó fuera de la ventana.",
        ],
        extra={"indicadores": [medida],
               "cobertura": {"desastres_onu": cobertura},
               "resumen": {"con_desastre_en_la_ventana": cobertura,
                           "con_desastre_activo_hoy": sum(1 for r in registros
                                                          if r["indicadores"]["desastres_onu"]["activos_hoy"]),
                           "ventana_anios": ANIOS_VENTANA, "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
