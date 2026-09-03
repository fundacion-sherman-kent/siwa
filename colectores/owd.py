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
     "rotulo": "Nivel democrático — democracia electoral", "eje": "Gobernanza",
     "unidad": "índice de 0 a 1", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Es el NIVEL DEMOCRATICO medido por elecciones limpias, sufragio, "
                "libertad de expresión y asociación. Se construye con el juicio "
                "codificado de varios especialistas por país y año: es una medición "
                "experta, no un recuento de hechos. V-Dem publica un intervalo de "
                "incertidumbre propio; acá se toma la estimación central."},
    {"clave": "democracia_liberal", "slug": "liberal-democracy-index",
     "columna": "libdem_vdem__estimate_best",
     "rotulo": "Democracia liberal — límites al poder", "eje": "Gobernanza",
     "unidad": "índice de 0 a 1", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Agrega a lo electoral los límites efectivos al poder ejecutivo: "
                "control judicial y legislativo, y protección de las libertades "
                "individuales. La brecha con el índice electoral muestra Estados que "
                "votan pero no controlan a quien gobierna."},
    {"clave": "democracia_participativa", "slug": "participatory-democracy-index",
     "columna": "participdem_vdem__estimate_best",
     "rotulo": "Democracia participativa", "eje": "Gobernanza",
     "unidad": "índice de 0 a 1", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Mide participación mas allá del voto: sociedad civil organizada, "
                "gobierno local electo y mecanismos de democracia directa."},
    {"clave": "corrupcion_politica", "slug": "political-corruption-index",
     "columna": "corruption_vdem__estimate_best",
     "rotulo": "Corrupción política", "eje": "Gobernanza",
     "unidad": "índice de 0 a 1", "mas_es_peor": True,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Abarca al ejecutivo, al legislativo, a la administración y a la "
                "justicia. ATENCIÓN: en este índice el valor ALTO es el peor, al revés "
                "que en los demas índices de V-Dem."},
    {"clave": "libertad_expresion", "slug": "freedom-of-expression-index",
     "columna": "freeexpr_vdem__estimate_best",
     "rotulo": "Libertad de expresión y de prensa", "eje": "Gobernanza",
     "unidad": "índice de 0 a 1", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Censura estatal a los medios, represalia contra periodistas y "
                "libertad academica. Se lee junto con la cobertura noticiosa de este "
                "mismo registro: donde la libertad cae, la corroboración cruzada vale mas."},
    {"clave": "libertad_asociacion", "slug": "freedom-of-association-index",
     "columna": "freeassoc_vdem__estimate_best",
     "rotulo": "Libertad de asociación y partidos", "eje": "Gobernanza",
     "unidad": "índice de 0 a 1", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Libertad para formar partidos y organizaciones civiles, y grado de "
                "represión sobre ellas. Es la materia de CONFLICTO POLÍTICO leida por "
                "el lado del espacio disponible para la oposición."},
    {"clave": "terrorismo_muertes", "slug": "terrorism-deaths",
     "columna": "total_killed",
     "rotulo": "Muertes por atentados terroristas", "eje": "Seguridad",
     "unidad": "personas por año", "mas_es_peor": True,
     "origen": "Base Global de Terrorismo, consorcio START, Universidad de Maryland, "
               "via Our World in Data",
     "cautela": "LA SERIE TERMINA EN 2021: la Base Global de Terrorismo dejo de "
                "actualizarse. No hay dato posterior y no se estima ninguno. Además, "
                "la definición de terrorismo es disputada y varios Estados de la región "
                "califican como terrorista a la protesta social."},
    {"clave": "terrorismo_atentados", "slug": "terrorist-attacks",
     "columna": "total_incident_counts",
     "rotulo": "Atentados terroristas registrados", "eje": "Seguridad",
     "unidad": "hechos por año", "mas_es_peor": True,
     "origen": "Base Global de Terrorismo, consorcio START, Universidad de Maryland, "
               "via Our World in Data",
     "cautela": "Misma advertencia: LA SERIE TERMINA EN 2021. Cuenta hechos "
                "registrados, de modo que un Estado con mejor registro puede aparecer "
                "peor que uno que no lleva la cuenta."},
    {"clave": "conflicto_no_estatal", "slug": "deaths-in-non-state-conflicts",
     "columna": None,   # se resuelve sola: es la unica columna de valor
     "rotulo": "Muertes en conflicto entre grupos armados", "eje": "Seguridad",
     "unidad": "personas por año", "mas_es_peor": True,
     "origen": "UCDP, Programa de Datos de Conflicto de Upsala, via Our World in Data",
     "cautela": "Enfrentamientos armados ENTRE GRUPOS, sin el Estado como parte. En "
                "esta región eso es, en buena medida, disputa entre organizaciones "
                "criminales por territorio o por renta: es el indicador de PRESENCIA DE "
                "GRUPOS CRIMINALES ORGANIZADOS que mas se acerca, y aun así solo cuenta "
                "muertes en enfrentamiento, no presencia ni control territorial. El "
                "umbral de UCDP exige 25 muertes anuales para registrar un conflicto: "
                "por debajo de eso el país figura en cero sin estar en paz."},
    {"clave": "objetos_espacio", "slug": "cumulative-number-of-objects-launched-into-outer-space",
     "columna": None,
     "rotulo": "Objetos puestos en órbita, acumulado", "eje": "Defensa",
     "unidad": "objetos", "mas_es_peor": False,
     "origen": "Oficina de Asuntos del Espacio Ultraterrestre de Naciones Unidas, "
               "via Our World in Data",
     "cautela": "Es la única medida de CAPACIDAD AEROESPACIAL comparable y gratuita que "
                "se encontro para la región. Cuenta objetos registrados ante Naciones "
                "Unidas por cada Estado: satelites propios, no necesariamente lanzados "
                "por el. NO mide capacidad de lanzamiento, ni satelites militares, ni "
                "aviación. Solo 13 de los 33 Estados registran alguno."},
    {"clave": "lanzamientos_anuales", "slug": "yearly-number-of-objects-launched-into-outer-space",
     "columna": None,
     "rotulo": "Objetos puestos en órbita por año", "eje": "Defensa",
     "unidad": "objetos por año", "mas_es_peor": False,
     "origen": "Oficina de Asuntos del Espacio Ultraterrestre de Naciones Unidas, "
               "via Our World in Data",
     "cautela": "El movimiento anual detras del acumulado. Un año en cero es lo normal "
                "para casi todos los Estados del padron y no indica retroceso."},
    # --- El entorno informativo -------------------------------------------
    #
    # Las cinco primeras se nombran «ausencia de»: en la escala de V-Dem el valor
    # ALTO es el bueno, y llamarlas «censura» o «sesgo» invitaria a leerlas al
    # reves. Verificado contra controles conocidos con el dato de 2025 —Uruguay
    # 1,90 y Chile 2,65 contra Nicaragua -2,21 y Venezuela -2,04 en censura—, de
    # modo que la orientacion no queda supuesta.
    {"clave": "censura_medios", "slug": "key-media-freedoms",
     "columna": "v2mecenefm__estimate_best",
     "rotulo": "Ausencia de censura estatal a los medios", "eje": "Gobernanza",
     "unidad": "índice de -4 a 4", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Mide el esfuerzo del gobierno por censurar a los medios: cuanto MAS "
                "ALTO, MENOS censura. No cuenta episodios: es evaluación experta "
                "codificada por varios especialistas por país y año."},
    {"clave": "hostigamiento_periodistas", "slug": "key-media-freedoms",
     "columna": "v2meharjrn__estimate_best",
     "rotulo": "Ausencia de hostigamiento a periodistas", "eje": "Gobernanza",
     "unidad": "índice de -4 a 4", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Cuanto MAS ALTO, menos hostigamiento —amenazas, detenciones, "
                "agresiones— a periodistas por su trabajo. Mide el clima, NO la "
                "cantidad de agresiones: para el recuento de hechos no hay fuente "
                "regional que responda de forma automatizada."},
    {"clave": "autocensura", "slug": "key-media-freedoms",
     "columna": "v2meslfcen__estimate_best",
     "rotulo": "Ausencia de autocensura periodistica", "eje": "Gobernanza",
     "unidad": "índice de -4 a 4", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Cuanto MAS ALTO, menos se callan los medios por temor. Es la medida "
                "del efecto que la censura y el hostigamiento dejan cuando ya no hace "
                "falta ejercerlos."},
    {"clave": "sesgo_medios", "slug": "key-media-freedoms",
     "columna": "v2mebias__estimate_best",
     "rotulo": "Ausencia de sesgo en la cobertura", "eje": "Gobernanza",
     "unidad": "índice de -4 a 4", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Cuanto MAS ALTO, mas parejo el trato de los medios a oficialismo y "
                "oposición. Un valor bajo no dice quien esta favorecido: dice que la "
                "cobertura no es pareja."},
    {"clave": "medios_corruptos", "slug": "media-corruption-score",
     "columna": "v2mecorrpt__estimate_best",
     "rotulo": "Ausencia de corrupción en los medios", "eje": "Gobernanza",
     "unidad": "índice de -4 a 4", "mas_es_peor": False,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "Cuanto MAS ALTO, menos frecuente que los medios reciban pagos para "
                "publicar, silenciar o torcer una nota. Es la puerta de entrada de la "
                "desinformación pagada."},
    {"clave": "polarizacion", "slug": "political-polarization-score",
     "columna": "v2cacamps__estimate_best",
     "rotulo": "Polarización política", "eje": "Gobernanza",
     "unidad": "índice de -4 a 4", "mas_es_peor": True,
     "origen": "V-Dem, Universidad de Gotemburgo, via Our World in Data",
     "cautela": "ATENCIÓN: en esta el valor ALTO es el PEOR, al revés que las cinco "
                "anteriores. Mide hasta que punto la sociedad esta partida en campos "
                "irreconciliables. Nicaragua 3,14 y Venezuela 2,23 contra Uruguay -1,81 "
                "con el dato de 2025."},
]


