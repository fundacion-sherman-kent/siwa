# -*- coding: utf-8 -*-
"""Incautación de basuco por departamento (Colombia) — Ministerio de Defensa /
Policía Nacional, datos.gov.co, id `3cjd-phaj`.

De las cinco incautaciones de droga del brief, esta es la de fuente más
limpia: verificado en vivo el 23/9/2026, ninguna fila trae un código de
departamento espurio.
"""
from __future__ import annotations

import comun
import subnacional_colombia_mindefensa as base

COLECTOR = "subnacional_colombia_incautacion_basuco"
DATASET_ID = "3cjd-phaj"


def construir():
    return base.construir_indicador(
        colector=COLECTOR, dataset_id=DATASET_ID,
        titulo="Incautación de basuco",
        nota="Kilogramos de basuco incautados por la Policía Nacional, por departamento "
             "del hecho. Recuento en kilogramos, no número de operativos.",
        url_ficha=f"https://www.datos.gov.co/resource/{DATASET_ID}.json",
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
