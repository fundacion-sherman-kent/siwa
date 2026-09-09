# -*- coding: utf-8 -*-
"""Drogas: incautaciones por droga y por año, y cultivo de coca, de UNODC.

POR QUÉ EXISTE
--------------
La Dirección probó el registro con la región completa y en cocaína no había
historia. El Índice Global de Crimen Organizado da tres ediciones de una
evaluación experta; lo que faltaba era UN HECHO CONTADO: kilos incautados por
Estado y por año, y hectáreas de coca donde se cultiva.

Los dos están publicados por la Oficina de las Naciones Unidas contra la Droga
y el Delito en el anexo estadístico del Informe Mundial sobre las Drogas, como
planillas de descarga libre: incautaciones 2019–2023 por país y por droga
(tabla 7.1) y cultivo de coca 2010–2023 en Bolivia, Colombia y Perú (tabla
6.1.1). La interfaz de datos de UNODC —que no responde a los programas— no hace
falta para esto.

LICENCIA
--------
El Informe Mundial sobre las Drogas «puede reproducirse en todo o en parte, en
cualquier forma, con fines educativos o sin fines de lucro, sin autorización
especial, siempre que se cite la fuente». SIWA es gratuito, sin publicidad y
sin botón de donaciones: califica. No se hace uso comercial.

LO QUE LA CIFRA NO DICE, Y SE DECLARA
-------------------------------------
Una incautación mide la acción policial tanto como el flujo: más kilos pueden
ser más tráfico, más control o las dos cosas, y menos kilos, lo contrario. Por
eso esta capa NO entra al compuesto y NO se orienta —no hay «peor» ni «mejor»—;
se muestra como magnitud con su año, y el pie lo dice.

CÓMO SE LEE LA PLANILLA SIN DEPENDENCIAS
----------------------------------------
Un archivo .xlsx es un zip con XML adentro. Se abre con zipfile y se lee con
ElementTree, que vienen con Python: el robot sigue sin instalar nada. Las
celdas de texto viven en sharedStrings.xml y las hojas en worksheets/. La tabla
de cultivo trae los años 2010–2013 como fechas de Excel (40182 = 1/1/2010): se
convierten.

PRUEBA DEL LECTOR
-----------------
Colombia tiene incautaciones de cocaína todos los años y cultivo de coca todos
los años. Si el lector no las encuentra, el que falló es el lector —la planilla
cambió de forma—, y NO se publica una lectura a ciegas.
"""
from __future__ import annotations

import io
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, timedelta

import comun
import geo

BASE = "https://www.unodc.org/documents/data-and-analysis/WDR_2025/Annex/"
INCAUTACIONES = "7.1_Drug_seizures_2019-2023.xlsx"
CULTIVO = "6.1.1_Global_illicit_coca_bush_cultivation.xlsx"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
CONTROL = "COL"

# Los grupos de droga de la fuente, llevados a cuatro familias. Se compara el
# nombre del grupo, no la posición, y lo que no encaja se declara en «otras».
# LA HOJA DE COCA NO ES COCAÍNA. La fuente las pone en el mismo grupo
# («Cocaine-type»), y sumarlas daba a Colombia 987 toneladas de «cocaína» en
# 2019 cuando 984 eran hoja. Se separan: la familia «cocaina» es el subgrupo
# «Cocaine» —clorhidrato, crack, pasta y base, otras formas fumables— y la hoja
# y el arbusto van aparte, como «hoja_coca».
FAMILIAS = [
    ("hoja_coca", re.compile(r"coca-type|coca leaf|coca bush", re.I)),
    ("cocaina", re.compile(r"cocaine", re.I)),
    ("cannabis", re.compile(r"cannabis", re.I)),
    ("opiaceos", re.compile(r"opioid|opiate|heroin|opium", re.I)),
    ("sinteticas", re.compile(r"amphetamine|ecstasy|nps|synthetic|stimulant", re.I)),
]
ROTULOS = {"cocaina": "cocaína", "hoja_coca": "hoja de coca", "cannabis": "cannabis",
           "opiaceos": "opiáceos", "sinteticas": "drogas sintéticas", "otras": "otras sustancias"}
# Algunos Estados informan el total de la familia además de —o en vez de— sus
# partes. Si hay una fila «total», manda ella: sumar total y partes duplica.
TOTAL = re.compile(r"\(total", re.I)


