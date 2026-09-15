# -*- coding: utf-8 -*-
"""Recursos estratégicos: qué tiene bajo tierra cada Estado de la región.

POR QUÉ ESTÁ EN EL EJE DEFENSA
--------------------------------
Porque un recurso estratégico no es el que da más dinero: es **el que otro
necesita**. El niobio brasileño no figura en ninguna discusión pública de la
región y sin embargo Brasil produce más del noventa por ciento del mundial, en
un metal sin el cual no se hacen ciertos aceros de uso militar y aeronáutico.
Esa clase de hecho no aparece en las cuentas de exportación: aparece cuando se
mira la producción de cada país contra la del mundo entero.

QUÉ PUBLICA, Y DE DÓNDE SALE
------------------------------
Dos fuentes distintas, y a propósito:

  · **Hidrocarburos y litio** — producción de petróleo, gas y carbón, reservas
    probadas de petróleo y producción de litio, con serie larga. Vienen del
    Energy Institute y del Servicio Geológico de los Estados Unidos, por la vía
    que los redistribuye abiertos.
  · **Minerales** — el Servicio Geológico de los Estados Unidos publica cada
    año producción y reservas por país de más de setenta minerales no
    combustibles. De ahí sale lo que ninguna otra fuente de la región dice:
    **cuánto pesa cada Estado en el mundo, mineral por mineral.**

LO QUE ESTA MEDIDA NO ES
-------------------------
No es un juicio sobre qué debería importarle a cada país. Es un recuento: qué
produce, cuánto, y qué proporción del total mundial representa. Que un recurso
sea estratégico **para quién** y **para qué** es análisis, y el análisis no va
en el registro: va en los informes.

EL VACÍO MÁS GRANDE, DECLARADO DESDE EL PRINCIPIO
---------------------------------------------------
La base mundial de minerales lista a los productores de escala mundial, y en
América Latina y el Caribe eso son **doce Estados de treinta y tres**. Los otros
veintiuno no aparecen, y no aparecer no es lo mismo que no tener: significa que
no producen a una escala que mueva el total del mundo. Se declara así y no se
rellena.
"""
from __future__ import annotations

import csv
import re
import io
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "recursos"
CAPA = "publico"

# EL AÑO EN CURSO NO ENTRA. La fuente de energía publica un valor para el año
# que todavía no terminó y es una proyección, no una medición: ponerlo al lado
# de años cerrados haría ver un movimiento que nadie midió. Misma regla que el
# resto del registro.
HASTA = datetime.now(timezone.utc).year - 1

REJILLA = "https://ourworldindata.org/grapher/{slug}.csv"
# Edición 2026 (publicada el 6/2/2026). Cambió de forma: ya no trae la tabla ancha
# «World_Data_Release» sino «MCS2026_Commodities_Data.csv» en formato largo.
USGS_ITEM = "https://www.sciencebase.gov/catalog/item/69837e43b66b01367d7ec7c7?format=json"

ORIGEN_ENERGIA = ("Energy Institute y Servicio Geológico de los Estados Unidos, "
                  "via Our World in Data")
ORIGEN_USGS = ("Servicio Geológico de los Estados Unidos — Mineral Commodity "
               "Summaries, base mundial de producción y reservas")

