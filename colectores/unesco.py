# -*- coding: utf-8 -*-
"""Educación: la materia que el eje Desarrollo no medía en absoluto.

EL HUECO. Desarrollo medía catorce cosas —agua, internet, pobreza, desigualdad,
informalidad, trabajo infantil— y **ni una sola de educación**. Un registro que
dice describir la situación de la región sin decir cuántos chicos están fuera de
la escuela describe la mitad.

LA PUERTA. El Instituto de Estadística de la UNESCO publica su base con interfaz
abierta, sin credencial y con licencia que permite redifundir. No es la ruta que
se le pide a la UNESCO por carta —esa es otra, por el convenio de 1970, y sigue
pendiente—: es una puerta distinta y ya está abierta.

QUÉ ENTRA, Y POR QUÉ ESTAS CINCO
----------------------------------
Se consultaron los 33 Estados antes de elegir. Cubren las tres preguntas que
un lector hace sobre educación: **cuánto pone el Estado**, **quién queda
afuera** y **hasta dónde llega quien entra**.

Se eligió la TASA de chicos fuera de la escuela y no el recuento: un recuento
premia al Estado grande por ser grande, que es el error que este registro ya
corrigió en efectivos militares y en artículos científicos.

LO QUE ESTAS CIFRAS NO DICEN
------------------------------
**Nada sobre la calidad de lo que se enseña.** Un Estado puede tener a todos sus
chicos adentro de la escuela y enseñarles poco. La medición de aprendizajes
existe y se hace con pruebas que no cubren a los 33: cuando se cubran, entran.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "unesco"
CAPA = "publico"

BASE = "https://api.uis.unesco.org/api/public/data/indicators"
DESDE = 2010

ORIGEN = "Instituto de Estadística de la UNESCO (UIS), interfaz abierta"

MEDIDAS = [
    {"clave": "gasto_educacion", "codigo": "XGDP.FSGOV",
     "rotulo": "Gasto público en educación", "eje": "Desarrollo",
     "unidad": "% del producto", "mas_es_peor": False,
     "cautela": "Cuánto destina el Estado a educación. Mide el esfuerzo, NO el resultado: "
                "gastar más no enseña mejor por sí solo. Y se lee contra el producto, así "
                "que un Estado que se empobrece puede subir acá sin haber puesto un peso más."},
    {"clave": "fuera_escuela", "codigo": "ROFST.1.CP",
     "rotulo": "Chicos fuera de la escuela primaria", "eje": "Desarrollo",
     "unidad": "% de los chicos en edad escolar", "mas_es_peor": True,
     "cautela": "Es la TASA y no el recuento: un recuento premia al Estado grande por ser "
                "grande. Cuenta a quienes no están matriculados en ningún nivel; no cuenta "
                "a quienes están matriculados y no van, que en varios Estados del padrón "
                "es un problema tan grande como el primero y nadie mide igual."},
    {"clave": "termina_secundaria", "codigo": "CR.3",
     "rotulo": "Terminan la secundaria", "eje": "Desarrollo",
     "unidad": "% de la cohorte", "mas_es_peor": False,
     "cautela": "Qué parte de una generación completa la secundaria alta. Es la medida "
                "que mejor anticipa el trabajo informal y el desempleo juvenil, dos cosas "
                "que este registro ya mide por separado."},
    {"clave": "matricula_terciaria", "codigo": "GER.5T8",
     "rotulo": "Matrícula terciaria", "eje": "Desarrollo",
     "unidad": "% del grupo de edad", "mas_es_peor": False,
     "cautela": "Es una razón BRUTA: cuenta a todos los matriculados contra el grupo de "
                "edad teórico, así que puede pasar de 100 cuando estudia gente mayor. Un "
                "valor alto indica acceso, no calidad ni egreso."},
    {"clave": "alfabetizacion", "codigo": "LR.AG15T99",
     "rotulo": "Alfabetización adulta", "eje": "Desarrollo",
     "unidad": "% de las personas de 15 años o más", "mas_es_peor": False,
     "cautela": "La cobertura más floja de este bloque. En buena parte se releva por "
                "AUTODECLARACIÓN en censos —se pregunta si sabe leer, no se toma una "
                "prueba— y eso tiende a sobrestimar. Sirve para el orden de magnitud."},
]


def pedir(codigo: str, isos: str) -> list:
    url = (f"{BASE}?indicator={codigo}&geoUnit={isos}&start={DESDE}&format=json")
    peticion = urllib.request.Request(
        url, headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=180) as respuesta:
        d = json.loads(respuesta.read().decode("utf-8", "replace"))
    return d.get("records") or []


def series(recs: list, del_padron: set) -> dict:
    salida = {}
    for r in recs:
        iso, anio, valor = r.get("geoUnit"), r.get("year"), r.get("value")
        if iso not in del_padron or valor is None:
            continue
        try:
            salida.setdefault(iso, []).append((int(anio), round(float(valor), 3)))
        except (TypeError, ValueError):
            continue
    # Un mismo año puede venir dos veces con revisiones distintas: se conserva
    # la última, que es la que la fuente da por buena.
    return {i: sorted(dict(v).items()) for i, v in salida.items()}


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
    pedido = ",".join(isos)

    datos, caidos = {}, []
    for m in MEDIDAS:
        try:
            datos[m["clave"]] = series(pedir(m["codigo"], pedido), del_padron)
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
        for clave in fuera:
            f["indicadores"].pop(clave, None)
    registros = [r for r in registros if r["indicadores"]]
    registros.sort(key=lambda r: r["pais"])

    sin_dato = sorted(p["pais"] for p in padron
                      if p["iso"] not in {r["iso"] for r in registros})
    anios = sorted({x["anio"] for r in registros for x in r["indicadores"].values()})

    vacios = [
        "ESTAS CIFRAS NO DICEN NADA SOBRE LA CALIDAD DE LO QUE SE ENSEÑA. Un Estado puede "
        "tener a todos sus chicos adentro de la escuela y enseñarles poco. La medición de "
        "aprendizajes existe y se hace con pruebas que no cubren a los 33 Estados: cuando "
        "los cubran, entran.",
        "«Fuera de la escuela» cuenta a quienes NO ESTÁN MATRICULADOS. No cuenta a quienes "
        "están matriculados y no van, que en varios Estados del padrón es un problema tan "
        "grande como el primero y que nadie mide con la misma vara.",
        "La matrícula terciaria es una razón BRUTA: cuenta a todos los matriculados contra "
        "el grupo de edad teórico, de modo que puede pasar de 100 cuando estudia gente "
        "mayor. Indica acceso, no calidad ni egreso.",
        "La alfabetización adulta se releva en buena parte por AUTODECLARACIÓN en censos "
        "—se pregunta si sabe leer, no se toma una prueba— y eso tiende a sobrestimar.",
        "Esta es la interfaz abierta de la UNESCO, no la ruta del convenio de 1970 que se "
        "le pide por carta: son dos puertas distintas y aquella sigue pendiente.",
    ]
    if sin_dato:
        vacios.append(f"{len(sin_dato)} Estados sin ninguna de estas medidas: "
                      + ", ".join(sin_dato) + ".")
    vacios.extend(caidos)

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente=ORIGEN,
        url_fuente="https://uis.unesco.org/",
        calificacion=comun.calificar(
            "B", 2, False,
            "Organismo multilateral que compila lo que declaran los ministerios de "
            "educación y lo estandariza con una clasificación internacional. No es el "
            "productor original —lo es cada ministerio— y por eso no sube de B; responde "
            "siempre y con serie, y por eso la corroboración es 2."),
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": [{"clave": m["clave"], "rotulo": m["rotulo"], "eje": m["eje"],
                             "unidad": m["unidad"], "mas_es_peor": m["mas_es_peor"],
                             "origen": ORIGEN, "cautela": m["cautela"]}
                            for m in publicables],
            "cobertura": cobertura,
            "ventana_anios": [anios[0], anios[-1]] if anios else None,
            "licencia": "CC BY-SA 3.0 IGO",
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
