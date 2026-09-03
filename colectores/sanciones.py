"""Quiénes de cada Estado figuran en registros de sanciones y de personas expuestas.

POR QUÉ EXISTE
--------------
«Economías ilícitas» es una de las materias que el registro nombraba y medía con
indicadores prestados de otras cosas. Los registros consolidados de sanciones y
de personas políticamente expuestas son la fuente pública más cercana al asunto,
y publican su recuento por país en un archivo de menos de cien kilobytes.

LA TRAMPA, Y ES LA RAZÓN DE QUE ESTO NO ORDENE ESTADOS
------------------------------------------------------
La lista mundial la encabeza **Estados Unidos**, con más de doscientos sesenta
mil registros. No es el país más sancionado del mundo: **es el que mejor publica
quiénes son sus funcionarios**. Esta cifra se mueve por tres cosas que no tienen
que ver con la conducta del Estado medido:

1. **Quién sanciona a quién**, que es un acto geopolítico de terceros.
2. **Qué tan completo es el registro público de funcionarios** de ese Estado —de
   modo que aparecer mucho puede indicar transparencia, no lo contrario—.
3. **El tamaño del país**.

Por eso se publica como **hecho**, con su recuento y su fecha, y **jamás como un
orden entre Estados**. Es la misma arquitectura que Defensa, la medición de red y
la contratación pública: al lado del dato comparable, nunca adentro.

LA LICENCIA MANDA, Y VIAJA CON EL DATO
--------------------------------------
La fuente publica bajo atribución **no comercial**. Alcanza de sobra para este
registro, que es público y gratuito. **No alcanza para un producto que la
Fundación venda**, y esa restricción va declarada en el propio archivo para que
no dependa de que alguien se acuerde dentro de seis meses.
"""

from __future__ import annotations

import json
import urllib.request

import comun
import geo

INDICE = "https://data.opensanctions.org/datasets/latest/default/index.json"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# El padrón usa ISO de tres letras; la fuente, de dos.
DOS_LETRAS = {
    "ARG": "ar", "BOL": "bo", "BRA": "br", "CHL": "cl", "COL": "co", "CRI": "cr",
    "CUB": "cu", "DOM": "do", "ECU": "ec", "SLV": "sv", "GTM": "gt", "HTI": "ht",
    "HND": "hn", "MEX": "mx", "NIC": "ni", "PAN": "pa", "PRY": "py", "PER": "pe",
    "URY": "uy", "VEN": "ve", "BLZ": "bz", "GUY": "gy", "SUR": "sr",
    "ATG": "ag", "BHS": "bs", "BRB": "bb", "DMA": "dm", "GRD": "gd", "JAM": "jm",
    "KNA": "kn", "LCA": "lc", "VCT": "vc", "TTO": "tt",
}


def _json(url: str, tope: int = 4_000_000):
    peticion = urllib.request.Request(
        url, headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=90) as respuesta:
        return json.loads(respuesta.read(tope).decode("utf-8", "replace"))


def recolectar():
    # La dirección de la estadística CAMBIA con cada publicación de la fuente:
    # lleva la versión adentro. Se lee el índice y se sigue el puntero, en lugar
    # de fijar una dirección que se rompe sola en la próxima entrega.
    indice = _json(INDICE, 400_000)
    url = indice.get("statistics_url")
    if not url:
        raise RuntimeError(
            "El índice de la fuente no declara «statistics_url». No se inventa la "
            "dirección: la versión va adentro de la ruta y adivinarla daría un 404 "
            "o, peor, una estadística de otra fecha.")
    est = _json(url, 2_000_000)

    objetivos = {c["code"]: c for c in (est.get("targets") or {}).get("countries", [])}
    cosas = {c["code"]: c for c in (est.get("things") or {}).get("countries", [])}
    mundo = (est.get("targets") or {}).get("total") or 0

    registros, conRegistro = [], 0
    for pais in geo.padron():
        cc = DOS_LETRAS.get(pais["iso"])
        o = objetivos.get(cc) or {}
        t = cosas.get(cc) or {}
        n = o.get("count") or 0
        if n:
            conRegistro += 1
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "listados": n,
            "entidades": t.get("count") or 0,
            "estado": "con_registro" if n else "sin_registro",
        })

    enLaRegion = sum(r["listados"] for r in registros)

    vacios = [
        "ESTO NO ORDENA ESTADOS Y NO ES UNA MEDIDA DE CORRUPCION. La lista mundial la "
        "encabeza ESTADOS UNIDOS con mas de doscientos sesenta mil registros, y no es el "
        "pais mas sancionado del mundo: es el que mejor publica quienes son sus "
        "funcionarios. APARECER MUCHO PUEDE INDICAR TRANSPARENCIA, no lo contrario.",
        "LA CIFRA SE MUEVE POR TRES COSAS AJENAS A LA CONDUCTA DEL ESTADO MEDIDO: quien "
        "sanciona a quien —que es un acto geopolitico de terceros—, que tan completo es "
        "el registro publico de funcionarios de ese Estado, y el tamanio del pais.",
        "PERSONA EXPUESTA NO ES PERSONA SOSPECHADA. La categoria incluye a funcionarios "
        "en ejercicio por el solo hecho de serlo: un ministro figura por ser ministro. "
        "Leer estas cifras como recuento de delincuentes seria un error grave.",
        "SE PUBLICA EL RECUENTO, NO LOS NOMBRES. El registro no reproduce identidades: "
        "publica cuantos registros hay y manda a la fuente, que es donde cada caso tiene "
        "su rastro y su fecha.",
        "UN ESTADO EN CERO NO ESTA LIMPIO: puede no tener registro publico de "
        "funcionarios que la fuente haya podido incorporar. La ausencia acá dice mas "
        "sobre el registro que sobre el Estado.",
    ]

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=2,
        corroborado=False,
        nota=("Consolidador que reune listas oficiales de sanciones y registros de "
              "personas politicamente expuestas de multiples jurisdicciones. Fiabilidad B "
              "porque es un tercero que agrega, no el organismo que sanciona. "
              "Credibilidad 2 porque se verifico el recuento que la fuente publica, NO "
              "cada registro individual."),
    )

    return comun.escribir(
        colector="sanciones",
        capa="publico",
        fuente="OpenSanctions — registros de sanciones y personas expuestas",
        url_fuente="https://www.opensanctions.org/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        restriccion="solo_registro_publico",
        extra={
            "resumen": {
                "estados_con_registro": conRegistro,
                "estados_del_padron": len(registros),
                "listados_en_la_region": enLaRegion,
                "listados_en_el_mundo": mundo,
                "actualizado_por_la_fuente": est.get("last_change"),
                "estadistica": url,
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("sanciones", recolectar)
