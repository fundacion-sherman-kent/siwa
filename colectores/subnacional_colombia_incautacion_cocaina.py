# -*- coding: utf-8 -*-
"""Incautación de cocaína por departamento (Colombia) — Ministerio de Defensa /
Policía Nacional, datos.gov.co, id `26zg-9p9r`.

El brief detectó ~55 filas agregadas con código de departamento espurio (p. ej.
"1111"); este colector las descarta por el filtro de código DANE de
`subnacional_colombia_mindefensa` y declara cuántas fueron, en cada corrida.
"""
from __future__ import annotations

import comun
import subnacional_colombia_mindefensa as base

COLECTOR = "subnacional_colombia_incautacion_cocaina"
DATASET_ID = "26zg-9p9r"


def construir():
    return base.construir_indicador(
        colector=COLECTOR, dataset_id=DATASET_ID,
        titulo="Incautación de cocaína",
        nota="Kilogramos de cocaína incautados por la Policía Nacional, por departamento "
             "del hecho. La unidad de medida (kilogramos) es la que declara MinDefensa "
             "para el resto de los flujos ilícitos de este mismo esqueleto; la consulta "
             "en vivo del campo «unidad» de este conjunto en particular no se pudo "
             "confirmar con certeza en esta sesión (no se toma como verificado).",
        url_ficha=f"https://www.datos.gov.co/resource/{DATASET_ID}.json",
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
