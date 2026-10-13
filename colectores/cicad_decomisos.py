# -*- coding: utf-8 -*-
"""Decomisos de cocaina segun CICAD (OEA): segunda fuente PARCIAL de incautaciones.

POR QUE EXISTE
--------------
La materia 'incautaciones de cocaina' del asunto 'drogas' tenia un solo productor
(UNODC). La CICAD (Comision Interamericana para el Control del Abuso de Drogas, de
la OEA) publica su propio dato de decomisos en el Report on Drug Supply in the
Americas, asi que es una segunda fuente independiente para esa materia.

QUE ES, Y QUE NO ES (se declara sin vueltas)
--------------------------------------------
PARCIAL A PROPOSITO. El reporte 2022 NO trae tabla numerica: los decomisos por pais
estan en graficos de barras apiladas SIN numeros, con la mayoria de los paises
amontonados en 'Other'. Las unicas cifras por pais que el reporte declara en el TEXTO
son las de cocaina de Colombia, Ecuador, Brasil y Bolivia (p. 21). Esas, y solo esas,
entran aca -no se estiman alturas de barra, no se inventa-. Peru y el resto quedan sin
dato CICAD. Ademas la procedencia es PARCIALMENTE COMPARTIDA con UNODC (los mismos
Estados informan a los dos), asi que la independencia no es total: se rotula.

COMO SE ACTUALIZA
-----------------
File-drop: lee fuentes/entrada-manual/cicad_cocaina.json, cargado a mano desde el PDF
del reporte (oas.org bloquea la descarga automatica con un muro anti-bot; lo baja una
persona). Cuando salga una edicion nueva, se agregan los anios al file-drop.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun

ENTRADA = AQUI.parent / "fuentes" / "entrada-manual" / "cicad_cocaina.json"
PAIS = {"COL": "Colombia", "ECU": "Ecuador", "BRA": "Brasil", "BOL": "Bolivia"}


def main():
    datos = json.loads(ENTRADA.read_text(encoding="utf-8"))
    series = datos["series"]

    registros = []
    for iso, pais in PAIS.items():
        s = series.get(iso, {})
        # Solo los anios con cifra numerica declarada en el texto del reporte.
        pares = sorted((int(a), v) for a, v in s.items() if a.isdigit() and isinstance(v, (int, float)))
        if not pares:
            continue
        # Toneladas metricas -> kilogramos, para ser comparable con UNODC (que va en kg).
        serie = [{"anio": a, "valor": round(v * 1000)} for a, v in pares]
        ultimo = serie[-1]
        registros.append({
            "iso": iso, "pais": pais,
            "indicadores": {
                "incautaciones_cocaina_cicad": {
                    "valor": ultimo["valor"], "anio": ultimo["anio"], "serie": serie,
                    "origen": "CICAD (OEA)",
                },
            },
        })

    calificacion = comun.calificar(
        fiabilidad="B", credibilidad=2, corroborado=False,
        nota=("Report on Drug Supply in the Americas 2022, CICAD (Observatorio Interamericano "
              "sobre Drogas, OEA). Fiabilidad B: organismo multilateral con historial. Credibilidad "
              "2: recuento administrativo sobre lo que informan los Estados, procedencia PARCIALMENTE "
              "COMPARTIDA con UNODC. Entra como segunda fuente de los decomisos de cocaina, PARCIAL: "
              "solo los 4 paises que el reporte declara con numero en el texto."),
    )
    vacios = [
        "PARCIAL: solo Colombia, Ecuador, Brasil y Bolivia -los unicos que el reporte 2022 "
        "declara con numero en el texto-. El resto de los paises va amontonado en 'Other' en los "
        "graficos, sin cifra propia, y no se estima.",
        "Procedencia parcialmente compartida con UNODC: los mismos Estados informan a los dos, asi "
        "que corrobora, pero no son dos fuentes del todo ciegas entre si.",
        "Solo cocaina. El reporte da las otras drogas por pais solo en graficos sin numeros.",
        "Edicion 2022 (datos hasta 2020): no suma frescura frente a UNODC, suma independencia.",
    ]
    indicadores = [{
        "clave": "incautaciones_cocaina_cicad",
        "nombre": "Incautaciones de cocaina (CICAD, OEA) — parcial",
        "unidad": "kilogramos",
        "origen": "CICAD (OEA)",
        "rotulo": "Segunda fuente parcial (4 paises), procedencia parcialmente compartida con UNODC",
    }]
    comun.escribir(
        colector="cicad_decomisos",
        capa="publico",
        fuente=("CICAD — Comision Interamericana para el Control del Abuso de Drogas (OEA), "
                "Report on Drug Supply in the Americas 2022, Observatorio Interamericano sobre Drogas"),
        url_fuente=datos.get("fuente", {}).get("url", "https://oas.org/en/sms/cicad/"),
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": indicadores,
            "licencia": "Reproduccion permitida citando la fuente (OEA/CICAD). Sin uso comercial.",
        },
    )
    print(f"[cicad_decomisos] {len(registros)} paises con decomisos de cocaina (CICAD 2022, parcial, "
          f"segunda fuente de 'drogas')")


if __name__ == "__main__":
    main()
