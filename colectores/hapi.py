# -*- coding: utf-8 -*-
"""HDX HAPI: población, pobreza y riesgo, por unidad de primer orden.

QUÉ RESUELVE, Y POR QUÉ ERA LO QUE FALTABA
--------------------------------------------
Tres cosas que el registro venía necesitando y no tenía:

  · **La población de cada unidad de primer orden.** Sin ese denominador, los
    recuentos subnacionales —homicidios por provincia, por ejemplo— no se pueden
    convertir en tasas, y sin tasa una provincia grande siempre parece la peor.
    Ninguna de las fuentes anteriores lo daba: el tercer archivo de Global Data
    Lab resultó ser porcentaje urbano, no total de habitantes.

  · **Pobreza multidimensional por unidad**, que es una pregunta que la Dirección
    hizo expresamente y que hasta ahora se contestaba solo a escala de país.

  · **El riesgo INFORM de los 33**, a escala nacional, con sus tres componentes
    separados: exposición a amenazas, vulnerabilidad y capacidad de respuesta.

Y encima **tapa dos de los cuatro agujeros de Global Data Lab**: el Ecuador y El
Salvador, que allá aparecían medidos por regiones de encuesta —«Sierra»,
«Oriental»—, acá vienen por provincia y por departamento.

SOBRE EL IDENTIFICADOR
-----------------------
La interfaz exige un identificador de aplicación y **no es una credencial**: es
el nombre de quien consulta y un correo, en base64, que la propia fuente arma en
una página suya. No da acceso a nada privado ni tiene cupo asignado; sirve para
que sepan quién los usa. Igual se lee del entorno y no se escribe acá, porque un
correo dentro de un repositorio público es un correo que van a cosechar.

LO QUE ESTE COLECTOR NO TRAE TODAVÍA
-------------------------------------
Los hechos de conflicto —que la fuente sí publica, y que darían eje Seguridad
subnacional en Colombia, Venezuela y Haití— vienen **por municipio y por mes**,
desagregados por tipo de hecho. Son decenas de miles de renglones por país: hay
que sumarlos a provincia y a año antes de guardarlos, y eso merece su propio
recorrido para no volver lento al robot de cada hora. Queda anotado, no olvidado.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402
from cotejo import cubre, sello  # noqa: E402

COLECTOR = "hapi"
CAPA = "publico"

BASE = "https://hapi.humdata.org/api/v2"
TOPE = 1000          # lo máximo que la fuente entrega por consulta
SECRETO = "HDX_HAPI_APP"


def identificador() -> str:
    v = (os.environ.get(SECRETO) or "").strip()
    if not v:
        raise RuntimeError(
            f"falta la variable {SECRETO}. No es una credencial: es el nombre de quien "
            "consulta y un correo, en base64, que arma la propia fuente en "
            "https://hapi.humdata.org/docs. Se carga como secreto del repositorio para no "
            "dejar el correo escrito en un archivo público.")
    return v


def traer(ruta: str, **filtros) -> list:
    """Todas las filas de un recorrido, de a mil, hasta que se terminan.

    SE PIDE EL MUNDO ENTERO Y SE FILTRA ACÁ, y no país por país, que era lo
    primero que se probó: 66 consultas seguidas hacen que la fuente corte por
    exceso de pedidos, y con razón. El mundo entero son seis consultas, así que
    pedir de más resulta ser pedir menos.

    Y si aun así corta, se espera y se reintenta: un servicio público que dice
    «más despacio» está pidiendo cortesía, no anunciando una falla.
    """
    filas, desde = [], 0
    while True:
        consulta = dict(filtros, output_format="json", limit=TOPE, offset=desde,
                        app_identifier=identificador())
        url = f"{BASE}/{ruta}?" + urllib.parse.urlencode(consulta)
        peticion = urllib.request.Request(
            url, headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
        for intento in range(6):
            try:
                with urllib.request.urlopen(peticion, timeout=180) as respuesta:
                    lote = json.loads(
                        respuesta.read().decode("utf-8", "replace")).get("data") or []
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or intento == 5:
                    raise
                time.sleep(3 * (intento + 1))
        filas += lote
        if len(lote) < TOPE:
            return filas
        desde += TOPE
        time.sleep(1)


def _anio(fila: dict) -> int | None:
    t = fila.get("reference_period_start") or ""
    return int(t[:4]) if t[:4].isdigit() else None


def por_estado(filas: list, isos: set) -> dict:
    """Reparte las filas del mundo entre los Estados del padrón."""
    d = {}
    for f in filas:
        if f.get("location_code") in isos:
            d.setdefault(f["location_code"], []).append(f)
    return d


def poblacion_de(filas: list) -> list:
    """Habitantes por unidad. Se pide el total ya sumado por la fuente.

    Se exige «todas las edades y todos los géneros»: la fuente entrega la
    población partida en tramos, y sumar los tramos a mano corre el riesgo de
    contar dos veces a quien aparece en el total y en su tramo. Si un Estado no
    tiene ese renglón total, se declara sin población y no se inventa una suma.
    """
    ultimo = {}
    for f in filas:
        clave, anio = f.get("admin1_code"), _anio(f)
        if not clave or anio is None or f.get("population") is None:
            continue
        if clave not in ultimo or anio > ultimo[clave]["anio"]:
            ultimo[clave] = {"codigo": clave, "unidad": f.get("admin1_name"),
                             "habitantes": int(f["population"]), "anio": anio}
    return sorted(ultimo.values(), key=lambda x: x["unidad"] or "")


def pobreza_de(filas: list) -> list:
    """Pobreza multidimensional por unidad, en su medición más reciente."""
    ultimo = {}
    for f in filas:
        clave, anio = f.get("admin1_code"), _anio(f)
        if not clave or anio is None or f.get("headcount_ratio") is None:
            continue
        if clave not in ultimo or anio > ultimo[clave]["anio"]:
            ultimo[clave] = {
                "codigo": clave, "unidad": f.get("admin1_name"), "anio": anio,
                "hasta": (f.get("reference_period_end") or "")[:4],
                "pobres_por_ciento": f.get("headcount_ratio"),
                "indice": f.get("mpi"),
                "intensidad": f.get("intensity_of_deprivation"),
                "pobreza_severa_por_ciento": f.get("in_severe_poverty"),
                "vulnerables_por_ciento": f.get("vulnerable_to_poverty"),
            }
    return sorted(ultimo.values(), key=lambda x: x["unidad"] or "")


def padron_de_unidades() -> dict:
    ruta = comun.DATOS / "publico" / "unidades.json"
    if not ruta.exists():
        return {}
    d = json.loads(ruta.read_text(encoding="utf-8"))
    return {r["iso"]: {sello(x.get("nombre")): x.get("nombre")
                       for x in (r.get("lista") or []) if x.get("nombre")}
            for r in d.get("registros", [])}


def _acomodar(lista: list, propio: dict) -> list:
    """Le pone a cada renglón de la fuente la unidad del padrón que le toca."""
    salida = []
    for x in lista:
        cubiertas, clase, enumera, entero = cubre(x.get("unidad") or "", propio)
        salida.append(dict(x, clase=clase, cubre=cubiertas,
                           lugares_que_nombra=enumera, identificado_entero=entero))
    return salida


def construir() -> Path:
    padron = {p["iso"]: p for p in geo.padron()}
    unidades = padron_de_unidades()
    if not unidades:
        raise RuntimeError("falta datos/publico/unidades.json: sin padrón no se puede cotejar")

    riesgo = {}
    for f in traer("coordination-context/national-risk"):
        if f.get("location_code") in padron:
            riesgo[f["location_code"]] = {
                "anio": _anio(f), "clase": f.get("risk_class"),
                "puesto_mundial": f.get("global_rank"),
                "riesgo": f.get("overall_risk"),
                "exposicion": f.get("hazard_exposure_risk"),
                "vulnerabilidad": f.get("vulnerability_risk"),
                "capacidad_de_respuesta": f.get("coping_capacity_risk"),
            }

    poblacion_mundo = por_estado(traer("geography-infrastructure/baseline-population",
                                       admin_level=1, gender="all", age_range="all"), set(padron))
    pobreza_mundo = por_estado(traer("food-security-nutrition-poverty/poverty-rate",
                                     admin_level=1), set(padron))

    registros, con_poblacion, con_pobreza = [], 0, 0
    for iso in sorted(padron):
        propio = unidades.get(iso) or {}
        pobl = _acomodar(poblacion_de(poblacion_mundo.get(iso) or []), propio)
        pobr = _acomodar(pobreza_de(pobreza_mundo.get(iso) or []), propio)
        # Un solo renglón es el país entero disfrazado de unidad: la fuente
        # devuelve el nivel nacional cuando no tiene desagregación. No cuenta.
        hay_pobl = len(pobl) > 1
        hay_pobr = len(pobr) > 1
        con_poblacion += hay_pobl
        con_pobreza += hay_pobr

        # Solo cuenta lo que de veras se conserva: si la fuente devolvió el país
        # entero disfrazado de unidad, ese renglón no cubre a nadie.
        alcanzadas = {x for lista in (pobl if hay_pobl else [], pobr if hay_pobr else [])
                      for f in lista if f["identificado_entero"] for x in f["cubre"]}
        registros.append({
            "iso": iso,
            "pais": padron[iso]["pais"],
            "bloque": padron[iso].get("bloque"),
            "unidades_del_padron": len(propio),
            "unidades_alcanzadas": len(alcanzadas),
            "unidades_sin_dato": sorted(set(propio.values()) - alcanzadas),
            "poblacion_por_unidad": pobl if hay_pobl else [],
            "pobreza_por_unidad": pobr if hay_pobr else [],
            "anio_poblacion": max((x["anio"] for x in pobl), default=None) if hay_pobl else None,
            "anios_pobreza": sorted({x["anio"] for x in pobr}) if hay_pobr else [],
            "riesgo_del_pais": riesgo.get(iso),
        })

    sin_pobl = sorted(r["pais"] for r in registros if not r["poblacion_por_unidad"])
    anios = sorted({a for r in registros for a in r["anios_pobreza"]})

    vacios = [
        f"{con_poblacion} Estados de 33 tienen población por unidad de primer orden. Los "
        "otros solo la tienen a escala de país, y en ellos un recuento subnacional NO se "
        "puede convertir en tasa: se publica el recuento y se dice por qué. Sin dato por "
        "unidad: " + ", ".join(sin_pobl) + ".",
        f"{con_pobreza} Estados tienen pobreza por unidad. LAS MEDICIONES NO SON DEL MISMO "
        f"AÑO —van de {anios[0]} a {anios[-1]} según el país— así que **no se comparan "
        "unidades de países distintos**: solo unidades del mismo país entre sí, y cada una "
        "con el año de su medición a la vista." if anios else
        f"{con_pobreza} Estados tienen pobreza por unidad.",
        "La pobreza acá es MULTIDIMENSIONAL: mide privaciones en salud, educación y nivel "
        "de vida, no ingreso. Un hogar puede estar sobre la línea de pobreza por ingreso y "
        "ser pobre en esta medición, y al revés. No reemplaza a la pobreza monetaria que "
        "publica cada Estado.",
        "La población por unidad es una ESTIMACIÓN o proyección, no un censo del año que "
        "figura. Sirve de denominador; no es un recuento de personas contadas.",
        "El riesgo INFORM va solo a escala de país: la fuente no lo desagrega. Se publica "
        "con sus tres componentes separados porque el número solo, sin ellos, no dice si el "
        "riesgo viene de la amenaza o de la falta de capacidad para responderle.",
        "Los hechos de conflicto que esta fuente publica NO están acá: vienen por municipio "
        "y por mes, y hay que sumarlos a unidad y a año antes de guardarlos. Darían eje "
        "Seguridad subnacional en Colombia, Venezuela y Haití, y quedan pendientes.",
    ]

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="HDX HAPI — Oficina de Coordinación de Asuntos Humanitarios de las Naciones "
               "Unidas (OCHA): población base, pobreza multidimensional y riesgo INFORM",
        url_fuente="https://hapi.humdata.org/",
        calificacion=comun.calificar(
            "A", 2, False,
            "Interfaz oficial de Naciones Unidas que redistribuye datos de productores "
            "identificados —oficinas de estadística, Universidad de Oxford, Comisión "
            "Europea— con su procedencia declarada renglón por renglón. No es el productor "
            "original, y por eso la corroboración no baja de 2 pero tampoco llega a 1."),
        registros=registros,
        vacios=vacios,
        extra={"resumen": {
            "estados_del_padron": len(padron),
            "con_poblacion_por_unidad": con_poblacion,
            "con_pobreza_por_unidad": con_pobreza,
            "con_riesgo_del_pais": len(riesgo),
        }},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
