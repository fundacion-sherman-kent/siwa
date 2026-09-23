# -*- coding: utf-8 -*-
"""Incautación de insumos líquidos por departamento (Colombia) — Ministerio de
Defensa / Policía Nacional, datos.gov.co, id `k2wp-tdv7`.

Insumos líquidos para el procesamiento de estupefacientes (no el estupefaciente
en sí). El brief detectó ~4 filas agregadas con código de departamento
espurio; se descartan por el filtro de código DANE.
"""
from __future__ import annotations

import comun
import subnacional_colombia_mindefensa as base

COLECTOR = "subnacional_colombia_incautacion_insumos_liquidos"
DATASET_ID = "k2wp-tdv7"


def construir():
    return base.construir_indicador(
        colector=COLECTOR, dataset_id=DATASET_ID,
        titulo="Incautación de insumos líquidos",
        nota="Galones de insumos líquidos para el procesamiento de estupefacientes, "
             "incautados por la Policía Nacional, por departamento del hecho. "
             "Verificado en vivo (23/9/2026): la unidad declarada por la fuente es "
             "galones — NO es kilogramos como los otros cuatro flujos ilícitos de "
             "este bloque; no se compara entre sí.",
        url_ficha=f"https://www.datos.gov.co/resource/{DATASET_ID}.json",
        es_entero=False,
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
