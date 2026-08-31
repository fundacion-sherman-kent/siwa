"""Democracia, terrorismo y conflicto no estatal.

Fuente: **Our World in Data**, que publica en planilla limpia y con licencia
abierta lo que los productores originales entregan en formatos que no se pueden
consumir de forma automatizada.

Los productores originales, que son quienes responden por el dato
--------------------------------------------------------------
- **V-Dem**, Instituto de Variedades de Democracia, Universidad de Gotemburgo.
  Los seis índices de gobernanza. Se construyen con el juicio codificado de
  varios especialistas por país y año, y **publican su propio intervalo de
  incertidumbre**: acá se toma la estimación central.
- **Base Global de Terrorismo**, consorcio START, Universidad de Maryland.
  Atentados y muertes.
- **UCDP**, Programa de Datos de Conflicto de Upsala. Muertes en conflicto no
  estatal, es decir enfrentamientos armados **entre grupos, sin el Estado como
  parte**: en esta región eso es, en buena medida, disputa entre organizaciones
  criminales por territorio o por renta.

Por qué no se consultó a cada productor directamente
----------------------------------------------------
Se intentó. La interfaz de UCDP devuelve **401 sin credencial**; V-Dem publica el
conjunto completo en un archivo de 34 MB pensado para un programa estadístico, no
para consulta; la Base Global de Terrorismo exige registro académico. Our World
in Data republica las tres con licencia **Creative Commons de atribución**, que sí
admite uso comercial, y mantiene la dirección estable.

**La atribución va al productor original en cada ficha**, no a quien republica.
"""

from __future__ import annotations

import csv
import io
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import comun
import geo

VENTANA = 12          # años hacia atrás desde el último dato de cada serie
NAVEGADOR = comun.AGENTE

SERIES = [
    {"clave": "democracia_electoral", "slug": "electoral-democracy-index",
     "columna": "electdem_vdem__estimate_best",
     "rotulo": "Nivel democratico — democracia electoral", "eje": "Gobernanza",
     "unidad": "indice de 0 a 1", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Es el NIVEL DEMOCRATICO medido por elecciones limpias, sufragio, "
                "libertad de expresion y asociacion. Se construye con el juicio "
                "codificado de varios especialistas por pais y anio: es una medicion "
                "experta, no un recuento de hechos. V-Dem publica un intervalo de "
                "incertidumbre propio; aca se toma la estimacion central."},
    {"clave": "democracia_liberal", "slug": "liberal-democracy-index",
     "columna": "libdem_vdem__estimate_best",
     "rotulo": "Democracia liberal — limites al poder", "eje": "Gobernanza",
     "unidad": "indice de 0 a 1", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Agrega a lo electoral los limites efectivos al poder ejecutivo: "
                "control judicial y legislativo, y proteccion de las libertades "
                "individuales. La brecha con el indice electoral muestra Estados que "
                "votan pero no controlan a quien gobierna."},
    {"clave": "democracia_participativa", "slug": "participatory-democracy-index",
     "columna": "participdem_vdem__estimate_best",
     "rotulo": "Democracia participativa", "eje": "Gobernanza",
     "unidad": "indice de 0 a 1", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Mide participacion mas alla del voto: sociedad civil organizada, "
                "gobierno local electo y mecanismos de democracia directa."},
    {"clave": "corrupcion_politica", "slug": "political-corruption-index",
     "columna": "corruption_vdem__estimate_best",
     "rotulo": "Corrupcion politica", "eje": "Gobernanza",
     "unidad": "indice de 0 a 1", "mas_es_peor": True,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Abarca al ejecutivo, al legislativo, a la administracion y a la "
                "justicia. ATENCION: en este indice el valor ALTO es el peor, al reves "
                "que en los demas indices de V-Dem."},
    {"clave": "libertad_expresion", "slug": "freedom-of-expression-index",
     "columna": "freeexpr_vdem__estimate_best",
     "rotulo": "Libertad de expresion y de prensa", "eje": "Gobernanza",
     "unidad": "indice de 0 a 1", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Censura estatal a los medios, represalia contra periodistas y "
                "libertad academica. Se lee junto con la cobertura noticiosa de este "
                "mismo registro: donde la libertad cae, la corroboracion cruzada vale mas."},
    {"clave": "libertad_asociacion", "slug": "freedom-of-association-index",
     "columna": "freeassoc_vdem__estimate_best",
     "rotulo": "Libertad de asociacion y partidos", "eje": "Gobernanza",
     "unidad": "indice de 0 a 1", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Libertad para formar partidos y organizaciones civiles, y grado de "
                "represion sobre ellas. Es la materia de CONFLICTO POLITICO leida por "
                "el lado del espacio disponible para la oposicion."},
    {"clave": "terrorismo_muertes", "slug": "terrorism-deaths",
     "columna": "total_killed",
     "rotulo": "Muertes por atentados terroristas", "eje": "Seguridad",
     "unidad": "personas por anio", "mas_es_peor": True,
     "origen": "Base Global de Terrorismo, consorcio START, Universidad de Maryland, "
               "via Our World in Data",
     "cautela": "LA SERIE TERMINA EN 2021: la Base Global de Terrorismo dejo de "
                "actualizarse. No hay dato posterior y no se estima ninguno. Ademas, "
                "la definicion de terrorismo es disputada y varios Estados de la region "
                "califican como terrorista a la protesta social."},
    {"clave": "terrorismo_atentados", "slug": "terrorist-attacks",
     "columna": "total_incident_counts",
     "rotulo": "Atentados terroristas registrados", "eje": "Seguridad",
     "unidad": "hechos por anio", "mas_es_peor": True,
     "origen": "Base Global de Terrorismo, consorcio START, Universidad de Maryland, "
               "via Our World in Data",
     "cautela": "Misma advertencia: LA SERIE TERMINA EN 2021. Cuenta hechos "
                "registrados, de modo que un Estado con mejor registro puede aparecer "
                "peor que uno que no lleva la cuenta."},
    {"clave": "conflicto_no_estatal", "slug": "deaths-in-non-state-conflicts",
     "columna": None,   # se resuelve sola: es la unica columna de valor
     "rotulo": "Muertes en conflicto entre grupos armados", "eje": "Seguridad",
     "unidad": "personas por anio", "mas_es_peor": True,
     "origen": "UCDP, Programa de Datos de Conflicto de Upsala, via Our World in Data",
     "cautela": "Enfrentamientos armados ENTRE GRUPOS, sin el Estado como parte. En "
                "esta region eso es, en buena medida, disputa entre organizaciones "
                "criminales por territorio o por renta: es el indicador de PRESENCIA DE "
                "GRUPOS CRIMINALES ORGANIZADOS que mas se acerca, y aun asi solo cuenta "
                "muertes en enfrentamiento, no presencia ni control territorial. El "
                "umbral de UCDP exige 25 muertes anuales para registrar un conflicto: "
                "por debajo de eso el pais figura en cero sin estar en paz."},
]


