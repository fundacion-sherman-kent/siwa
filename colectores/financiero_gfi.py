# -*- coding: utf-8 -*-
"""Flujos financieros ilícitos: brecha de valor del comercio (trade misinvoicing) por país.

DE DÓNDE SALE
-------------
Del informe de Global Financial Integrity «Trade-Related Illicit Financial Flows in 134
Developing Countries 2009-2018», bajado a mano a `fuentes/entrada-manual/gfi_iff.xlsx`
(file-drop). Se lee la «Table A» (suma de brechas de valor por país y año, en USD
millones).

QUÉ MIDE, Y POR QUÉ NO ES CORREDOR
----------------------------------
Mide la **brecha de valor** entre lo que dos socios declaran del mismo comercio: un
proxy de cuánto capital sale o entra mal declarado por país. Es una MAGNITUD DE PAÍS,
no un par origen→destino: dice cuánto, no hacia dónde. En el mapa se dibuja como
EXPOSICIÓN —un arco de cada Estado hacia los centros financieros offshore, genérico—,
no como un corredor medido. El destino exacto no lo da esta fuente. Y llega hasta 2018.
"""
from __future__ import annotations

from pathlib import Path

import comun
import openpyxl

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
ARCHIVO = RAIZ / "fuentes" / "entrada-manual" / "gfi_iff.xlsx"

# Nombres GFI de los Estados del padrón (formas simples; se resuelve por inicio también).
ALC = {
    "Argentina": "ARG", "Bolivia": "BOL", "Brazil": "BRA", "Chile": "CHL", "Colombia": "COL",
    "Costa Rica": "CRI", "Cuba": "CUB", "Dominican Republic": "DOM", "Ecuador": "ECU",
    "El Salvador": "SLV", "Guatemala": "GTM", "Honduras": "HND", "Mexico": "MEX",
    "Nicaragua": "NIC", "Panama": "PAN", "Paraguay": "PRY", "Peru": "PER", "Uruguay": "URY",
    "Venezuela": "VEN", "Haiti": "HTI", "Jamaica": "JAM", "Trinidad and Tobago": "TTO",
    "Guyana": "GUY", "Suriname": "SUR", "Belize": "BLZ", "Bahamas": "BHS", "Barbados": "BRB",
    "Grenada": "GRD", "Saint Lucia": "LCA", "Saint Vincent and the Grenadines": "VCT",
    "Antigua and Barbuda": "ATG", "Dominica": "DMA",
}


def _iso(nombre: str):
    nombre = (nombre or "").strip()
    if nombre in ALC:
        return ALC[nombre]
    for k, v in ALC.items():
        if nombre.startswith(k):
            return v
    return None


def recolectar():
    if not ARCHIVO.exists():
        raise RuntimeError(
            f"No está {ARCHIVO.name} en fuentes/entrada-manual/. Es un file-drop: se baja el "
            "anexo de datos de GFI y se sube. Sin ese archivo no se publica.")

    wb = openpyxl.load_workbook(ARCHIVO, read_only=True, data_only=True)
    ws = wb["Table A"]
    filas = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()

    # fila de años: la que tiene varias celdas que son años
    cab = next((i for i, r in enumerate(filas)
                if sum(1 for c in r if isinstance(c, (int, float)) and 1990 <= c <= 2100) >= 5), None)
    if cab is None:
        raise RuntimeError("La Table A de GFI no trae la fila de años. La planilla cambió. NO se publica.")
    aniocol = {j: int(c) for j, c in enumerate(filas[cab])
               if isinstance(c, (int, float)) and 1990 <= c <= 2100}
    # columna del país: la anterior a la primera de años
    col_pais = min(aniocol) - 1

    registros = []
    for r in filas[cab + 1:]:
        if len(r) <= col_pais:
            continue
        iso = _iso(r[col_pais] if isinstance(r[col_pais], str) else "")
        if not iso:
            continue
        serie = {}
        for j, anio in aniocol.items():
            if j < len(r) and isinstance(r[j], (int, float)):
                serie[anio] = round(float(r[j]))
        if not serie:
            continue
        ultimo = max(serie)
        registros.append({
            "iso": iso, "pais": str(r[col_pais]).strip(),
            "brecha_usd_millones": serie[ultimo], "anio": ultimo,
            "serie": [{"anio": a, "valor": serie[a]} for a in sorted(serie)],
        })

    if len(registros) < 10:
        raise RuntimeError(
            f"Sólo se leyeron {len(registros)} Estados de GFI y deberían ser más de veinte. La "
            "planilla cambió de forma o los nombres no coinciden. NO se publica.")

    registros.sort(key=lambda r: -r["brecha_usd_millones"])
    vacios = [
        "Es la BRECHA DE VALOR del comercio (trade misinvoicing): la diferencia entre lo que dos "
        "socios declaran del mismo intercambio. Es un proxy de capital mal declarado, no una "
        "medición directa del dinero ilícito.",
        "Es una MAGNITUD DE PAÍS, no un corredor: dice cuánto, no hacia dónde. En el mapa se "
        "dibuja como exposición hacia los centros offshore de forma genérica; el destino exacto "
        "no lo da esta fuente.",
        "La serie llega hasta 2018 (última edición de GFI hallada). No es tiempo real; se declara.",
        "Valores en dólares de EE.UU., en millones.",
    ]
    calificacion = comun.calificar(
        fiabilidad="B", credibilidad=2, corroborado=False,
        nota=("Global Financial Integrity, sobre datos espejo de Comtrade. Fiabilidad B porque es "
              "una estimación con supuestos metodológicos, no un registro. Credibilidad 2 porque el "
              "insumo (comercio bilateral declarado) es sólido pero la atribución a flujo ilícito es "
              "indirecta."),
    )
    return comun.escribir(
        colector="financiero_gfi",
        capa="publico",
        fuente="Global Financial Integrity — Trade-Related Illicit Financial Flows in 134 Developing Countries 2009-2018",
        url_fuente="https://gfintegrity.org/report/trade-related-illicit-financial-flows-in-134-developing-countries-2009-2018/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados": len(registros),
                "brecha_total_ultimo_anio_usd_millones": sum(r["brecha_usd_millones"] for r in registros),
                "consultado": comun.ahora(),
            },
            "licencia": ("GFI, licencia CC BY-NC-ND. SIWA se considera uso no comercial; se cita a GFI "
                         "y no se altera el dato original."),
        },
    )


if __name__ == "__main__":
    comun.correr("financiero_gfi", recolectar)
