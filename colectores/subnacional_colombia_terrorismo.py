# -*- coding: utf-8 -*-
"""Terrorismo / acciones subversivas por departamento (Colombia) — Ministerio
de Defensa, datos.gov.co, id `yi5j-5fe9`.

Es la cifra de MINISTERIO DE DEFENSA, no la de la Policía Nacional/DIJIN (id
`37p5-impc`, que el brief marcó como un colector aparte y de esfuerzo medio
por necesitar un mapeo municipio→departamento: queda para otra vuelta, no se
mezcla con esta).

Verificado en vivo el 23/9/2026: el conjunto trae además una columna «zona»
(rural/urbana) que no se usa para filtrar —se suman ambas— porque el brief
pide el total por departamento, no por zona.

El brief registró 32 de 33 departamentos y dejó pendiente identificar cuál
falta; esta corrida declara la cobertura real de cada ejecución.
"""
from __future__ import annotations

import comun
import subnacional_colombia_mindefensa as base

COLECTOR = "subnacional_colombia_terrorismo"
DATASET_ID = "yi5j-5fe9"


def construir():
    return base.construir_indicador(
        colector=COLECTOR, dataset_id=DATASET_ID,
        titulo="Terrorismo / acciones subversivas",
        nota="Acciones terroristas o subversivas registradas por el Ministerio de "
             "Defensa, por departamento del hecho (zona rural y urbana sumadas). "
             "Es la cifra de MinDefensa, distinta de la de Policía/DIJIN (otra fuente, "
             "no se mezcla).",
        url_ficha=f"https://www.datos.gov.co/resource/{DATASET_ID}.json",
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