def _traer(serie: dict) -> tuple:
    """Trae una planilla. Devuelve (serie, filas, falla)."""
    url = (f"https://ourworldindata.org/grapher/{serie['slug']}.csv"
           f"?csvType=full&useColumnShortNames=true")
    try:
        peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
        with urllib.request.urlopen(peticion, timeout=180) as respuesta:
            texto = respuesta.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return serie, [], f"HTTP {error.code}"
    except Exception as error:  # noqa: BLE001 — la falla se declara, no se oculta
        return serie, [], type(error).__name__
    return serie, list(csv.DictReader(io.StringIO(texto))), None


def recolectar():
    padron = geo.padron()
    isos = {p["iso"] for p in padron}

    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        crudo = list(ejecutor.map(_traer, SERIES))

    caidas = [f"{s['rotulo']}: {f}" for s, _, f in crudo if f]
    datos = {p["iso"]: {} for p in padron}
    cobertura, en_servicio = {}, []

    for serie, filas, falla in crudo:
        if falla or not filas:
            continue
        columna = serie["columna"]
        if not columna:
            candidatas = [c for c in filas[0]
                          if c not in ("entity", "code", "year", "owid_region")]
            if not candidatas:
                continue
            columna = candidatas[0]
        if columna not in filas[0]:
            caidas.append(f"{serie['rotulo']}: la columna «{columna}» ya no existe")
            continue

        por_pais = {}
        for fila in filas:
            iso, bruto = fila.get("code"), fila.get(columna)
            if iso not in isos or bruto in (None, ""):
                continue
            try:
                anio, valor = int(fila["year"]), float(bruto)
            except (TypeError, ValueError):
                continue
            if valor != valor or valor in (float("inf"), float("-inf")):
                continue
            por_pais.setdefault(iso, []).append({"anio": anio, "valor": valor})

        if not por_pais:
            caidas.append(f"{serie['rotulo']}: ningun Estado del padron tiene dato")
            continue

        # La ventana se cuenta desde el ultimo anio con dato de la propia serie:
        # la de terrorismo termina en 2021 y la de democracia llega a 2025.
        ultimo_global = max(p[-1]["anio"] for p in
                            (sorted(v, key=lambda x: x["anio"]) for v in por_pais.values()))
        desde = ultimo_global - VENTANA

        for iso, puntos in por_pais.items():
            puntos.sort(key=lambda x: x["anio"])
            ventana = [p for p in puntos if p["anio"] >= desde]
            if not ventana:
                continue
            ultimo, primero = ventana[-1], ventana[0]
            anterior = ventana[-2] if len(ventana) > 1 else None
            datos[iso][serie["clave"]] = {
                "valor": ultimo["valor"],
                "anio": ultimo["anio"],
                "anio_anterior": anterior["anio"] if anterior else None,
                "variacion_pct": (
                    (ultimo["valor"] - anterior["valor"]) / abs(anterior["valor"]) * 100
                    if anterior and anterior["valor"] else None),
                "anio_inicial": primero["anio"],
                "valor_inicial": primero["valor"],
                "tendencia_ventana_pct": (
                    (ultimo["valor"] - primero["valor"]) / abs(primero["valor"]) * 100
                    if primero["valor"] else None),
                "serie": ventana,
            }
        cobertura[serie["clave"]] = len(por_pais)
        en_servicio.append({k: serie[k] for k in
                            ("clave", "rotulo", "eje", "unidad", "mas_es_peor",
                             "origen", "cautela")} | {"fuente_slug": serie["slug"]})

    registros = [{"iso": p["iso"], "pais": p["pais"], "bloque": p["bloque"],
                  "indicadores": datos[p["iso"]]}
                 for p in padron if datos[p["iso"]]]

    sin_vdem = sorted(p["pais"] for p in padron
                      if "democracia_electoral" not in datos[p["iso"]])
    vacios = [
        "V-Dem no cubre a los Estados chicos del Caribe: "
        + (", ".join(sin_vdem) if sin_vdem else "ninguno")
        + ". Sin dato no significa sin democracia ni sin problema: significa que el "
          "proyecto no los codifica.",
        "LA SERIE DE TERRORISMO TERMINA EN 2021. La Base Global de Terrorismo dejo de "
        "actualizarse y no hay reemplazo gratuito. No se estima ningun valor posterior.",
        "«Terrorismo» es una definicion disputada. Varios Estados de la region califican "
        "de terrorista a la protesta social, y esa calificacion entra en las bases que "
        "se nutren de prensa. El dato se publica con esa advertencia y no sostiene por "
        "si solo ningun juicio.",
        "El conflicto entre grupos armados exige 25 muertes anuales para que UCDP lo "
        "registre. Por debajo de ese umbral el Estado figura en cero SIN ESTAR EN PAZ. "
        "Y cuenta muertes en enfrentamiento, no presencia ni control territorial: NO es "
        "una medida de cuanto territorio dominan los grupos criminales.",
        "Los indices de V-Dem son medicion experta codificada, no recuento de hechos. "
        "El proyecto publica un intervalo de incertidumbre por dato; aca se toma la "
        "estimacion central y el intervalo no se muestra.",
        "PERCEPCION democratica y de las instituciones: NO HAY DATO. Latinobarometro y "
        "el Barometro de las Americas la miden, pero exigen registro para descargar los "
        "microdatos. Lo que se publica aca es el nivel democratico segun especialistas, "
        "que es otra cosa: mide como funciona el sistema, no que piensa la gente de el.",
        "CONFLICTO URBANO: no hay fuente gratuita comparable para los 33. Lo que mas se "
        "acerca es el conflicto entre grupos armados, que no distingue campo de ciudad.",
    ]
    if caidas:
        vacios.append("Series que fallaron en esta corrida: " + "; ".join(caidas))

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=2,
        corroborado=False,
        nota=("Proyectos academicos con metodo publicado y revision por pares. Se "
              "consultan por medio de Our World in Data, que republica con licencia "
              "abierta lo que los productores entregan en formatos no consultables. "
              "La responsabilidad por el dato es del productor original, citado en "
              "cada indicador."),
    )

    return comun.escribir(
        colector="owd",
        capa="publico",
        fuente="V-Dem, Base Global de Terrorismo y UCDP, via Our World in Data",
        url_fuente="https://ourworldindata.org/grapher/electoral-democracy-index",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": en_servicio,
            "cobertura": cobertura,
            "ventana_anios": VENTANA,
            "licencia": ("Creative Commons de atribucion. Admite uso comercial con "
                         "atribucion al productor original."),
        },
    )


if __name__ == "__main__":
    comun.correr("owd", recolectar)
