# -*- coding: utf-8 -*-
"""Homicidios según la OMS: la segunda fuente, que cuenta de otra manera.

POR QUÉ EXISTE
--------------
El registro publica homicidios de UNODC, compilados por el Banco Mundial, y lo
declara como **fuente única**: «la segunda fuente independiente sería el
registro nacional de cada Estado, que no es comparable entre sí». Por la regla
de la casa, un dato de fuente única no sostiene un juicio de confianza alta.

La Organización Mundial de la Salud publica la misma materia contada de otra
manera. **UNODC cuenta lo que registra la policía; la OMS cuenta lo que
certifica el médico.** Son dos caminos independientes hasta el mismo hecho, y
por eso el dato pasa a estar corroborado.

Y DONDE LAS DOS DIFIEREN, LA DIFERENCIA ES EL HALLAZGO. Un Estado cuya cifra
sanitaria supera con holgura a la policial está diciendo algo sobre su
subregistro policial, y al revés. El registro no interpreta esa brecha: la
muestra y dice qué es cada punta.

LO QUE AGREGA ADEMÁS
--------------------
**Desagregación por sexo**, que el registro no tiene en ninguna materia. La OMS
publica la serie de varones y la de mujeres por separado.

LO QUE ESTA CIFRA NO ES, Y SE DECLARA
--------------------------------------
No es un recuento: es una **estimación** de la OMS a partir de los registros de
hechos vitales de cada Estado, modelada donde ese registro es incompleto. En un
Estado con registro civil endeble la cifra depende más del modelo que del
archivo, y eso no se ve en el número.

LICENCIA — Y POR QUÉ VIAJA PEGADA AL DATO
------------------------------------------
La OMS publica bajo **CC BY-NC-SA 3.0 IGO**. El «no comercial» no estorba: este
registro es gratuito, sin publicidad y sin botón de donaciones. El «compartir
igual» sí obliga: lo derivado de este dato va bajo la misma licencia. Por eso la
restricción se declara en el archivo, la muestra el sitio, y no queda en la
cabeza de nadie.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

import comun
import geo

BASE = "https://ghoapi.azureedge.net/api"
# Tasa por cada 100.000 personas y número de hechos. Los dos, de la misma fuente.
INDICADORES = {"tasa": "VIOLENCE_HOMICIDERATE", "numero": "VIOLENCE_HOMICIDENUM"}
# Los tres cortes que publica la fuente: ambos sexos, varones, mujeres.
SEXOS = {"SEX_BTSX": "total", "SEX_MLE": "varones", "SEX_FMLE": "mujeres"}
INTENTOS = 3
# Argentina y Colombia tienen serie larga en las dos. Si el lector no las halla,
# el que falló es el lector, no la fuente.
CONTROL = ("ARG", "COL")


def _traer(indicador: str) -> list:
    ultimo = None
    for intento in range(INTENTOS):
        if intento:
            time.sleep(2 * intento)
        try:
            peticion = urllib.request.Request(
                f"{BASE}/{indicador}",
                headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
            with urllib.request.urlopen(peticion, timeout=180) as respuesta:
                crudo = json.loads(respuesta.read().decode("utf-8", "replace"))
            valor = crudo.get("value")
            if valor:
                return valor
            ultimo = "la fuente respondió sin filas"
        except Exception as error:  # noqa: BLE001 — se reintenta y, si no, se declara
            ultimo = f"{type(error).__name__}: {error}"
    raise RuntimeError(
        f"La OMS no entregó «{indicador}» en {INTENTOS} intentos: {ultimo}. "
        "NO se publica una serie vacía: la anterior queda intacta.")


def _ordenar(filas: list, isos: set) -> dict:
    """{iso: {corte: [{anio, valor}]}} con los años ordenados y sin repetidos."""
    salida = {}
    for f in filas:
        iso = f.get("SpatialDim")
        if iso not in isos or f.get("SpatialDimType") not in (None, "COUNTRY"):
            continue
        corte = SEXOS.get(f.get("Dim1"))
        anio, valor = f.get("TimeDim"), f.get("NumericValue")
        if corte is None or anio is None or valor is None:
            continue
        salida.setdefault(iso, {}).setdefault(corte, {})[int(anio)] = round(float(valor), 2)
    return {iso: {corte: [{"anio": a, "valor": v} for a, v in sorted(porAnio.items())]
                  for corte, porAnio in cortes.items()}
            for iso, cortes in salida.items()}


def recolectar():
    padron = geo.padron()
    isos = {p["iso"] for p in padron}
    tasas = _ordenar(_traer(INDICADORES["tasa"]), isos)
    numeros = _ordenar(_traer(INDICADORES["numero"]), isos)

    # SE PRUEBA EL LECTOR ANTES DE CREERLE UN VACÍO A NADIE.
    for iso in CONTROL:
        if len(tasas.get(iso, {}).get("total", [])) < 10:
            raise RuntimeError(
                f"La prueba del lector falló: en {iso} no se leyó una serie de al menos "
                "diez años. La interfaz cambió de forma. NO se publica una lectura a ciegas.")
    if not any("mujeres" in c for c in tasas.values()):
        raise RuntimeError(
            "La prueba del lector falló: no se leyó ni un corte por sexo, que es la mitad "
            "de lo que esta fuente agrega. NO se publica una lectura a ciegas.")

    registros, conDato = [], 0
    for p in padron:
        cortes = tasas.get(p["iso"], {})
        serie = cortes.get("total", [])
        if serie:
            conDato += 1
        ultimoNumero = (numeros.get(p["iso"], {}).get("total") or [None])[-1]
        registros.append({
            "iso": p["iso"], "pais": p["pais"], "bloque": p["bloque"],
            "estado": "con_dato" if serie else "sin_dato",
            "tasa": serie[-1] if serie else None,
            "serie": serie,
            "serie_varones": cortes.get("varones", []),
            "serie_mujeres": cortes.get("mujeres", []),
            "numero": ultimoNumero,
        })

    anios = sorted({a["anio"] for r in registros for a in r["serie"]})
    sinDato = [r["iso"] for r in registros if not r["serie"]]
    calificacion = comun.calificar(
        fiabilidad="A", credibilidad=2, corroborado=True,
        nota=("Organismo multilateral sobre los registros de hechos vitales de cada Estado. "
              "Fiabilidad A por el organismo y su metodología publicada. Credibilidad 2 "
              "porque es una estimación construida sobre certificados de defunción, no un "
              "recuento directo. CORROBORA la cifra de UNODC por un camino independiente: "
              "una la registra la policía, la otra la certifica un médico. La corroboración "
              "es de método, no de resultado: hay Estados donde las dos cifras se separan "
              "mucho, y esa separación se muestra en vez de taparse."),
    )
    vacios = [
        "No es un recuento: es una estimación de la OMS a partir de los registros de hechos "
        "vitales, modelada donde ese registro es incompleto. En un Estado con registro civil "
        "endeble la cifra depende más del modelo que del archivo, y eso no se ve en el número.",
        f"La serie llega hasta {anios[-1] if anios else '—'}: no es un dato en vivo y va "
        "algunos años detrás de la cifra policial.",
        (f"Sin dato para {len(sinDato)} Estados del padrón ({', '.join(sinDato)}): la fuente "
         "no publica estimación para ellos.") if sinDato else
        "Los 33 Estados del padrón tienen serie.",
        "Cuando esta cifra y la de UNODC difieren, la diferencia NO se interpreta acá: puede "
        "venir del subregistro policial, de la cobertura del registro civil o de las dos "
        "cosas. El registro muestra las dos y dice qué es cada una.",
        "LA CORROBORACIÓN NO ES ACUERDO. Medido el 9 de septiembre de 2026, en el mismo año "
        "2021 El Salvador tiene 17,3 homicidios por 100.000 según UNODC y 93,8 según la OMS: "
        "cinco veces más. No es un error de lectura ni una diferencia de años: son dos "
        "métodos que en ese Estado no coinciden. Que exista una segunda fuente permite VER "
        "la brecha; no la resuelve, y el registro no elige cuál tiene razón.",
        "El corte por sexo es el que publica la fuente —varones y mujeres—: no hay otras "
        "categorías disponibles en esta serie.",
    ]
    return comun.escribir(
        colector="oms_homicidios",
        capa="publico",
        fuente="Observatorio Mundial de la Salud — Organización Mundial de la Salud (OMS)",
        url_fuente="https://www.who.int/data/gho",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        restriccion="no_comercial_compartir_igual",
        extra={
            "resumen": {
                "estados_con_dato": conDato,
                "estados_del_padron": len(registros),
                "anios": anios,
                "cortes": ["total", "varones", "mujeres"],
                "lector_probado": True,
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("oms_homicidios", recolectar)
