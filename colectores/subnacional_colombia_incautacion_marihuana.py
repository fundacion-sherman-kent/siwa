# -*- coding: utf-8 -*-
"""Incautación de marihuana por departamento (Colombia) — Ministerio de Defensa /
Policía Nacional, datos.gov.co, id `g228-vp9d`.

El brief detectó ~20 filas agregadas con código de departamento espurio; se
descartan por el filtro de código DANE y se declara cuántas fueron.
"""
from __future__ import annotations

import comun
import subnacional_colombia_mindefensa as base

COLECTOR = "subnacional_colombia_incautacion_marihuana"
DATASET_ID = "g228-vp9d"


def construir():
    return base.construir_indicador(
        colector=COLECTOR, dataset_id=DATASET_ID,
        titulo="Incautación de marihuana",
        nota="Kilogramos de marihuana incautados por la Policía Nacional, por "
             "departamento del hecho. Verificado en vivo (23/9/2026): la unidad "
             "declarada por la fuente es kilogramos.",
        url_ficha=f"https://www.datos.gov.co/resource/{DATASET_ID}.json",
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
