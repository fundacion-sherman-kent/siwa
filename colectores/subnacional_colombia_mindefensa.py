# -*- coding: utf-8 -*-
"""Ocho indicadores de Colombia por departamento — Ministerio de Defensa / Policía
Nacional, vía la API Socrata de datos.gov.co.

QUÉ ES ESTO
-----------
Nueve conjuntos de datos.gov.co comparten LITERALMENTE el mismo esqueleto de
columnas (`fecha_hecho, cod_depto, departamento, cod_muni, municipio, cantidad
[, unidad]`), verificado en vivo el 23/9/2026 con una petición real a cada uno
de los nueve identificadores. Este módulo trae la lógica de petición y
agregación UNA sola vez —el mismo patrón SoQL que ya usa
`subnacional_robos.colombia()`— y cada indicador es un archivo aparte que la
importa, para poder wirearse a `sitio/subnacional.html` uno por uno, igual
que homicidios y robos.

ANTECEDENTE
-----------
`productos/siwa-subnacional/brief-fuentes.md` (23/9/2026, osint-profundo),
Bloque 1 — Colombia. Este módulo retoma esa tabla y le agrega la verificación
en vivo propia hecha antes de escribir código (columnas exactas, licencia por
metadato Socrata, y el hallazgo sobre el conjunto de víctimas — ver abajo).

QUÉ QUEDÓ AFUERA, Y POR QUÉ (no se fabrica una vigencia que no existe)
-----------------------------------------------------------------------
El brief marcaba «desplazamiento forzado» (Unidad para las Víctimas, id
`y6ru-nqsj`) como "listo para colector". La verificación en vivo del
23/9/2026 mostró algo que el brief no llegó a mirar: el metadato Socrata de
ese conjunto informa `rowsUpdatedAt` = 1/1/2018 y `publicationDate` =
26/5/2018 — la fuente no se actualiza desde entonces — y el archivo trae UNA
FILA POR MUNICIPIO con columnas tituladas "..._2012_2017" (acumulado
histórico), no una serie con fecha de hecho como los otros nueve. Publicarlo
junto a los ocho de abajo —que traen filas de agosto de 2026— daría la
impresión de un dato vigente que no lo es. Se declara aquí y NO se escribe
colector para él en esta tarea.

REGLA DE LA CASA
-----------------
- Es RECUENTO por departamento, no tasa. Sin población por departamento no
  se calcula tasa.
- No se compara entre indicadores de este módulo ni con ningún otro país:
  cada uno mide una figura penal distinta, y esta capa cubre un solo Estado.
- Credibilidad tope 2 (no hay segunda fuente independiente para el dato exacto
  por departamento): se publica, rotulado, nunca como corroborado.
"""
from __future__ import annotations

import collections
import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import comun

# Los 33 códigos DANE de departamento (32 departamentos + Bogotá D.C.), para
# descartar sin ambigüedad los códigos espurios que el brief detectó en cinco
# de los nueve conjuntos (p. ej. "1111", que no es un código de departamento).
DEPTOS_DANE = {
    "05", "08", "11", "13", "15", "17", "18", "19", "20", "23", "25", "27", "41",
    "44", "47", "50", "52", "54", "63", "66", "68", "70", "73", "76", "81", "85",
    "86", "88", "91", "94", "95", "97", "99",
}

BASE_URL = "https://www.datos.gov.co/resource/{id}.json"


def _cargar(dataset_id: str) -> dict:
    """Trae, agrupado por departamento y año, un conjunto del esqueleto MinDefensa.

    La suma la hace el servidor (SoQL `$group`/`sum`), una sola llamada — mismo
    patrón que `subnacional_robos.colombia()`. Se descarta toda fila cuyo
    `cod_depto` no sea uno de los 33 códigos DANE (código espurio de la fuente,
    no de este colector).
    """
    soql = urllib.parse.urlencode({
        "$select": "cod_depto, departamento, date_extract_y(fecha_hecho) as anio, sum(cantidad) as t",
        "$group": "cod_depto, departamento, date_extract_y(fecha_hecho)",
        "$limit": "20000",
    })
    url = BASE_URL.format(id=dataset_id) + "?" + soql
    filas = json.loads(comun.traer_crudo(url, espera=90).decode("utf-8", "replace"))
    por = collections.defaultdict(dict)
    espurios = 0
    for f in filas:
        cod = (f.get("cod_depto") or "").strip()
        dep = (f.get("departamento") or "").strip()
        if cod not in DEPTOS_DANE:
            if cod:
                espurios += 1
            continue
        try:
            anio = int(f["anio"])
            tot = float(f["t"])
        except (KeyError, ValueError, TypeError):
            continue
        if dep:
            por[dep][anio] = por[dep].get(anio, 0) + tot
    return {"por_departamento": {d: s for d, s in por.items() if s}, "espurios": espurios}


