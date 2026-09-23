# -*- coding: utf-8 -*-
"""Secuestro por departamento (Colombia) — Ministerio de Defensa / Policía
Nacional, datos.gov.co, id `d7zw-hpf4`.

Verificado en vivo (23/9/2026): el conjunto trae dos figuras penales —
«ARTICULO 168. SECUESTRO SIMPLE» y «ARTICULO 169. SECUESTRO EXTORSIVO»—; se
suman las dos bajo «secuestro», sin distinguir modalidad (el brief no pidió
desagregar por artículo).

El brief registró 32 de 33 departamentos y dejó pendiente identificar cuál
falta y por qué; esta corrida declara la cobertura real, sin completarla a
mano.
"""
from __future__ import annotations

import comun
import subnacional_colombia_mindefensa as base

COLECTOR = "subnacional_colombia_secuestro"
DATASET_ID = "d7zw-hpf4"


def construir():
    return base.construir_indicador(
        colector=COLECTOR, dataset_id=DATASET_ID,
        titulo="Secuestro",
        nota="Casos de secuestro (simple y extorsivo, artículos 168 y 169 del Código "
             "Penal, sumados) registrados por la Policía Nacional, por departamento "
             "del hecho. Recuento de casos, no de víctimas.",
        url_ficha=f"https://www.datos.gov.co/resource/{DATASET_ID}.json",
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
