# -*- coding: utf-8 -*-
"""Robos por unidad de primer orden — segunda categoría del eje Seguridad.

Mismo criterio que los homicidios por unidad: se toma la fuente NACIONAL que
publica el delito por provincia/departamento/división, machine-readable. Arranca
con los tres Estados de fuente más limpia y se extiende a los demás (Argentina
SNIC, Brasil BancoVDE, Chile INE, Panamá, Uruguay) en las próximas vueltas.

REGLA DE LA CASA: es RECUENTO por unidad, no tasa. Y NO se compara entre países:
cada Estado define el robo/hurto a su manera (hurto, rapiña, robbery). Se declara
qué mide cada fuente.
"""
from __future__ import annotations

import collections
import csv
import io
import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import comun
import geo
import subnacional_homicidios as base  # reutiliza _sin_acentos, _decodificar, TTPS, Bolivia XLSX

COLECTOR = "subnacional_robos"
CAPA = "publico"

# ── COLOMBIA — hurto por departamento (Policía Nacional, Socrata) ──────────────
CO_HURTO = "https://www.datos.gov.co/resource/d4fr-sbn2.json"


def colombia() -> dict:
    por = collections.defaultdict(dict)
    este = datetime.now(timezone.utc).year
    for anio in range(este, este - 4, -1):
        soql = urllib.parse.urlencode({
            "$select": "departamento,sum(cantidad) as t",
            "$where": f"fecha_hecho like '%/{anio}'",
            "$group": "departamento", "$limit": "60"})
        try:
            filas = json.loads(comun.traer_crudo(f"{CO_HURTO}?{soql}", espera=90).decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            continue
        for f in filas:
            dep = (f.get("departamento") or "").strip()
            if dep and f.get("t"):
                try:
                    por[dep][anio] = int(float(f["t"]))
                except ValueError:
                    pass
    por = {d: s for d, s in por.items() if s}
    curso = None
    anios = sorted({a for s in por.values() for a in s})
    if anios and anios[-1] == este:
        u = anios[-1]
        curso = {"anio": u, "por_unidad": {d: s.pop(u) for d, s in por.items() if u in s}}
        por = {d: s for d, s in por.items() if s}
    return {"unidad": "departamento", "por_unidad": por, "en_curso": curso,
            "organismo": "Policía Nacional de Colombia (DIJIN) — datos.gov.co",
            "licencia": "datos abiertos de Colombia",
            "nota": "Recuento de HURTOS (todas las modalidades) por departamento."}


# ── BOLIVIA — «Robo» por departamento (mismo XLSX del INE que homicidios) ──────
def bolivia() -> dict:
    import re
    raw = comun.traer_crudo(base.BOLIVIA_URL)
    filas = base.er._planilla(raw, "3.08.02.13")
    col_anio = {}
    for num in sorted(filas):
        for c, v in filas[num].items():
            m = re.match(r"(20\d\d)", str(v).strip())
            if m:
                col_anio[c] = int(m.group(1))
        if col_anio:
            break
    por = collections.defaultdict(dict)
    dept = None
    for num in sorted(filas):
        b = filas[num].get("B")
        if not isinstance(b, str):
            continue
        clave = base._sin_acentos(b)
        if clave in base._DEPTOS_BOL:
            dept = b.strip()
            continue
        if dept and clave == "robo":
            for c, anio in col_anio.items():
                try:
                    por[dept][anio] = int(float(filas[num].get(c)))
                except (TypeError, ValueError):
                    continue
            dept = None
    return {"unidad": "departamento", "por_unidad": dict(por), "en_curso": None,
            "organismo": "INE Bolivia — denuncias registradas por la Policía Boliviana",
            "licencia": "estadística oficial publicada",
            "nota": "Recuento de DENUNCIAS de robo por departamento. Serie 2007 en adelante."}


# ── TRINIDAD Y TOBAGO — robberies por división policial (TTPS) ─────────────────
def trinidad() -> dict:
    por = collections.defaultdict(dict)
    este = datetime.now(timezone.utc).year
    curso = None
    for anio in range(2018, este + 1):
        try:
            raw = comun.traer_crudo(base.TTPS_CSV.format(anio=anio))
        except Exception:  # noqa: BLE001
            continue
        lineas = raw.decode("utf-8-sig", "replace").splitlines()
        cab = next((i for i, l in enumerate(lineas) if l.lower().startswith("year,")), None)
        if cab is None:
            continue
        acum = collections.defaultdict(int)
        hubo = False
        for fila in csv.DictReader(io.StringIO("\n".join(lineas[cab:]))):
            m = {base._sin_acentos(k): k for k in fila if k}
            delito = (fila.get(m.get("offence", "")) or "").strip().lower()
            division = (fila.get(m.get("division", "")) or "").strip()
            rep = fila.get(m.get("reported", "")) or "0"
            if "robber" in delito and division:
                try:
                    acum[division] += int(float(str(rep).strip() or 0))
                    hubo = True
                except ValueError:
                    continue
        if hubo:
            for div, n in acum.items():
                por[div][anio] = n
    por = {d: s for d, s in por.items() if s}
    anios = sorted({a for s in por.values() for a in s})
    if anios and anios[-1] == este:
        u = anios[-1]
        curso = {"anio": u, "por_unidad": {d: s.pop(u) for d, s in por.items() if u in s}}
        por = {d: s for d, s in por.items() if s}
    return {"unidad": "división policial", "por_unidad": por, "en_curso": curso,
            "organismo": "Trinidad and Tobago Police Service (TTPS)",
            "licencia": "datos públicos del TTPS",
            "nota": "Recuento de robberies por división policial. Serie desde 2018."}


# Colombia queda FUERA por ahora: el dataset d4fr-sbn2 resultó ser solo hurto de
# nicho (abigeato, piratería terrestre, entidades financieras), NO hurto general.
# Se suma cuando se confirme el dataset correcto de «hurto a personas» por departamento.
PAISES = {"BOL": bolivia, "TTO": trinidad}


def construir() -> Path:
    nombres = {p["iso"]: p["pais"] for p in geo.padron()}
    bloques = {p["iso"]: p.get("bloque") for p in geo.padron()}
    estados, caidas = [], []
    for iso, lector in PAISES.items():
        try:
            dato = lector()
            por = dato["por_unidad"]
            if not por:
                caidas.append(f"{nombres.get(iso, iso)}: sin unidades")
                continue
            anios = sorted({a for s in por.values() for a in s})
            ultimo = anios[-1] if anios else None
            unidades = [{"nombre": u,
                         "ultimo": {"anio": ultimo, "valor": s.get(ultimo)} if ultimo in s else None,
                         "serie": [{"anio": a, "valor": v} for a, v in sorted(s.items())]}
                        for u, s in sorted(por.items())]
            estados.append({"iso": iso, "pais": nombres.get(iso, iso), "bloque": bloques.get(iso),
                            "nombre_unidad": dato["unidad"], "cuantas": len(unidades),
                            "organismo": dato["organismo"], "licencia": dato["licencia"],
                            "nota": dato.get("nota"), "en_curso": dato.get("en_curso"),
                            "unidades": unidades})
        except Exception as e:  # noqa: BLE001
            caidas.append(f"{nombres.get(iso, iso)}: {type(e).__name__}: {str(e)[:100]}")
    if not estados:
        raise RuntimeError("Ningún Estado devolvió robos por unidad: " + " | ".join(caidas))
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="Robos/hurtos por unidad de primer orden, de la fuente nacional de cada Estado "
               "(Bolivia INE, Trinidad TTPS)",
        url_fuente="https://nube.ine.gob.bo/",
        calificacion=comun.calificar(
            "A", 2, False,
            "Registro administrativo oficial por unidad de primer orden. Credibilidad 2: cada "
            "Estado define el robo/hurto a su manera y el nombre de la unidad no se cotejó aún."),
        registros=estados,
        vacios=[
            "ES RECUENTO POR UNIDAD, NO TASA: sin población por unidad no se calcula tasa.",
            "NO SE COMPARA ENTRE PAÍSES: hurto (Colombia), denuncia de robo (Bolivia) y robbery "
            "(Trinidad) no son la misma figura legal.",
            "COBERTURA INICIAL DE TRES ESTADOS: se extiende a Argentina (SNIC), Brasil (BancoVDE), "
            "Chile (INE), Panamá y Uruguay en las próximas vueltas.",
        ] + ([f"No se pudo desagregar: {' | '.join(caidas)}."] if caidas else []),
        extra={"resumen": {"estados_con_desglose": len(estados),
                           "unidades_totales": sum(e["cuantas"] for e in estados),
                           "es_prototipo": True,
                           "capa_subnacional": "APAGADA — alimenta el prototipo, no el mapa",
                           "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