# Cada medida dice de qué rejilla sale y qué columna leer. Agregar una es
# agregar una línea.
ENERGIA = [
    {"clave": "produccion_petroleo", "slug": "fossil-fuel-production", "columna": "Oil production",
     "rotulo": "Producción de petróleo", "unidad": "teravatios hora equivalentes",
     "cautela": "Se publica en energía equivalente y no en barriles, que es como la "
                "redistribuye la fuente: así el petróleo, el gas y el carbón se pueden "
                "sumar y comparar entre sí. Producir mucho NO significa refinar ni "
                "consumir: varios Estados de la región exportan crudo e importan combustible."},
    {"clave": "produccion_gas", "slug": "fossil-fuel-production", "columna": "Gas production",
     "rotulo": "Producción de gas natural", "unidad": "teravatios hora equivalentes",
     "cautela": "El gas pesa distinto al petróleo en la seguridad de un país: no se "
                "almacena ni se transporta con la misma facilidad, y quien depende de un "
                "gasoducto depende también de por dónde pasa."},
    {"clave": "produccion_carbon", "slug": "fossil-fuel-production", "columna": "Coal production",
     "rotulo": "Producción de carbón", "unidad": "teravatios hora equivalentes",
     "cautela": "En esta región lo produce casi solo Colombia, y en su mayor parte para "
                "exportar. Un cero acá no es un vacío: es que ese Estado no produce carbón."},
    {"clave": "reservas_petroleo", "slug": "oil-proved-reserves", "columna": "Oil",
     "rotulo": "Reservas probadas de petróleo", "unidad": "barriles",
     "cautela": "RESERVAS PROBADAS quiere decir lo que hoy se puede extraer con la técnica "
                "y el precio de hoy. No es cuánto petróleo hay: es cuánto conviene sacar. "
                "Sube y baja con el precio sin que cambie una gota bajo tierra, y cada "
                "Estado declara las suyas con su propio criterio."},
    {"clave": "produccion_litio", "slug": "lithium-production", "columna": "Lithium Production",
     "rotulo": "Producción de litio", "unidad": "toneladas de contenido de litio",
     "cautela": "El llamado triángulo del litio —Chile, la Argentina y Bolivia— concentra "
                "buena parte de las reservas del mundo, pero RESERVA Y PRODUCCIÓN NO SON LO "
                "MISMO: Bolivia figura entre los mayores tenedores y no aparece produciendo "
                "a escala mundial. Tener no es extraer."},
]


def rejilla(slug: str) -> list:
    peticion = urllib.request.Request(REJILLA.format(slug=slug),
                                      headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=90) as respuesta:
        texto = respuesta.read().decode("utf-8", "replace")
    return list(csv.DictReader(io.StringIO(texto)))


def serie_de(filas: list, columna: str, del_padron: set) -> tuple:
    """Arma la serie por Estado, descartando el año en curso y lo que no es país."""
    por_iso, futuros = {}, 0
    for x in filas:
        iso = (x.get("Code") or "").strip()
        if iso not in del_padron:
            continue
        try:
            anio = int(x.get("Year") or 0)
            valor = float(x.get(columna) or "")
        except ValueError:
            continue
        if anio > HASTA:
            futuros += 1
            continue
        por_iso.setdefault(iso, []).append((anio, valor))
    for iso in por_iso:
        por_iso[iso].sort()
    return por_iso, futuros


def ficha(serie: list) -> dict:
    anio, valor = serie[-1]
    anterior = serie[-2] if len(serie) >= 2 else None
    return {
        "valor": valor, "anio": anio,
        "anio_anterior": anterior[0] if anterior else None,
        "valor_anterior": anterior[1] if anterior else None,
        "variacion_pct": (round((valor - anterior[1]) / abs(anterior[1]) * 100, 1)
                          if anterior and anterior[1] else None),
        "anio_inicial": serie[0][0], "valor_inicial": serie[0][1],
        "tendencia_ventana_pct": (round((valor - serie[0][1]) / abs(serie[0][1]) * 100, 1)
                                  if len(serie) >= 3 and serie[0][1] else None),
        "serie": [{"anio": a, "valor": v} for a, v in serie],
    }


# Los nombres con que la base mundial de minerales llama a los Estados del
# padrón. Se escriben porque esa base usa nombres en inglés y sin código: sin
# esta tabla habría que adivinar, y adivinar es lo que este registro no hace.
NOMBRE_USGS = {
    "Argentina": "ARG", "Bolivia": "BOL", "Brazil": "BRA", "Chile": "CHL",
    "Colombia": "COL", "Costa Rica": "CRI", "Cuba": "CUB",
    "Dominican Republic": "DOM", "Ecuador": "ECU", "El Salvador": "SLV",
    "Guatemala": "GTM", "Guyana": "GUY", "Haiti": "HTI", "Honduras": "HND",
    "Jamaica": "JAM", "Mexico": "MEX", "Nicaragua": "NIC", "Panama": "PAN",
    "Paraguay": "PRY", "Peru": "PER", "Suriname": "SUR",
    "Trinidad and Tobago": "TTO", "Uruguay": "URY", "Venezuela": "VEN",
    "Belize": "BLZ", "Bahamas, The": "BHS", "Barbados": "BRB",
    "Antigua and Barbuda": "ATG", "Dominica": "DMA", "Grenada": "GRD",
    "Saint Kitts and Nevis": "KNA", "Saint Lucia": "LCA",
    "Saint Vincent and the Grenadines": "VCT",
}

