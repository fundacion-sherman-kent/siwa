# -*- coding: utf-8 -*-
"""Global Data Lab: desarrollo humano, corrupción y urbanización por región.

QUÉ TRAE, Y POR QUÉ IMPORTA
----------------------------
Tres medidas subnacionales que ninguna otra fuente da para tantos países de la
región a la vez: el **índice de desarrollo humano subnacional**, el **índice
subnacional de corrupción** y el **porcentaje de población urbana**. Con esto,
los ejes Desarrollo y Gobernanza bajan de escala en veintisiete y veinticinco
Estados del padrón; hasta ahora la única capa subnacional del registro era
Seguridad, en dos países.

LA TRAMPA QUE ESTE COLECTOR EVITA, Y QUE HABRÍA SIDO GRAVE
------------------------------------------------------------
**Las unidades de Global Data Lab NO son siempre las unidades del padrón.**
Medido sobre los 286 renglones subnacionales de la región:

  · **6 Estados** usan las mismas unidades que este registro —Bolivia, Brasil,
    Costa Rica, Guyana, Honduras y México—.
  · **7 lo hacen a medias** —Colombia casa 25 de 33, Venezuela 15 de 23—.
  · **15 usan otra geografía**: regiones de encuesta. La Argentina aparece con
    «Cuyo», «NOA», «Patagonia» y «Gran Buenos Aires», que no son provincias sino
    agrupamientos con los que se levantan las encuestas de hogares.

Unir eso a ciegas con el padrón habría publicado «Cuyo» como si fuera una
provincia argentina, o habría tirado quince países en silencio. **Cada unidad
declara acá si corresponde a una unidad de primer orden del padrón o a una
región propia de la fuente**, y el mapa solo pinta las primeras. Las otras se
publican igual, como tabla y con su nombre: el dato existe y no se esconde.

POR QUÉ EL ARCHIVO SE CARGA A MANO
-----------------------------------
Se buscó la forma de que el robot lo trajera solo y **no existe**: el sitio no
publica ningún archivo abierto, la descarga exige sesión iniciada y la interfaz
que ofrecen es para R y con tope de mil consultas. Así que los tres archivos se
descargan una vez y viven en el repositorio.

No es un problema mayor: **estas series son anuales**. Lo que sí queda por
hacer es un vigía que mire la página de la fuente y avise cuando publiquen una
edición nueva, para que nadie tenga que acordarse.
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402
from cotejo import cubre, sello  # noqa: E402

COLECTOR = "gdl"
CAPA = "publico"
AQUI = Path(__file__).resolve().parent

# Los tres archivos, con la clave y el rótulo que llevan en el registro. El
# nombre del archivo es el que la fuente pone al descargar: no se lo renombra
# para que se vea de dónde salió.
ARCHIVOS = [
    {"clave": "hdi_subnacional",
     "archivo": "GDL-Subnational-HDI-data.csv",
     "rotulo": "Desarrollo humano subnacional",
     "unidad": "índice de 0 a 1",
     "eje": "Desarrollo",
     "sube_es_peor": False,
     "que_mide": "Salud, educación e ingreso combinados, con la misma fórmula del índice "
                 "de Naciones Unidas pero calculada para cada región."},
    {"clave": "corrupcion_subnacional",
     "archivo": "GDL-Comprehensive-Subnational-Corruption-Index-(SCI)-data.csv",
     "rotulo": "Corrupción subnacional",
     "unidad": "índice de 0 a 100",
     "eje": "Gobernanza",
     "sube_es_peor": True,
     "que_mide": "Índice compuesto de corrupción a escala de región. Es una estimación "
                 "del productor, no un recuento de hechos."},
    {"clave": "urbanizacion_subnacional",
     "archivo": "GDL-Population-in-urban-areas-(%)-data.csv",
     "rotulo": "Población urbana",
     "unidad": "% de la población de la región",
     "eje": "Desarrollo",
     "sube_es_peor": None,
     "que_mide": "Qué parte de la población de cada región vive en zonas urbanas. NO es "
                 "el total de habitantes: no sirve como denominador para calcular tasas."},
]

def padron_de_unidades() -> dict:
    """Las unidades de primer orden que este registro ya tiene, por Estado."""
    ruta = comun.DATOS / "publico" / "unidades.json"
    if not ruta.exists():
        return {}
    import json
    d = json.loads(ruta.read_text(encoding="utf-8"))
    return {r["iso"]: {sello(x.get("nombre")): x.get("nombre")
                       for x in (r.get("lista") or []) if x.get("nombre")}
            for r in d.get("registros", [])}


def leer(archivo: dict, isos: set, unidades: dict) -> tuple:
    ruta = AQUI / archivo["archivo"]
    if not ruta.exists():
        return {}, f"falta el archivo {archivo['archivo']}"
    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    if not filas:
        return {}, f"{archivo['archivo']} está vacío"
    anios = sorted(c for c in filas[0] if str(c).isdigit())

    por_pais = {}
    for f in filas:
        if f.get("Level") != "Subnat" or f.get("ISO_Code") not in isos:
            continue
        iso = f["ISO_Code"]
        serie = []
        for a in anios:
            v = (f.get(a) or "").strip()
            if not v:
                continue
            try:
                serie.append({"anio": int(a), "valor": float(v)})
            except ValueError:
                continue
        if not serie:
            continue
        propio = unidades.get(iso) or {}
        cubiertas, clase, enumera, entero = cubre(f.get("Region") or "", propio)
        por_pais.setdefault(iso, []).append({
            "unidad": (f.get("Region") or "").strip(),
            # LOS CAMPOS QUE EVITAN EL ERROR. «clase» dice qué es este renglón:
            #   unidad        — una unidad de primer orden del padrón; el mapa la pinta.
            #   agrupamiento  — varias unidades juntas, y «cubre» dice cuáles; el mapa
            #                   las pinta todas con el mismo valor, declarado como
            #                   valor del grupo y no de cada una.
            #   region_propia — una región de la fuente que no se corresponde con
            #                   ninguna unidad: se publica con su nombre y no se pinta.
            "clase": clase,
            "cubre": cubiertas,
            # Cuántos lugares nombra el renglón y si se los identificó a todos.
            # Un agrupamiento incompleto NO se pinta: no se sabe sobre qué
            # territorio se calculó el número.
            "lugares_que_nombra": enumera,
            "identificado_entero": entero,
            "gdlcode": f.get("GDLCODE"),
            "serie": serie,
            "ultimo": serie[-1],
            "desde": serie[0]["anio"],
            "hasta": serie[-1]["anio"],
        })
    return por_pais, None


def construir() -> Path:
    padron = {p["iso"]: p for p in geo.padron()}
    unidades = padron_de_unidades()
    if not unidades:
        raise RuntimeError("falta datos/publico/unidades.json: sin padrón no se puede cotejar")

    medidas, faltantes = [], []
    por_pais_total = {}
    for a in ARCHIVOS:
        datos, error = leer(a, set(padron), unidades)
        if error:
            faltantes.append(error)
            continue
        renglones = [u for v in datos.values() for u in v]
        # Cuántas unidades del padrón quedan con dato: no cuántos renglones trae la
        # fuente. Un renglón que agrupa cuatro departamentos cubre cuatro unidades,
        # y uno que mide «Cuyo» no cubre ninguna.
        alcanzadas = {(iso, x) for iso, v in datos.items() for u in v
                      if u["identificado_entero"] for x in u["cubre"]}
        medidas.append({
            "clave": a["clave"], "rotulo": a["rotulo"], "unidad": a["unidad"],
            "eje": a["eje"], "sube_es_peor": a["sube_es_peor"], "que_mide": a["que_mide"],
            "archivo": a["archivo"],
            "estados": len(datos), "renglones": len(renglones),
            "unidades_del_padron_alcanzadas": len(alcanzadas),
            "renglones_por_clase": {c: sum(1 for u in renglones if u["clase"] == c)
                                    for c in ("unidad", "agrupamiento", "region_propia")},
            "hasta": max((u["hasta"] for u in renglones), default=None),
        })
        for iso, lista in datos.items():
            por_pais_total.setdefault(iso, {})[a["clave"]] = lista

    if not medidas:
        raise RuntimeError("ninguno de los tres archivos de Global Data Lab se pudo leer")

    registros = []
    for iso, med in sorted(por_pais_total.items()):
        todas = [u for lista in med.values() for u in lista]
        del_padron_iso = {n for x in unidades.get(iso, {}).values() for n in [x]}
        alcanzadas = {x for u in todas if u["identificado_entero"] for x in u["cubre"]}
        # LA CUENTA QUE IMPORTA: qué proporción de las unidades de primer orden
        # DEL PADRÓN quedan con dato. Es distinta de la proporción de renglones
        # de la fuente que casan, y es la que decide si el mapa de este Estado se
        # puede pintar entero.
        cobertura = len(alcanzadas) / len(del_padron_iso) if del_padron_iso else 0
        # LA SEGUNDA DIMENSION, QUE NO SE PUEDE CONFUNDIR CON LA PRIMERA. Una cosa
        # es que una unidad tenga dato y otra muy distinta es que ese dato sea SUYO.
        # Jamaica queda cubierta entera, pero por grupos de dos y tres parroquias:
        # cada parroquia lleva el promedio de su grupo, no su propia medición. El
        # Perú, igual, con grupos de cuatro y cinco departamentos. Publicar eso como
        # «dato de la unidad» sería decir algo que la fuente no dice.
        propias = {x for u in todas
                   if u["identificado_entero"] and u["clase"] == "unidad" for x in u["cubre"]}
        finura = len(propias) / len(alcanzadas) if alcanzadas else 0
        registros.append({
            "iso": iso,
            "pais": padron[iso]["pais"],
            "bloque": padron[iso].get("bloque"),
            # LA GEOGRAFIA QUE USA LA FUENTE PARA ESTE ESTADO, dicha sin rodeos.
            "geografia": ("padron" if cobertura >= 0.9
                          else "parcial" if cobertura >= 0.4
                          else "agrupada" if alcanzadas else "regiones_de_la_fuente"),
            "unidades_del_padron": len(del_padron_iso),
            "unidades_alcanzadas": len(alcanzadas),
            "cobertura_del_padron": round(cobertura, 3),
            "unidades_con_dato_propio": len(propias),
            "proporcion_con_dato_propio": round(finura, 3),
            "resolucion": ("propia" if finura >= 0.9
                           else "mezclada" if finura >= 0.3 else "por_agrupamientos"),
            "unidades_sin_dato": sorted(del_padron_iso - alcanzadas),
            "renglones": len(todas),
            "medidas": {clave: lista for clave, lista in med.items()},
        })

    del_padron = sum(1 for r in registros if r["geografia"] == "padron")
    mixtos = sum(1 for r in registros if r["geografia"] == "parcial")
    agrupados = sum(1 for r in registros if r["geografia"] == "agrupada")
    otros = sum(1 for r in registros if r["geografia"] == "regiones_de_la_fuente")
    sin_cobertura = sorted(padron[i]["pais"] for i in padron if i not in por_pais_total)

    propias = sum(1 for r in registros if r["resolucion"] == "propia")
    por_grupo = sum(1 for r in registros if r["resolucion"] == "por_agrupamientos")

    vacios = [
        "LAS UNIDADES DE ESTA FUENTE NO SIEMPRE SON LAS DEL PADRÓN. "
        f"{del_padron} Estados quedan cubiertos casi por entero con sus unidades de primer "
        f"orden; {mixtos} a medias; {agrupados} solo por agrupamientos gruesos; y {otros} con "
        "regiones propias de la fuente que no se corresponden con ninguna unidad —la "
        "Argentina aparece con «Cuyo», «NOA» y «Patagonia», que son agrupamientos de "
        "encuesta y no provincias—. Cada renglón declara su clase: «unidad» se pinta en el "
        "mapa; «agrupamiento» pinta a todas las unidades que abarca; «región propia» no se "
        "pinta y se publica con su nombre.",
        "TENER DATO NO ES LO MISMO QUE TENER DATO PROPIO, y es la distinción que más "
        f"importa acá. En {propias} Estados cada unidad lleva su propia medición. En "
        f"{por_grupo} el número existe pero es el de un grupo de unidades: Jamaica queda "
        "cubierta entera con grupos de dos y tres parroquias, y el Perú con grupos de "
        "cuatro y cinco departamentos. Esas unidades llevan el promedio de su grupo, no lo "
        "suyo, y así se rotulan. Un agrupamiento del que no se pudieron identificar TODAS "
        "las unidades que enumera no se pinta: no se sabría sobre qué territorio se calculó.",
        "El porcentaje de población urbana NO es el total de habitantes: no sirve como "
        "denominador para convertir recuentos en tasas.",
        "El índice de corrupción es una ESTIMACIÓN del productor, no un recuento de hechos "
        "comprobables. No debe leerse con la misma vara que el Índice de Opacidad de esta "
        "casa, que mide actos observables.",
        "Los nombres se cotejaron a máquina, tolerando una letra de diferencia y solo una. "
        "Hizo falta porque las erratas están de los dos lados: la fuente escribe «Arbucania» "
        "por Araucanía y «Canideyu» por Canindeyú, y el padrón heredó de la CEPAL nombres "
        "rotos —«Camag» por Camagüey, «CA8AR» por Cañar—. Doce parejas se resolvieron así, "
        "todas revisadas una por una.",
        "Los tres archivos se cargan a mano: la fuente no publica ningún archivo abierto, "
        "su descarga exige sesión y su interfaz es para R con tope de mil consultas. Las "
        "series son anuales, así que se recargan una vez por año.",
    ]
    if sin_cobertura:
        vacios.append(f"{len(sin_cobertura)} Estados del padrón sin ninguna medida de esta "
                      "fuente: " + ", ".join(sin_cobertura) + ".")
    vacios.extend(faltantes)

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Global Data Lab — Universidad Radboud de Nimega: base de datos subnacional "
               "de desarrollo humano, corrupción y demografía",
        url_fuente="https://globaldatalab.org/",
        calificacion=comun.calificar(
            "B", 3, False,
            "Centro académico con método publicado. Sus cifras subnacionales se estiman a "
            "partir de encuestas de hogares, no se cuentan: por eso la credibilidad no sube "
            "de 3 y por eso sus unidades a veces son regiones de encuesta y no provincias."),
        registros=registros,
        vacios=vacios,
        extra={"medidas": medidas,
               "resumen": {
                   "estados_con_dato": len(registros),
                   "estados_del_padron": len(padron),
                   "con_unidades_del_padron": del_padron,
                   "con_cobertura_parcial": mixtos,
                   "solo_por_agrupamientos_gruesos": agrupados,
                   "con_dato_propio_por_unidad": propias,
                   "con_dato_solo_de_grupo": por_grupo,
                   "con_regiones_de_la_fuente": otros,
               }},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
