# -*- coding: utf-8 -*-
"""Trata de personas: víctimas detectadas por ciudadanía (origen) y país de detección.

DE DÓNDE SALE
-------------
Del dataset GLOTIP de UNODC (Global Report on Trafficking in Persons), bajado a mano a
`fuentes/entrada-manual/unodc_glotip.xlsx` (file-drop). Se lee el XML crudo porque el
archivo trae una dimensión rota que confunde a openpyxl.

QUÉ CORREDOR ARMA
-----------------
El único cruce casi bilateral de trata que publica UNODC: **Indicator «Detected
trafficking victims», Dimension «by citizenship»**. Ahí, `Country` es el país que
DETECTA a la víctima (destino) y `Category` es la CIUDADANÍA de la víctima (origen).
Se suma por (ciudadanía → detección) las víctimas contadas, 2007–2023, sólo Sex=Total.

QUÉ MIDE, Y QUÉ NO
------------------
Es DETECCIÓN, no flujo: refleja tanto la trata como la capacidad de cada Estado de
detectarla. Una ciudadanía distinta del país de detección NO equivale a una ruta. Los
valores «<5» están suprimidos por privacidad y se cuentan como 3 (punto medio 1–4),
declarado. Se excluyen «Own country nationals» (no es corredor) y «Unknown».
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

import comun

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
ARCHIVO = RAIZ / "fuentes" / "entrada-manual" / "unodc_glotip.xlsx"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

# Nombres ONU de los 33 Estados, tal como los escribe el dataset.
ALC_NOMBRES = {
    "Argentina", "Bolivia (Plurinational State of)", "Brazil", "Chile", "Colombia",
    "Costa Rica", "Cuba", "Dominican Republic", "Ecuador", "El Salvador", "Guatemala",
    "Honduras", "Mexico", "Nicaragua", "Panama", "Paraguay", "Peru", "Uruguay",
    "Venezuela (Bolivarian Republic of)", "Haiti", "Jamaica", "Trinidad and Tobago",
    "Guyana", "Suriname", "Belize", "Bahamas", "Barbados", "Antigua and Barbuda",
    "Dominica", "Grenada", "Saint Kitts and Nevis", "Saint Lucia",
    "Saint Vincent and the Grenadines",
}
NO_CORREDOR = {"Own country nationals", "Unknown", "Other", "Stateless", "All",
               "Various countries", "Not specified", "Other countries"}


def _valor(t: str):
    t = (t or "").strip()
    if not t:
        return None
    if t.startswith("<"):
        return 3.0  # «<5» suprimido: punto medio 1–4, declarado
    try:
        return float(t.replace(",", ""))
    except ValueError:
        return None


def _filas(z: zipfile.ZipFile) -> tuple:
    ss = ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"]))
          for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]

    def celda(c):
        v = c.find("m:v", NS)
        return "" if v is None else (ss[int(v.text)] if c.get("t") == "s" else (v.text or ""))

    sheet = next(n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
    filas = [[celda(c) for c in f.findall("m:c", NS)]
             for f in ET.fromstring(z.read(sheet)).iter("{%s}row" % NS["m"])]
    hi = next((i for i, r in enumerate(filas) if "Iso3_code" in r), None)
    if hi is None:
        raise RuntimeError("El GLOTIP no trae la fila de encabezados (Iso3_code…). NO se publica.")
    col = {n: j for j, n in enumerate(filas[hi]) if n}
    return filas[hi + 1:], col


def recolectar():
    if not ARCHIVO.exists():
        raise RuntimeError(
            f"No está {ARCHIVO.name} en fuentes/entrada-manual/. Es un file-drop: se baja el "
            "dataset GLOTIP de data.unodc.org y se sube. Sin ese archivo no se publica.")

    filas, col = _filas(zipfile.ZipFile(ARCHIVO))
    need = ("Indicator", "Dimension", "Category", "Country", "Sex", "Year", "txtVALUE")
    for c in need:
        if c not in col:
            raise RuntimeError(f"El GLOTIP no trae la columna «{c}». La planilla cambió. NO se publica.")

    par = defaultdict(lambda: {"victimas": 0.0, "anios": set(), "suprimidos": 0})
    tope = max(col.values())
    for r in filas:
        if len(r) <= tope:
            continue
        if r[col["Indicator"]] != "Detected trafficking victims" or r[col["Dimension"]] != "by citizenship":
            continue
        if r[col["Sex"]] != "Total":
            continue
        origen = r[col["Category"]]            # ciudadanía
        destino = r[col["Country"]]            # país de detección
        if origen in NO_CORREDOR or not origen or not destino:
            continue
        if origen == destino:  # ciudadano detectado en su propio país: trata interna, no corredor
            continue
        if destino not in ALC_NOMBRES and origen not in ALC_NOMBRES:
            continue
        val = _valor(r[col["txtVALUE"]])
        if val is None:
            continue
        d = par[(origen, destino)]
        d["victimas"] += val
        if r[col["txtVALUE"]].strip().startswith("<"):
            d["suprimidos"] += 1
        if r[col["Year"]].strip().isdigit():
            d["anios"].add(int(r[col["Year"]]))

    if len(par) < 30:
        raise RuntimeError(
            f"Sólo se leyeron {len(par)} pares de trata y deberían ser cientos. El GLOTIP cambió "
            "de forma o vino incompleto. NO se publica.")

    registros = []
    for (origen, destino), d in par.items():
        anios = d["anios"]
        registros.append({
            "origen": origen, "destino": destino,
            "victimas": round(d["victimas"]),
            "celdas_suprimidas": d["suprimidos"],
            "desde": min(anios) if anios else None, "hasta": max(anios) if anios else None,
        })
    registros.sort(key=lambda r: -r["victimas"])

    vacios = [
        "Es DETECCIÓN, no flujo: el número refleja tanto la trata como la capacidad del Estado "
        "de detectarla. Una ciudadanía distinta del país donde se detecta a la víctima NO "
        "equivale a una ruta comprobada.",
        "Los valores «<5» están suprimidos por privacidad en la fuente; se cuentan como 3 (punto "
        "medio de 1 a 4). Por eso el total de un par puede estar levemente sobre o subestimado.",
        "Se toma sólo el cruce «víctimas detectadas por ciudadanía» con Sex=Total, para no "
        "duplicar con las filas abiertas por sexo. «Own country nationals» y «Unknown» no forman "
        "corredor y se excluyen.",
        "Cubre los pares donde el país de detección o la ciudadanía es uno de los 33 Estados. Los "
        "años van de 2007 a 2023 según lo que cada país reportó; un hueco es un hueco, no un cero.",
    ]

    calificacion = comun.calificar(
        fiabilidad="B", credibilidad=2, corroborado=False,
        nota=("UNODC, Global Report on Trafficking in Persons (GLOTIP). Fiabilidad B porque el dato "
              "lo produce cada Estado según su capacidad de detección, muy desigual. Credibilidad 2 "
              "porque es un recuento administrativo de casos detectados, no una medición del "
              "fenómeno real, que en su mayor parte no se detecta."),
    )

    return comun.escribir(
        colector="trata_unodc",
        capa="publico",
        fuente="UNODC — Global Report on Trafficking in Persons (GLOTIP): víctimas detectadas por ciudadanía",
        url_fuente="https://data.unodc.org/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "pares": len(registros),
                "victimas_totales": round(sum(r["victimas"] for r in registros)),
                "consultado": comun.ahora(),
            },
            "licencia": "UNODC, uso no comercial con cita. SIWA se considera uso no comercial.",
        },
    )


if __name__ == "__main__":
    comun.correr("trata_unodc", recolectar)
