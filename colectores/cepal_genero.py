# -*- coding: utf-8 -*-
"""Femicidios y violencia contra la mujer: el hueco más grande que quedaba.

POR QUÉ EXISTE
--------------
El registro no medía **nada** de violencia de género. Ninguna de sus 40 fuentes
la publica de forma comparable para los 33, y por eso la materia no existía: ni
como dato ni como vacío del que se pudiera decir dónde buscarlo.

La CEPAL sí la publica, y con la autoridad de ser el organismo estadístico de
Naciones Unidas para la región: su **Observatorio de Igualdad de Género de
América Latina y el Caribe** recopila la cifra que cada Estado informa, y la
sirve por una interfaz abierta con el código ISO de cada país adentro.

QUÉ ENTRA, Y POR QUÉ ESTOS
---------------------------
- **Tasa de femicidios o feminicidios** por cada 100.000 mujeres. Es la única
  medida comparable de la forma más extrema de esa violencia.
- **Ocupación carcelaria** sobre la capacidad oficial. El registro tenía presos
  sin condena, que dice quién espera juicio; no tenía hacinamiento, que dice en
  qué condiciones espera.

LO QUE ESTA CIFRA NO ES, Y SE DECLARA
--------------------------------------
El femicidio **no se define igual en todos los Estados**. Algunos cuentan solo
el homicidio cometido por la pareja o expareja; otros incluyen todo asesinato de
una mujer por razones de género. La CEPAL lo advierte y este registro lo repite:
la comparación entre Estados es indicativa, no exacta, y una cifra baja puede
significar menos casos o una definición más estrecha.

CÓMO SE LEE LA INTERFAZ
------------------------
Cada indicador trae sus dimensiones —país, año y a veces alguna más— y sus
filas apuntan a los miembros por identificador. El colector arma el diccionario
de cada dimensión y traduce. **Si un indicador tiene una dimensión que el
colector no sabe resolver, no se publica a medias: se descarta y se declara.**
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

import comun
import geo

BASE = "https://api-cepalstat.cepal.org/cepalstat/api/v1"
INTENTOS = 3

# Los indicadores elegidos, con la clave con que viajan al registro.
INDICADORES = [
    {"id": 2812, "clave": "femicidios",
     "rotulo": "Femicidios o feminicidios",
     "unidad": "por cada 100.000 mujeres", "mas_es_peor": True},
    {"id": 4143, "clave": "ocupacion_carcelaria",
     "rotulo": "Ocupación carcelaria sobre la capacidad oficial",
     "unidad": "% de la capacidad oficial", "mas_es_peor": True},
]
# Los Estados que la fuente agrega —«América Latina», «El Caribe»— no son
# Estados: se descartan por no estar en el padrón, sin ruido.
CONTROL = "femicidios"


def _pedir(ruta: str) -> dict:
    ultimo = None
    for intento in range(INTENTOS):
        if intento:
            time.sleep(2 * intento)
        try:
            peticion = urllib.request.Request(
                f"{BASE}/{ruta}", headers={"User-Agent": comun.AGENTE,
                                           "Accept": "application/json"})
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                return json.loads(respuesta.read().decode("utf-8", "replace"))
        except Exception as error:  # noqa: BLE001 — se reintenta y, si no, se declara
            ultimo = f"{type(error).__name__}: {error}"
    raise RuntimeError(f"CEPALSTAT no respondió «{ruta}» en {INTENTOS} intentos: {ultimo}. "
                       "NO se publica una serie vacía: la anterior queda intacta.")


def _anios(dimensiones: list) -> tuple:
    """El diccionario {id de miembro: año} y el nombre de su dimensión."""
    for d in dimensiones:
        nombre = str(d.get("name") or "")
        if "Años" in nombre or "Anios" in nombre or "Year" in nombre:
            mapa = {}
            for m in d.get("members") or []:
                texto = str(m.get("name") or "")
                if texto.isdigit():
                    mapa[m.get("id")] = int(texto)
            return mapa, d.get("dim_id") or d.get("id")
    return {}, None


def _serie(indicador: dict, isos: set) -> tuple:
    """{iso: [{anio, valor}]} para un indicador, y lo que no se pudo resolver."""
    cuerpo = _pedir(f"indicator/{indicador['id']}/data?lang=es&format=json").get("body") or {}
    dims = cuerpo.get("dimensions") or []
    porAnio, _ = _anios(dims)
    if not porAnio:
        return {}, "no se halló la dimensión de años"

    # Las dimensiones que no son país ni año: solo se aceptan si la fila trae el
    # miembro que agrega el total. Si no se puede resolver, no se publica.
    otras = []
    for d in dims:
        nombre = str(d.get("name") or "")
        if "País" in nombre or "Pais" in nombre or "Años" in nombre:
            continue
        totales = {m.get("id") for m in (d.get("members") or [])
                   if str(m.get("name") or "").strip().lower() in
                   ("total", "ambos sexos", "total nacional", "ambos")}
        if not totales:
            return {}, f"tiene la dimensión «{nombre}» y ningún miembro que agregue el total"
        otras.append(totales)

    salida = {}
    for fila in cuerpo.get("data") or []:
        iso = fila.get("iso3")
        if iso not in isos:
            continue
        anio = next((porAnio[v] for k, v in fila.items()
                     if k.startswith("dim_") and v in porAnio), None)
        if anio is None:
            continue
        if otras:
            valores = {v for k, v in fila.items() if k.startswith("dim_")}
            if not all(valores & t for t in otras):
                continue
        try:
            valor = float(str(fila.get("value")).replace(",", "."))
        except (TypeError, ValueError):
            continue
        salida.setdefault(iso, {})[anio] = round(valor, 2)
    return ({iso: [{"anio": a, "valor": v} for a, v in sorted(por.items())]
             for iso, por in salida.items()}, None)


def recolectar():
    padron = geo.padron()
    isos = {p["iso"] for p in padron}
    series, descartados = {}, []
    for ind in INDICADORES:
        serie, porque = _serie(ind, isos)
        if porque:
            descartados.append(f"{ind['rotulo']}: {porque}")
            continue
        series[ind["clave"]] = serie

    # SE PRUEBA EL LECTOR ANTES DE CREERLE UN VACÍO A NADIE.
    if len(series.get(CONTROL, {})) < 10:
        raise RuntimeError(
            "La prueba del lector falló: se leyeron menos de diez Estados con tasa de "
            "femicidios, y la fuente publica muchos más. La interfaz cambió de forma. "
            "NO se publica una lectura a ciegas.")

    registros, conAlguno = [], 0
    for p in padron:
        fila = {"iso": p["iso"], "pais": p["pais"], "bloque": p["bloque"], "indicadores": {}}
        for ind in INDICADORES:
            serie = series.get(ind["clave"], {}).get(p["iso"])
            if not serie:
                continue
            fila["indicadores"][ind["clave"]] = {
                "valor": serie[-1]["valor"], "anio": serie[-1]["anio"], "serie": serie,
                "valor_anterior": serie[-2]["valor"] if len(serie) > 1 else None,
                "anio_anterior": serie[-2]["anio"] if len(serie) > 1 else None,
            }
        fila["estado"] = "con_dato" if fila["indicadores"] else "sin_dato"
        if fila["indicadores"]:
            conAlguno += 1
        registros.append(fila)

    cobertura = {ind["clave"]: sum(1 for r in registros if ind["clave"] in r["indicadores"])
                 for ind in INDICADORES}
    publicables = [i for i in INDICADORES if cobertura.get(i["clave"], 0) > 0]
    if not publicables:
        raise RuntimeError("Ningún indicador quedó con un solo Estado. NO se publica un "
                           "archivo hueco: el anterior queda intacto.")

    calificacion = comun.calificar(
        fiabilidad="A", credibilidad=2, corroborado=False,
        nota=("Comisión Económica para América Latina y el Caribe, organismo estadístico de "
              "Naciones Unidas para la región, sobre lo que informa cada Estado a su "
              "Observatorio de Igualdad de Género. Fiabilidad A por el organismo y su "
              "metodología publicada. Credibilidad 2 porque el dato lo produce cada Estado "
              "con su propia definición legal, y la CEPAL lo recopila sin homologarlo."),
    )
    vacios = [
        "EL FEMICIDIO NO SE DEFINE IGUAL EN TODOS LOS ESTADOS. Algunos cuentan solo el "
        "homicidio cometido por la pareja o la expareja; otros, todo asesinato de una mujer "
        "por razones de género. La comparación entre Estados es indicativa, no exacta: una "
        "cifra baja puede significar menos casos o una definición más estrecha.",
        "Es la cifra que cada Estado informa. Donde el sistema judicial no tipifica el "
        "femicidio, o no lo registra aparte del homicidio, la cifra no existe o queda corta.",
        "Serie anual con rezago: no es un dato en vivo.",
        f"Cobertura del padrón: " + " · ".join(
            f"{i['rotulo']}, {cobertura.get(i['clave'], 0)} de {len(registros)} Estados"
            for i in publicables) + ".",
    ] + ([f"Indicadores que la fuente publica y este colector NO pudo leer: "
          + "; ".join(descartados) + "."] if descartados else [])

    return comun.escribir(
        colector="cepal_genero",
        capa="publico",
        fuente="CEPALSTAT — Comisión Económica para América Latina y el Caribe (CEPAL), "
               "Observatorio de Igualdad de Género de América Latina y el Caribe",
        url_fuente="https://oig.cepal.org",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": [{"clave": i["clave"], "rotulo": i["rotulo"], "unidad": i["unidad"],
                             "mas_es_peor": i["mas_es_peor"], "eje": "Seguridad",
                             "origen": "CEPAL, Observatorio de Igualdad de Género",
                             "cepalstat_id": i["id"]}
                            for i in publicables],
            "resumen": {
                "estados_con_algun_dato": conAlguno,
                "estados_del_padron": len(registros),
                "cobertura": cobertura,
                "lector_probado": True,
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("cepal_genero", recolectar)
