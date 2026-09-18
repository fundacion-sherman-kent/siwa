# -*- coding: utf-8 -*-
"""Violencia política por unidad de primer orden — ACLED.

QUÉ ES ESTO
-----------
Eventos de violencia política (batallas, violencia contra civiles, explosiones /
violencia remota) y sus víctimas, agregados POR UNIDAD DE PRIMER ORDEN (admin1)
de cada uno de los 33 Estados, del Armed Conflict Location & Event Data Project
(ACLED). Alimenta el prototipo de la capa subnacional —todavía APAGADA—, y suma
una CATEGORÍA nueva (violencia política) al lado de homicidios y robos.

CREDENCIAL
----------
ACLED cambió (mayo 2025) a autenticación OAuth: no hay «clave» suelta, se entra
con el correo y la contraseña de la cuenta, que la dirección cargó como secretos
del repositorio (ACLED_USUARIO y ACLED_CLAVE). El colector pide un token y lo usa
en la cabecera. Sin secretos NO falla el robot: avisa que faltan y termina en verde.

REGLAS DE LA CASA
-----------------
  · Es RECUENTO de eventos y de víctimas por unidad, no tasa.
  · No se compara entre países como ranking: cada contexto es distinto.
  · El nombre de la unidad (admin1) se deja como lo publica ACLED; el cotejo con
    un padrón geográfico es el paso siguiente y se declara pendiente.
  · Fuente secundaria estructurada (ACLED codifica de prensa y fuentes locales):
    credibilidad 2, declarada.
"""
from __future__ import annotations

import collections
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import comun
import geo

COLECTOR = "subnacional_acled"
CAPA = "publico"
UA = "Mozilla/5.0 (compatible; SIWA/1.0; +https://siwa.fundacionkent.org)"

TOKEN_URL = "https://acleddata.com/oauth/token"
READ_URL = "https://acleddata.com/api/acled/read"

# ISO3 -> ISO numérico (3166-1), para pedirle a ACLED cada Estado sin ambigüedad
# de nombre. Son los 33 del padrón.
ISO_NUM = {
    "ARG": 32, "BOL": 68, "BRA": 76, "CHL": 152, "COL": 170, "CRI": 188, "CUB": 192,
    "DOM": 214, "ECU": 218, "SLV": 222, "GTM": 320, "GUY": 328, "HTI": 332, "HND": 340,
    "JAM": 388, "MEX": 484, "NIC": 558, "PAN": 591, "PRY": 600, "PER": 604, "SUR": 740,
    "URY": 858, "VEN": 862, "ATG": 28, "BHS": 44, "BRB": 52, "BLZ": 84, "DMA": 212,
    "GRD": 308, "KNA": 659, "LCA": 662, "VCT": 670, "TTO": 780,
}


def _token() -> str:
    usuario = os.environ.get("ACLED_USUARIO")
    clave = os.environ.get("ACLED_CLAVE")
    if not usuario or not clave:
        raise RuntimeError("Faltan los secretos ACLED_USUARIO / ACLED_CLAVE")
    body = urllib.parse.urlencode({
        "username": usuario, "password": clave,
        "grant_type": "password", "client_id": "acled", "scope": "authenticated",
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["access_token"]


def _pedir(token: str, iso_num: int, anio: int) -> list:
    """Eventos de violencia política de un Estado y un año, campos acotados."""
    params = {
        "iso": iso_num,
        "year": anio,
        "disorder_type": "Political violence",
        "fields": "iso|admin1|year|event_type|fatalities",
        "limit": 0,
    }
    url = READ_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    return d.get("data") or []


def _un_estado(token: str, iso_num: int, anios: range) -> dict:
    """{admin1: {anio: {'eventos': n, 'victimas': m}}} de un Estado."""
    por = collections.defaultdict(lambda: collections.defaultdict(lambda: {"eventos": 0, "victimas": 0}))
    for anio in anios:
        try:
            filas = _pedir(token, iso_num, anio)
        except Exception:  # noqa: BLE001 — un año que falla no voltea al Estado
            continue
        for f in filas:
            unidad = (f.get("admin1") or "").strip()
            if not unidad:
                continue
            try:
                muertos = int(float(f.get("fatalities") or 0))
            except (TypeError, ValueError):
                muertos = 0
            celda = por[unidad][anio]
            celda["eventos"] += 1
            celda["victimas"] += muertos
    return {u: dict(s) for u, s in por.items() if s}


def construir():
    nombres = {p["iso"]: p["pais"] for p in geo.padron()}
    bloques = {p["iso"]: p.get("bloque") for p in geo.padron()}
    token = _token()
    este = datetime.now(timezone.utc).year
    anios = range(este - 5, este + 1)  # últimos seis años, incluido el corriente
    estados, caidas = [], []
    for iso, iso_num in ISO_NUM.items():
        try:
            por = _un_estado(token, iso_num, anios)
        except Exception as e:  # noqa: BLE001
            caidas.append(f"{nombres.get(iso, iso)}: {type(e).__name__}: {str(e)[:80]}")
            continue
        if not por:
            continue
        todos = sorted({a for s in por.values() for a in s})
        ultimo = todos[-1] if todos else None
        unidades = [{
            "nombre": u,
            "ultimo": ({"anio": ultimo, **s[ultimo]} if ultimo in s else None),
            "serie": [{"anio": a, "eventos": v["eventos"], "victimas": v["victimas"]}
                      for a, v in sorted(s.items())],
        } for u, s in sorted(por.items())]
        estados.append({
            "iso": iso, "pais": nombres.get(iso, iso), "bloque": bloques.get(iso),
            "nombre_unidad": "unidad de primer orden (admin1)", "cuantas": len(unidades),
            "organismo": "ACLED — Armed Conflict Location & Event Data Project",
            "licencia": "ACLED, uso con atribución (cuenta myACLED)",
            "nota": "Recuento de EVENTOS de violencia política y de sus VÍCTIMAS por unidad, "
                    "por año. No es tasa ni ranking entre países.",
            "unidades": unidades,
        })
    if not estados:
        raise RuntimeError("Ningún Estado devolvió eventos de ACLED: " + " | ".join(caidas or ["(sin detalle)"]))
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="ACLED — Armed Conflict Location & Event Data Project: eventos de violencia "
               "política por unidad de primer orden (admin1) de cada Estado",
        url_fuente="https://acleddata.com/",
        calificacion=comun.calificar(
            "B", 2, False,
            "Base estructurada que codifica violencia política a partir de prensa y fuentes "
            "locales. Fiabilidad B y credibilidad 2: no es registro oficial del Estado, y el "
            "nombre de la unidad no se cotejó aún contra un padrón geográfico."),
        registros=estados,
        vacios=[
            "ES RECUENTO POR UNIDAD, NO TASA: sin población por unidad no se calcula tasa.",
            "NO SE COMPARA ENTRE PAÍSES COMO RANKING: la intensidad y la cobertura mediática "
            "difieren entre contextos.",
            "FUENTE SECUNDARIA: ACLED codifica de terceros; no reemplaza el dato oficial cuando existe.",
        ] + ([f"No se pudo desagregar: {' | '.join(caidas)}."] if caidas else []),
        extra={"resumen": {
            "estados_con_desglose": len(estados),
            "unidades_totales": sum(e["cuantas"] for e in estados),
            "anios": [min(anios), max(anios)],
            "es_prototipo": True,
            "capa_subnacional": "APAGADA — alimenta el prototipo, no el mapa",
            "consultado": comun.ahora(),
        }},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
