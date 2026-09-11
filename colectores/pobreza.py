"""Pobreza por ingresos — CEPALSTAT, la fuente estadística de la propia región.

**Es la única fuente estadística del registro que es nativa de América Latina y
el Caribe.** La Comisión Económica para América Latina y el Caribe es la comisión
regional de las Naciones Unidas para esta región: no mira desde afuera, y publica
en castellano.

El robot la tenía anotada como candidata desde hacía semanas con una traba
declarada —«500, error interno del servidor»— y **esa traba ya no existe**. Se
volvió a probar y la puerta abre.

Qué mide
--------
El porcentaje de personas con ingresos por debajo de **tres umbrales distintos**,
en dólares de paridad de poder adquisitivo por día: **3,0** —pobreza extrema—,
**4,1** y **8,3**. Los tres se publican por separado, sin promediarlos: son tres
preguntas y no una.

Lo que hay que tener presente
-----------------------------
**Sale de encuestas de hogares, no de un censo ni de un registro.** Cada Estado
levanta la suya con su propia periodicidad, y por eso **el último año disponible
no es el mismo para todos**: comparar el 2024 de uno con el 2019 de otro es
comparar dos momentos distintos del mundo. Cada ficha publica su año.

**Y el umbral en dólares de paridad no es lo que cuesta vivir en cada país.** Es
una vara común para poder comparar; la línea de pobreza que cada Estado usa para
su política social es otra, y suele ser distinta.
"""

from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.error
import urllib.request

import comun
import geo

BASE = "https://api-cepalstat.cepal.org/cepalstat/api/v1"
INDICADOR = 160
FUENTE = ("CEPALSTAT — Comisión Económica para América Latina y el Caribe "
          "(Naciones Unidas)")
URL_FUENTE = "https://statistics.cepal.org/portal/cepalstat/"
NAVEGADOR = comun.AGENTE

ESPERA = 120
INTENTOS = 3
DESCANSO = 10
VENTANA = 12             # años de serie que se publican por Estado

# PROBAR ANTES DE AFIRMAR: si ningun Estado del padron trae dato, lo que fallo es
# la lectura y no la pobreza de la region.
MINIMO_ESTADOS = 12
MINIMO_FILAS = 500

# Los tres umbrales, reconocidos POR LO QUE DICEN y no por su numero interno: si
# la CEPAL agrega o renumera un umbral, se declara en vez de publicar el valor de
# un umbral bajo el rotulo de otro.
UMBRALES = [
    {"clave": "extrema", "dolares": 3.0, "rotulo": "Pobreza extrema",
     "dice": "Personas con ingresos menores a 3,0 dólares de paridad por día."},
    {"clave": "pobreza", "dolares": 4.1, "rotulo": "Pobreza",
     "dice": "Personas con ingresos menores a 4,1 dólares de paridad por día."},
    {"clave": "vulnerabilidad", "dolares": 8.3, "rotulo": "Ingresos bajos",
     "dice": "Personas con ingresos menores a 8,3 dólares de paridad por día. No "
             "es pobreza según esta escala: marca a quienes viven cerca del límite."},
]


# LAS MATERIAS. Este conjunto existía y no era una materia: alimentaba una vista
# propia y nada más. La pobreza la medía solo el Banco Mundial, con la línea
# nacional de cada Estado; esta la mide con metodología propia y comparable, que
# es otra manera de contar pobres.
MATERIAS_POBREZA = [
    {"clave": "pobreza_cepal", "campo": "pobreza",
     "rotulo": "Pobreza · segunda fuente", "eje": "Desarrollo",
     "unidad": "% de las personas", "mas_es_peor": True,
     "cautela": "SEGUNDA MEDICIÓN de algo que el registro ya publica con el Banco Mundial. "
                "No miden lo mismo de la misma manera: aquella usa la línea de pobreza que "
                "fija cada Estado, y esta una metodología regional comparable. Si difieren, "
                "la diferencia dice cómo define la pobreza cada quien, no quién se equivoca."},
    {"clave": "pobreza_extrema", "campo": "extrema",
     "rotulo": "Pobreza extrema", "eje": "Desarrollo",
     "unidad": "% de las personas", "mas_es_peor": True,
     "cautela": "Quienes no cubren la canasta básica de alimentos. Es el piso duro: por "
                "debajo de esta línea no se trata de desigualdad sino de hambre."},
    {"clave": "vulnerabilidad", "campo": "vulnerabilidad",
     "rotulo": "Población vulnerable a la pobreza", "eje": "Desarrollo",
     "unidad": "% de las personas", "mas_es_peor": True,
     "cautela": "Quienes no son pobres hoy y caerían con un golpe —una enfermedad, un "
                "despido, una devaluación—. Es la medida que explica por qué la pobreza "
                "sube tan rápido en las crisis de esta región."},
]