def _traer(slug: str) -> tuple:
    """Trae una planilla. Devuelve (slug, filas, falla)."""
    url = (f"https://ourworldindata.org/grapher/{slug}.csv"
           f"?csvType=full&useColumnShortNames=true")
    try:
        peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
        with urllib.request.urlopen(peticion, timeout=180) as respuesta:
            texto = respuesta.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return slug, [], f"HTTP {error.code}"
    except Exception as error:  # noqa: BLE001 — la falla se declara, no se oculta
        return slug, [], type(error).__name__
    return slug, list(csv.DictReader(io.StringIO(texto))), None


def recolectar():
    padron = geo.padron()
    isos = {p["iso"] for p in padron}

    # Cuatro indicadores del entorno informativo salen de la MISMA planilla:
    # se la pide una sola vez y se reparte, en lugar de bajarla cuatro veces.
    planillas = sorted({s["slug"] for s in SERIES})
    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        traidas = {slug: (filas, falla)
                   for slug, filas, falla in ejecutor.map(_traer, planillas)}
    crudo = [(s, *traidas[s["slug"]]) for s in SERIES]

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
            caidas.append(f"{serie['rotulo']}: ningún Estado del padron tiene dato")
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
        "actualizarse y no hay reemplazo gratuito. No se estima ningún valor posterior.",
        "«Terrorismo» es una definición disputada. Varios Estados de la región califican "
        "de terrorista a la protesta social, y esa calificación entra en las bases que "
        "se nutren de prensa. El dato se publica con esa advertencia y no sostiene por "
        "si solo ningún juicio.",
        "El conflicto entre grupos armados exige 25 muertes anuales para que UCDP lo "
        "registre. Por debajo de ese umbral el Estado figura en cero SIN ESTAR EN PAZ. "
        "Y cuenta muertes en enfrentamiento, no presencia ni control territorial: NO es "
        "una medida de cuanto territorio dominan los grupos criminales.",
        "Los índices de V-Dem son medición experta codificada, no recuento de hechos. "
        "El proyecto publica un intervalo de incertidumbre por dato; acá se toma la "
        "estimación central y el intervalo no se muestra.",
        "PERCEPCION democrática y de las instituciones: NO HAY DATO. Latinobarometro y "
        "el Barometro de las Americas la miden, pero exigen registro para descargar los "
        "microdatos. Lo que se publica acá es el nivel democratico según especialistas, "
        "que es otra cosa: mide como funciona el sistema, no que piensa la gente de el.",
        "DEFENSA, LO QUE NO HAY: no existe fuente gratuita que publique los efectivos "
        "DESAGREGADOS POR ARMA —ejercito, armada, aviación— ni el inventario de "
        "material: vehiculos blindados, aeronaves y buques por tipo. El registro de "
        "referencia es el Balance Militar del Instituto Internacional de Estudios "
        "Estrategicos, que es de pago y no admite redifusión. Lo que se publica acá es "
        "el gasto, los efectivos totales y la ADQUISICION de armamento mayor, que es la "
        "aproximación mas cercana al material y no lo reemplaza.",
        "CONFLICTO URBANO: no hay fuente gratuita comparable para los 33. Lo que mas se "
        "acerca es el conflicto entre grupos armados, que no distingue campo de ciudad.",
    ]
    if caidas:
        vacios.append("Series que fallaron en esta corrida: " + "; ".join(caidas))

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=2,
        corroborado=False,
        nota=("Proyectos academicos con método publicado y revisión por pares. Se "
              "consultan por medio de Our World in Data, que republica con licencia "
              "abierta lo que los productores entregan en formatos no consultables. "
              "La responsabilidad por el dato es del productor original, citado en "
              "cada indicador."),
    )

    return comun.escribir(
        colector="owd",
        capa="publico",
        fuente="V-Dem, Base Global de Terrorismo y UCDP, vía Our World in Data",
        url_fuente="https://ourworldindata.org/grapher/electoral-democracy-index",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": en_servicio,
            "cobertura": cobertura,
            "ventana_anios": VENTANA,
            "licencia": ("Creative Commons de atribución. Admite uso comercial con "
                         "atribución al productor original."),
        },
    )


if __name__ == "__main__":
    comun.correr("owd", recolectar)