def _separar_en_curso(por: dict) -> tuple[dict, dict | None]:
    """Como en homicidios/robos: si el último año es el corriente, se separa
    como provisional en vez de mezclarlo con años cerrados."""
    anios = sorted({a for s in por.values() for a in s})
    if not anios:
        return por, None
    este = datetime.now(timezone.utc).year
    if anios[-1] != este:
        return por, None
    u = anios[-1]
    curso = {"anio": u, "por_unidad": {d: s.pop(u) for d, s in por.items() if u in s}}
    return {d: s for d, s in por.items() if s}, curso


def _redondear(por: dict, decimales: int = 2) -> dict:
    """Las incautaciones vienen con decimales (kilogramos, galones): se
    conservan con hasta dos decimales, sin forzarlas a entero como los
    recuentos de hechos (secuestro, extorsión, terrorismo)."""
    return {d: {a: round(v, decimales) for a, v in s.items()} for d, s in por.items()}


def construir_indicador(colector: str, dataset_id: str, titulo: str, nota: str,
                         url_ficha: str, es_entero: bool = True) -> Path:
    """Arma y escribe el archivo de un indicador de Colombia por departamento."""
    dato = _cargar(dataset_id)
    por = dato["por_departamento"]
    if not por:
        raise RuntimeError(f"{colector}: la fuente no devolvió ningún departamento con "
                            "código DANE válido — puede haber cambiado de esquema.")
    if not es_entero:
        por = _redondear(por)
    por, curso = _separar_en_curso(por)
    anios = sorted({a for s in por.values() for a in s})
    ultimo = anios[-1] if anios else None
    unidades = []
    for d, serie in sorted(por.items()):
        unidades.append({
            "nombre": d,
            "ultimo": {"anio": ultimo, "valor": serie.get(ultimo)} if ultimo in serie else None,
            "serie": [{"anio": a, "valor": v} for a, v in sorted(serie.items())],
        })
    registro = {
        "iso": "COL", "pais": "Colombia", "bloque": "Andina",
        "nombre_unidad": "departamento", "cuantas": len(unidades),
        "organismo": "Ministerio de Defensa Nacional — Policía Nacional de Colombia",
        "licencia": "CC BY-SA 4.0",
        "nota": nota,
        "en_curso": curso,
        "unidades": unidades,
    }
    vacios = [
        "ES RECUENTO POR DEPARTAMENTO, NO TASA: sin población por departamento no se "
        "calcula tasa. Comparar departamentos de tamaño muy distinto engaña.",
        "COBERTURA DE UN SOLO PAÍS: este indicador cubre solo Colombia; en el mapa, el "
        "resto de la región queda sin colorear para esta materia. Es cobertura parcial "
        "de la capa subnacional, no un vacío de la fuente colombiana.",
        f"NO SE COMPARA con ningún otro indicador de este módulo ni con otro país: {titulo} "
        "es una figura penal propia, definida y registrada solo por Colombia.",
        "DOS FUENTES O ROTULADO (regla de la casa): no existe una segunda fuente "
        "independiente que corrobore el dato exacto por departamento. Se publica con "
        "credibilidad 2, no como dato corroborado.",
    ]
    if dato["espurios"]:
        vacios.append(f"Se descartaron {dato['espurios']} fila(s) agregada(s) con un "
                       "código de departamento que no corresponde a ningún código DANE "
                       "válido (código espurio de la fuente, no de este colector).")
    if len(unidades) < 33:
        vacios.append(f"Cubre {len(unidades)} de 33 departamentos en esta corrida: al "
                       "menos uno no registra hechos en el período, o la fuente no lo "
                       "trae. No se completó a mano.")
    return comun.escribir(
        colector=colector, capa="publico",
        fuente=f"{titulo} — Ministerio de Defensa Nacional / Policía Nacional de Colombia, "
               "vía datos.gov.co (Socrata)",
        url_fuente=url_ficha,
        calificacion=comun.calificar(
            "A", 2, False,
            "Registro administrativo oficial de la Policía Nacional de Colombia, por "
            "departamento. Credibilidad 2: es la única fuente que este registro tiene "
            "para esta figura penal — no hay segunda fuente independiente que corrobore "
            "el dato exacto por departamento; se publica rotulado (regla de la casa de "
            "dos fuentes)."),
        registros=[registro],
        vacios=vacios,
        extra={"resumen": {
            "departamentos": len(unidades), "es_prototipo": True,
            "capa_subnacional": "APAGADA — alimenta la vista preliminar "
                                 "(sitio/subnacional.html), no el mapa principal del índice",
            "consultado": comun.ahora(),
        }},
    )
