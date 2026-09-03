"""Libertad de prensa: en qué condiciones se puede publicar en cada Estado.

POR QUÉ EXISTE
--------------
«Desinformación» era una de las materias que el registro nombraba y medía con
indicadores prestados de gobernanza. Faltaba lo específico: **en qué condiciones
trabaja quien publica**.

Esta clasificación lo mide con cinco dimensiones declaradas —contexto político,
económico, legal, social y **seguridad de los periodistas**— y publica su archivo
de datos abierto, sin credencial, con la edición del año en curso.

LO QUE MIDE, Y LO QUE NO
------------------------
Mide **las condiciones para ejercer el periodismo**, no la cantidad de
desinformación que circula. Son cosas distintas y conviene no confundirlas: un
Estado puede tener prensa libre y mucha desinformación, y otro puede tener poca
desinformación visible porque nadie puede publicar nada.

De hecho la relación suele ser inversa a la intuición: **donde la prensa está
más cercada, menos desinformación se detecta** —porque detectarla también es
publicar—.

CÓMO SE CONSTRUYE, Y POR QUÉ IMPORTA DECIRLO
--------------------------------------------
El puntaje sale de una **encuesta a periodistas, académicos y defensores de
derechos humanos**, combinada con un recuento de abusos. Es **evaluación
experta**, no medición instrumental: dos personas informadas pueden puntuar
distinto el mismo país. Por eso entra calificada como tal.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from datetime import datetime, timezone

import comun
import geo

# El año va en la dirección. Se prueba el corriente y se retrocede: publicar una
# edición vieja sin decirlo seria peor que no publicar ninguna.
PLANTILLA = "https://rsf.org/sites/default/files/import_classement/{anio}.csv"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Las cinco dimensiones que la fuente declara, con el rótulo de la casa.
DIMENSIONES = [
    ("Political Context", "contexto_politico", "Contexto político"),
    ("Economic Context", "contexto_economico", "Contexto económico"),
    ("Legal Context", "contexto_legal", "Contexto legal"),
    ("Social Context", "contexto_social", "Contexto social"),
    ("Safety", "seguridad_periodistas", "Seguridad de los periodistas"),
]


def _numero(t: str | None):
    """La fuente escribe los decimales con coma, no con punto."""
    if t is None or str(t).strip() == "":
        return None
    try:
        return float(str(t).strip().replace(",", "."))
    except ValueError:
        return None


def _traer() -> tuple:
    """Trae la edición más reciente que exista, y declara cuál es."""
    anio = datetime.now(timezone.utc).year
    for candidato in (anio, anio - 1, anio - 2):
        url = PLANTILLA.format(anio=candidato)
        try:
            peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
            with urllib.request.urlopen(peticion, timeout=60) as respuesta:
                crudo = respuesta.read(2_000_000)
        except Exception:  # noqa: BLE001 — se prueba el año anterior
            continue
        if len(crudo) < 500:
            continue
        # El archivo NO viene en UTF-8: viene en la codificación de Windows para
        # Europa occidental. Leerlo como UTF-8 rompe en el primer acento.
        for codificacion in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return candidato, crudo.decode(codificacion), url
            except UnicodeDecodeError:
                continue
    raise RuntimeError(
        "No se halló ninguna edición de la clasificación en los últimos tres años. "
        "NO se publica la anterior como si fuera la vigente: si la fuente cambió de "
        "dirección, el registro se queda sin el dato y lo dice.")


def recolectar():
    anio, texto, url = _traer()
    filas = list(csv.DictReader(io.StringIO(texto), delimiter=";"))
    porIso = {f.get("ISO", "").strip(): f for f in filas if f.get("ISO")}

    registros, conDato = [], 0
    for pais in geo.padron():
        f = porIso.get(pais["iso"])
        if not f:
            registros.append({
                "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
                "estado": "sin_evaluar",
            })
            continue
        conDato += 1
        dims = {}
        for columna, clave, _rot in DIMENSIONES:
            v = _numero(f.get(columna))
            if v is not None:
                dims[clave] = v
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": "evaluado",
            "puntaje": _numero(f.get(f"Score {anio}") or f.get("Score")),
            "puesto_mundial": _numero(f.get("Rank")),
            "dimensiones": dims,
        })

    sinEvaluar = [r["pais"] for r in registros if r["estado"] == "sin_evaluar"]

    vacios = [
        "MIDE LAS CONDICIONES PARA EJERCER EL PERIODISMO, NO CUANTA DESINFORMACION "
        "CIRCULA. Son cosas distintas: un Estado puede tener prensa libre y mucha "
        "desinformacion, y otro puede tener poca desinformacion VISIBLE porque nadie "
        "puede publicar nada. La relacion suele ser inversa a la intuicion: donde la "
        "prensa esta mas cercada, menos desinformacion se detecta, porque detectarla "
        "tambien es publicar.",
        "ES EVALUACION EXPERTA, NO MEDICION INSTRUMENTAL. El puntaje sale de una "
        "encuesta a periodistas, academicos y defensores de derechos humanos, combinada "
        "con un recuento de abusos. Dos personas informadas pueden puntuar distinto el "
        "mismo pais, y por eso entra calificada como evaluacion y no como registro.",
        f"NO EVALUA A LOS {len(sinEvaluar)} ESTADOS MAS CHICOS DEL CARIBE: "
        f"{', '.join(sinEvaluar)}. Eso NO significa que tengan prensa libre ni que no la "
        "tengan: significa que la fuente no los evalua, y el registro lo dice en lugar "
        "de dejarlos en blanco.",
        "EL PUESTO MUNDIAL ORDENA CONTRA 180 PAISES, no contra los 33 del padron. Un "
        "Estado de la region puede estar bien situado en el mundo y mal en su zona, o al "
        "reves: son dos preguntas distintas y esta cifra contesta la primera.",
        "UNA EDICION POR ANIO. Entre ediciones la cifra NO se mueve aunque el pais si: "
        "sirve para comparar Estados en un momento, no para seguir una crisis.",
    ]

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=3,
        corroborado=False,
        nota=("Organizacion internacional de defensa de la libertad de prensa, con "
              "metodologia publicada y serie anual. Fiabilidad B porque es una "
              "organizacion con posicion tomada sobre la materia que mide —lo cual no la "
              "invalida, pero se declara—. Credibilidad 3 porque el puntaje es "
              "EVALUACION EXPERTA agregada, no un hecho verificable de forma "
              "independiente."),
    )

    return comun.escribir(
        colector="prensa_libre",
        capa="publico",
        fuente="Reporteros Sin Fronteras — clasificación mundial de la libertad de prensa",
        url_fuente=url,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "edicion": anio,
                "estados_evaluados": conDato,
                "estados_sin_evaluar": len(sinEvaluar),
                "estados_del_padron": len(registros),
                "paises_en_la_clasificacion": len(porIso),
                "consultado": comun.ahora(),
            },
            "dimensiones": [{"clave": c, "rotulo": r} for _col, c, r in DIMENSIONES],
            "sin_evaluar": sinEvaluar,
        },
    )


if __name__ == "__main__":
    comun.correr("prensa_libre", recolectar)
