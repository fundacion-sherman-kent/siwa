# -*- coding: utf-8 -*-
"""Extorsión por departamento (Colombia) — Ministerio de Defensa / Policía
Nacional, datos.gov.co, id `q2ib-t9am`.

Verificado en vivo el 23/9/2026: mismo esqueleto de columnas que el resto del
bloque, sin código de departamento espurio detectado por el brief.
"""
from __future__ import annotations

import comun
import subnacional_colombia_mindefensa as base

COLECTOR = "subnacional_colombia_extorsion"
DATASET_ID = "q2ib-t9am"


def construir():
    return base.construir_indicador(
        colector=COLECTOR, dataset_id=DATASET_ID,
        titulo="Extorsión",
        nota="Casos de extorsión registrados por la Policía Nacional, por "
             "departamento del hecho. Recuento de casos.",
        url_ficha=f"https://www.datos.gov.co/resource/{DATASET_ID}.json",
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