def _ficha(serie, campo):
    """La forma que usa todo el registro para cualquier serie."""
    puntos = [(x["anio"], x[campo]) for x in serie
              if x.get(campo) is not None and x.get("anio")]
    if not puntos:
        return None
    puntos.sort()
    anio, valor = puntos[-1]
    ant = puntos[-2] if len(puntos) >= 2 else None
    return {
        "valor": valor, "anio": anio,
        "anio_anterior": ant[0] if ant else None,
        "valor_anterior": ant[1] if ant else None,
        "variacion_pct": (round((valor - ant[1]) / abs(ant[1]) * 100, 1)
                          if ant and ant[1] else None),
        "anio_inicial": puntos[0][0], "valor_inicial": puntos[0][1],
        "tendencia_ventana_pct": (round((valor - puntos[0][1]) / abs(puntos[0][1]) * 100, 1)
                                  if len(puntos) >= 3 and puntos[0][1] else None),
        "serie": [{"anio": a, "valor": v} for a, v in puntos],
    }


def _pedir(ruta: str) -> dict:
    url = f"{BASE}/{ruta}"
    ultimo = ""
    for intento in range(INTENTOS):
        try:
            peticion = urllib.request.Request(url, headers={
                "User-Agent": NAVEGADOR, "Accept": "application/json",
                "Accept-Language": "es"})
            with urllib.request.urlopen(peticion, timeout=ESPERA,
                                        context=ssl.create_default_context()) as r:
                return json.loads(r.read(40_000_000).decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"CEPALSTAT respondió HTTP {e.code} en «{ruta}»") from e
        except Exception as e:  # noqa: BLE001 — falla de red: se reintenta
            ultimo = f"{type(e).__name__}: {e}"
            print(f"[pobreza] intento {intento + 1} de {INTENTOS}: {ultimo}",
                  file=sys.stderr)
            time.sleep(DESCANSO * (intento + 1))
    raise RuntimeError(f"CEPALSTAT no respondió en {INTENTOS} intentos: {ultimo}")


def _dimension(cuerpo: dict, pedazo: str) -> dict:
    """La dimensión que se busca, hallada por su nombre y no por su posición."""
    for dim in cuerpo.get("dimensions") or []:
        if pedazo.lower() in str(dim.get("name", "")).lower():
            return dim
    raise RuntimeError(
        f"No se halló la dimensión «{pedazo}» entre "
        f"{[d.get('name') for d in cuerpo.get('dimensions') or []]}. El indicador "
        "cambió de forma y no se publica una lectura a ciegas.")


def _numero(valor):
    try:
        return round(float(valor), 1)
    except (TypeError, ValueError):
        return None


