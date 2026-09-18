# -*- coding: utf-8 -*-
"""Estado de derecho — World Justice Project (WJP Rule of Law Index).

QUÉ AGREGA
----------
El índice de referencia mundial de estado de derecho, medido con 8 factores a
partir de encuestas a población y expertos. SIWA ya trae el estado de derecho del
Banco Mundial (WGI), que es una agregación de percepciones; el WJP lo mide con su
propia recolección primaria y en una escala 0–1 comparable en el tiempo.

  · estado_derecho_wjp — índice general de estado de derecho (0 = peor, 1 = mejor).

CÓMO — archivo directo, sin navegador
-------------------------------------
El sitio de WJP es una app JavaScript (no renderiza para un programa), pero la app
referencia un Excel histórico REAL en el servidor. El colector lo baja directo con
la biblioteca estándar y lee la hoja «Historical Data» (formato largo: una fila por
país y año) con openpyxl, que el robot instala. El año del archivo cambia por
edición y se descubre probando los años recientes.
"""
from __future__ import annotations

import io
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

import comun
import geo

COLECTOR = "wjp"
CAPA = "publico"
UA = "Mozilla/5.0 (compatible; SIWA/1.0; +https://siwa.fundacionkent.org)"
PLANTILLA = ("https://worldjusticeproject.org/rule-of-law-index/downloads/"
             "{anio}_wjp_rule_of_law_index_HISTORICAL_DATA_FILE.xlsx")


def _url_actual() -> str:
    # El servidor de WJP devuelve 200 con una página HTML para un archivo que no
    # existe (soft-404); por eso NO alcanza con el código: se comprueba que la
    # respuesta sea realmente una planilla (Content-Type) antes de aceptarla.
    este = date.today().year
    for anio in range(este + 1, este - 4, -1):
        url = PLANTILLA.format(anio=anio)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                ct = (r.headers.get("Content-Type") or "").lower()
                if r.status == 200 and ("spreadsheet" in ct or "officedocument" in ct
                                        or "octet-stream" in ct):
                    return url
        except urllib.error.HTTPError:
            continue
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError("WJP: no se encontró el Excel histórico en los años recientes")


def _anio(txt) -> int | None:
    m = re.findall(r"\d{4}", str(txt))
    return int(m[-1]) if m else None


def construir():
    import openpyxl
    padron = geo.padron()
    isos = {p["iso"] for p in padron}
    nombres = {p["iso"]: p["pais"] for p in padron}
    bloques = {p["iso"]: p.get("bloque") for p in padron}

    url = _url_actual()
    wb = openpyxl.load_workbook(io.BytesIO(comun.traer_crudo(url)), read_only=True, data_only=True)
    sh = wb["Historical Data"]
    filas = list(sh.iter_rows(values_only=True))
    hdr = filas[0]
    col = {c: n for n, c in enumerate(hdr)}
    c_iso = col.get("Country Code")
    c_anio = col.get("Year")
    c_val = next((n for c, n in col.items() if str(c).strip().startswith("WJP Rule of Law Ind")), None)
    if c_iso is None or c_anio is None or c_val is None:
        raise RuntimeError("WJP: faltan columnas esperadas en la hoja Historical Data")

    por = {}
    for r in filas[1:]:
        iso = r[c_iso]
        if iso not in isos:
            continue
        anio = _anio(r[c_anio])
        try:
            val = float(r[c_val])
        except (TypeError, ValueError):
            continue
        if anio:
            por.setdefault(iso, {})[anio] = val

    registros = []
    for p in padron:
        iso = p["iso"]
        serie = por.get(iso) or {}
        ind = {}
        if serie:
            ultimo = max(serie)
            ind["estado_derecho_wjp"] = {
                "rotulo": "Estado de derecho (WJP)",
                "valor": round(serie[ultimo], 3),
                "anio": ultimo,
                "unidad": "índice WJP (0 a 1)",
                "no_comparable_entre_paises": False,
                "serie": [{"anio": a, "valor": round(v, 3)} for a, v in sorted(serie.items())],
            }
        registros.append({"iso": iso, "pais": nombres[iso], "bloque": bloques.get(iso),
                          "estado": "con_dato" if ind else "sin_dato_wjp", "indicadores": ind})

    con = sum(1 for r in registros if r["indicadores"])
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="World Justice Project — WJP Rule of Law Index (índice general de estado de derecho)",
        url_fuente="https://worldjusticeproject.org/rule-of-law-index",
        calificacion=comun.calificar(
            "A", 2, False,
            "Índice de referencia mundial de estado de derecho, con metodología declarada y "
            "recolección primaria (encuestas a población y expertos). Credibilidad 2: es un índice "
            "compuesto, no un acto administrativo único."),
        registros=registros,
        vacios=[
            "WJP no cubre a todos los Estados del padrón todos los años: el vacío se declara.",
            "Es un índice 0–1; más alto es mejor estado de derecho. No es un acto observable único "
            "sino un compuesto de ocho factores.",
        ],
        extra={"indicadores": [{"clave": "estado_derecho_wjp", "rotulo": "Estado de derecho (WJP)",
                                "unidad": "índice WJP (0 a 1)"}],
               "resumen": {"estados_con_dato": con, "estados_del_padron": len(registros),
                           "archivo": url.rsplit("/", 1)[-1], "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
