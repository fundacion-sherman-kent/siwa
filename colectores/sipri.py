# -*- coding: utf-8 -*-
"""Gasto militar por país — SIPRI (Stockholm International Peace Research Institute).

QUÉ AGREGA
----------
SIPRI es la referencia mundial del gasto militar. SIWA ya trae el gasto del Banco
Mundial; SIPRI lo complementa con tres miradas, y aporta una que el Banco Mundial
no da cómoda: cuánto del PRESUPUESTO del Estado se va a lo militar.

  · gasto_militar_pbi        — % del PBI (comparable entre países).
  · gasto_militar_gasto_pub  — % del gasto público total (prioridad presupuestaria).
  · gasto_militar_usd_const  — millones de USD constantes de 2024 (tamaño real).

CÓMO
----
El archivo de SIPRI es un Excel pensado para lectura humana (regiones, notas,
columnas intercaladas); se lee con openpyxl, que el robot instala igual que pypdf
y shapely. La URL del archivo cambia cada año, así que se resuelve raspando la
página de la base (no se fija a mano).
"""
from __future__ import annotations

import io
import re
import unicodedata
import urllib.request
from datetime import datetime, timezone

import comun
import geo

COLECTOR = "sipri"
CAPA = "publico"
UA = "Mozilla/5.0 (compatible; SIWA/1.0; +https://siwa.fundacionkent.org)"
PAGINA = "https://www.sipri.org/databases/milex"

# Nombre de SIPRI (en inglés) -> ISO3, para los 33 del padrón.
NOMBRE_ISO = {
    "argentina": "ARG", "bolivia": "BOL", "brazil": "BRA", "chile": "CHL",
    "colombia": "COL", "costa rica": "CRI", "cuba": "CUB", "dominican republic": "DOM",
    "ecuador": "ECU", "el salvador": "SLV", "guatemala": "GTM", "guyana": "GUY",
    "haiti": "HTI", "honduras": "HND", "jamaica": "JAM", "mexico": "MEX",
    "nicaragua": "NIC", "panama": "PAN", "paraguay": "PRY", "peru": "PER",
    "suriname": "SUR", "uruguay": "URY", "venezuela": "VEN",
    "antigua and barbuda": "ATG", "bahamas": "BHS", "barbados": "BRB",
    "belize": "BLZ", "dominica": "DMA", "grenada": "GRD",
    "saint kitts and nevis": "KNA", "st kitts and nevis": "KNA",
    "saint lucia": "LCA", "st lucia": "LCA",
    "saint vincent and the grenadines": "VCT", "st vincent and the grenadines": "VCT",
    "trinidad and tobago": "TTO",
}

HOJAS = {
    "gasto_militar_pbi": ("Share of GDP", 100, "porcentaje del PBI"),
    "gasto_militar_gasto_pub": ("Share of Govt. spending", 100, "porcentaje del gasto público"),
    "gasto_militar_usd_const": ("Constant (2024) US$", 1, "millones de USD constantes de 2024"),
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def _url_actual() -> str:
    pagina = comun.traer_crudo(PAGINA).decode("utf-8", "replace")
    rel = re.findall(r"/sites/[^\"')\s]+?\.xlsx", pagina)
    if not rel:
        raise RuntimeError("SIPRI: no se encontró el enlace al Excel en la página de la base")
    return "https://www.sipri.org" + rel[0]


def _leer_hoja(wb, hoja: str) -> tuple:
    """Devuelve ({iso: {anio: valor}}, ultimo_anio_de_la_serie)."""
    import openpyxl  # noqa: F401 — declarado; el robot lo instala
    sh = wb[hoja]
    filas = list(sh.iter_rows(values_only=True))
    # La cabecera es la fila que trae la palabra "Country" y los años como números.
    hdr_idx = next((i for i, r in enumerate(filas[:12])
                    if any(_norm(x) == "country" for x in r if x is not None)), None)
    if hdr_idx is None:
        raise RuntimeError(f"SIPRI: no se halló la cabecera en la hoja {hoja}")
    hdr = filas[hdr_idx]
    col_pais = next((j for j, x in enumerate(hdr) if _norm(x) == "country"), 0)
    anio_col = {j: int(x) for j, x in enumerate(hdr)
                if isinstance(x, (int, float)) and 1949 <= int(x) <= 2100}
    por = {}
    for r in filas[hdr_idx + 1:]:
        nom = _norm(r[col_pais]) if col_pais < len(r) and r[col_pais] else ""
        iso = NOMBRE_ISO.get(nom)
        if not iso:
            continue
        serie = {a: float(r[j]) for j, a in anio_col.items()
                 if j < len(r) and isinstance(r[j], (int, float))}
        if serie:
            por[iso] = serie
    anios = sorted({a for s in por.values() for a in s})
    return por, (anios[-1] if anios else None)


def construir():
    import io as _io
    import openpyxl
    padron = geo.padron()
    nombres = {p["iso"]: p["pais"] for p in padron}
    bloques = {p["iso"]: p.get("bloque") for p in padron}

    url = _url_actual()
    wb = openpyxl.load_workbook(_io.BytesIO(comun.traer_crudo(url)), read_only=True, data_only=True)

    datos = {}
    indicadores = []
    for clave, (hoja, factor, unidad) in HOJAS.items():
        por, ultimo = _leer_hoja(wb, hoja)
        datos[clave] = (por, factor, unidad, ultimo)
        indicadores.append({"clave": clave, "hoja": hoja, "unidad": unidad, "ultimo_anio": ultimo})

    corte = datetime.now(timezone.utc).year - 15  # serie de los últimos ~15 años
    registros = []
    for p in padron:
        iso = p["iso"]
        ind = {}
        for clave, (por, factor, unidad, _ult) in datos.items():
            serie = por.get(iso) or {}
            if not serie:
                continue
            recientes = {a: round(v * factor, 3) for a, v in serie.items() if a >= corte}
            ultimo = max(serie)
            ind[clave] = {
                "valor": round(serie[ultimo] * factor, 3),
                "anio": ultimo,
                "unidad": unidad,
                "serie": [{"anio": a, "valor": recientes[a]} for a in sorted(recientes)],
            }
        registros.append({"iso": iso, "pais": nombres[iso], "bloque": bloques.get(iso),
                          "estado": "con_dato" if ind else "sin_dato_sipri", "indicadores": ind})

    con = sum(1 for r in registros if r["indicadores"])
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="SIPRI — Stockholm International Peace Research Institute: base de gasto militar",
        url_fuente="https://www.sipri.org/databases/milex",
        calificacion=comun.calificar(
            "A", 2, False,
            "Estimación de referencia mundial del gasto militar, con metodología declarada. "
            "Credibilidad 2: SIPRI estima e imputa donde el Estado no publica, y advierte esos casos."),
        registros=registros,
        vacios=[
            "Costa Rica y Panamá no tienen fuerzas armadas; su gasto militar es nulo o no aplica.",
            "Algunos Estados del Caribe oriental no figuran en SIPRI: se declaran sin dato, no en cero.",
            "SIPRI imputa y estima donde la fuente nacional no publica; el detalle está en sus notas.",
        ],
        extra={"indicadores": indicadores,
               "resumen": {"estados_con_dato": con, "estados_del_padron": len(registros),
                           "archivo": url.rsplit("/", 1)[-1], "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
