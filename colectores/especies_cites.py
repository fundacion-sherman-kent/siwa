# -*- coding: utf-8 -*-
"""Especies: comercio de fauna y flora CITES que toca a ALC, exportador→importador.

DE DÓNDE SALE
-------------
La CITES Trade Database no tiene API: se baja la base completa (unos 4,9 GB, 29 M de
registros). Esa descarga NO entra al repositorio. Se procesó una vez con
`herramientas/agregar_cites.py` (fuera de línea), que se quedó con las ~2,6 M de filas
donde el importador o el exportador es uno de los 33 Estados y las sumó por
(exportador, importador, grupo, año) en `fuentes/entrada-manual/cites_alc.csv`. Este
colector lee ESE archivo agregado y arma los corredores. Cuando CITES publique una
edición nueva (anual), se re-baja y se re-agrega; el nombre del archivo no cambia.

QUÉ MIDE, Y QUÉ NO
------------------
Es comercio de especímenes CITES DECLARADO y autorizado (permisos), más las
INCAUTACIONES, que la fuente marca con Source='I'. La cantidad de registros mide el
número de envíos, no kilos ni ejemplares (las unidades no se pueden sumar entre sí).
La ilicitud no se afirma: las incautaciones (Source='I') son el indicio duro; el resto
es comercio legal que sirve para ver la ruta. Flora vs fauna se separa por si la fila
trae Clase zoológica (fauna) o no (flora).
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import comun

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
ARCHIVO = RAIZ / "fuentes" / "entrada-manual" / "cites_alc.csv"

ALC2 = {"AR","BO","BR","CL","CO","CR","CU","DO","EC","SV","GT","HN","MX","NI","PA",
        "PY","PE","UY","VE","HT","JM","TT","GY","SR","BZ","BS","BB","AG","DM","GD",
        "KN","LC","VC"}


def recolectar():
    if not ARCHIVO.exists():
        raise RuntimeError(
            f"No está {ARCHIVO.name} en fuentes/entrada-manual/. Es un file-drop: se baja la "
            "base completa de CITES, se agrega con herramientas/agregar_cites.py y se sube el "
            "resultado. Sin ese archivo no se publica.")

    # (exportador, importador) -> {registros, incautaciones, flora, fauna, anios:set}
    par = defaultdict(lambda: {"registros": 0, "incautaciones": 0, "flora": 0, "fauna": 0, "anios": set()})
    with ARCHIVO.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            exp, imp = row["exportador"], row["importador"]
            if exp not in ALC2 and imp not in ALC2:
                continue
            n = int(row["registros"] or 0)
            inc = int(row["incautaciones"] or 0)
            d = par[(exp, imp)]
            d["registros"] += n
            d["incautaciones"] += inc
            d[row["grupo"]] = d.get(row["grupo"], 0) + n
            if row["anio"]:
                d["anios"].add(int(row["anio"]))

    if len(par) < 100:
        raise RuntimeError(
            f"Sólo se leyeron {len(par)} pares de CITES y deberían ser miles. El archivo "
            "agregado cambió de forma o vino incompleto. NO se publica.")

    registros = []
    for (exp, imp), d in par.items():
        anios = d["anios"]
        registros.append({
            "exportador": exp, "importador": imp,
            "registros": d["registros"], "incautaciones": d["incautaciones"],
            "flora": d["flora"], "fauna": d["fauna"],
            "desde": min(anios) if anios else None, "hasta": max(anios) if anios else None,
        })
    registros.sort(key=lambda r: -r["registros"])

    total_reg = sum(r["registros"] for r in registros)
    total_inc = sum(r["incautaciones"] for r in registros)
    vacios = [
        "Es comercio de especímenes CITES DECLARADO y autorizado (con permiso), más las "
        "incautaciones, que la fuente marca con Source='I'. La ilicitud no se afirma: la "
        "incautación es el indicio duro; el resto es comercio legal que muestra la ruta.",
        "La cantidad es NÚMERO DE REGISTROS (envíos), no kilos ni ejemplares: las unidades de "
        "la base (kg, items, pares, m³) no se pueden sumar entre sí, así que se cuenta el envío.",
        "La guía de CITES avisa que algunos Estados informan permisos EMITIDOS y no comercio "
        "efectivo, así que los volúmenes pueden estar inflados. Y el importador y el exportador "
        "no siempre declaran lo mismo: la diferencia es un indicio, no una prueba.",
        "Flora vs fauna se separa por si la fila trae clase zoológica (fauna) o no (flora); es "
        "una aproximación, no la determinación taxonómica formal.",
        "Cubre sólo los pares donde el importador o el exportador es uno de los 33 Estados. El "
        "resto del comercio mundial CITES existe pero no es de esta región y no se trae.",
    ]

    calificacion = comun.calificar(
        fiabilidad="B", credibilidad=2, corroborado=False,
        nota=("CITES Trade Database, compilada por UNEP-WCMC para la Secretaría CITES. "
              "Fiabilidad B porque el dato lo declara cada Parte con método propio y hay "
              "asimetrías entre importador y exportador. Credibilidad 2 porque es un registro "
              "administrativo de permisos e incautaciones, no una medición del tráfico real."),
    )

    return comun.escribir(
        colector="especies_cites",
        capa="publico",
        fuente="CITES Trade Database — UNEP-WCMC para la Secretaría CITES (descarga completa, agregada a ALC)",
        url_fuente="https://trade.cites.org/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "pares": len(registros),
                "registros_totales": total_reg,
                "incautaciones_totales": total_inc,
                "consultado": comun.ahora(),
            },
            "licencia": ("CITES Trade Database. Cita obligatoria: «CITES Trade Database. Compiled "
                         "by UNEP-WCMC for the CITES Secretariat». SIWA se considera uso no "
                         "comercial; conviene avisar a species@unep-wcmc.org por el dato derivado."),
        },
    )


if __name__ == "__main__":
    comun.correr("especies_cites", recolectar)
