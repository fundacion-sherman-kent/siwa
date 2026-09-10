# -*- coding: utf-8 -*-
"""El primer dato subnacional del registro, y el contraste vertical que lo prueba.

QUÉ TRAE. Homicidios por unidad de primer orden, de la fuente NACIONAL de cada
Estado. Es el primer dato que este registro publica por debajo de la escala de
país, y arranca con la Argentina porque su Sistema Nacional de Información
Criminal expone las series por provincia en una interfaz legible por máquina.

EL CONTRASTE VERTICAL, QUE ES LO QUE ESTO VINO A PROBAR
--------------------------------------------------------
La regla de la casa dice que ninguna unidad se publica solo con lo que dice de
ella el organismo nacional: hay que buscar lo que publica la propia
jurisdicción. Con Santa Fe se pudo hacer la prueba completa, y el resultado es
un hecho sobre la publicación que ninguna de las dos fuentes declara sola:

  · **La Nación publica Santa Fe en serie legible por máquina, y llega a 2022.**
  · **La provincia publica todos los meses —agosto de 2026, subido el 7 de
    septiembre— y lo hace en infografías que ninguna máquina lee.**

Son **cuatro años** de distancia. Ninguno de los dos caminos entrega hoy una
cifra fresca Y legible: el que es legible llega tarde, y el que llega a tiempo
no es legible. **Esa es la brecha, y es un dato sobre la transparencia
argentina, no sobre su violencia.**

POR QUÉ NO SE COMPARAN LOS NÚMEROS
-----------------------------------
Porque no se pueden comparar sin leer la infografía a ojo, y eso este registro
no lo hace. Y aunque se pudiera: la Nación cuenta **víctimas de homicidio
doloso** con corte anual y la provincia publica con **triangulación de fuentes
policiales, judiciales y de salud** con corte mensual. Sin definición y período
declarados como equivalentes, la diferencia entre dos cifras no prueba
discrepancia: prueba que miden cosas distintas. La regla ya estaba escrita para
el eje horizontal —solo se comparan años comunes— y rige igual acá.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

COLECTOR = "subnacional_datos"
CAPA = "publico"

BUSCAR = ("https://apis.datos.gob.ar/series/api/search?"
          "q=homicidios%20dolosos&limit=200")
SERIES = "https://apis.datos.gob.ar/series/api/series?ids={ids}&format=json&limit=1000"

# Las fuentes nacionales que publican por unidad de primer orden. Se agrega un
# Estado agregando una entrada: el recorrido no cambia.
FUENTES = [
    {
        "iso": "COL",
        "pais": "Colombia",
        "nombre_local": "departamento",
        "fuente": "Policía Nacional de Colombia — conjunto «HOMICIDIO», víctimas de homicidio "
                  "intencional, vía el portal de datos abiertos del Estado",
        "url": "https://www.datos.gov.co/d/m8fd-ahd9",
        "materia": "homicidios",
        "que_cuenta": "víctimas de homicidio intencional, recuento anual",
        # OJO CON EL CONJUNTO. El portal tiene varios que empiezan con «Homicidio»
        # y el primero que aparece buscando es «Homicidios accidente de transito»,
        # que NO es lo mismo. Este declara en su descripcion «Incluye: HOMICIDIO
        # INTENCIONAL» y se mide en victimas. Tomarlo por el nombre habria puesto
        # muertes de transito donde el registro dice homicidios.
        "recurso": "m8fd-ahd9",
        "como": "socrata",
    },
    {
        "iso": "ARG",
        "pais": "Argentina",
        "nombre_local": "provincia",
        "fuente": "Sistema Nacional de Información Criminal (SNIC) — Ministerio de "
                  "Seguridad de la Nación, vía la interfaz de series de tiempo del Estado",
        # La raiz de la interfaz devuelve 404 a quien la abre: se cita la
        # documentacion, que es lo que una persona puede leer.
        "url": "https://datosgobar.github.io/series-tiempo-ar-api/",
        "materia": "homicidios",
        "que_cuenta": "víctimas de homicidio doloso, recuento anual",
        "como": "series_ar",
    },
]

# «Cantidad de víctimas de homicidios dolosos. Provincia de Santa Fe.»
UNIDAD = re.compile(r"\.\s*(?:Provincia de\s+)?([^.]+?)\s*\.?\s*$")


def pedir(url: str, espera: int = 90):
    peticion = urllib.request.Request(
        url, headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=espera) as respuesta:
        return json.loads(respuesta.read().decode("utf-8", "replace"))


def de_argentina(f: dict) -> tuple:
    """Las series de víctimas por provincia, de la interfaz nacional."""
    d = pedir(BUSCAR)
    porId = {}
    for x in d.get("data", []):
        campo = x.get("field") or {}
        ident, desc = campo.get("id") or "", campo.get("description") or ""
        # Solo el recuento de VICTIMAS por provincia: la tasa la calcula la
        # fuente con una población que no publica al lado, así que se toma el
        # recuento, que es el hecho.
        if not ident.startswith("snic_hdv_") or ident.endswith("_arg"):
            continue
        m = UNIDAD.search(desc)
        if not m:
            continue
        porId[ident] = m.group(1).strip()
    if not porId:
        raise RuntimeError("la interfaz nacional no devolvió series por provincia")

    unidades = []
    ids = sorted(porId)
    # De a diez por consulta: la interfaz admite varias series juntas y así se
    # baja el número de llamadas sin pedirle todo de una vez.
    for i in range(0, len(ids), 10):
        lote = ids[i:i + 10]
        d = pedir(SERIES.format(ids=",".join(lote)))
        meta = d.get("meta") or []
        columnas = [(m.get("field") or {}).get("id") for m in meta[1:]]
        serie = {c: [] for c in columnas if c}
        for fila in d.get("data") or []:
            fecha = str(fila[0])[:4]
            for k, c in enumerate(columnas, start=1):
                if c and k < len(fila) and isinstance(fila[k], (int, float)):
                    serie[c].append({"anio": int(fecha), "valor": fila[k]})
        for c in lote:
            puntos = serie.get(c) or []
            if not puntos:
                continue
            unidades.append({
                "unidad": porId[c],
                "id_en_la_fuente": c,
                "serie": puntos,
                "ultimo": puntos[-1],
                "desde": puntos[0]["anio"],
                "hasta": puntos[-1]["anio"],
            })
    return unidades, len(ids)


# La consulta lleva espacios y parentesis: se codifica antes de pedirla, porque
# una direccion con espacios no es una direccion.
_SEL = "departamento, date_extract_y(fecha_hecho) AS anio, sum(cantidad) AS n"
SOCRATA = ("https://www.datos.gov.co/resource/{recurso}.json?$select="
           + urllib.parse.quote(_SEL)
           + "&$group=" + urllib.parse.quote("departamento, anio") + "&$limit=5000")


def de_socrata(f: dict) -> tuple:
    """Recuento por unidad y por año, agregado por el propio portal.

    La suma la hace la fuente y no esta casa: pedirle 500.000 filas para sumarlas
    acá sería descortés con un portal público y daría el mismo número.
    """
    filas = pedir(SOCRATA.format(recurso=f["recurso"]), espera=180)
    por_unidad = {}
    for x in filas:
        nombre, anio, n = x.get("departamento"), x.get("anio"), x.get("n")
        if not nombre or not anio:
            continue
        try:
            anio, n = int(str(anio)[:4]), float(n)
        except (TypeError, ValueError):
            continue
        por_unidad.setdefault(nombre.strip(), []).append({"anio": anio, "valor": n})

    # EL ANIO EN CURSO NO ENTRA. La fuente publica mes a mes: su ultimo anio esta
    # incompleto y dibujarlo al lado de anios cerrados haria ver una caida que no
    # existe. Es la misma regla que el registro ya aplica a las series anuales.
    completos = [a["anio"] for v in por_unidad.values() for a in v]
    tope = max(completos) - 1 if completos else None
    unidades = []
    for nombre, serie in por_unidad.items():
        serie = sorted((a for a in serie if tope is None or a["anio"] <= tope),
                       key=lambda a: a["anio"])
        if not serie:
            continue
        unidades.append({"unidad": nombre, "id_en_la_fuente": f["recurso"], "serie": serie,
                         "ultimo": serie[-1], "desde": serie[0]["anio"],
                         "hasta": serie[-1]["anio"]})
    return unidades, len(por_unidad)


def construir() -> Path:
    registros, vacios = [], []
    for f in FUENTES:
        unidades, pedidas = (de_socrata(f) if f.get("como") == "socrata"
                             else de_argentina(f))
        if not unidades:
            raise RuntimeError(f"{f['iso']}: ninguna serie utilizable")
        anios = sorted({u["hasta"] for u in unidades})
        registros.append({
            "iso": f["iso"],
            "pais": f["pais"],
            "nombre_local": f["nombre_local"],
            "materia": f["materia"],
            "que_cuenta": f["que_cuenta"],
            "fuente_nacional": {"nombre": f["fuente"], "url": f["url"]},
            "unidades_con_serie": len(unidades),
            "unidades_pedidas": pedidas,
            "ultimo_anio": max(anios) if anios else None,
            "unidades": sorted(unidades, key=lambda u: u["unidad"]),
        })

    ultimo = next((r["ultimo_anio"] for r in registros if r["iso"] == "ARG"), None)
    vacios.append(
        f"{len(registros)} Estados con dato subnacional, de 33. El resto no significa que no "
        "publiquen: significa que todavía no se buscó su fuente nacional por unidad.")
    vacios.append(
        "El año en curso NO entra en las series que la fuente publica mes a mes: está "
        "incompleto, y dibujarlo al lado de años cerrados haría ver una caída que no existe.")
    vacios.append(
        "Estas cifras NO son comparables con las de otros países: cada Estado define el "
        "homicidio a su manera y lo cuenta con su método. Sirven para comparar unidades "
        "DENTRO del mismo país y para contrastarlas con lo que publica cada jurisdicción "
        "de sí misma.")
    if ultimo:
        vacios.append(
            f"La serie nacional por provincia llega a {ultimo}. El Observatorio de Seguridad "
            "Pública de Santa Fe publica hasta agosto de 2026, en infografías que ninguna "
            "máquina lee. Ninguno de los dos caminos entrega hoy una cifra fresca Y legible: "
            "el legible llega tarde y el que llega a tiempo no es legible. Es un hecho sobre "
            "la publicación, no sobre la violencia.")
    vacios.append(
        "NO se comparan los números de la Nación con los de la provincia. Además de que uno "
        "está adentro de una imagen, cuentan cosas distintas: la Nación, víctimas de "
        "homicidio doloso con corte anual; la provincia, con triangulación de fuentes "
        "policiales, judiciales y de salud y corte mensual. Sin definición y período "
        "declarados equivalentes, una diferencia no prueba discrepancia.")

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Fuentes oficiales nacionales que publican por unidad de primer orden: "
               + "; ".join(f["fuente"].split("—")[0].strip() for f in FUENTES),
        url_fuente=FUENTES[0]["url"],
        calificacion=comun.calificar(
            "A", 2, False,
            "Fuente oficial nacional, legible por máquina y repetible. Sin corroboración "
            "independiente: la fuente de la propia jurisdicción publica en un formato que "
            "no se puede leer sin transcribir a ojo, y eso este registro no lo hace."),
        registros=registros,
        vacios=vacios,
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
