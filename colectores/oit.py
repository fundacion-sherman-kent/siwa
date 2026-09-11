# -*- coding: utf-8 -*-
"""OIT: la segunda fuente del bloque laboral, que hasta hoy tenía una sola.

POR QUÉ ESTE COLECTOR Y NO OTRO
---------------------------------
La regla de la casa pide dos fuentes por dato. Medido por el control que la
vigila: **20 de los 31 asuntos del registro tienen un solo productor**, y el
bloque laboral —empleo informal, desempleo juvenil— era uno de ellos, sostenido
únicamente por el Banco Mundial.

Esta fuente mide lo mismo con otra mano: la Organización Internacional del
Trabajo armoniza las encuestas de hogares de cada Estado con su propia
metodología. **No es la misma cifra con otro sello**: cuando las dos difieren,
la diferencia es un dato sobre cómo se mide, no un error de ninguna.

LA TRAMPA QUE ESTE COLECTOR EVITA
-----------------------------------
**La fuente publica hasta 2027.** Son proyecciones, no mediciones. Y tampoco
entra el año en curso, que todavía no terminó: también es una estimación.
Se corta en el último año cerrado y se declara cuántos puntos quedaron afuera.

Las dimensiones vienen desagregadas por sexo y por tramo de edad. Se toma el
total de ambos, y se dice cuál: quien quiera el detalle por sexo lo tiene en la
fuente, y este registro no lo publica a medias.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "oit"
CAPA = "publico"

BASE = "https://rplumber.ilo.org/data/indicator/"
DESDE = 2000
# EL AÑO EN CURSO TAMPOCO ENTRA, no solo el futuro. La fuente publica un valor
# para el año que todavía no terminó, y es una estimación: ponerlo al lado de
# años cerrados haría ver un movimiento que nadie midió. Es la misma regla que
# este registro ya aplica a las series que una fuente publica mes a mes.
HASTA = datetime.now(timezone.utc).year - 1

ORIGEN = ("Organización Internacional del Trabajo — ILOSTAT, armonización de las "
          "encuestas de hogares de cada Estado")

MEDIDAS = [
    {"clave": "empleo_informal_oit", "codigo": "SDG_0831_SEX_ECO_RT_A",
     "sexo": "SEX_T", "clasif": "ECO_SECTOR_TOTAL",
     "rotulo": "Empleo informal · segunda fuente", "eje": "Desarrollo",
     "unidad": "% del empleo total", "mas_es_peor": True,
     "cautela": "ES UNA SEGUNDA MEDICIÓN de algo que el registro ya publica con el Banco "
                "Mundial, y por eso está: dos fuentes que miden lo mismo permiten ver si "
                "coinciden. Si difieren, ninguna está mal: armonizan las encuestas de "
                "hogares con reglas distintas, y esa diferencia es un dato sobre cómo se "
                "mide. Es el total de ambos sexos y de todos los sectores."},
    {"clave": "desempleo_joven_oit", "codigo": "UNE_2EAP_SEX_AGE_RT_A",
     "sexo": "SEX_T", "clasif": "AGE_YTHADULT_Y15-24",
     "rotulo": "Desempleo juvenil · segunda fuente", "eje": "Desarrollo",
     "unidad": "% de los jóvenes de 15 a 24 activos", "mas_es_peor": True,
     "cautela": "Segunda medición del desempleo entre 15 y 24 años, que el registro ya "
                "publica con el Banco Mundial. Cuenta a quien BUSCA trabajo y no encuentra: "
                "quien dejó de buscar no figura, y en la región eso es mucha gente."},
    {"clave": "desempleo_oit", "codigo": "UNE_DEAP_SEX_AGE_RT_A",
     "sexo": "SEX_T", "clasif": "AGE_YTHADULT_YGE15",
     "rotulo": "Desempleo", "eje": "Desarrollo",
     "unidad": "% de la población activa", "mas_es_peor": True,
     "cautela": "Materia nueva: el registro medía el desempleo juvenil y no el total. "
                "Cuenta a quien BUSCA trabajo y no encuentra, de 15 años en adelante. Un "
                "desempleo bajo con empleo informal alto no es una buena noticia: significa "
                "que la gente trabaja, pero sin registro ni derechos. Las dos se leen juntas."},
]


def pedir(codigo: str, areas: list) -> list:
    url = f"{BASE}?id={codigo}&ref_area={'+'.join(areas)}&format=.json"
    peticion = urllib.request.Request(
        url, headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=300) as respuesta:
        d = json.loads(respuesta.read().decode("utf-8", "replace"))
    return d if isinstance(d, list) else []


def series(filas: list, m: dict, del_padron: set) -> tuple:
    """{iso: [(año, valor)]} y cuántos puntos se dejaron afuera por ser del futuro."""
    crudo, futuros = {}, 0
    for x in filas:
        if x.get("sex") != m["sexo"] or x.get("classif1") != m["clasif"]:
            continue
        iso, anio, valor = x.get("ref_area"), x.get("time"), x.get("obs_value")
        if iso not in del_padron or valor is None:
            continue
        try:
            anio, valor = int(str(anio)[:4]), round(float(valor), 3)
        except (TypeError, ValueError):
            continue
        if anio > HASTA:
            futuros += 1      # proyección: no es una medición y no entra
            continue
        if anio < DESDE:
            continue
        # Un mismo año puede venir de más de una encuesta. Se conserva el último
        # que llega, que es el que la fuente ordena al final, y se declara que
        # puede haber más de una medición por año.
        crudo.setdefault(iso, {})[anio] = valor
    return {i: sorted(v.items()) for i, v in crudo.items()}, futuros


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
    isos = sorted(p["iso"] for p in padron)
    del_padron = set(isos)

    datos, caidos, futuros = {}, [], 0
    for m in MEDIDAS:
        try:
            s, f = series(pedir(m["codigo"], isos), m, del_padron)
            datos[m["clave"]], futuros = s, futuros + f
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
        f"NI EL AÑO EN CURSO NI EL FUTURO ENTRAN: se corta en {HASTA}, el último año "
        f"cerrado. La fuente publica valores más allá y son estimaciones, no mediciones: "
        f"{futuros} puntos quedaron afuera. Ponerlos al lado de años medidos haría ver un "
        "movimiento que nadie midió.",
        "DOS DE ESTAS TRES MEDIDAS SON SEGUNDAS FUENTES a propósito: el registro ya publica "
        "empleo informal y desempleo juvenil con el Banco Mundial. Si las cifras difieren, "
        "ninguna está mal: cada organismo armoniza las encuestas de hogares con reglas "
        "distintas, y la diferencia es un dato sobre cómo se mide.",
        "El desempleo cuenta a quien BUSCA trabajo y no encuentra. Quien dejó de buscar no "
        "figura, y en la región eso es mucha gente: un desempleo bajo puede convivir con "
        "una masa grande fuera del mercado.",
        "Un desempleo bajo con empleo informal alto NO es una buena noticia: significa que "
        "la gente trabaja sin registro ni derechos. Las dos medidas se leen juntas.",
        "Se toma el total de ambos sexos y de todos los sectores. La fuente publica el "
        "detalle por sexo y por rama; este registro no lo publica a medias.",
        "Un mismo año puede venir de más de una encuesta. Se conserva la última que entrega "
        "la fuente, sin promediar: promediar dos encuestas distintas inventaría una tercera.",
    ]
    if sin_dato:
        vacios.append(f"{len(sin_dato)} Estados sin ninguna de estas medidas: "
                      + ", ".join(sin_dato) + ".")
    vacios.extend(caidos)

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente=ORIGEN,
        url_fuente="https://ilostat.ilo.org/",
        calificacion=comun.calificar(
            "B", 2, True,
            "Organismo multilateral que armoniza las encuestas de hogares de cada Estado "
            "con metodología propia y publicada. No es el productor original —lo es cada "
            "instituto de estadística— y por eso no sube de B. Entra CORROBORANDO: dos de "
            "sus tres medidas ya las publica otra fuente en este registro."),
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": [{"clave": m["clave"], "rotulo": m["rotulo"], "eje": m["eje"],
                             "unidad": m["unidad"], "mas_es_peor": m["mas_es_peor"],
                             "origen": ORIGEN, "cautela": m["cautela"]}
                            for m in publicables],
            "cobertura": cobertura,
            "ventana_anios": [anios[0], anios[-1]] if anios else None,
            "puntos_del_futuro_descartados": futuros,
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
