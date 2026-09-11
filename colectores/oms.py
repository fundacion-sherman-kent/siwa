# -*- coding: utf-8 -*-
"""OMS: muertes que el registro no contaba, y la vida que se espera vivir.

QUÉ TRAE, Y POR QUÉ ES DISTINTO DE LO QUE YA HABÍA
-----------------------------------------------------
El registro contaba muertes violentas de una sola clase: el homicidio. Pero en
la región se muere de otras maneras que tampoco son accidentes del azar, y que
ningún organismo de seguridad cuenta porque no son delitos:

  · **Suicidio**, que en varios Estados del padrón mata más gente que el
    homicidio y no aparece en ninguna estadística criminal.
  · **Muertes de tránsito**, que son la principal causa de muerte violenta entre
    jóvenes y se leen como accidente cuando son en buena medida una cuestión de
    reglas, control y carretera.
  · **Mortalidad materna**, que es la medida más dura que existe de si un Estado
    llega o no llega con lo básico.
  · **Esperanza de vida**, que es el resumen de todo lo anterior.

QUÉ NO TRAE, Y ES A PROPÓSITO
-------------------------------
No trae homicidios. El registro ya los tiene de **tres fuentes** —Banco Mundial,
comisión regional y esta misma casa por otra vía—, y agregar una cuarta no
corrobora nada nuevo.

UNA ADVERTENCIA QUE VALE PARA LAS CUATRO
------------------------------------------
**Son estimaciones, no recuentos.** La OMS modela a partir de los registros de
defunción de cada Estado, corrigiendo por subregistro y por causas mal
clasificadas. Donde el registro civil es flojo, la corrección es grande: la
cifra es la mejor disponible y no es un conteo.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "oms"
CAPA = "publico"

BASE = "https://ghoapi.azureedge.net/api"
AMBOS = "SEX_BTSX"   # el total: sin esto se contarían tres veces los mismos muertos

ORIGEN = "Observatorio Mundial de la Salud — Organización Mundial de la Salud (OMS)"

MEDIDAS = [
    {"clave": "suicidio", "codigo": "SDGSUICIDE", "sexo": AMBOS,
     "rotulo": "Suicidio", "eje": "Seguridad",
     "unidad": "por cada 100.000 personas", "mas_es_peor": True,
     "cautela": "MATERIA NUEVA: el registro contaba homicidios y no esto, y en varios "
                "Estados del padrón el suicidio mata más gente que el homicidio. No "
                "aparece en ninguna estadística criminal porque no es un delito. Es una "
                "ESTIMACIÓN modelada sobre registros de defunción, con corrección por "
                "subregistro: donde el registro civil es flojo, la corrección es grande."},
    {"clave": "muertes_transito", "codigo": "RS_198", "sexo": None,
     "rotulo": "Muertes de tránsito", "eje": "Seguridad",
     "unidad": "por cada 100.000 personas", "mas_es_peor": True,
     "cautela": "Principal causa de muerte violenta entre jóvenes en la región. Se lee "
                "como accidente y es en buena medida una cuestión de reglas, control y "
                "carretera. UN SOLO AÑO: la fuente publica esta medida por ronda y no "
                "todos los años, así que no hay serie para ver si mejora o empeora."},
    {"clave": "mortalidad_materna", "codigo": "MDG_0000000026", "sexo": None,
     "rotulo": "Mortalidad materna", "eje": "Desarrollo",
     "unidad": "por cada 100.000 nacidos vivos", "mas_es_peor": True,
     "cautela": "La medida más dura de si un Estado llega o no llega con lo básico: son "
                "muertes evitables casi en su totalidad. Es una estimación de un grupo "
                "interinstitucional, no un recuento, y en los Estados chicos del Caribe "
                "el número de casos es tan bajo que un año cualquiera salta mucho sin que "
                "haya cambiado nada."},
    {"clave": "esperanza_vida", "codigo": "WHOSIS_000001", "sexo": AMBOS,
     "rotulo": "Esperanza de vida al nacer", "eje": "Desarrollo",
     "unidad": "años", "mas_es_peor": False,
     "cautela": "El resumen de todo lo demás: cuánto vive en promedio quien nace hoy si "
                "las condiciones no cambian. NO es una predicción sobre nadie en "
                "particular. La serie llega hasta 2021 e incluye el golpe de la pandemia, "
                "que en la región fue grande: comparar 2021 con 2019 no describe una "
                "tendencia."},
]


def pedir(codigo: str) -> list:
    peticion = urllib.request.Request(
        f"{BASE}/{codigo}", headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=240) as respuesta:
        d = json.loads(respuesta.read().decode("utf-8", "replace"))
    return d.get("value") or []


def series(filas: list, m: dict, del_padron: set) -> dict:
    crudo = {}
    for x in filas:
        if x.get("SpatialDimType") != "COUNTRY":
            continue
        if m["sexo"] and x.get("Dim1") != m["sexo"]:
            continue
        iso, anio, valor = x.get("SpatialDim"), x.get("TimeDim"), x.get("NumericValue")
        if iso not in del_padron or valor is None:
            continue
        try:
            crudo.setdefault(iso, {})[int(anio)] = round(float(valor), 3)
        except (TypeError, ValueError):
            continue
    return {i: sorted(v.items()) for i, v in crudo.items()}


def ficha(serie: list) -> dict:
    anio, valor = serie[-1]
    anterior = serie[-2] if len(serie) >= 2 else None
    variacion = (round((valor - anterior[1]) / abs(anterior[1]) * 100, 1)
                 if anterior and anterior[1] else None)
    ventana = (round((valor - serie[0][1]) / abs(serie[0][1]) * 100, 1)
               if len(serie) >= 3 and serie[0][1] else None)
    return {"valor": valor, "anio": anio,
            "anio_anterior": anterior[0] if anterior else None,
            "valor_anterior": anterior[1] if anterior else None,
            "variacion_pct": variacion,
            "anio_inicial": serie[0][0], "valor_inicial": serie[0][1],
            "tendencia_ventana_pct": ventana,
            "serie": [{"anio": a, "valor": v} for a, v in serie]}


def construir() -> Path:
    padron = geo.padron()
    del_padron = {p["iso"] for p in padron}

    datos, caidos = {}, []
    for m in MEDIDAS:
        try:
            datos[m["clave"]] = series(pedir(m["codigo"]), m, del_padron)
        except Exception as error:  # noqa: BLE001 — la medida caída se declara
            caidos.append(f"{m['rotulo']}: {type(error).__name__}")
            datos[m["clave"]] = {}

    if not any(datos.values()):
        raise RuntimeError("ninguna medida devolvió serie. No se escribe nada.")

    registros, cobertura = [], {}
    for p in padron:
        f = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        for m in MEDIDAS:
            s = datos[m["clave"]].get(p["iso"])
            if s:
                f["indicadores"][m["clave"]] = ficha(s)
                cobertura[m["clave"]] = cobertura.get(m["clave"], 0) + 1
        if f["indicadores"]:
            registros.append(f)

    publicables = [m for m in MEDIDAS if cobertura.get(m["clave"], 0)]
    for m in MEDIDAS:
        if not cobertura.get(m["clave"], 0):
            caidos.append(f"{m['rotulo']}: la fuente no dejó un solo Estado del padrón")
    fuera = {m["clave"] for m in MEDIDAS} - {m["clave"] for m in publicables}
    for f in registros:
        for c in fuera:
            f["indicadores"].pop(c, None)
    registros = [r for r in registros if r["indicadores"]]
    registros.sort(key=lambda r: r["pais"])

    sin_dato = sorted(p["pais"] for p in padron
                      if p["iso"] not in {r["iso"] for r in registros})
    anios = sorted({x["anio"] for r in registros for x in r["indicadores"].values()})

    vacios = [
        "SON ESTIMACIONES, NO RECUENTOS. La fuente modela a partir de los registros de "
        "defunción de cada Estado, corrigiendo por subregistro y por causas mal "
        "clasificadas. Donde el registro civil es flojo, la corrección es grande: la cifra "
        "es la mejor disponible y no es un conteo.",
        "NO SE PUBLICAN HOMICIDIOS POR ESTA VÍA, y no es un olvido: el registro ya los "
        "tiene de tres fuentes distintas, y una cuarta no corrobora nada nuevo.",
        "El suicidio no aparece en ninguna estadística criminal porque no es un delito, y "
        "en varios Estados del padrón mata más gente que el homicidio. Contar solo "
        "homicidios describe una parte de la muerte violenta.",
        "En los Estados chicos del Caribe, el número de casos de mortalidad materna es tan "
        "bajo que un año cualquiera salta mucho sin que haya cambiado nada. Se lee la serie "
        "entera, no el último punto.",
        "La esperanza de vida llega hasta 2021 e incluye el golpe de la pandemia, que en la "
        "región fue grande: comparar 2021 con 2019 no describe una tendencia.",
    ]
    if sin_dato:
        vacios.append(f"{len(sin_dato)} Estados sin ninguna de estas medidas: "
                      + ", ".join(sin_dato) + ".")
    vacios.extend(caidos)

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente=ORIGEN,
        url_fuente="https://www.who.int/data/gho",
        calificacion=comun.calificar(
            "B", 2, False,
            "Organismo multilateral que modela sobre los registros de defunción de cada "
            "Estado con metodología publicada. No es el productor original —lo es cada "
            "registro civil— y por eso no sube de B; responde siempre y con serie larga, "
            "y por eso la corroboración es 2."),
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": [{"clave": m["clave"], "rotulo": m["rotulo"], "eje": m["eje"],
                             "unidad": m["unidad"], "mas_es_peor": m["mas_es_peor"],
                             "origen": ORIGEN, "cautela": m["cautela"]}
                            for m in publicables],
            "cobertura": cobertura,
            "ventana_anios": [anios[0], anios[-1]] if anios else None,
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
