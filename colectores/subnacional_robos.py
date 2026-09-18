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

# ── ARGENTINA — «Robos» por provincia (mismo CSV del SNIC que los homicidios) ──
# El SNIC publica todas las figuras en la misma planilla por provincia; se toma la
# categoría de robo base (excluye los agravados con lesiones/muerte, que son otra
# fila) y se cuenta por HECHOS, no por víctimas: un robo no tiene «víctima» contada.
_ROBO_SNIC = "Robos (excluye los agravados por el resultado de lesiones y/o muertes)"


def argentina() -> dict:
    filas = list(csv.reader(io.StringIO(base.er.pedir(base.er.SNIC_PROVINCIAS).decode("utf-8-sig", "replace")),
                            delimiter=";"))
    cab = [c.strip('"') for c in filas[0]]
    i = {c: n for n, c in enumerate(cab)}
    por = collections.defaultdict(dict)
    for f in filas[1:]:
        if len(f) < len(cab) or f[i["codigo_delito_snic_nombre"]].strip('"') != _ROBO_SNIC:
            continue
        try:
            por[f[i["provincia_nombre"]].strip('"')][int(f[i["anio"]])] = int(float(f[i["cantidad_hechos"]]))
        except (ValueError, KeyError):
            continue
    return {"unidad": "provincia", "por_unidad": dict(por), "en_curso": None,
            "organismo": "Ministerio de Seguridad — SNIC (Argentina)", "licencia": "CC BY 4.0",
            "nota": "Robos (excluye los agravados con lesiones/muerte), contados por HECHOS."}


# ── COLOMBIA — hurto a personas por departamento (Policía Nacional, Socrata) ───
CO_HURTO = "https://www.datos.gov.co/resource/4rxi-8m8d.json"


def colombia() -> dict:
    """Hurto a personas por departamento. Se agrega por departamento y año con la
    API Socrata (la suma la hace el servidor: una sola llamada)."""
    soql = urllib.parse.urlencode({
        "$select": "departamento, date_extract_y(fecha_hecho) as anio, sum(cantidad) as t",
        "$group": "departamento, date_extract_y(fecha_hecho)", "$limit": "20000"})
    filas = json.loads(comun.traer_crudo(f"{CO_HURTO}?{soql}", espera=90).decode("utf-8", "replace"))
    por = collections.defaultdict(dict)
    for f in filas:
        dep = (f.get("departamento") or "").strip()
        try:
            anio = int(f["anio"])
            tot = int(float(f["t"]))
        except (KeyError, ValueError, TypeError):
            continue
        if dep and dep.upper() not in ("NO REPORTA", "-", ""):
            por[dep][anio] = por[dep].get(anio, 0) + tot
    por = {d: s for d, s in por.items() if s}
    curso = None
    este = datetime.now(timezone.utc).year
    anios = sorted({a for s in por.values() for a in s})
    if anios and anios[-1] == este:
        u = anios[-1]
        curso = {"anio": u, "por_unidad": {d: s.pop(u) for d, s in por.items() if u in s}}
        por = {d: s for d, s in por.items() if s}
    return {"unidad": "departamento", "por_unidad": por, "en_curso": curso,
            "organismo": "Policía Nacional de Colombia — datos.gov.co",
            "licencia": "Datos Abiertos de Colombia",
            "nota": "Recuento de HURTO A PERSONAS por departamento."}


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


# ── REPÚBLICA DOMINICANA ─────────────────────────────────────────────────────
# El Portal de Datos Abiertos de RD (datos.gob.do, CKAN) publica, de la Policía
# Nacional, los robos reportados POR PROVINCIA. Se resuelve el CSV por la API del
# portal —no por una URL fija, que cambia cuando actualizan el archivo—. No hace
# falta ningún permiso ni correo: el portal responde a un programa.
DOM_API = ("https://datos.gob.do/api/3/action/package_search?q="
           + urllib.parse.quote("Robos reportados por provincia") + "&rows=5")


def dominicana() -> dict:
    """Robos por provincia (Policía Nacional), del Portal de Datos Abiertos de RD.

    El CSV viene agregado por delito, nacionalidad, sexo, provincia, mes y año; se
    suma «Cantidad de casos» de los robos, por provincia y año.
    """
    d = json.loads(comun.traer_crudo(DOM_API).decode("utf-8", "replace"))
    url = None
    for p in (d.get("result") or {}).get("results") or []:
        t = (p.get("title") or "").lower()
        if "robo" in t and "provincia" in t:
            for r in p.get("resources") or []:
                if (r.get("format") or "").upper() == "CSV" and r.get("url"):
                    url = r["url"]
                    break
        if url:
            break
    if not url:
        raise RuntimeError("RD: el portal no devolvió CSV de robos por provincia")
    txt = base._decodificar(comun.traer_crudo(url))
    head = txt.splitlines()[0] if txt else ""
    delim = ";" if head.count(";") >= head.count(",") else ","
    lector = csv.DictReader(io.StringIO(txt), delimiter=delim)
    mapa = {base._sin_acentos(c): c for c in (lector.fieldnames or []) if c}
    col_delito = next((mapa[k] for k in mapa if "tipo de delito" in k), None)
    col_cant = next((mapa[k] for k in mapa if "cantidad" in k), None)
    col_prov = next((mapa[k] for k in mapa if k.strip() == "provincia"), None)
    col_anio = next((mapa[k] for k in mapa if k.strip() in ("ano", "anio", "year")), None)
    if not (col_delito and col_cant and col_prov and col_anio):
        raise RuntimeError("RD: faltan columnas esperadas en el CSV de robos")
    por = collections.defaultdict(lambda: collections.defaultdict(int))
    for fila in lector:
        if "robo" not in (fila.get(col_delito) or "").strip().lower():
            continue
        prov = (fila.get(col_prov) or "").strip()
        try:
            anio = int(str(fila.get(col_anio) or "").strip()[:4])
            n = int(float(str(fila.get(col_cant) or 0).strip() or 0))
        except ValueError:
            continue
        if prov and prov.lower() != "provincia":
            por[prov][anio] += n
    por = {p: dict(s) for p, s in por.items() if s}
    curso = None
    anios = sorted({a for s in por.values() for a in s})
    if anios:
        este = datetime.now(timezone.utc).year
        if anios[-1] == este:
            u = anios[-1]
            curso = {"anio": u, "por_unidad": {p: s.pop(u) for p, s in por.items() if u in s}}
            por = {p: s for p, s in por.items() if s}
    return {"unidad": "provincia", "por_unidad": por, "en_curso": curso,
            "organismo": "Policía Nacional (PN) — República Dominicana",
            "licencia": "Portal de Datos Abiertos de la República Dominicana",
            "nota": "Recuento de casos de robo reportados por provincia, agregado del dato "
                    "oficial por delito, provincia y mes."}


PAISES = {"ARG": argentina, "BOL": bolivia, "COL": colombia, "TTO": trinidad, "DOM": dominicana}


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
               "(Argentina SNIC, Colombia Policía Nacional, Bolivia INE, Trinidad TTPS, "
               "República Dominicana — Policía Nacional vía datos.gob.do)",
        url_fuente="https://www.datos.gov.co/",
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
