# -*- coding: utf-8 -*-
"""Cultivo de coca segun EE.UU. (ONDCP): la SEGUNDA FUENTE del cultivo de coca.

POR QUE EXISTE
--------------
El asunto "drogas" tenia UNA SOLA fuente -UNODC- y la regla de la casa pide dos
(doctrina/fuentes.md, y herramientas/segunda-fuente.py lo mide). La contraparte
independiente natural del cultivo de coca es la estimacion oficial del gobierno
de EE.UU. (ONDCP / Crime and Narcotics Center): mide lo mismo -hectareas de coca
en Colombia, Peru y Bolivia- con OTRA metodologia, no comparte procedencia con
UNODC (a diferencia de CICAD, que se nutre de lo que informan los mismos Estados)
y por eso es corroboracion de verdad. Emite la clave `cultivo_coca_ondcp`, que
segunda-fuente.py suma al asunto "drogas" para que pase a dos productores.

QUE NO HACE, Y SE DECLARA
-------------------------
No agrega frescura: la ultima edicion publica de ONDCP es 2022 (datos 2021), mas
vieja que UNODC (2023). Suma INDEPENDENCIA, no actualidad; la frescura la sigue
poniendo UNODC. Las dos series no coinciden en el numero -metodologias distintas-
y asi tiene que ser: son dos mediciones del mismo hecho, no una copia.

COMO SE ACTUALIZA
-----------------
File-drop: lee fuentes/entrada-manual/ondcp_coca.json, que se carga a mano cuando
la ONDCP publica una edicion nueva (no hay API ni planilla; es un comunicado). No
descarga nada: por eso no falla si la Casa Blanca cambia la URL del comunicado.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun

ENTRADA = AQUI.parent / "fuentes" / "entrada-manual" / "ondcp_coca.json"
PAIS = {"COL": "Colombia", "PER": "Peru", "BOL": "Bolivia"}


def main():
    datos = json.loads(ENTRADA.read_text(encoding="utf-8"))
    series = datos["series"]
    ediciones = datos.get("ediciones", [])
    ultima = max((e.get("datos_hasta") or 0) for e in ediciones) if ediciones else None

    registros = []
    for iso, pais in PAIS.items():
        serie = sorted(series.get(iso, []), key=lambda x: x["anio"])
        if not serie:
            continue
        ultimo = serie[-1]
        registros.append({
            "iso": iso,
            "pais": pais,
            "indicadores": {
                "cultivo_coca_ondcp": {
                    "valor": ultimo["ha"],
                    "anio": ultimo["anio"],
                    "serie": [{"anio": s["anio"], "valor": s["ha"]} for s in serie],
                    "origen": "ONDCP (Casa Blanca, EE.UU.)",
                },
            },
        })

    calificacion = comun.calificar(
        fiabilidad="B", credibilidad=2, corroborado=False,
        nota=("Estimacion oficial del gobierno de EE.UU. (ONDCP / Crime and Narcotics "
              "Center). Fiabilidad B: fuente oficial con historial. Credibilidad 2: es una "
              "estimacion por teledeteccion y modelo, metodologicamente distinta de UNODC y "
              "no verificable de forma independiente. Entra como SEGUNDA fuente del cultivo "
              "de coca: corrobora a UNODC por ser productor distinto, sin reemplazarlo."),
    )
    vacios = [
        "Solo Colombia, Peru y Bolivia: es donde EE.UU. publica la estimacion de coca.",
        "La cifra de EE.UU. NO coincide con la de UNODC -otra metodologia- y no debe "
        "mezclarse en una sola serie: son dos mediciones del mismo hecho.",
        f"No suma frescura: la ultima edicion publica de ONDCP llega a {ultima}, mas vieja "
        "que UNODC. Aporta independencia, no actualidad.",
        "Las hectareas de 2020 son las REVISADAS en la edicion 2022; una estimacion de EE.UU. "
        "de un ano se corrige en la edicion siguiente.",
    ]
    indicadores = [{
        "clave": "cultivo_coca_ondcp",
        "nombre": "Cultivo de coca (estimacion de EE.UU., ONDCP)",
        "unidad": "hectareas",
        "origen": "ONDCP (Casa Blanca, EE.UU.)",
        "rotulo": "Segunda fuente, independiente de UNODC",
    }]
    comun.escribir(
        colector="coca_ondcp",
        capa="publico",
        fuente=("ONDCP -- Oficina de Politica Nacional de Control de Drogas de la Casa Blanca "
                "(EE.UU.), estimacion de cultivo de coca y produccion potencial de cocaina en la region andina"),
        url_fuente=(ediciones[-1]["url"] if ediciones else "https://www.whitehouse.gov/ondcp/"),
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": indicadores,
            "ediciones": ediciones,
            "produccion_cocaina_t": {iso: series.get(iso, []) for iso in PAIS},
            "licencia": "Obra del gobierno de EE.UU.: dominio publico. Se cita la fuente.",
        },
    )
    print(f"[coca_ondcp] {len(registros)} paises, cultivo de coca ONDCP hasta {ultima} "
          f"(segunda fuente de 'drogas', independiente de UNODC)")


if __name__ == "__main__":
    main()