# EL NOMBRE DEL MINERAL, EN CASTELLANO. La base publica en inglés, y una tarjeta
# que dice «Brasil, 92,29 % de la producción mundial de Niobium» obliga al lector
# a traducir para entender de qué le hablan. Se traduce acá y no en la pantalla
# porque el dato tiene que viajar entendible también para quien se lleve el
# archivo. El nombre original queda al lado: lo que no está en esta tabla
# conserva su nombre en inglés, y eso se ve.
EN_CASTELLANO = {
    "lithium": "litio", "tin": "estaño", "niobium": "niobio", "iodine": "yodo",
    "gold": "oro", "silver": "plata", "arsenic": "arsénico", "bauxite": "bauxita",
    "copper": "cobre", "zinc": "cinc", "lead": "plomo", "nickel": "níquel",
    "cobalt": "cobalto", "molybdenum": "molibdeno", "rhenium": "renio",
    "beryllium": "berilio", "boron": "boro", "bismuth": "bismuto",
    "antimony": "antimonio", "cadmium": "cadmio", "selenium": "selenio",
    "tellurium": "telurio", "indium": "indio", "mercury": "mercurio",
    "manganese": "manganeso", "titanium": "titanio", "vanadium": "vanadio",
    "tungsten": "wolframio", "magnesium": "magnesio", "aluminum": "aluminio",
    "silicon": "silicio", "strontium": "estroncio", "bromine": "bromo",
    "iron ore": "mineral de hierro", "rare earths": "tierras raras",
    "phosphate rock": "roca fosfórica", "potash": "potasa", "sulfur": "azufre",
    "salt": "sal", "cement": "cemento", "gypsum": "yeso", "lime": "cal",
    "barite": "baritina", "feldspar": "feldespato", "graphite": "grafito",
    "fluorspar": "fluorita", "wollastonite": "wollastonita",
    "diatomite": "diatomita", "asbestos": "amianto", "talc": "talco",
    "mica": "mica", "kaolin": "caolín", "clays": "arcillas", "perlite": "perlita",
    "vermiculite": "vermiculita", "garnet": "granate", "helium": "helio",
    "peat": "turba", "abrasives": "abrasivos", "soda ash": "carbonato de sodio",
    "zeolites (natural)": "zeolitas naturales",
    "pumice & pumicite": "piedra pómez",
    "nitrogen(fixed) - ammonia": "nitrógeno fijado (amoníaco)",
    "sand and gravel": "arena y grava", "stone": "piedra",
    # Nombres de la edición 2026, que cambió la forma de escribirlos.
    "zeolites": "zeolitas naturales", "pumice and pumicite": "piedra pómez",
    "nitrogen (fixed)—ammonia": "nitrógeno fijado (amoníaco)",
    "magnesium compounds": "compuestos de magnesio", "alumina": "alúmina",
    "chromium": "cromo", "iron and steel": "hierro y acero", "tantalum": "tántalo",
    "feldspar and nepheline syenite": "feldespato y sienita nefelínica",
}


def en_castellano(nombre: str) -> str:
    """El nombre en castellano, o el original si no está en la tabla."""
    return EN_CASTELLANO.get((nombre or "").strip().lower(), (nombre or "").strip())


# Filas que NO son un país y que, sumadas al total del mundo, lo inflarían.
NO_ES_PAIS = {"world total", "world total (rounded)", "other countries",
              "united states and canada", "world total (rounded, excluding u.s.)"}