def recolectar():
    respuesta = _pedir(f"indicator/{INDICADOR}/data?lang=es&format=json")
    cabeza = respuesta.get("header") or {}
    if not cabeza.get("success"):
        raise RuntimeError(
            f"CEPALSTAT contestó sin éxito declarado: {json.dumps(cabeza)[:200]}. "
            "No se publica.")
    cuerpo = respuesta.get("body") or {}
    datos = cuerpo.get("data") or []
    if len(datos) < MINIMO_FILAS:
        raise RuntimeError(
            f"Llegaron {len(datos)} filas y se esperaban al menos {MINIMO_FILAS}: "
            "la lectura vino corta o el indicador cambió. No se publica.")

    anios_dim = _dimension(cuerpo, "años")
    umbral_dim = _dimension(cuerpo, "dólares")
    anio_de = {m["id"]: _numero(m["name"]) for m in anios_dim["members"]}
    clave_anio = f"dim_{anios_dim['id']}"
    clave_umbral = f"dim_{umbral_dim['id']}"

    # Cada umbral se reconoce por la cifra que su propio rotulo declara.
    porMiembro = {}
    for miembro in umbral_dim["members"]:
        rotulo = str(miembro.get("name", ""))
        for u in UMBRALES:
            if str(u["dolares"]) in rotulo:
                porMiembro[miembro["id"]] = u
                break
    faltan = [u["rotulo"] for u in UMBRALES
              if u not in porMiembro.values()]
    if faltan:
        raise RuntimeError(
            f"No se hallaron los umbrales {faltan} entre los que publica el "
            f"indicador: {[m.get('name') for m in umbral_dim['members']]}. Cambió la "
            "escala y no se publica un umbral bajo el rótulo de otro.")

    isos = {p["iso"] for p in geo.padron()}
    porIso: dict = {}
    for fila in datos:
        iso = str(fila.get("iso3") or "").strip().upper()
        umbral = porMiembro.get(fila.get(clave_umbral))
        anio = anio_de.get(fila.get(clave_anio))
        valor = _numero(fila.get("value"))
        # Los agregados —«América Latina», «América Central»— vienen SIN iso3, y
        # por eso el filtro por iso3 los deja afuera solo: no son Estados.
        if iso not in isos or not umbral or anio is None or valor is None:
            continue
        porIso.setdefault(iso, {}).setdefault(int(anio), {})[umbral["clave"]] = valor

    if len(porIso) < MINIMO_ESTADOS:
        raise RuntimeError(
            f"Sólo {len(porIso)} de los 33 Estados trajeron dato, y se esperaban al "
            f"menos {MINIMO_ESTADOS}. Eso no describe a la región: describe una "
            "lectura fallida. No se publica.")

    fuentes = {f["id"]: f for f in (cuerpo.get("sources") or [])}
    registros = []
    for pais in geo.padron():
        porAnio = porIso.get(pais["iso"]) or {}
        registro = {"iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
                    "medido": bool(porAnio)}
        if porAnio:
            ultimo = max(porAnio)
            registro["anio"] = ultimo
            for u in UMBRALES:
                registro[u["clave"]] = porAnio[ultimo].get(u["clave"])
            serie = [{"anio": a, **porAnio[a]} for a in sorted(porAnio)[-VENTANA:]]
            registro["serie"] = serie
            primero = serie[0]
            if len(serie) > 1 and primero.get("pobreza") is not None \
                    and registro.get("pobreza") is not None:
                registro["variacion"] = round(registro["pobreza"] - primero["pobreza"], 1)
                registro["desde"] = primero["anio"]
        else:
            registro["por_que_no"] = (
                "CEPALSTAT no publica este indicador para este Estado: la mayoría de "
                "los Estados chicos del Caribe no levantan la encuesta de hogares con "
                "la que se construye.")
        registros.append(registro)
    registros.sort(key=lambda r: (not r["medido"], -(r.get("pobreza") or -1), r["pais"]))

    medidos = [r for r in registros if r["medido"]]
    sin_medir = [r["pais"] for r in registros if not r["medido"]]
    anios = sorted({r["anio"] for r in medidos})

    vacios = [
        "**Sale de encuestas de hogares, no de un censo ni de un registro.** Cada "
        "Estado levanta la suya con su periodicidad, y por eso **el último año "
        "disponible no es el mismo para todos**: comparar el dato de un Estado con el "
        "de otro puede ser comparar dos momentos distintos. Cada ficha publica su año, "
        "y hay que mirarlo antes de comparar.",
        "**El umbral en dólares de paridad no es lo que cuesta vivir en cada país.** Es "
        "una vara común para poder comparar. La línea de pobreza que cada Estado usa "
        "para su política social es otra y suele ser distinta: un Estado puede tener "
        "más pobres según su propia medición que según ésta, o al revés.",
        "**Los tres umbrales no se suman ni se promedian.** Quien está por debajo de "
        "3,0 dólares también está por debajo de 4,1 y de 8,3: son tres cortes de la "
        "misma distribución, no tres grupos distintos.",
        f"**{len(sin_medir)} Estados no tienen dato**"
        + (f": {', '.join(sin_medir)}. " if sin_medir else ". ")
        + "Son en su mayoría los del Caribe chico, que no levantan la encuesta de "
          "hogares con la que se construye este indicador. **No significa que no "
          "tengan pobreza: significa que no se la mide así.**",
        "**Mide ingresos, no privación.** Alguien puede estar por encima del umbral y "
        "no tener agua, cloaca ni escuela cerca. La pobreza multidimensional es otra "
        "medición y este registro todavía no la trae.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Comisión regional de las Naciones Unidas para América Latina y el "
              "Caribe, con metodología publicada y armonización declarada entre las "
              "encuestas nacionales. Es la fuente estadística nativa de la región. Lo "
              "que se registra es su estimación armonizada, no el dato crudo de cada "
              "encuesta nacional."),
    )

    for r in registros:
        fichas = {}
        for m in MATERIAS_POBREZA:
            f = _ficha(r.get("serie") or [], m["campo"])
            if f:
                fichas[m["clave"]] = f
        r["indicadores"] = fichas   # siempre presente, vacío si no hay serie

    return comun.escribir(
        colector="pobreza",
        capa="publico",
        fuente=FUENTE,
        url_fuente=URL_FUENTE,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": [{"clave": m["clave"], "rotulo": m["rotulo"], "eje": m["eje"],
                             "unidad": m["unidad"], "mas_es_peor": m["mas_es_peor"],
                             "origen": "CEPALSTAT — Comisión Económica para América Latina y el Caribe",
                             "cautela": m["cautela"]} for m in MATERIAS_POBREZA],
            "cobertura": {m["clave"]: sum(1 for r in registros
                                          if (r.get("indicadores") or {}).get(m["clave"]))
                          for m in MATERIAS_POBREZA},
            "resumen": {
                "indicador": (cuerpo.get("metadata") or {}).get("indicator_name"),
                "unidad": (cuerpo.get("metadata") or {}).get("unit"),
                "estados_medidos": len(medidos),
                "estados_del_padron": len(registros),
                "anio_mas_nuevo": max(anios) if anios else None,
                "anio_mas_viejo": min(anios) if anios else None,
                "filas_leidas": len(datos),
                "consultado": comun.ahora(),
            },
            "umbrales": [{"clave": u["clave"], "rotulo": u["rotulo"],
                          "dolares": u["dolares"], "dice": u["dice"]}
                         for u in UMBRALES],
            "fuentes_declaradas": [
                {"organismo": f.get("organization_name"),
                 "descripcion": f.get("description")}
                for f in fuentes.values()][:6],
        },
    )


if __name__ == "__main__":
    comun.correr("pobreza", recolectar)
