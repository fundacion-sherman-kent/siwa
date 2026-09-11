# -*- coding: utf-8 -*-
"""Gasto del Estado por función: seguridad y defensa, con medio siglo de serie.

QUÉ RESUELVE. El registro medía cuánto gasta cada Estado en defensa —con la
fuente de SIPRI, compilada por el Banco Mundial— y **no medía cuánto gasta en
seguridad interior**, que es la pregunta que hace cualquiera que mira la región.
Faltaba porque la fuente evidente, la comisión regional, consulta por número de
indicador y no publica catálogo: no hay forma automática de saber cuál pedir.

Esta es otra puerta a la misma clase de dato: las estadísticas de finanzas
públicas del Fondo Monetario, con la clasificación internacional del gasto por
función, redifundidas con interfaz abierta y sin credencial.

LO QUE TRAE, MEDIDO ANTES DE ESCRIBIRLO
----------------------------------------
  · **Orden público y seguridad**, veintidós de los 33 Estados.
  · **Defensa**, otros veintidós, que además es una **segunda fuente
    independiente** para contrastar la de SIPRI que el registro ya publica. Que
    dos fuentes distintas midan lo mismo es la regla de la casa, no un lujo.
  · Series **desde 1990**, de hasta treinta y cuatro años. Eso ataca de frente la
    brecha más grande que el propio registro se declara: 33 de sus 46 conjuntos
    muestran el último valor y no dejan ver si mejora o empeora.

Una advertencia sobre el primer número: la fuente devuelve series para treinta y
un Estados, pero la mayoría vienen llenas de «NA». **Contar series no es contar
datos**: los que traen al menos un valor real son veintidós.

POR QUÉ NO HAY UN MONTO EN PESOS NI EN DÓLARES
------------------------------------------------
La fuente publica el monto absoluto **en moneda de cada país**, y eso no se
compara: un billón de pesos colombianos y un billón de guaraníes no son la misma
cosa, y convertirlos exigiría un tipo de cambio y una decisión sobre cuál, que
sería una opinión metida adentro de un dato. Lo comparable es la proporción, y
va en dos formas: sobre el producto y sobre el gasto total del Estado. **Un
Estado chico que dedica mucho de lo poco que tiene no es lo mismo que uno grande
que dedica poco de mucho**, y por eso las dos se leen juntas.
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

COLECTOR = "gasto_publico"
CAPA = "publico"

BASE = "https://api.db.nomics.world/v22/series/IMF/GFSCOFOG"
# QUÉ PEDAZO DEL ESTADO SE MIDE, y por qué este. Se probaron los cuatro sectores
# que la fuente ofrece, contra los 33 Estados del padrón:
#
#     gobierno general .......................  6 de 33
#     gobierno central sin seguridad social ..  12 de 33
#     presupuesto del gobierno central .......  22 de 33   ← se toma este
#     gobierno central extrapresupuestario ...   0 de 33
#
# El gobierno general sería el ideal, porque incluye a las provincias, y cubre
# seis Estados: con eso no se puede pintar un mapa ni afirmar nada de la región.
#
# EL COSTO DE LA ELECCIÓN, QUE NO SE ESCONDE: en los Estados federales del padrón
# la policía es en buena medida provincial, y esta cifra no la cuenta. Para esos
# cuatro es un piso, no el total, y así se declara en cada ficha.
SECTOR = "S1311B"
FEDERALES = ("la Argentina", "el Brasil", "México", "Venezuela")
DESDE = 1990   # antes de eso la cobertura de la región es demasiado rala

# TECHO DE PLAUSIBILIDAD. El Ecuador salía con 416,8 % del producto gastado en
# orden público, en un único punto de 1990: un arrastre de la fuente, casi
# seguro cifras en sucres previas a la dolarización mal rotuladas. Un valor así
# no se corrige adivinando el verdadero —eso sería fabricar—: se descarta y se
# declara. El techo va bien por encima de cualquier cifra real: El Salvador
# llegó a 11,4 % en 1993, saliendo de su guerra civil, y esa entra sin problema.
TECHO = 25.0
descartados = []

MEDIDAS = [
    {"clave": "gasto_seguridad", "funcion": "GF03", "unidad_fuente": "XDC_R_B1GQ",
     "rotulo": "Gasto en orden público y seguridad", "eje": "Seguridad",
     "unidad": "% del producto", "mas_es_peor": False,
     "cautela": "Incluye policía, bomberos, tribunales y cárceles: es el aparato de "
                "seguridad y justicia entero, no solo la policía. Es el PRESUPUESTO DEL "
                "GOBIERNO CENTRAL: en los Estados federales —la Argentina, el Brasil, "
                "México, Venezuela— la policía es en buena medida provincial y no entra "
                "acá, así que para ellos la cifra es un piso. Y mide cuánto se destina, NO "
                "qué se obtiene: gastar más no es estar más seguro, y varios de los "
                "Estados que más gastan son los que más homicidios tienen."},
    {"clave": "gasto_seguridad_publico", "funcion": "GF03", "unidad_fuente": "XDC_R_OTE",
     "rotulo": "Seguridad sobre el gasto del Estado", "eje": "Seguridad",
     "unidad": "% del gasto público", "mas_es_peor": False,
     "cautela": "La misma cifra contra otra vara: qué parte de todo lo que el Estado gasta "
                "va a seguridad y justicia. Se lee junto a la anterior, porque un Estado "
                "chico que dedica mucho de lo poco que tiene no es lo mismo que uno grande "
                "que dedica poco de mucho."},
    {"clave": "gasto_defensa_fmi", "funcion": "GF02", "unidad_fuente": "XDC_R_B1GQ",
     "rotulo": "Gasto en defensa · segunda fuente", "eje": "Defensa",
     "unidad": "% del producto", "mas_es_peor": False,
     "cautela": "ES UNA SEGUNDA MEDICIÓN de algo que el registro ya publica con la fuente "
                "de SIPRI, y por eso está: dos fuentes que miden lo mismo permiten ver si "
                "coinciden. Si difieren, ninguna de las dos está mal: cuentan con reglas "
                "distintas —esta, lo que el Estado ejecutó por presupuesto; la otra, lo "
                "que destinó a fines militares— y la diferencia es en sí misma un dato."},
]

ORIGEN = ("Estadísticas de Finanzas Públicas del Fondo Monetario Internacional, "
          "clasificación del gasto por función (COFOG), vía DBnomics")


def pedir(funcion: str, unidad: str) -> list:
    dim = json.dumps({"COFOG_FUNCTION": [funcion], "UNIT_MEASURE": [unidad],
                      "FREQ": ["A"], "REF_SECTOR": [SECTOR]})
    url = (f"{BASE}?dimensions={urllib.parse.quote(dim)}&observations=1&limit=1000")
    peticion = urllib.request.Request(
        url, headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=180) as respuesta:
        d = json.loads(respuesta.read().decode("utf-8", "replace"))
    return (d.get("series") or {}).get("docs") or []


def serie_por_estado(docs: list, al_iso3: dict) -> dict:
    """{iso3: [(año, valor)]}, ya limpia.

    La fuente marca lo que falta con la palabra «NA», que en un archivo de
    números es texto: si no se lo saca, entra como valor y arruina la escala del
    mapa. Se descarta todo lo que no sea un número.
    """
    salida = {}
    for s in docs:
        area = (s.get("dimensions") or {}).get("REF_AREA")
        iso = al_iso3.get(area)
        if not iso:
            continue
        puntos = []
        for anio, valor in zip(s.get("period") or [], s.get("value") or []):
            try:
                a, v = int(str(anio)[:4]), float(valor)
            except (TypeError, ValueError):
                continue          # «NA» y cualquier otro texto se van por acá
            if a < DESDE:
                continue
            if not 0 <= v <= TECHO:
                descartados.append(f"{iso} {a}: {round(v, 1)} % — fuera de lo posible")
                continue
            puntos.append((a, round(v, 3)))
        if puntos:
            salida[iso] = sorted(puntos)
    return salida


def ficha(serie: list) -> dict:
    """La forma que el registro le da a cualquier serie, para que el sitio la lea igual."""
    anio, valor = serie[-1]
    anterior = serie[-2] if len(serie) >= 2 else None
    variacion = (round((valor - anterior[1]) / abs(anterior[1]) * 100, 1)
                 if anterior and anterior[1] else None)
    ventana = (round((valor - serie[0][1]) / abs(serie[0][1]) * 100, 1)
               if len(serie) >= 3 and serie[0][1] else None)
    return {
        "valor": valor, "anio": anio,
        "anio_anterior": anterior[0] if anterior else None,
        "valor_anterior": anterior[1] if anterior else None,
        "variacion_pct": variacion,
        "anio_inicial": serie[0][0], "valor_inicial": serie[0][1],
        "tendencia_ventana_pct": ventana,
        "serie": [{"anio": a, "valor": v} for a, v in serie],
    }


def construir() -> Path:
    padron = geo.padron()
    al_iso3 = {v: k for k, v in comun.DOS_LETRAS.items()}

    datos, caidos = {}, []
    for m in MEDIDAS:
        try:
            datos[m["clave"]] = serie_por_estado(
                pedir(m["funcion"], m["unidad_fuente"]), al_iso3)
        except Exception as error:  # noqa: BLE001 — la medida caída se declara
            caidos.append(f"{m['rotulo']}: {type(error).__name__}")
            datos[m["clave"]] = {}

    if not any(datos.values()):
        raise RuntimeError("ninguna medida devolvió serie. No se escribe nada.")

    registros, cobertura = [], {}
    for p in padron:
        f = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        for m in MEDIDAS:
            serie = datos[m["clave"]].get(p["iso"])
            if serie:
                f["indicadores"][m["clave"]] = ficha(serie)
                cobertura[m["clave"]] = cobertura.get(m["clave"], 0) + 1
        if f["indicadores"]:
            registros.append(f)

    # Una medida sin un solo Estado no se ofrece: el sitio no puede prometer lo
    # que no existe. Es la misma regla que ya aplica el colector del Banco.
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
        "NO HAY MONTO EN PESOS NI EN DÓLARES, y no es un olvido. La fuente publica el "
        "monto absoluto en la moneda de cada país, y eso no se compara: convertirlo "
        "exigiría elegir un tipo de cambio, y esa elección es una opinión metida adentro "
        "de un dato. Lo comparable es la proporción, y va en dos formas: sobre el producto "
        "y sobre el gasto total del Estado.",
        "El gasto en seguridad incluye policía, bomberos, tribunales y cárceles: es el "
        "aparato de seguridad y justicia entero, no solo la policía.",
        "GASTAR MÁS NO ES ESTAR MÁS SEGURO. Estas cifras miden lo que el Estado destina, "
        "no lo que obtiene, y en la región varios de los Estados que más gastan son los "
        "que más homicidios tienen. La relación entre gasto y resultado no se afirma acá.",
        "SE MIDE EL PRESUPUESTO DEL GOBIERNO CENTRAL, y eso tiene un costo que conviene "
        "saber. La fuente ofrece cuatro pedazos del Estado; el gobierno general, que "
        "incluiría a las provincias, solo cubre 6 de los 33 Estados, y con seis no se "
        "puede afirmar nada de la región. El presupuesto del gobierno central cubre 22. "
        "En los Estados federales —la Argentina, el Brasil, México, Venezuela— la policía "
        "es en buena medida provincial y NO entra en esta cifra: para esos cuatro es un "
        "piso y no el total. Comparar a la Argentina con El Salvador sin saber esto lleva "
        "a una conclusión falsa.",
        "La serie empieza en 1990: antes de esa fecha la cobertura de la región es "
        "demasiado rala para comparar.",
        "LA FRESCURA ES MUY DESPAREJA, y conviene mirar el año antes de comparar. El "
        "Salvador trae treinta y cuatro años hasta 2023; Granada, cinco, y termina en "
        "1995. Las dos se publican con su fecha a la vista, pero comparar la primera con "
        "la segunda es comparar dos épocas distintas, no dos Estados.",
    ]
    if sin_dato:
        vacios.append(f"{len(sin_dato)} Estados sin ninguna de estas medidas: "
                      + ", ".join(sin_dato) + ".")
    if descartados:
        vacios.append(
            f"{len(descartados)} valores descartados por imposibles —un gasto no puede "
            f"superar el {TECHO:.0f} % del producto—: " + "; ".join(descartados[:6])
            + ". No se corrigen adivinando el verdadero: se sacan y se dice cuáles.")
    vacios.extend(caidos)

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente=ORIGEN,
        url_fuente="https://db.nomics.world/IMF/GFSCOFOG",
        calificacion=comun.calificar(
            "B", 2, False,
            "Organismo multilateral que compila lo que declara cada Estado, redifundido "
            "por un tercero que no lo modifica. No es el productor original —el productor "
            "es cada ministerio de hacienda— y por eso la fuente no sube de B; responde "
            "siempre y con serie larga, y por eso la corroboración es 2."),
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
