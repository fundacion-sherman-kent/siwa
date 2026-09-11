# -*- coding: utf-8 -*-
"""Infraestructuras críticas: por dónde entra y sale un país.

POR QUÉ ESTÁ EN EL EJE DEFENSA
--------------------------------
Porque una infraestructura es crítica cuando su falla no se reemplaza. Un país
con un solo punto de amarre de cable submarino queda incomunicado con un
accidente de ancla; uno con veinte, no. Esa diferencia no aparece en ninguna
estadística de conectividad —las dos pueden tener el mismo porcentaje de gente
con internet— y sin embargo es la que importa cuando algo se corta.

QUÉ PUBLICA
------------
  · **Puntos de amarre de cables submarinos.** Dónde toca tierra el internet de
    cada Estado. Es el dato más revelador del conjunto y el que menos se
    publica: la región tiene Estados con un solo punto.
  · **Aeropuertos grandes y medianos.** La otra puerta física, y la única que
    queda cuando el mar se complica.
  · **Generación eléctrica y capacidad solar instalada.** Con serie larga, y de
    un productor distinto del que el registro ya usaba para electricidad: dos
    fuentes sobre lo mismo permiten ver si coinciden.

DOS CEROS QUE NO SON VACÍOS
-----------------------------
Bolivia y el Paraguay no tienen ningún punto de amarre porque **no tienen
costa**. Ese cero no es un dato que falta: es el dato, y además explica por qué
los dos dependen de la infraestructura de sus vecinos para salir al mundo.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "infraestructura"
CAPA = "publico"
HASTA = datetime.now(timezone.utc).year - 1
AHORA = datetime.now(timezone.utc).year

CABLES = "https://www.submarinecablemap.com/api/v3/landing-point/landing-point-geo.json"
AEROPUERTOS = "https://davidmegginson.github.io/ourairports-data/airports.csv"
REJILLA = "https://ourworldindata.org/grapher/{slug}.csv"

ORIGEN_CABLES = "Mapa de cables submarinos — TeleGeography, interfaz pública"
ORIGEN_AEROPUERTOS = "OurAirports — censo abierto y colaborativo de aeródromos del mundo"
ORIGEN_ENERGIA = "Energy Institute y Ember, via Our World in Data"

# Los Estados del padrón sin salida al mar. El cero de cables no es un vacío:
# es geografía, y hay que decirlo o el lector lo lee como falta de dato.
SIN_COSTA = {"BOL", "PRY"}

# Cómo llama a los Estados del padrón el mapa de cables, que escribe en inglés
# y sin código. Se usa SOLO cuando el punto no cae dentro del padrón: los
# amarres están sobre la línea de costa y varios quedan unos metros mar adentro.
EN_INGLES = {
    "Argentina": "ARG", "Bolivia": "BOL", "Brazil": "BRA", "Chile": "CHL",
    "Colombia": "COL", "Costa Rica": "CRI", "Cuba": "CUB",
    "Dominican Republic": "DOM", "Ecuador": "ECU", "El Salvador": "SLV",
    "Guatemala": "GTM", "Guyana": "GUY", "Haiti": "HTI", "Honduras": "HND",
    "Jamaica": "JAM", "Mexico": "MEX", "Nicaragua": "NIC", "Panama": "PAN",
    "Paraguay": "PRY", "Peru": "PER", "Suriname": "SUR",
    "Trinidad and Tobago": "TTO", "Uruguay": "URY", "Venezuela": "VEN",
    "Belize": "BLZ", "Bahamas": "BHS", "The Bahamas": "BHS", "Barbados": "BRB",
    "Antigua and Barbuda": "ATG", "Antigua": "ATG", "Dominica": "DMA",
    "Grenada": "GRD", "Saint Kitts and Nevis": "KNA",
    "St. Kitts and Nevis": "KNA", "Saint Lucia": "LCA", "St. Lucia": "LCA",
    "Saint Vincent and the Grenadines": "VCT",
    "St. Vincent and the Grenadines": "VCT",
}

ENERGIA = [
    {"clave": "generacion_electrica", "slug": "electricity-generation",
     "columna": "Total electricity", "rotulo": "Generación eléctrica",
     "unidad": "teravatios hora",
     "cautela": "SEGUNDA FUENTE de algo que el registro ya publica con el Banco Mundial. "
                "Generar mucha electricidad no dice nada sobre si llega a todos ni sobre "
                "cuánta se pierde en el camino: esas dos cosas están en esta misma "
                "sección y se leen juntas."},
    {"clave": "capacidad_solar", "slug": "installed-solar-pv-capacity",
     "columna": "Solar", "rotulo": "Capacidad solar instalada",
     "unidad": "gigavatios",
     "cautela": "CAPACIDAD INSTALADA no es energía generada: es cuánto podría generar si "
                "el sol pegara todo el tiempo. Sirve para ver el ritmo al que un país "
                "cambia su matriz, no para saber cuánto produce."},
]


def pedir(url: str, espera: int = 120) -> bytes:
    peticion = urllib.request.Request(url, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=espera) as respuesta:
        return respuesta.read()


def cables() -> tuple:
    """Puntos de amarre por Estado, resueltos por geometría y, si no, por nombre.

    DOS CAMINOS Y NO UNO, y quedó escrito porque el primero solo fallaba en
    silencio: los amarres están sobre la línea de costa y varios caen unos
    metros fuera del padrón. Granada aparecía con su nombre en el archivo y el
    recuento le daba cero. Se resuelve por geometría; lo que no cae adentro se
    busca por el nombre del país, que la fuente escribe al final del rótulo.
    """
    d = json.loads(pedir(CABLES))
    por_iso, por_geometria, por_nombre, ajenos = {}, 0, 0, 0
    for f in d.get("features") or []:
        c = ((f.get("geometry") or {}).get("coordinates") or [])
        nombre = ((f.get("properties") or {}).get("name") or "")
        p = geo.pais_de(c[0], c[1]) if len(c) >= 2 else None
        iso = p["iso"] if p else EN_INGLES.get(nombre.split(",")[-1].strip())
        if not iso:
            ajenos += 1
            continue
        por_iso[iso] = por_iso.get(iso, 0) + 1
        if p:
            por_geometria += 1
        else:
            por_nombre += 1
    return por_iso, por_geometria, por_nombre, ajenos


def aeropuertos() -> tuple:
    """Aeródromos grandes y medianos por Estado.

    Se cuentan grandes y medianos y NO los pequeños: el censo trae más de diez
    mil pistas chicas en la región, muchas de ellas privadas o de estancia, y
    contarlas mediría otra cosa —cuánta aviación general hay— en vez de por
    dónde entra y sale un país.
    """
    texto = pedir(AEROPUERTOS, espera=180).decode("utf-8", "replace")
    filas = list(csv.DictReader(io.StringIO(texto)))
    dos_letras = {v: k for k, v in comun.DOS_LETRAS.items()}
    por_iso, chicos = {}, 0
    for x in filas:
        iso = dos_letras.get((x.get("iso_country") or "").strip())
        if not iso:
            continue
        if x.get("type") in ("large_airport", "medium_airport"):
            por_iso[iso] = por_iso.get(iso, 0) + 1
        else:
            chicos += 1
    return por_iso, chicos, len(filas)


def rejilla(slug: str) -> list:
    texto = pedir(REJILLA.format(slug=slug), espera=90).decode("utf-8", "replace")
    return list(csv.DictReader(io.StringIO(texto)))


def serie_de(filas: list, columna: str, del_padron: set) -> tuple:
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


def foto(valor) -> dict:
    """La ficha de un recuento sin historia: un punto, y se dice que es un punto."""
    return {"valor": valor, "anio": AHORA,
            "anio_anterior": None, "valor_anterior": None, "variacion_pct": None,
            "anio_inicial": AHORA, "valor_inicial": valor,
            "tendencia_ventana_pct": None,
            "serie": [{"anio": AHORA, "valor": valor}]}


def construir() -> Path:
    padron = geo.padron()
    del_padron = {p["iso"] for p in padron}
    caidos = []

    try:
        por_cable, por_geo, por_nom, ajenos = cables()
    except Exception as error:  # noqa: BLE001 — la fuente caída se declara
        caidos.append(f"cables submarinos: {type(error).__name__}")
        por_cable, por_geo, por_nom, ajenos = {}, 0, 0, 0

    try:
        por_aero, chicos, censo = aeropuertos()
    except Exception as error:  # noqa: BLE001
        caidos.append(f"aeropuertos: {type(error).__name__}")
        por_aero, chicos, censo = {}, 0, 0

    datos, futuros, rejillas = {}, 0, {}
    for m in ENERGIA:
        if m["slug"] not in rejillas:
            try:
                rejillas[m["slug"]] = rejilla(m["slug"])
            except Exception as error:  # noqa: BLE001
                caidos.append(f"{m['slug']}: {type(error).__name__}")
                rejillas[m["slug"]] = []
        s, f = serie_de(rejillas[m["slug"]], m["columna"], del_padron)
        datos[m["clave"]], futuros = s, futuros + f

    registros, cobertura = [], {}
    for p in padron:
        f = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        # EL CERO DE UN PAIS SIN COSTA SE PUBLICA. No es un dato que falta: es el
        # dato, y explica por que Bolivia y el Paraguay salen al mundo por la
        # infraestructura de sus vecinos.
        if por_cable or p["iso"] in SIN_COSTA:
            n = por_cable.get(p["iso"], 0)
            if n or p["iso"] in SIN_COSTA:
                ficha_cables = foto(n)
                # EL CERO DE UN PAIS SIN COSTA ENCABEZA LA TARJETA, porque se
                # ordena de menor a mayor. Sin esta nota el lector lee «Bolivia,
                # 0 puntos de amarre» como la peor fragilidad de la región, y es
                # geografía: no hay costa donde amarrar. La nota viaja con el
                # dato y no solo en la pantalla.
                if p["iso"] in SIN_COSTA:
                    ficha_cables["nota"] = "no tiene costa"
                f["indicadores"]["cables_submarinos"] = ficha_cables
                cobertura["cables_submarinos"] = cobertura.get("cables_submarinos", 0) + 1
        if p["iso"] in por_aero:
            f["indicadores"]["aeropuertos"] = foto(por_aero[p["iso"]])
            cobertura["aeropuertos"] = cobertura.get("aeropuertos", 0) + 1
        for m in ENERGIA:
            s = datos[m["clave"]].get(p["iso"])
            if s:
                f["indicadores"][m["clave"]] = ficha(s)
                cobertura[m["clave"]] = cobertura.get(m["clave"], 0) + 1
        if f["indicadores"]:
            registros.append(f)
    registros.sort(key=lambda r: r["pais"])

    medidas = [
        # ESTA SI TIENE DIRECCION, y es al reves de lo que uno esperaría de un
        # recuento: pocos puntos de amarre es PEOR, porque un solo accidente de
        # ancla deja a un Estado incomunicado. Marcarla como magnitud sin lado
        # ponía a Brasil con 75 al frente y escondía a Guyana con 1, que es el
        # único dato que este cuadro tiene para contar. No es un juicio
        # político: es cómo funciona una red sin camino alternativo.
        {"clave": "cables_submarinos", "rotulo": "Puntos de amarre de cable submarino",
         "eje": "Defensa", "unidad": "puntos de amarre",
         "unidad_singular": "punto de amarre", "mas_es_peor": False,
         "origen": ORIGEN_CABLES,
         "cautela": "Es DÓNDE TOCA TIERRA el internet del país. Lo que importa no es el "
                    "número alto sino el bajo: con un solo punto, un accidente de ancla "
                    "deja a un Estado incomunicado, y varios de la región tienen uno. Un "
                    "CERO puede ser geografía y no falta de dato: Bolivia y el Paraguay no "
                    "tienen costa. Cuenta puntos, no cables: por un mismo punto pueden "
                    "entrar varios."},
        {"clave": "aeropuertos", "rotulo": "Aeropuertos grandes y medianos",
         "eje": "Defensa", "unidad": "aeropuertos", "unidad_singular": "aeropuerto",
         "mas_es_peor": False, "sin_direccion": True, "origen": ORIGEN_AEROPUERTOS,
         "cautela": "NO se cuentan las pistas chicas, que en la región son más de diez mil "
                    "y en buena parte privadas: contarlas mediría cuánta aviación general "
                    "hay, no por dónde entra y sale un país. El censo es COLABORATIVO y no "
                    "oficial: es el más completo que existe abierto, y eso mismo quiere "
                    "decir que un Estado con poca gente cargando datos puede figurar con "
                    "menos de los que tiene."},
    ] + [
        {"clave": m["clave"], "rotulo": m["rotulo"], "eje": "Defensa",
         "unidad": m["unidad"], "mas_es_peor": False, "sin_direccion": True,
         "origen": ORIGEN_ENERGIA, "cautela": m["cautela"]}
        for m in ENERGIA
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

    sin_cable = sorted(p["pais"] for p in padron
                       if p["iso"] not in por_cable and p["iso"] not in SIN_COSTA)
    vacios = [
        "UN CERO EN CABLES PUEDE SER GEOGRAFÍA. Bolivia y el Paraguay no tienen costa: su "
        "cero no es un dato que falta, es el dato, y explica por qué salen al mundo por la "
        "infraestructura de sus vecinos.",
        "SE CUENTAN PUNTOS DE AMARRE, NO CABLES. Por un mismo punto pueden entrar varios "
        "cables, y un país con dos puntos y diez cables está mejor parado que uno con dos "
        "puntos y dos cables. Este recuento no distingue esa diferencia.",
        f"Los puntos se ubican por su coordenada contra el padrón de esta casa, y los que "
        f"caen fuera —están sobre la línea de costa y varios quedan metros mar adentro— se "
        f"resuelven por el nombre del país que la fuente escribe en el rótulo: "
        f"{por_geo} por coordenada y {por_nom} por nombre. Sin ese segundo camino, Granada "
        "figuraba con cero teniendo sus amarres nombrados en el archivo.",
        "EL CENSO DE AEROPUERTOS ES COLABORATIVO, no oficial. Es el más completo que existe "
        "abierto y por eso se usa, pero un Estado con poca gente cargando datos puede "
        "figurar con menos aeródromos de los que tiene.",
        "NI LOS CABLES NI LOS AEROPUERTOS TIENEN SERIE: la fuente publica el estado de hoy, "
        "no su historia. Se guarda como un punto del año en curso y no se dibuja tendencia, "
        "porque no la hay.",
        f"NI EL AÑO EN CURSO NI EL FUTURO ENTRAN en las series de energía: se corta en "
        f"{HASTA}. {futuros} puntos quedaron afuera.",
        "La generación eléctrica es SEGUNDA FUENTE de algo que el registro ya publica con "
        "el Banco Mundial. Si difieren, ninguna está mal: cada una arma el total con reglas "
        "propias, y la diferencia es un dato sobre cómo se mide.",
    ]
    if sin_cable:
        vacios.append(
            f"{len(sin_cable)} Estados con costa y sin ningún punto de amarre en la fuente: "
            + ", ".join(sin_cable) + ". No se afirma que no lo tengan: se afirma que la "
            "fuente no lo registra.")
    if ajenos:
        vacios.append(f"{ajenos} puntos de amarre del mundo quedan fuera de este registro "
                      "por no pertenecer a ningún Estado del padrón.")
    vacios.extend(caidos)

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente=f"{ORIGEN_CABLES}; {ORIGEN_AEROPUERTOS}; {ORIGEN_ENERGIA}",
        url_fuente="https://www.submarinecablemap.com/",
        calificacion=comun.calificar(
            "B", 3, False,
            "Tres fuentes abiertas y verificables, dos de ellas colaborativas y no "
            "oficiales. Se califica B-3 y no A-2 justamente por eso: el censo de "
            "aeródromos y el mapa de cables los mantienen comunidades, no Estados, y su "
            "cobertura depende de quién cargue los datos."),
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": publicables,
            "cobertura": {m["clave"]: cobertura.get(m["clave"], 0) for m in publicables},
            "censo_de_aerodromos": censo,
            "aerodromos_chicos_no_contados": chicos,
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