def _bajar(nombre: str) -> bytes:
    peticion = urllib.request.Request(BASE + nombre, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=180) as respuesta:
        return respuesta.read()


def _filas(crudo: bytes) -> list:
    """La primera hoja, fila por fila, con el texto ya resuelto."""
    z = zipfile.ZipFile(io.BytesIO(crudo))
    cadenas = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            cadenas.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    hoja = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
    filas = []
    for fila in ET.fromstring(z.read(hoja)).iter("{%s}row" % NS["m"]):
        celdas = []
        for c in fila.findall("m:c", NS):
            v = c.find("m:v", NS)
            if v is None:
                celdas.append(None)
            elif c.get("t") == "s":
                celdas.append(cadenas[int(v.text)])
            else:
                celdas.append(v.text)
        filas.append(celdas)
    return filas


def _numero(t) -> float | None:
    try:
        return float(str(t).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _anio(t) -> int | None:
    """Un año escrito, o una fecha de Excel (días desde 1899-12-30)."""
    n = _numero(t)
    if n is None:
        return None
    if 1990 <= n <= 2100:
        return int(n)
    if 30000 <= n <= 60000:
        return (date(1899, 12, 30) + timedelta(days=int(n))).year
    return None


def _incautaciones(filas: list, isos: set) -> dict:
    """{iso: {familia: {anio: kg}}}, sumando las drogas de cada familia."""
    cab = next((i for i, f in enumerate(filas) if f and f[0] == "Region" and "Country" in f), None)
    if cab is None:
        raise RuntimeError("La planilla de incautaciones cambió de forma: no se halló la fila "
                           "de encabezados (Region · SubRegion · Country …). NO se publica.")
    col = {nombre: i for i, nombre in enumerate(filas[cab]) if nombre}
    for necesaria in ("DrugGroup", "DrugSubGroup", "DrugName", "Reference year", "Kilograms", "msCode"):
        if necesaria not in col:
            raise RuntimeError(f"La planilla de incautaciones no trae la columna «{necesaria}».")
    partes, totales = {}, {}
    for f in filas[cab + 1:]:
        if len(f) <= max(col.values()):
            continue
        iso = f[col["msCode"]]
        if iso not in isos:
            continue
        anio, kg = _anio(f[col["Reference year"]]), _numero(f[col["Kilograms"]])
        if anio is None or kg is None:
            continue
        # La familia se decide por el subgrupo primero —ahí se separa la hoja de
        # la cocaína— y por el grupo si el subgrupo no dice nada.
        subgrupo, grupo = str(f[col["DrugSubGroup"]] or ""), str(f[col["DrugGroup"]] or "")
        familia = next((n for n, patron in FAMILIAS if patron.search(subgrupo)), None) \
            or next((n for n, patron in FAMILIAS if patron.search(grupo)), "otras")
        destino = totales if TOTAL.search(str(f[col["DrugName"]] or "")) else partes
        destino.setdefault(iso, {}).setdefault(familia, {})
        destino[iso][familia][anio] = destino[iso][familia].get(anio, 0.0) + kg
    # Donde hay total, manda el total; donde no, la suma de las partes.
    salida = {}
    for iso in set(partes) | set(totales):
        for familia in set(partes.get(iso, {})) | set(totales.get(iso, {})):
            porAnio = dict(partes.get(iso, {}).get(familia, {}))
            porAnio.update(totales.get(iso, {}).get(familia, {}))
            salida.setdefault(iso, {})[familia] = porAnio
    return salida


def _cultivo(filas: list) -> dict:
    """{iso: [{anio, valor}]} para Bolivia, Colombia y Perú, en hectáreas."""
    cab = next((f for f in filas if f and sum(1 for c in f if _anio(c)) >= 8), None)
    if cab is None:
        raise RuntimeError("La planilla de cultivo de coca cambió de forma: no se halló la fila de años.")
    anios = {i: _anio(c) for i, c in enumerate(cab) if _anio(c)}
    nombres = {"BOL": re.compile(r"bolivia", re.I), "COL": re.compile(r"colombia", re.I),
               "PER": re.compile(r"peru", re.I)}
    salida = {}
    for f in filas:
        rotulo = str(f[0] or "").strip() if f else ""
        for iso, patron in nombres.items():
            if not patron.search(rotulo):
                continue
            serie = [{"anio": a, "valor": _numero(f[i])} for i, a in anios.items()
                     if i < len(f) and _numero(f[i]) is not None]
            # Perú trae dos filas —bruta y neta—; se conserva la más larga y,
            # a igual largo, la última, que es la neta al 31 de diciembre.
            if iso not in salida or len(serie) >= len(salida[iso]):
                salida[iso] = serie
    return {iso: sorted(s, key=lambda x: x["anio"]) for iso, s in salida.items() if len(s) >= 2}


def recolectar():
    padron = geo.padron()
    isos = {p["iso"] for p in padron}
    incaut = _incautaciones(_filas(_bajar(INCAUTACIONES)), isos)
    cultivo = _cultivo(_filas(_bajar(CULTIVO)))

    # SE PRUEBA EL LECTOR ANTES DE CREERLE UN VACÍO A NADIE.
    if len(incaut.get(CONTROL, {}).get("cocaina", {})) < 3:
        raise RuntimeError(
            f"La prueba del lector falló: en {CONTROL} no se leyeron incautaciones de cocaína "
            "de al menos tres años. La planilla cambió de forma. NO se publica.")
    if len(cultivo.get(CONTROL, [])) < 8:
        raise RuntimeError(
            f"La prueba del lector falló: en {CONTROL} no se leyó la serie de cultivo de coca. "
            "La planilla cambió de forma. NO se publica.")

    registros, conDato = [], 0
    for p in padron:
        familias = incaut.get(p["iso"], {})
        series = {}
        for familia, porAnio in familias.items():
            serie = [{"anio": a, "valor": round(v, 2)} for a, v in sorted(porAnio.items())]
            series[familia] = {"rotulo": ROTULOS[familia], "serie": serie, "ultimo": serie[-1]}
        if series:
            conDato += 1
        registros.append({
            "iso": p["iso"], "pais": p["pais"], "bloque": p["bloque"],
            "estado": "con_dato" if series else "sin_dato",
            "incautaciones": series,
            "cultivo_coca": cultivo.get(p["iso"]),
        })

    anios = sorted({a["anio"] for r in registros for s in r["incautaciones"].values() for a in s["serie"]})
    calificacion = comun.calificar(
        fiabilidad="B", credibilidad=2, corroborado=False,
        nota=("Oficina de las Naciones Unidas contra la Droga y el Delito, sobre lo que cada "
              "Estado informa en el cuestionario anual. Fiabilidad B porque el dato lo "
              "produce el Estado que se describe. Credibilidad 2 porque es un recuento "
              "administrativo, coherente con otras fuentes, no verificable de forma "
              "independiente."),
    )
    vacios = [
        "Una incautación mide la acción policial tanto como el flujo: más kilos pueden ser "
        "más tráfico, más control o las dos cosas. Por eso esta capa no entra al compuesto y "
        "no se orienta: no hay «peor» ni «mejor».",
        "Los Estados que no contestaron el cuestionario de un año no aparecen ese año. Un "
        "hueco en la serie es un hueco en el informe, no un cero.",
        "El cultivo de coca solo se mide en Bolivia, Colombia y Perú, que son donde se cultiva; "
        "los demás Estados no tienen la cifra porque no hay qué medir, y así se declara.",
        "Es la planilla del informe anual: la incautación de este año recién se publica el "
        "año que viene.",
    ]
    return comun.escribir(
        colector="drogas",
        capa="publico",
        fuente="Informe Mundial sobre las Drogas 2025, anexo estadístico — Oficina de las Naciones Unidas contra la Droga y el Delito (UNODC)",
        url_fuente="https://www.unodc.org/unodc/en/data-and-analysis/world-drug-report-2025-annex.html",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados_con_incautaciones": conDato,
                "estados_del_padron": len(registros),
                "anios_incautaciones": anios,
                "estados_con_cultivo": sorted(cultivo.keys()),
                "familias": ROTULOS,
                "lector_probado": True,
                "consultado": comun.ahora(),
            },
            "licencia": ("Reproducción permitida con fines educativos o sin fines de lucro, "
                         "citando la fuente. Sin uso comercial."),
        },
    )


if __name__ == "__main__":
    comun.correr("drogas", recolectar)
