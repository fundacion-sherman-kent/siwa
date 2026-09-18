# -*- coding: utf-8 -*-
"""Transferencias de armas mayores — SIPRI (valores TIV).

QUÉ AGREGA
----------
El VOLUMEN de armamento convencional mayor que cada Estado recibe y envía, medido
en TIV (Trend-Indicator Value) de SIPRI. No es el valor en dólares (eso lo trae
Comtrade cap. 93): el TIV mide capacidad militar transferida, comparable en el
tiempo. Dos indicadores por país y año:

  · armas_recibidas_tiv — transferencias recibidas (como receptor).
  · armas_enviadas_tiv  — transferencias enviadas (como proveedor).

CÓMO — API directa, sin navegador
---------------------------------
El generador de SIPRI es una app JavaScript, pero por debajo hace un POST a un
backend JSON abierto (atbackend.sipri.org). El colector reproduce ese POST con la
biblioteca estándar: pide el CSV de importaciones y el de exportaciones, y los
parsea. No hace falta clave ni navegador.
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
from datetime import datetime, timezone

import comun
import geo
import sipri  # reutiliza el mapa de nombre inglés -> ISO3 de los 33

COLECTOR = "sipri_transferencias"
CAPA = "publico"
UA = "Mozilla/5.0 (compatible; SIWA/1.0; +https://siwa.fundacionkent.org)"
API = "https://atbackend.sipri.org/api/p/trades/import-export-csv-str/"


def _pedir(export: bool, desde: int, hasta: int) -> str:
    filtros = [
        {"field": "Year range 1", "oldField": "", "condition": "contains",
         "value1": desde, "value2": hasta, "listData": []},
        {"field": "DeliveryType", "oldField": "", "condition": "", "value1": "delivered", "value2": "", "listData": []},
        {"field": "Status", "oldField": "", "condition": "", "value1": "0", "value2": "", "listData": []},
    ]
    if export:  # como PROVEEDOR: la app agrega este filtro para ordenar por vendedor
        filtros.insert(1, {"field": "orderbyseller", "oldField": "", "condition": "",
                           "value1": "", "value2": "", "listData": []})
    cuerpo = json.dumps({"filters": filtros, "logic": "AND"}).encode()
    req = urllib.request.Request(API, data=cuerpo, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": UA,
        "Origin": "https://armstransfers.sipri.org"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())["result"]


def _parsear(texto: str) -> dict:
    """{nombre_de_país: {anio: TIV}} desde el CSV de SIPRI."""
    lineas = texto.splitlines()
    hi = next((n for n, l in enumerate(lineas)
               if l.lower().startswith(("recipient", "supplier", "exports by", "imports by"))), None)
    if hi is None:
        return {}
    filas = list(csv.reader(io.StringIO("\n".join(lineas[hi:]))))
    cab = filas[0]
    anios_col = {j: int(c) for j, c in enumerate(cab) if c.strip().isdigit() and len(c.strip()) == 4}
    por = {}
    for f in filas[1:]:
        if not f or not (f[0] or "").strip():
            continue
        nombre = f[0].strip()
        serie = {}
        for j, anio in anios_col.items():
            if j < len(f):
                v = (f[j] or "").strip()
                if v and v not in ("-", ".."):
                    try:
                        serie[anio] = float(v)
                    except ValueError:
                        continue
        if serie:
            por[nombre] = serie
    return por


def construir():
    padron = geo.padron()
    nombres = {p["iso"]: p["pais"] for p in padron}
    bloques = {p["iso"]: p.get("bloque") for p in padron}
    hasta = datetime.now(timezone.utc).year
    desde = hasta - 11

    recibidas = _parsear(_pedir(False, desde, hasta))   # receptor
    enviadas = _parsear(_pedir(True, desde, hasta))      # proveedor

    def por_iso(por_nombre):
        out = {}
        for nombre, serie in por_nombre.items():
            iso = sipri.NOMBRE_ISO.get(sipri._norm(nombre))
            if iso:
                out[iso] = serie
        return out

    rec_iso, env_iso = por_iso(recibidas), por_iso(enviadas)
    fuentes = {"armas_recibidas_tiv": (rec_iso, "Armas mayores recibidas (TIV)"),
               "armas_enviadas_tiv": (env_iso, "Armas mayores enviadas (TIV)")}

    registros = []
    for p in padron:
        iso = p["iso"]
        ind = {}
        for clave, (datos, rotulo) in fuentes.items():
            serie = datos.get(iso) or {}
            if not serie:
                continue
            ultimo = max(serie)
            ind[clave] = {
                "rotulo": rotulo, "valor": round(serie[ultimo], 1), "anio": ultimo,
                "unidad": "millones de TIV (SIPRI)", "no_comparable_entre_paises": False,
                "serie": [{"anio": a, "valor": round(v, 1)} for a, v in sorted(serie.items())],
            }
        registros.append({"iso": iso, "pais": nombres[iso], "bloque": bloques.get(iso),
                          "estado": "con_dato" if ind else "sin_dato_sipri", "indicadores": ind})

    con = sum(1 for r in registros if r["indicadores"])
    indicadores = [{"clave": c, "rotulo": rot, "unidad": "millones de TIV (SIPRI)"}
                   for c, (_d, rot) in fuentes.items()]
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="SIPRI — Stockholm International Peace Research Institute: base de transferencias "
               "de armas mayores (valores TIV)",
        url_fuente="https://armstransfers.sipri.org/",
        calificacion=comun.calificar(
            "A", 2, False,
            "Estimación de referencia mundial del volumen de transferencias de armas mayores. "
            "Credibilidad 2: el TIV es un indicador de volumen/capacidad, no un valor de mercado, "
            "y SIPRI lo estima con su metodología declarada."),
        registros=registros,
        vacios=[
            "El TIV mide VOLUMEN de armamento mayor (capacidad), no valor en dólares ni unidades.",
            "Un '0' es una entrega de entre 0 y 0,5 millones de TIV; el vacío es sin transferencia identificada.",
        ],
        extra={"indicadores": indicadores,
               "resumen": {"estados_con_dato": con, "estados_del_padron": len(registros),
                           "ventana": [desde, hasta], "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
