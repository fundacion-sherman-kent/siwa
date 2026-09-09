"""Crimen organizado: qué mercados operan, qué actores los operan, y qué resiste el Estado.

POR QUÉ EXISTE
--------------
La Dirección pidió tres cosas que ninguna fuente del registro cubría: **quiénes
son los actores criminales** —transnacionales y locales—, el **tráfico de flora
y fauna**, y **poder comparar Estados**. Esta fuente contesta las tres de una
vez, y con la misma medida.

Cubre **193 países** con 36 medidas: 15 mercados criminales, 5 tipos de actor y
12 de resiliencia estatal. Entra por la condición de miembro permanente de la
Fundación en la organización que la produce.

LO QUE MIDE, Y CÓMO
-------------------
Es **evaluación experta**, no recuento de hechos. Cada puntaje va de 1 a 10 y lo
fija un panel de especialistas con evidencia documental, revisado por pares y
por expertos regionales. Dos personas informadas pueden puntuar distinto el
mismo país, y por eso entra calificada como evaluación.

**No es tiempo real y no pretende serlo.** La edición es bienal —2019, 2021,
2023, 2025— y describe estructura, no coyuntura: sirve para saber qué opera en
un Estado y con qué fuerza, no qué pasó anoche.

LO QUE NO MIDE
--------------
**Un puntaje alto de mercado no dice cuánta droga pasó ni cuántos animales se
traficaron**: dice cuán extendido y arraigado está ese mercado según el panel.
No hay tonelaje, no hay recuento de operaciones y **no debe inventarse ninguno**.

Y una distinción que el propio índice hace y conviene respetar: **la resiliencia
NO es lo contrario de la criminalidad**. Un Estado puede tener mucha de las dos
—capacidad real y crimen arraigado a la vez— y la relación entre ambas es
justamente lo que el índice deja mirar.

POR QUÉ NO ENTRA AL COMPUESTO, TODAVÍA
---------------------------------------
Son treinta y seis medidas nuevas sobre un compuesto armado con cuatro ejes:
meterlas de golpe cambiaría el orden de los Estados sin que nadie pueda
explicar por qué. Entran como **capa propia y comparable**, con su puesto
mundial y regional, y la Dirección decide después si alguna se suma.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import comun
import geo

BASE = "https://ocindex.net"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
INTENTOS = 3
ESPERA = 4
# Argentina tiene puntaje en las 36 medidas. Si el control sale vacio, el que
# fallo es el lector, no la fuente: la pagina pudo cambiar de forma.
CONTROL = "ARG"

# Los cuatro rotulos que la casa quiere en castellano. El resto viaja como lo
# publica la fuente: traducir treinta y seis nombres a mano es otra cosa que
# envejece, y el nombre original es el que permite volver a la fuente.
# LOS TREINTA Y SEIS ROTULOS, EN CASTELLANO. Estaban en ingles y el registro los
# mostraba asi: un lector de la region veia «Cocaine trade 9,5» y no encontraba la
# palabra narcotrafico en ninguna parte del sitio. La traduccion es LITERAL, no
# interpretativa, y el nombre original viaja al lado en cada ficha para que
# cualquiera pueda contrastarla.
ROTULOS = {
    "1": "Criminalidad",
    "2": "Resiliencia del Estado",
    "1.1": "Mercados criminales",
    "1.2": "Actores criminales",
    # Los quince mercados criminales
    "1.1.1": "Trata de personas",
    "1.1.2": "Tráfico de migrantes",
    "1.1.3": "Extorsión y cobro de protección",
    "1.1.4": "Tráfico de armas",
    "1.1.5": "Comercio de mercadería falsificada",
    "1.1.6": "Comercio ilícito de bienes gravados",
    "1.1.7": "Delitos contra la flora",
    "1.1.8": "Delitos contra la fauna",
    "1.1.9": "Delitos contra recursos no renovables",
    "1.1.10": "Mercado de heroína",
    "1.1.11": "Mercado de cocaína",
    "1.1.12": "Mercado de cannabis",
    "1.1.13": "Mercado de drogas sintéticas",
    "1.1.14": "Delitos informáticos",
    "1.1.15": "Delitos financieros",
    # Los cinco tipos de actor
    "1.2.1": "Grupos de tipo mafioso",
    "1.2.2": "Redes criminales",
    "1.2.3": "Actores incrustados en el Estado",
    "1.2.4": "Actores extranjeros",
    "1.2.5": "Actores del sector privado",
    # Las doce medidas de resiliencia
    "2.1": "Liderazgo y gobernanza políticos",
    "2.2": "Transparencia y rendición de cuentas del Estado",
    "2.3": "Cooperación internacional",
    "2.4": "Políticas y leyes nacionales",
    "2.5": "Sistema judicial y detención",
    "2.6": "Fuerzas del orden",
    "2.7": "Integridad territorial",
    "2.8": "Regulación contra el lavado de dinero",
    "2.9": "Capacidad de regulación económica",
    "2.10": "Apoyo y protección a las víctimas",
    "2.11": "Prevención",
    "2.12": "Actores no estatales",
}

# Los cuatro mercados de drogas, agrupados aparte: el registro los muestra juntos
# en el eje de Seguridad porque «narcotrafico» es una pregunta que la gente hace,
# y estaban repartidos entre otros once mercados sin que se los pudiera ver.
DROGAS = ["1.1.11", "1.1.10", "1.1.12", "1.1.13"]

# Y las definiciones de LAS TREINTA Y SEIS medidas, en castellano. Eran cuatro
# —las de drogas— y las otras treinta y dos se mostraban en ingles: un registro
# que se publica para America Latina no puede explicar en ingles que es la
# extorsion. No son traducciones literales sino definiciones propias de lo que
# cada medida cubre; la original de GI-TOC viaja al lado, en el mismo archivo y
# en el campo de siempre, para que cualquiera contraste.
DEFINICIONES = {
    "1": ("Nivel general del crimen organizado en el Estado. Sale de "
              "promediar los mercados criminales y los actores criminales."),
    "1.1": ("Valor, extensión y daño —monetario y no monetario— de los mercados "
              "ilícitos que operan en el Estado."),
    "1.1.1": ("Captación, traslado o retención de personas mediante coacción, "
              "engaño, secuestro o fraude, con fines de explotación."),
    "1.1.2": ("Facilitación del ingreso o del tránsito irregular de personas a "
              "cambio de un beneficio, por parte de un grupo organizado."),
    "1.1.3": ("Cobro forzado sobre un territorio o un mercado, incluida la "
              "protección impuesta a comercios y vecinos."),
    "1.1.4": ("Venta, adquisición, traslado y desvío de armas, sus partes y sus "
              "municiones fuera del circuito legal."),
    "1.1.5": ("Producción, transporte, depósito y venta de mercadería que se hace "
              "pasar por original."),
    "1.1.6": ("Transporte, manipulación y venta de bienes gravados —tabaco, "
              "alcohol, combustible— evadiendo el impuesto."),
    "1.1.7": ("Comercio y tenencia ilícita de especies vegetales protegidas, "
              "incluida la tala y el tráfico de madera."),
    "1.1.8": ("Caza furtiva, comercio y tenencia ilícita de especies animales "
              "protegidas."),
    "1.1.9": ("Extracción, contrabando, adulteración y minería ilegal de recursos "
              "que no se reponen: minerales, hidrocarburos, piedras."),
    "1.1.14": ("Delitos que dependen enteramente de la tecnología informática: "
              "intrusión, secuestro de datos, ataque a sistemas."),
    "1.1.15": ("Delitos que producen una pérdida de dinero por fraude, estafa o "
              "manipulación financiera."),
    "1.2": ("Peso e influencia de cada tipo de actor dentro del crimen "
              "organizado del Estado."),
    "1.2.1": ("Grupos con estructura definida, jerarquía reconocible y control "
              "sobre un territorio o un mercado."),
    "1.2.2": ("Asociaciones flexibles, sin estructura fija, que se juntan para "
              "una actividad y se dispersan."),
    "1.2.3": ("Actores criminales que operan desde adentro del aparato del "
              "Estado."),
    "1.2.4": ("Actores criminales, estatales o no, que operan fuera de su país de "
              "origen."),
    "1.2.5": ("Personas o empresas que, buscando ganancia, controlan parte de una "
              "cadena legal y la usan para actividad ilícita."),
    "2": ("Mecanismos que el Estado tiene en pie para enfrentar al crimen "
              "organizado."),
    "2.1": ("Papel del Estado frente al crimen organizado, y eficacia de esa "
              "respuesta en el nivel más alto de decisión."),
    "2.2": ("Mecanismos de control sobre el propio Estado, y grado en que rinde "
              "cuentas de lo que hace."),
    "2.3": ("Estructuras y procesos de trabajo con otros Estados y con "
              "organismos internacionales."),
    "2.4": ("Marco legal y estructuras que el Estado creó para responder al "
              "crimen organizado."),
    "2.5": ("Capacidad de la justicia para actuar con independencia, y del "
              "sistema penitenciario para sostener esa acción."),
    "2.6": ("Capacidad del Estado para investigar, reunir inteligencia y "
              "proteger a la población."),
    "2.7": ("Grado de control efectivo sobre el territorio propio y sobre las "
              "fronteras."),
    "2.8": "Capacidad de aplicar medidas contra el lavado de activos.",
    "2.9": ("Capacidad de administrar la economía y de regular las "
              "transacciones."),
    "2.10": "Asistencia que se presta a las víctimas del crimen organizado.",
    "2.11": ("Estrategias, medidas y recursos asignados a prevenir, antes de que "
              "el hecho ocurra."),
    "2.12": ("Grado en que la sociedad civil y otros actores no estatales pueden "
              "intervenir en la respuesta."),
    "1.1.10": ("La producción, la distribución y la venta de heroína. El consumo se "
               "tiene en cuenta para determinar el alcance del mercado criminal."),
    "1.1.11": ("La producción, la distribución y la venta de cocaína y sus derivados. "
               "El consumo se tiene en cuenta para determinar el alcance del mercado."),
    "1.1.12": ("El cultivo ilícito, la distribución y la venta de aceite, resina, hierba "
               "u hojas de cannabis. El consumo se usa para determinar el alcance del "
               "mercado."),
    "1.1.13": ("La producción, la distribución y la venta de drogas sintéticas. El "
               "consumo se tiene en cuenta para determinar el alcance del mercado."),
}


def _pedir(url: str) -> str:
    ultimo = None
    for numero in range(INTENTOS):
        try:
            peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
            with urllib.request.urlopen(peticion, timeout=90) as respuesta:
                return respuesta.read(4_000_000).decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            raise RuntimeError(
                f"La fuente rechazó {url}: HTTP {error.code}. NO se anota cero.") from error
        except Exception as error:  # noqa: BLE001 — falla de red: se reintenta
            ultimo = error
            time.sleep(ESPERA * (numero + 1))
    raise RuntimeError(
        f"No se pudo leer {url} en {INTENTOS} intentos: {type(ultimo).__name__}: {ultimo}. "
        "Es falla de RED, no respuesta de la fuente. NO se anota cero.")


def _arbol(html: str) -> dict:
    """El catálogo de medidas lo declara la propia página; acá no se inventa."""
    m = re.search(r"\$indicatorsindex\s*=\s*(\{.*?\});", html, re.S)
    if not m:
        raise RuntimeError(
            "La página dejó de declarar su catálogo de medidas ($indicatorsindex). "
            "Cambió de forma: NO se publica una lectura a ciegas.")
    plano: dict = {}

    def recorrer(d, padre=None):
        for v in d.values():
            plano[v["id"]] = {"nombre": v["name"], "padre": padre,
                              "descripcion": (v.get("short_description") or "").strip()}
            if v.get("children"):
                recorrer(v["children"], v["id"])

    recorrer(json.loads(m.group(1)))
    return plano


def _padronDeLaFuente(html: str) -> dict:
    """ISO3 → dirección de la ficha. La equivalencia la declara la fuente."""
    m = re.search(r"\$countries\s*=\s*(\[.*?\]);", html, re.S)
    if not m:
        raise RuntimeError("La página dejó de declarar su padrón de países ($countries).")
    return {c["iso3"]: c["slug"] for c in json.loads(m.group(1)) if c.get("iso3")}


def _valores(html: str) -> dict:
    """Cada medida viene marcada con su código; se lee el código, no la posición."""
    hallado = {}
    for m in re.finditer(r'data-crime="([\d.]+)"(.{0,400}?)(\d+(?:\.\d+)?)\s*<span', html, re.S):
        codigo, medio, valor = m.group(1), m.group(2), m.group(3)
        if "data-crime" in medio:        # se cruzó con la medida siguiente
            continue
        hallado.setdefault(codigo, float(valor))
    return hallado


# El puesto viene con el sufijo ordinal DENTRO de una etiqueta —«85<sup>th</sup>»—,
# de modo que el patron ingenuo «85th» no encuentra nada y deja los 33 Estados sin
# puesto. Se lee la forma real, no la que uno esperaria.
_PUESTO = re.compile(
    r"(\d+)\s*<sup>[a-z]{2}</sup>\s*</span>\s*of\s+(\d+)\s+countries(?:\s+in\s+([^<]+?))?\s*<",
    re.I)


def _puestos(html: str) -> dict:
    """Los puestos que la propia fuente calcula: mundial, continental y subregional.

    Son dos bloques —criminalidad y resiliencia— y cada uno trae sus tres puestos.
    Se los separa por su encabezado en vez de por el orden en que aparecen: el
    orden es una convencion de maquetacion y puede cambiar sin aviso.
    """
    puestos: dict = {}
    for clave, encabezado in (("criminalidad", "Criminality score"),
                              ("resiliencia", "Resilience score")):
        corte = html.find(encabezado)
        if corte < 0:
            continue
        # Hasta el encabezado siguiente, para no invadir el bloque vecino.
        fin = min([p for p in (html.find("Resilience score", corte + 1),
                               html.find("Analysis", corte + 1)) if p > 0] or [len(html)])
        trozo = html[corte:fin]
        de = []
        for m in _PUESTO.finditer(trozo):
            de.append({"puesto": int(m.group(1)), "sobre": int(m.group(2)),
                       "ambito": (m.group(3) or "el mundo").strip()})
        if de:
            puestos[clave] = de
    return puestos


def _serie(html: str, cual: str) -> list:
    """La serie histórica que la página adjunta al gráfico de cada compuesto."""
    for m in re.finditer(r'class="line-chart"\s+data-data=(\[[^\]]*\])', html):
        try:
            datos = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            continue
        if datos:
            # ORDENADA POR ANIO. La pagina la publica del ultimo al primero, y una
            # serie al reves dibuja la linea al reves el dia que alguien la use.
            return sorted(({"anio": int(d["year"]), "valor": float(d["value"])} for d in datos),
                          key=lambda x: x["anio"])
    return []


# LA SERIE DE CADA MEDIDA. La pagina adjunta un grafico de linea a cada una,
# con las tres ediciones. Se lee por codigo, igual que el valor: el bloque
# «data-crime="1.1.11"» contiene su propio grafico y termina donde empieza el
# siguiente bloque.
_BLOQUE = re.compile(r'data-crime="([\d.]+)"(.*?)(?=data-crime="|\Z)', re.S)
_GRAFICO = re.compile(r'class="line-chart"\s+data-data=(\[[^\]]*\])')


def _series(html: str) -> dict:
    series = {}
    for m in _BLOQUE.finditer(html):
        codigo, cuerpo = m.group(1), m.group(2)
        g = _GRAFICO.search(cuerpo)
        if not g:
            continue
        try:
            datos = json.loads(g.group(1))
        except Exception:  # noqa: BLE001 — un grafico ilegible no tumba la medida
            continue
        puntos = [{"anio": int(d["year"]), "valor": float(d["value"])}
                  for d in datos if d.get("year") is not None and d.get("value") is not None]
        if len(puntos) >= 2:
            series.setdefault(codigo, sorted(puntos, key=lambda x: x["anio"]))
    return series


def _delEstado(faena: tuple) -> tuple:
    iso, slug = faena
    html = _pedir(f"{BASE}/country/{slug}")
    return iso, _valores(html), _puestos(html), _serie(html, "1"), _series(html)


def recolectar():
    # Una sola lectura para el catálogo y la equivalencia; después, país por país.
    inicial = _pedir(f"{BASE}/country/argentina")
    arbol = _arbol(inicial)
    slugs = _padronDeLaFuente(inicial)

    faltan = [p["iso"] for p in geo.padron() if p["iso"] not in slugs]
    if faltan:
        raise RuntimeError(
            f"La fuente no reconoce a {len(faltan)} Estados del padrón: {', '.join(faltan)}. "
            "NO se publica una región incompleta sin advertirlo.")

    faenas = [(p["iso"], slugs[p["iso"]]) for p in geo.padron()]
    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        crudo = {iso: (v, p, s, ss) for iso, v, p, s, ss in ejecutor.map(_delEstado, faenas)}

    # SE PRUEBA EL LECTOR ANTES DE CREERLE UN VACIO A NADIE. Si la pagina cambia
    # de forma, el patron deja de encontrar y todos los Estados quedan en blanco:
    # eso NO es «no hay datos», es «no supimos leer».
    control = crudo.get(CONTROL, ({}, {}, [], {}))[0]
    if not crudo.get(CONTROL, ({}, {}, [], {}))[1]:
        raise RuntimeError(
            f"La prueba del lector falló: en {CONTROL} no se leyó ningún puesto. La "
            "página escribe el ordinal dentro de una etiqueta —«85<sup>th</sup>»— y eso "
            "ya rompió el patrón una vez. NO se publica una lectura a ciegas.")
    if len(control) < 20:
        raise RuntimeError(
            f"La prueba del lector falló: en {CONTROL} —que tiene puntaje en las 36 "
            f"medidas— sólo se leyeron {len(control)}. La página cambió de forma. NO se "
            "publica una lectura a ciegas.")
    # Y LA SERIE TAMBIEN SE PRUEBA: Argentina tiene tres ediciones en cada
    # medida. Si no se leyo ninguna, el que fallo es el lector.
    if len(crudo.get(CONTROL, ({}, {}, [], {}))[3]) < 20:
        raise RuntimeError(
            f"La prueba del lector falló: en {CONTROL} no se leyó la serie por medida. "
            "La página cambió de forma. NO se publica una lectura a ciegas.")

    registros, conDato = [], 0
    for pais in geo.padron():
        valores, puestos, serie, series = crudo.get(pais["iso"], ({}, {}, [], {}))
        if not valores:
            registros.append({"iso": pais["iso"], "pais": pais["pais"],
                              "bloque": pais["bloque"], "estado": "no_se_pudo_leer"})
            continue
        conDato += 1
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": "evaluado",
            "criminalidad": valores.get("1"),
            "resiliencia": valores.get("2"),
            "mercados_criminales": valores.get("1.1"),
            "actores_criminales": valores.get("1.2"),
            "medidas": {c: v for c, v in sorted(valores.items())},
            "puestos": puestos,
            "serie_criminalidad": serie,
            # La serie de cada medida, por codigo: tres ediciones bienales.
            "series": series,
        })

    vacios = [
        "Es evaluación experta, no recuento de hechos. Cada puntaje va de 1 a 10 y lo fija "
        "un panel de especialistas con evidencia documental, revisado por pares. Dos "
        "personas informadas pueden puntuar distinto el mismo país.",
        "Un puntaje alto de mercado no dice cuánto. No hay tonelaje, no hay recuento de "
        "operaciones ni de animales: dice cuan extendido y arraigado está ese mercado "
        "según el panel. El registro no inventa una cantidad que la fuente no da.",
        "No es tiempo real y no pretende serlo. La edición es bienal —2019, 2021, 2023, "
        "2025— y describe estructura, no coyuntura: sirve para saber que opera en un "
        "Estado y con que fuerza, no que pasó anoche. Para lo reciente no hay fuente "
        "libre, y el registro lo dice en vez de simularlo.",
        "La resiliencia no es lo contrario de la criminalidad. Son dos medidas "
        "independientes: un Estado puede tener mucha capacidad y crimen arraigado a la "
        "vez. Restarlas o tratarlas como una sola escala sería un error de lectura.",
        "No entra al compuesto del registro. Son treinta y seis medidas nuevas sobre un "
        "compuesto armado con cuatro ejes: sumarlas de golpe cambiaria el orden de los "
        "Estados sin que nadie pueda explicar por que. Entran como capa propia y "
        "comparable, con su puesto mundial.",
        "El puesto ordena contra 193 países, no contra los 33 del padrón. Un Estado de la "
        "región puede estar bien situado en el mundo y mal en su zona: son dos preguntas "
        "distintas y esta cifra contesta la primera.",
        f"ANTES DE CREER UN VACIO SE PRUEBA EL LECTOR contra {CONTROL}, que tiene puntaje "
        "en las 36 medidas. Si la pagina cambia de forma, el patron deja de encontrar y "
        "todos los Estados quedarian en blanco: eso no es «no hay datos», es «no supimos "
        "leer», y la corrida se detiene entera.",
    ]

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=3,
        corroborado=False,
        nota=("Iniciativa global contra el crimen organizado transnacional, red de "
              "expertos con sede en Ginebra y metodologia publicada. La Fundación es "
              "miembro permanente de la organización que produce el índice. Fiabilidad B "
              "porque es una organización con posición tomada sobre la materia que mide "
              "—lo cuál no la invalida, pero se declara—. Credibilidad 3 porque el "
              "puntaje es evaluación experta agregada, no un hecho verificable de forma "
              "independiente."),
    )

    return comun.escribir(
        colector="crimen_organizado",
        capa="publico",
        fuente="Índice Global de Crimen Organizado — Global Initiative Against Transnational Organized Crime",
        url_fuente=f"{BASE}/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "edicion": 2025,
                "ediciones_con_serie": sorted({a["anio"] for r in registros
                                               for ss in r.get("series", {}).values() for a in ss}),
                "estados_evaluados": conDato,
                "estados_del_padron": len(registros),
                "paises_en_el_indice": 193,
                "medidas_por_estado": len(arbol),
                "lector_probado": True,
                "consultado": comun.ahora(),
            },
            "drogas": DROGAS,
            "catalogo": [{"codigo": c, "nombre": d["nombre"],
                          "rotulo": ROTULOS.get(c, d["nombre"]),
                          "es_droga": c in DROGAS,
                          "padre": d["padre"], "descripcion": d["descripcion"],
                          **({"descripcion_es": DEFINICIONES[c]} if c in DEFINICIONES else {})}
                         for c, d in sorted(arbol.items(),
                                            key=lambda x: [int(p) for p in x[0].split(".")])],
        },
    )


if __name__ == "__main__":
    comun.correr("crimen_organizado", recolectar)