def numero(v) -> float | None:
    v = (v or "").replace(",", "").strip()
    if not v or v in ("NA", "—", "-"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


# LA COPIA DE LA EDICION VIGENTE. Desde el robot la descarga en linea falla y
# desde una maquina comun no, y sin esta copia las materias de minerales dejaban
# de publicarse. Sus metadatos oficiales declaran «Use constraints: None»: se
# puede redistribuir, y el LEEME de la carpeta dice cuando se reemplaza.
COPIA_USGS = Path(__file__).resolve().parent / "fijas" / "usgs-mcs2026" / "MCS2026_Commodities_World.csv"


def _por_codigo(error: Exception) -> str:
    """El error con su código, que es lo único que sirve para saber por qué cayó."""
    codigo = getattr(error, "code", None)
    return f"{type(error).__name__} {codigo}" if codigo else type(error).__name__


def _filas_en_linea() -> list:
    peticion = urllib.request.Request(USGS_ITEM, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=90) as respuesta:
        item = __import__("json").loads(respuesta.read())
    archivo = next((f for f in (item.get("files") or [])
                    if f.get("name", "").endswith("_Commodities_Data.csv")), None)
    if not archivo:
        raise RuntimeError("la base mundial de minerales no trae su archivo de datos")
    peticion = urllib.request.Request(archivo["url"], headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=180) as respuesta:
        crudo = respuesta.read()
    # EL ARCHIVO 2026 NO VIENE EN UTF-8 sino en la codificación de Windows: leído
    # como UTF-8, la raya de «Production—crude ore» se vuelve un signo roto.
    try:
        texto = crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = crudo.decode("cp1252")
    return list(csv.DictReader(io.StringIO(texto)))


def _a_la_forma_ancha(filas: list) -> tuple:
    """La edición 2026 viene en formato largo: una fila por país, mineral,
    estadística y año. Se la pasa a la forma que el resto del colector ya sabe
    leer —producción del último año, del anterior y reservas— sin tocar la cuenta.

    Devuelve las filas y el AÑO de la producción más nueva, que sale del archivo y
    no se escribe a mano.
    """
    if filas and "COMMODITY" in filas[0]:
        return filas, 2024   # la forma vieja (edición 2025) trae producción de 2024
    mundo = [x for x in filas if (x.get("Section") or "").startswith("World")]
    anios = [int(x["Year"]) for x in mundo
             if x.get("Statistics") == "Production" and (x.get("Year") or "").isdigit()]
    ultimo = max(anios) if anios else None
    ancha: dict = {}
    reservas: dict = {}
    for x in mundo:
        com = re.sub(r"\s*\(.*?\)\s*$", "", (x.get("Commodity") or "").strip())
        pais = (x.get("Country") or "").strip()
        if x.get("Statistics") == "Reserves":
            reservas.setdefault((com, pais), x.get("Value"))
            continue
        if x.get("Statistics") != "Production" or not (x.get("Year") or "").isdigit():
            continue
        detalle = (x.get("Statistics_detail") or "").strip()
        # «Mine production: beneficiated» y «Production—crude ore» se agrupan por su
        # primera parte, y el detalle completo se guarda para ver si es comparable.
        base = re.split(r"\s*[—:]\s*", detalle, maxsplit=1)[0]
        clave = (com, pais, base, (x.get("Unit") or "").strip())
        fila = ancha.setdefault(clave, {"SOURCE": "MCS" + str((ultimo or 0) + 1), "COMMODITY": com,
                                        "COUNTRY": pais, "TYPE": clave[2], "UNIT_MEAS": clave[3]})
        fila.setdefault("_detalles", set()).add(detalle)
        if int(x["Year"]) == ultimo:
            fila["PROD_ULTIMO"] = x.get("Value")
        elif int(x["Year"]) == (ultimo or 0) - 1:
            fila["PROD_ANTERIOR"] = x.get("Value")
    # UNA CUOTA MUNDIAL SOLO SE CALCULA SOBRE LO MISMO. Si un país declara boro en
    # bruto y otro en óxido bórico, sumarlos para sacar «el total del mundo» mezcla
    # cosas distintas: con eso Argentina y Perú salían con el 100 % del boro. Esos
    # grupos quedan sin cuota.
    detalles_por_grupo: dict = {}
    for (com, pais, tipo, unidad), fila in ancha.items():
        if pais.lower() in NO_ES_PAIS:
            continue
        detalles_por_grupo.setdefault((com, tipo, unidad), set()).update(fila["_detalles"])
    vistas = set()
    for (com, pais, _tipo, _unidad), fila in ancha.items():
        fila["COMPARABLE"] = len(detalles_por_grupo.get((com, _tipo, _unidad), set())) <= 1
        fila.pop("_detalles", None)
        if (com, pais) not in vistas:
            fila["RESERVAS"] = reservas.get((com, pais))
            vistas.add((com, pais))
    return list(ancha.values()), ultimo


def minerales() -> tuple:
    """Producción y reservas por país y mineral, y la cuota de cada uno en el mundo.

    Devuelve también POR QUÉ CAMINO se leyó. Si la descarga en línea cae se usa
    la copia guardada, y eso se declara: una copia usada en silencio es un dato
    viejo presentado como fresco.
    """
    try:
        filas, camino = _filas_en_linea(), None
    except Exception as error:  # noqa: BLE001 — se prueba la copia y se declara
        if not COPIA_USGS.exists():
            raise
        filas = list(csv.DictReader(io.StringIO(
            COPIA_USGS.read_text(encoding="utf-8-sig", errors="replace"))))
        camino = (f"la descarga en línea cayó ({_por_codigo(error)}) y se leyó la copia "
                  "guardada en el repositorio de la misma edición")

    # El total del mundo se SUMA, no se lee: la base trae renglones de «world
    # total» que ya vienen redondeados y agregados, y usarlos daría una cuota
    # que no cierra con las partes.
    filas, anio_produccion = _a_la_forma_ancha(filas)
    mundo, del_pais = {}, {}
    edicion = None
    for x in filas:
        com, tipo, pais = x.get("COMMODITY"), x.get("TYPE"), (x.get("COUNTRY") or "").strip()
        edicion = edicion or x.get("SOURCE")
        # UN SOLO AÑO POR CUENTA. En la edición 2026 se usa solo la producción del
        # último año: completar con la del anterior mezclaba años en el total del
        # mundo. En la forma vieja (2025) se conserva la regla de entonces.
        if "PROD_ULTIMO" in x or "PROD_ANTERIOR" in x:
            prod = numero(x.get("PROD_ULTIMO"))
        else:
            prod = numero(x.get("PROD_EST_ 2024"))
            prod = prod if prod is not None else numero(x.get("PROD_2023"))
        if not com or not prod or x.get("COMPARABLE") is False:
            continue
        unidad = (x.get("UNIT_MEAS") or "").strip()
        # «OTROS PAÍSES» ES PRODUCCIÓN REAL y va en el total del mundo; lo que no va
        # es el renglón de total ya sumado. Dejarlo afuera inflaba las cuotas: la
        # plata de México daba 26,4 % en vez de 24,3 % (auditoría del 15/9/2026).
        # La unidad va en la llave: arena en toneladas y en metros cúbicos no se suman.
        if pais.lower() not in NO_ES_PAIS or pais.lower() == "other countries":
            mundo[(com, tipo, unidad)] = mundo.get((com, tipo, unidad), 0.0) + prod
        iso = NOMBRE_USGS.get(pais)
        if iso:
            del_pais.setdefault(iso, []).append(
                {"mineral": en_castellano(com), "mineral_original": com,
                 "medida": tipo, "unidad": x.get("UNIT_MEAS"),
                 "produccion": prod, "reservas": numero(x.get("RESERVAS") or x.get("RESERVES_2024"))})

    for iso, lista in del_pais.items():
        for m in lista:
            # EL TOTAL DEL MUNDO SE BUSCA CON EL NOMBRE ORIGINAL. Traducirlo
            # antes de esta línea dejaba la cuota en nada para casi todos los
            # Estados, y el orden quedaba al azar: Brasil aparecía con 10 % de
            # tántalo en vez de 92 % de niobio. La traducción es para el lector;
            # la cuenta se hace con la llave de la fuente.
            total = mundo.get((m["mineral_original"], m["medida"], (m.get("unidad") or "").strip())) or 0
            m["cuota_mundial_pct"] = round(m["produccion"] / total * 100, 2) if total else None
        lista.sort(key=lambda m: -(m.get("cuota_mundial_pct") or 0))
    return del_pais, edicion, camino, anio_produccion


def construir() -> Path:
    padron = geo.padron()
    del_padron = {p["iso"] for p in padron}

    # Una sola descarga por rejilla, aunque la usen varias medidas.
    rejillas, caidos, futuros = {}, [], 0
    for m in ENERGIA:
        if m["slug"] in rejillas:
            continue
        try:
            rejillas[m["slug"]] = rejilla(m["slug"])
        except Exception as error:  # noqa: BLE001 — la rejilla caída se declara
            caidos.append(f"{m['slug']}: {type(error).__name__}")
            rejillas[m["slug"]] = []

    datos = {}
    for m in ENERGIA:
        s, f = serie_de(rejillas.get(m["slug"]) or [], m["columna"], del_padron)
        datos[m["clave"]], futuros = s, futuros + f

    # SE LEYO O NO SE LEYO. Esa diferencia decide qué vacío se declara: si la base
    # no se pudo leer por ningún camino, los Estados quedan SIN MIRAR, y afirmar
    # que «no figuran» sería falso —ya se publicó una vez, nombrando a Brasil y a
    # Chile—.
    minerales_leidos = False
    try:
        por_mineral, edicion, camino, anio_minerales = minerales()
        minerales_leidos = True
        if camino:
            caidos.append(f"MINERALES: {camino}. Las cifras son de la edición {edicion}, "
                          "que es la vigente; no hay una más nueva que se haya dejado de leer.")
    except Exception as error:  # noqa: BLE001
        caidos.append(f"base mundial de minerales: {_por_codigo(error)}")
        por_mineral, edicion, anio_minerales = {}, None, None

    registros, cobertura = [], {}
    for p in padron:
        f = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        for m in ENERGIA:
            s = datos[m["clave"]].get(p["iso"])
            if s:
                f["indicadores"][m["clave"]] = ficha(s)
                cobertura[m["clave"]] = cobertura.get(m["clave"], 0) + 1

        lista = por_mineral.get(p["iso"]) or []
        conCuota = [m for m in lista if m.get("cuota_mundial_pct")]
        if conCuota:
            mayor = conCuota[0]
            anio = anio_minerales
            f["indicadores"]["cuota_mineral_mundial"] = {
                "valor": mayor["cuota_mundial_pct"], "anio": anio,
                "anio_anterior": None, "valor_anterior": None, "variacion_pct": None,
                "anio_inicial": anio, "valor_inicial": mayor["cuota_mundial_pct"],
                "tendencia_ventana_pct": None,
                "serie": [{"anio": anio, "valor": mayor["cuota_mundial_pct"]}],
                "de_que_mineral": mayor["mineral"],
                "de_que_mineral_original": mayor.get("mineral_original"),
            }
            f["indicadores"]["minerales_escala_mundial"] = {
                "valor": len({m["mineral"] for m in conCuota}), "anio": anio,
                "anio_anterior": None, "valor_anterior": None, "variacion_pct": None,
                "anio_inicial": anio, "valor_inicial": len({m["mineral"] for m in conCuota}),
                "tendencia_ventana_pct": None,
                "serie": [{"anio": anio, "valor": len({m["mineral"] for m in conCuota})}],
            }
            cobertura["cuota_mineral_mundial"] = cobertura.get("cuota_mineral_mundial", 0) + 1
            cobertura["minerales_escala_mundial"] = cobertura.get("minerales_escala_mundial", 0) + 1
            f["minerales"] = conCuota[:20]

        if f["indicadores"]:
            registros.append(f)
    registros.sort(key=lambda r: r["pais"])

    medidas = [
        {"clave": m["clave"], "rotulo": m["rotulo"], "eje": "Defensa",
         "unidad": m["unidad"], "mas_es_peor": False, "sin_direccion": True,
         # EL LITIO NO ES DEL ENERGY INSTITUTE. Lo redistribuye Our World in
         # Data pero lo produce el mismo servicio geológico que publica los
         # minerales. Declararlo con el otro origen lo habría hecho contar como
         # un productor distinto, y la regla de las dos fuentes habría dado por
         # corroborado un asunto que depende de un solo organismo.
         "origen": ORIGEN_USGS if m["clave"] == "produccion_litio" else ORIGEN_ENERGIA,
         "cautela": m["cautela"]}
        for m in ENERGIA
    ] + [
        {"clave": "cuota_mineral_mundial",
         "rotulo": "Mayor cuota mundial en un mineral", "eje": "Defensa",
         "unidad": "% de la producción mundial", "mas_es_peor": False,
         "sin_direccion": True,
         "origen": ORIGEN_USGS,
         "cautela": "Es la cuota del mineral donde el país pesa MÁS en el mundo, y el "
                    "nombre de ese mineral viaja al lado de la cifra. Una cuota alta no "
                    "significa una industria grande: significa que si ese país deja de "
                    "producir, al mundo le cuesta reemplazarlo. Brasil con el niobio es el "
                    "caso extremo de la región."},
        {"clave": "minerales_escala_mundial",
         "rotulo": "Minerales que produce a escala mundial", "eje": "Defensa",
         "unidad": "recuento de minerales", "mas_es_peor": False,
         "sin_direccion": True,
         "origen": ORIGEN_USGS,
         "cautela": "Cuenta en cuántos minerales distintos el país aparece en la base "
                    "mundial con producción medible. Es amplitud, no tamaño: un país puede "
                    "producir muchos minerales en poca cantidad, o uno solo y dominar el "
                    "mercado."},
    ]
    publicables = [m for m in medidas if cobertura.get(m["clave"], 0)]
    for m in medidas:
        if not cobertura.get(m["clave"], 0):
            caidos.append(f"{m['rotulo']}: la fuente no dejó un solo Estado del padrón")
    fuera = {m["clave"] for m in medidas} - {m["clave"] for m in publicables}
    for r in registros:
        for c in fuera:
            r["indicadores"].pop(c, None)
    registros = [r for r in registros if r["indicadores"]]

    sin_mineral = sorted(p["pais"] for p in padron if p["iso"] not in por_mineral)
    vacios = [
        f"NI EL AÑO EN CURSO NI EL FUTURO ENTRAN: se corta en {HASTA}, el último año "
        f"cerrado. La fuente de energía publica el año corriente y es una proyección: "
        f"{futuros} puntos quedaron afuera.",
        "ESTO NO DICE QUÉ ES ESTRATÉGICO PARA QUIÉN. Cuenta qué produce cada Estado, "
        "cuánto, y qué proporción del mundo representa. Para quién y para qué eso importa "
        "es análisis, y el análisis no va en el registro.",
        "RESERVA Y PRODUCCIÓN NO SON LO MISMO, y confundirlas es el error más común con "
        "estos datos. Bolivia figura entre los mayores tenedores de litio del mundo y no "
        "aparece produciendo a escala mundial: tener no es extraer.",
        "La cuota mundial se calcula SUMANDO los países, no leyendo el renglón de total "
        "que publica la fuente: ese viene redondeado y agregado, y usarlo daría cuotas que "
        "no cierran con las partes.",
        "UN CERO EN RESERVAS ES LO QUE DICE LA FUENTE, NO LO QUE HAY BAJO TIERRA. El caso "
        "que lo prueba está adentro de este mismo archivo: la tabla de reservas le asigna "
        "CERO a Guyana, y la de producción muestra a Guyana produciendo petróleo desde "
        "2019. No se corrige ninguna de las dos ni se elige una: la tabla de reservas no "
        "desagrega a ese Estado, y la contradicción se declara porque es un dato sobre la "
        "fuente. Quien necesite las reservas guyanesas tiene que ir a otro lado.",
        "Las reservas probadas llegan hasta 2021 y la producción hasta el último año "
        "cerrado. Son dos frescuras distintas dentro del mismo tema, y compararlas como si "
        "fueran del mismo momento sería un error.",
        "Un mismo mineral puede aparecer dos veces con medidas distintas —el hierro se "
        "publica por contenido de hierro y por mineral utilizable— y no es una repetición: "
        "son dos maneras de pesar lo mismo. El recuento de minerales no las cuenta dos "
        "veces; el detalle por país las muestra separadas, con su medida al lado.",
        "La producción de minerales corresponde a la última estimación anual de la fuente, "
        "y las reservas a la declaración más reciente. No hay serie histórica: la base "
        "publica una foto por edición, no una serie.",
    ]
    if not minerales_leidos:
        vacios.append(
            "LOS MINERALES QUEDAN SIN MIRAR: la base mundial no se pudo leer por ningún "
            "camino. NO se afirma que ningún Estado esté ausente de ella —eso sería "
            "confundir una fuente caída con un país que no produce—.")
    elif sin_mineral:
        vacios.append(
            f"{len(sin_mineral)} Estados del padrón NO figuran en la base mundial de "
            "minerales. No aparecer NO significa no tener: significa que no producen a una "
            "escala que mueva el total del mundo. Son: " + ", ".join(sin_mineral) + ".")
    vacios.extend(caidos)

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente=ORIGEN_USGS + "; " + ORIGEN_ENERGIA,
        url_fuente="https://www.usgs.gov/centers/national-minerals-information-center",
        calificacion=comun.calificar(
            "A", 2, False,
            "Dos organismos oficiales con método publicado y repetible. Sin corroboración "
            "independiente: para la mayoría de estos minerales no existe una segunda base "
            "mundial abierta que mida lo mismo."),
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": publicables,
            "cobertura": {m["clave"]: cobertura.get(m["clave"], 0) for m in publicables},
            "edicion_minerales": edicion,
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
