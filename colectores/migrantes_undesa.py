# -*- coding: utf-8 -*-
"""Migración: stock de migrantes origen→destino de TODOS los países (UN DESA).

POR QUÉ, ADEMÁS DE R4V
----------------------
R4V mide sólo el éxodo venezolano. Para la migración de todos los países se usa la
matriz bilateral de UN DESA (International Migrant Stock 2024): por cada par
origen→destino, cuántos migrantes de ese origen viven en ese destino, 1990–2024, 233
países. Es la fuente canónica —la que R4V mismo cita para varios países—.

QUÉ LEE
-------
La «Table 1» de la planilla oficial (link directo, se baja sola: honra el mandato de
tiempo real). Encabezado con Index, nombre y código del destino, nombre y código del
origen, y ocho años (1990–2024) por cada sexo; se toma el bloque «Both sexes». Se queda
con los pares país→país donde el origen o el destino es uno de los 33 Estados.

QUÉ MIDE, Y QUÉ NO
------------------
Es STOCK a mitad de año (cuánta gente de un origen vive en un destino), no el flujo del
año. Los códigos de región y los agregados (World, «High-income», etc.) se descartan:
sólo país→país. La edición 2024 extrapola desde 2020 los países sin censo nuevo, y se
declara.
"""
from __future__ import annotations

import io
import urllib.request
from pathlib import Path

import comun
import openpyxl

URL = ("https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/"
       "files/undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx")

M49 = {  # ALC → ISO3 del padrón
    32: "ARG", 68: "BOL", 76: "BRA", 152: "CHL", 170: "COL", 188: "CRI", 192: "CUB",
    214: "DOM", 218: "ECU", 222: "SLV", 320: "GTM", 340: "HND", 484: "MEX", 558: "NIC",
    591: "PAN", 600: "PRY", 604: "PER", 858: "URY", 862: "VEN", 332: "HTI", 388: "JAM",
    780: "TTO", 328: "GUY", 740: "SUR", 84: "BLZ", 44: "BHS", 52: "BRB", 28: "ATG",
    212: "DMA", 308: "GRD", 659: "KNA", 662: "LCA", 670: "VCT",
}
ALC = set(M49.values())
HUB = {  # destinos/orígenes fuera de la región (código M49 → nombre del hub)
    840: "USA", 124: "Canada", 724: "Spain", 380: "Italy", 620: "Portugal", 276: "Germany",
    250: "France", 826: "United Kingdom", 528: "Netherlands", 756: "Switzerland",
    156: "China", 356: "India", 643: "Russian Federation", 392: "Japan", 752: "Sweden",
    36: "Australia", 40: "Austria", 56: "Belgium", 616: "Poland",
}
CLAVE = {**M49, **HUB}


def _bajar() -> bytes:
    pet = urllib.request.Request(URL, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(pet, timeout=180) as r:
        return r.read()


def recolectar():
    wb = openpyxl.load_workbook(io.BytesIO(_bajar()), read_only=True, data_only=True)
    ws = wb["Table 1"]
    filas = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()

    hi = next((i for i, r in enumerate(filas) if r and r[0] == "Index"), None)
    if hi is None:
        raise RuntimeError("La Table 1 de UN DESA no trae la fila «Index». La planilla cambió. NO se publica.")
    hdr = filas[hi]
    # columnas de destino/origen (fijas por diseño): nombre dest=1, cód dest=4, nombre orig=5, cód orig=6
    # años: las columnas cuyo encabezado es un año; el primer bloque de 8 es «Both sexes».
    anio_col = [(j, int(c)) for j, c in enumerate(hdr) if isinstance(c, (int, float)) and 1990 <= c <= 2100]
    if len(anio_col) < 8:
        raise RuntimeError("La Table 1 de UN DESA no trae las columnas de años esperadas. NO se publica.")
    both = anio_col[:8]  # primer bloque = ambos sexos
    j2024 = next((j for j, a in both if a == max(a for _, a in both)), both[-1][0])

    registros = []
    for r in filas[hi + 1:]:
        if len(r) <= 6:
            continue
        try:
            dcode, ocode = int(r[4]), int(r[6])
        except (TypeError, ValueError):
            continue
        if dcode not in CLAVE or ocode not in CLAVE or dcode == ocode:
            continue
        if dcode not in M49 and ocode not in M49:  # al menos un extremo debe ser ALC
            continue
        val = r[j2024] if j2024 < len(r) else None
        if not isinstance(val, (int, float)) or val <= 0:
            continue
        serie = []
        for j, a in both:
            if j < len(r) and isinstance(r[j], (int, float)) and r[j] > 0:
                serie.append({"anio": a, "valor": int(r[j])})
        registros.append({
            "origen": CLAVE[ocode], "destino": CLAVE[dcode],
            "personas": int(val), "anio": max(a for _, a in both),
            "serie": serie,
        })

    if len(registros) < 300:
        raise RuntimeError(
            f"Sólo se leyeron {len(registros)} pares de UN DESA y deberían ser más de mil. La "
            "planilla cambió de forma o los códigos no coinciden. NO se publica.")

    registros.sort(key=lambda r: -r["personas"])
    vacios = [
        "Es STOCK a mitad de año (cuánta gente de un origen vive en un destino), no el flujo del "
        "año. Un stock grande puede ser migración vieja consolidada, no movimiento reciente.",
        "Sólo pares país→país donde el origen o el destino es uno de los 33 Estados. Los agregados "
        "de la fuente (World, regiones, grupos de ingreso) se descartan: no son corredores.",
        "La edición 2024 reasignó con censo nuevo a 60 países; al resto lo extrapoló desde 2020. "
        "Los países sin censo reciente traen una estimación, no una medición fresca.",
        "R4V (venezolanos, actualizado a 2026) es la capa fresca y detallada de un origen; esta es "
        "la base comparable de todos los orígenes, hasta 2024.",
    ]
    calificacion = comun.calificar(
        fiabilidad="A", credibilidad=2, corroborado=False,
        nota=("División de Población de UN DESA, sobre censos y registros de cada país. Fiabilidad "
              "A porque el productor compila fuentes oficiales con método publicado. Credibilidad 2 "
              "porque parte de los países van extrapolados y el stock no distingue el año de "
              "llegada."),
    )
    return comun.escribir(
        colector="migrantes_undesa",
        capa="publico",
        fuente="UN DESA, División de Población — International Migrant Stock 2024 (origen×destino)",
        url_fuente=URL,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "pares": len(registros),
                "anio": max(a for _, a in both),
                "consultado": comun.ahora(),
            },
            "licencia": "UN DESA, CC BY 3.0 IGO, con cita. SIWA se considera uso no comercial.",
        },
    )


if __name__ == "__main__":
    comun.correr("migrantes_undesa", recolectar)
