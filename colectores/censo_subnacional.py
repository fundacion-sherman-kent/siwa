# -*- coding: utf-8 -*-
"""¿Qué se puede llegar a publicar por unidad, y para cuántos Estados?

POR QUÉ EXISTE
---------------
La Dirección fijó un umbral para encender la capa subnacional: **más del 60 %
de las categorías del eje Seguridad, en el 70 % o más de los Estados**. Son
cinco categorías de ocho, en veinticuatro Estados de treinta y tres.

Contestar eso exige saber qué hay disponible por unidad de primer orden, y ese
inventario no existía: se venía averiguando fuente por fuente y a mano. Esto lo
convierte en máquina.

NO RECOLECTA DATOS. Publica un CENSO: qué temas ofrece cada fuente, para qué
Estados y a qué nivel de desagregación. Es la diferencia entre saber si se puede
y hacerlo. La capa sigue apagada; esto solo dice cuán lejos está de poder
encenderse.

QUÉ MIRA, Y POR QUÉ ESAS DOS
------------------------------
  · **La interfaz humanitaria de Naciones Unidas.** Publica eventos de
    conflicto y desplazamiento interno **por unidad de primer orden**. Personas
    refugiadas y retornadas NO: se publican por país de origen y de asilo, y la
    primera versión de este censo las contaba por error. Necesita un
    identificador que vive en el robot.
  · **La base georreferenciada de Upsala.** Evento por evento, con unidad y
    coordenada, desde 1989 y sin credencial. Se mide acá mismo cuántos Estados
    de la región deja con dato por unidad.

LO QUE ESTE CENSO NO DICE
---------------------------
Si esos datos son buenos, comparables o suficientes. Dice qué existe. Que un
Estado figure con eventos de conflicto por provincia no lo convierte en un
Estado con estadística de seguridad subnacional: son cosas distintas, y
confundirlas sería exactamente el error que este registro evita.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "censo_subnacional"
CAPA = "publico"

HAPI = "https://hapi.humdata.org/api/v2"
GED = "https://ucdp.uu.se/downloads/ged/ged261-csv.zip"

# Las ocho categorías del eje Seguridad, tal como el lector las ve en la columna
# izquierda. El umbral se mide contra esta lista y no contra otra: si mañana se
# agrega una categoría, el denominador cambia acá y el censo lo refleja solo.
CATEGORIAS_SEGURIDAD = [
    "Violencia y víctimas",
    "Terrorismo",
    "Presupuesto de seguridad",
    "Muertes que no son delito",
    "Grupos y territorio",
    "Flujos ilícitos",
    "Personas en movimiento",
    "Ciberseguridad",
]

# Qué tema de la interfaz humanitaria alimentaría qué categoría. Se declara para
# que nadie tenga que adivinarlo después, y para que el recuento del umbral sea
# reproducible.
TEMAS = {
    "coordination-context/conflict-events": "Grupos y territorio",
    "affected-people/idps": "Personas en movimiento",
}

# LOS QUE NO ENTRAN, y por qué. Estaban en la primera versión y fue un error de
# concepto: la especificación pública muestra que refugiados y retornados se
# publican por país de ORIGEN y de ASILO, sin `admin_level` ni `admin1_code`. No
# tienen unidad de primer orden, así que no pueden alimentar un censo
# subnacional por más que respondan.
FUERA_DE_CENSO = {
    "affected-people/refugees-persons-of-concern":
        "se publica por país de origen y de asilo, sin unidad de primer orden",
    "affected-people/returnees":
        "se publica por país de origen y de asilo, sin unidad de primer orden",
}

# Lo que ya está recolectado por fuente nacional, y de qué categoría es. Se
# escribe a mano porque son acuerdos con fuentes distintas, una por una, y el
# día que sean veinte esto va a ser la lista que muestre por qué costó tanto.
# ESCRITO A MANO, ESTO ENVEJECÍA SOLO. Esta tabla tenía tres países cuando el
# registro ya traía siete, y el umbral —lo que decide si la capa se enciende— se
# medía con ese inventario viejo. Lo que queda a mano es solo lo que ningún
# colector mide todavía; el resto se lee de lo que `estado_reciente` ya contó al
# abrir cada archivo, en `_de_los_colectores()`.
NACIONALES = {
    "URY": [("Violencia y víctimas", "Ministerio del Interior — microdatos por departamento")],
}


def _de_los_colectores() -> dict:
    """Lo que los colectores ya midieron por unidad, sin volver a pedir nada.

    `estado_reciente` cuenta, con el archivo abierto, cuántas unidades de primer
    orden trae la fuente de cada Estado. Acá se lee ese recuento. Dos reglas:

      · **Una división policial NO es una unidad de primer orden.** Trinidad y
        Tobago publica por división de la policía, que no coincide con la unidad
        censal y no tiene población publicada: no cuenta para el umbral, y se
        declara por qué.
      · **Un nombre sin cotejar no es una unidad contada.** Panamá escribe el mismo
        lugar de varias maneras: se anota el caso y no se suma hasta cotejarlo.
    """
    ruta = comun.DATOS / "publico" / "estado_reciente.json"
    if not ruta.exists():
        return {}
    try:
        d = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — un archivo ilegible no inventa cobertura
        return {}
    salida = {}
    for iso, f in (d.get("fuentes_nacionales") or {}).items():
        u = (f or {}).get("unidades") or {}
        cuantas = u.get("cuantas")
        motivo = None
        if u.get("coincide_con_la_unidad_censal") is False:
            motivo = (f"publica por {u.get('nombre')} y no por unidad de primer orden: "
                      "no coincide con la división censal ni tiene población publicada")
        elif u.get("hay_que_cotejar_los_nombres"):
            motivo = (f"trae {u.get('etiquetas_distintas')} etiquetas para el mismo puñado de "
                      f"{u.get('nombre')}s: hay que cotejar los nombres antes de contarlas")
        elif not cuantas:
            motivo = "la fuente no dejó ver el desglose por unidad en esta corrida"
        salida[iso] = {
            "categoria": "Violencia y víctimas",
            "fuente": (f or {}).get("organismo") or "estadística oficial del propio Estado",
            "nombre_unidad": u.get("nombre"),
            "unidades": cuantas,
            "cuenta_para_el_umbral": motivo is None,
            "por_que_no": motivo,
        }
    return salida


# COLOMBIA, MEDIDA Y NO RECOLECTADA. El portal de datos abiertos publica, además de
# homicidios, cuatro categorías más por departamento. Se consulta SOLO cuántos
# departamentos trae cada conjunto: ninguna cifra de delitos entra a este archivo.
# La capa sigue apagada (acta, 13/9/2026) y medir no es publicar.
DATOS_COLOMBIA = "https://www.datos.gov.co"
CONJUNTOS_COLOMBIA = [
    ("26zg-9p9r", "Flujos ilícitos", "Ministerio de Defensa — incautaciones de cocaína", "cod_depto"),
    ("g228-vp9d", "Flujos ilícitos", "Ministerio de Defensa — incautaciones de marihuana", "cod_depto"),
    ("nxbk-nikm", "Flujos ilícitos", "Ministerio de Defensa — incautaciones de base de coca", "cod_depto"),
    ("3cjd-phaj", "Flujos ilícitos", "Ministerio de Defensa — incautaciones de basuco", "cod_depto"),
    ("k2wp-tdv7", "Flujos ilícitos", "Ministerio de Defensa — incautaciones de insumos líquidos", "cod_depto"),
    ("d7zw-hpf4", "Grupos y territorio", "Ministerio de Defensa — secuestro", "cod_depto"),
    ("q2ib-t9am", "Grupos y territorio", "Ministerio de Defensa — extorsión", "cod_depto"),
    ("yi5j-5fe9", "Terrorismo", "Ministerio de Defensa — terrorismo", "cod_depto"),
    ("37p5-impc", "Terrorismo", "Policía Nacional — terrorismo", "departamento"),
    ("krnc-8azs", "Personas en movimiento", "Unidad para las Víctimas — desplazamiento", "cod_estado_depto"),
]
# Los 32 departamentos y Bogotá, por su código DANE. Los conjuntos traen además
# códigos que no son departamentos —«1111», «1112»—: no se cuentan como unidad, se
# cuentan aparte y se declaran.
DEPARTAMENTOS_DANE = {
    "05", "08", "11", "13", "15", "17", "18", "19", "20", "23", "25", "27", "41", "44",
    "47", "50", "52", "54", "63", "66", "68", "70", "73", "76", "81", "85", "86", "88",
    "91", "94", "95", "97", "99",
}
# Una categoría cuenta para Colombia si algún conjunto la cubre en 24 de sus 33
# unidades o más: la misma vara del 70 % que la dirección fijó para los Estados.
MINIMO_UNIDADES_COL = 24


def de_colombia() -> tuple:
    """Cuántos departamentos trae cada conjunto. Solo recuentos, nunca valores."""
    conjuntos, categorias, caidos = [], set(), []
    for ident, categoria, rotulo, columna in CONJUNTOS_COLOMBIA:
        consulta = urllib.parse.urlencode({"$select": f"{columna},count(*)",
                                           "$group": columna, "$limit": 500})
        url = f"{DATOS_COLOMBIA}/resource/{ident}.json?{consulta}"
        try:
            peticion = urllib.request.Request(url, headers={"User-Agent": comun.AGENTE,
                                                            "Accept": "application/json"})
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                grupos = json.loads(respuesta.read())
        except Exception as error:  # noqa: BLE001 — se declara SIN MIRAR, no se cuenta
            caidos.append(f"Colombia · {rotulo}: {que_dijo(error)}. Queda SIN MIRAR.")
            continue
        claves = {str(g.get(columna) or "").strip() for g in grupos} - {""}
        if columna == "departamento":
            # Este conjunto trae el nombre y no el código: se cuentan los nombres
            # distintos, y se declara que la comparación no es exacta.
            validas, otras = claves, set()
        else:
            validas = {c.zfill(2) for c in claves if c.zfill(2) in DEPARTAMENTOS_DANE}
            otras = {c for c in claves if c.zfill(2) not in DEPARTAMENTOS_DANE}
        conjuntos.append({
            "conjunto": ident, "categoria": categoria, "fuente": rotulo,
            "unidades": len(validas), "de": len(DEPARTAMENTOS_DANE),
            "codigos_que_no_son_departamento": len(otras),
            "por_nombre": columna == "departamento",
        })
        if len(validas) >= MINIMO_UNIDADES_COL:
            categorias.add(categoria)
        time.sleep(1)
    return conjuntos, categorias, caidos


# TRINIDAD Y TOBAGO Y BOLIVIA, MEDIDOS Y NO RECOLECTADOS (autorizado el 13/9/2026).
# Igual que Colombia: se abre el archivo, se cuentan unidades y delitos, y ninguna
# cifra entra a este censo.
TTPS = "https://ttps.gov.tt/statistics/download/?year={anio}"
# Qué delito del Servicio de Policía alimenta qué categoría. El secuestro extorsivo
# va a «Grupos y territorio», con el mismo criterio que el secuestro en Colombia.
TTPS_CATEGORIAS = {
    "Murders": "Violencia y víctimas",
    "Kidnapping for Ransom": "Grupos y territorio",
}
INE_BOLIVIA = "https://nube.ine.gob.bo/index.php/s/rb85ZWi9fyUJFHl/download"
DEPARTAMENTOS_BOLIVIA = ["Chuquisaca", "La Paz", "Cochabamba", "Oruro", "Potosí",
                         "Tarija", "Santa Cruz", "Beni", "Pando"]


def de_trinidad() -> tuple:
    """Divisiones policiales y delitos del último año completo. Solo recuentos."""
    anio = datetime.now(timezone.utc).year - 1
    peticion = urllib.request.Request(TTPS.format(anio=anio),
                                      headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=120) as respuesta:
        texto = respuesta.read().decode("utf-8", "replace")
    # El archivo abre con un título antes de la cabecera: se busca la cabecera.
    lineas = texto.splitlines()
    desde = next(i for i, l in enumerate(lineas) if l.startswith("Year,"))
    filas = list(csv.DictReader(io.StringIO("\n".join(lineas[desde:]))))
    divisiones = {f.get("Division") for f in filas} - {None, ""}
    por_delito = {}
    for f in filas:
        por_delito.setdefault(f.get("Offence"), set()).add(f.get("Division"))
    categorias, detalle = set(), []
    for delito, categoria in TTPS_CATEGORIAS.items():
        cubre = len(por_delito.get(delito, set()))
        detalle.append({"delito": delito, "categoria": categoria,
                        "divisiones": cubre, "de": len(divisiones)})
        if divisiones and cubre >= 0.7 * len(divisiones):
            categorias.add(categoria)
    return {"anio": anio, "divisiones": len(divisiones), "delitos": detalle}, categorias


def de_bolivia() -> tuple:
    """Si el cuadro de delitos del INE nombra los nueve departamentos y el homicidio."""
    peticion = urllib.request.Request(INE_BOLIVIA, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=180) as respuesta:
        libro = zipfile.ZipFile(io.BytesIO(respuesta.read()))
    textos = libro.read("xl/sharedStrings.xml").decode("utf-8", "replace")
    nombrados = [d for d in DEPARTAMENTOS_BOLIVIA if f">{d}<" in textos]
    tiene_homicidio = ">Homicidio<" in textos
    categorias = {"Violencia y víctimas"} if tiene_homicidio and len(nombrados) >= 7 else set()
    return ({"departamentos": len(nombrados), "de": len(DEPARTAMENTOS_BOLIVIA),
             "trae_homicidio": tiene_homicidio,
             "cuadro": "INE, cuadro 3.08.02.13 — delitos por departamento, Policía Boliviana"},
            categorias)


def identificador() -> str | None:
    return os.environ.get("HDX_HAPI_APP") or None


def que_dijo(error: Exception) -> str:
    """El error con su código y lo que contestó la fuente.

    «HTTPError» a secas no distingue un identificador rechazado de un exceso de
    pedidos, y así quedó el primer censo: cuatro fallas que no decían por qué.
    """
    codigo = getattr(error, "code", None)
    cuerpo = ""
    try:
        cuerpo = error.read().decode("utf-8", "replace")[:160] if hasattr(error, "read") else ""
    except Exception:  # noqa: BLE001 — el cuerpo es un detalle, no puede tapar el error
        cuerpo = ""
    partes = [type(error).__name__] + ([str(codigo)] if codigo else [])
    return " ".join(partes) + (f": {' '.join(cuerpo.split())}" if cuerpo else "")


def hapi(ruta: str, **filtros) -> list:
    """Una consulta a la interfaz humanitaria, con cortesía si pide ir más despacio."""
    app = identificador()
    if not app:
        raise RuntimeError("sin identificador: no se puede preguntar")
    consulta = {"output_format": "json", "app_identifier": app, "limit": 10000}
    consulta.update({k: v for k, v in filtros.items() if v is not None})
    url = f"{HAPI}/{ruta}?" + urllib.parse.urlencode(consulta)
    peticion = urllib.request.Request(url, headers={"User-Agent": comun.AGENTE,
                                                    "Accept": "application/json"})
    for intento in range(6):
        try:
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                return json.loads(respuesta.read()).get("data") or []
        except urllib.error.HTTPError as e:
            # Un servicio público que dice «más despacio» pide cortesía, no anuncia
            # una falla: se espera y se reintenta. Cualquier otro código, se sube.
            if e.code != 429 or intento == 5:
                raise
            time.sleep(4 * (intento + 1))
    return []


def de_upsala(isos_por_nombre: dict) -> dict:
    """Cuántos Estados deja Upsala con dato por unidad, y desde cuándo.

    Se baja el archivo entero —unos cuarenta megas— y no se consulta la interfaz
    con credencial, por la misma razón que el resto del registro usa ese camino:
    se puede probar antes de publicar y no gasta cuota de nadie.
    """
    peticion = urllib.request.Request(GED, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=600) as respuesta:
        crudo = respuesta.read()
    z = zipfile.ZipFile(io.BytesIO(crudo))
    nombre = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    filas = csv.DictReader(io.StringIO(z.read(nombre).decode("utf-8", "replace")))
    por_iso = {}
    for x in filas:
        iso = isos_por_nombre.get((x.get("country") or "").strip())
        if not iso:
            continue
        r = por_iso.setdefault(iso, {"eventos": 0, "con_unidad": 0,
                                     "unidades": set(), "desde": None, "hasta": None})
        r["eventos"] += 1
        unidad = (x.get("adm_1") or "").strip()
        if unidad:
            r["con_unidad"] += 1
            r["unidades"].add(unidad)
        try:
            anio = int(x.get("year") or 0)
        except ValueError:
            continue
        r["desde"] = anio if r["desde"] is None else min(r["desde"], anio)
        r["hasta"] = anio if r["hasta"] is None else max(r["hasta"], anio)
    for r in por_iso.values():
        r["unidades"] = len(r["unidades"])
    return por_iso


# Cómo llama la base de Upsala a los Estados del padrón.
UPSALA = {
    "Argentina": "ARG", "Bolivia": "BOL", "Brazil": "BRA", "Chile": "CHL",
    "Colombia": "COL", "Costa Rica": "CRI", "Cuba": "CUB",
    "Dominican Republic": "DOM", "Ecuador": "ECU", "El Salvador": "SLV",
    "Guatemala": "GTM", "Guyana": "GUY", "Haiti": "HTI", "Honduras": "HND",
    "Jamaica": "JAM", "Mexico": "MEX", "Nicaragua": "NIC", "Panama": "PAN",
    "Paraguay": "PRY", "Peru": "PER", "Suriname": "SUR",
    "Trinidad and Tobago": "TTO", "Uruguay": "URY", "Venezuela": "VEN",
    "Belize": "BLZ", "Bahamas": "BHS", "Barbados": "BRB",
    "Antigua and Barbuda": "ATG", "Dominica": "DMA", "Grenada": "GRD",
    "Saint Kitts and Nevis": "KNA", "Saint Lucia": "LCA",
    "Saint Vincent and the Grenadines": "VCT",
}


def construir() -> Path:
    padron = geo.padron()
    del_padron = {p["iso"]: p for p in padron}
    caidos = []

    # ── Upsala, que se puede probar acá mismo ──────────────────────────────
    try:
        upsala = de_upsala(UPSALA)
    except Exception as error:  # noqa: BLE001
        caidos.append(f"base georreferenciada de Upsala: {type(error).__name__}")
        upsala = {}

    # ── Colombia, conjunto por conjunto ────────────────────────────────────
    colombia, cats_colombia, caidos_col = de_colombia()
    caidos.extend(caidos_col)

    # ── Trinidad y Tobago y Bolivia ────────────────────────────────────────
    medidos = {}
    for iso, medir, rotulo in (("TTO", de_trinidad, "Servicio de Policía de Trinidad y Tobago"),
                               ("BOL", de_bolivia, "INE de Bolivia")):
        try:
            detalle, cats = medir()
            medidos[iso] = {"fuente": rotulo, "detalle": detalle, "categorias": sorted(cats)}
        except Exception as error:  # noqa: BLE001 — SIN MIRAR, no se cuenta
            caidos.append(f"{rotulo}: {que_dijo(error)}. Queda SIN MIRAR.")

    # ── La interfaz humanitaria, que necesita la llave del robot ───────────
    humanitaria, por_tema = {}, {}
    if not identificador():
        caidos.append(
            "SIN IDENTIFICADOR de la interfaz humanitaria: sus temas quedan SIN MIRAR, que "
            "no es lo mismo que no existir. Se carga como secreto del repositorio y este "
            "censo lo vuelve a intentar en la próxima corrida completa.")
    else:
        for ruta, categoria in TEMAS.items():
            # ESTADO POR ESTADO Y NO EL MUNDO ENTERO. La interfaz corta en 10.000
            # filas por consulta, y con todo el mundo la región podía no entrar en
            # esa página sin que nada avisara. Treinta y tres consultas chicas,
            # espaciadas, en vez de una grande truncada.
            vistos, fallo_tema = {}, None
            for iso in sorted(del_padron):
                try:
                    filas = hapi(ruta, location_code=iso, admin_level=1)
                except Exception as error:  # noqa: BLE001
                    fallo_tema = f"{ruta}: {que_dijo(error)}"
                    # Si la fuente rechaza el pedido —identificador inválido, ruta
                    # mal armada— va a rechazar los otros treinta y dos igual.
                    # Insistir sería descortés y no enseñaría nada nuevo.
                    break
                for f in filas:
                    v = vistos.setdefault(iso, {"filas": 0, "unidades": set()})
                    v["filas"] += 1
                    if f.get("admin1_code"):
                        v["unidades"].add(f["admin1_code"])
                time.sleep(1.5)
            if fallo_tema:
                caidos.append(fallo_tema)
                continue
            por_tema[ruta] = {
                "categoria": categoria,
                "estados": sorted(vistos),
                "cuantos_estados": len(vistos),
                "detalle": {k: {"filas": v["filas"], "unidades": len(v["unidades"])}
                            for k, v in vistos.items()},
            }
            for iso, v in vistos.items():
                humanitaria.setdefault(iso, set()).add(categoria)

    # ── El recuento contra el umbral ───────────────────────────────────────
    colectores = _de_los_colectores()
    por_estado = {}
    for iso, p in del_padron.items():
        categorias = set()
        for cat, _ in NACIONALES.get(iso, []):
            categorias.add(cat)
        propia = colectores.get(iso)
        if propia and propia["cuenta_para_el_umbral"]:
            categorias.add(propia["categoria"])
        if iso == "COL":
            categorias |= cats_colombia
        if iso in medidos:
            categorias |= set(medidos[iso]["categorias"])
        u = upsala.get(iso)
        if u and u["con_unidad"]:
            categorias.add("Grupos y territorio")
        categorias |= humanitaria.get(iso, set())
        por_estado[iso] = {
            "iso": iso, "pais": p["pais"], "bloque": p.get("bloque"),
            "categorias_alcanzables": sorted(categorias),
            "cuantas": len(categorias),
            "de_upsala": {k: v for k, v in (u or {}).items()} or None,
            "de_fuente_nacional": [f"{c} · {d}" for c, d in NACIONALES.get(iso, [])]
                                  + ([f"{x['categoria']} · {x['fuente']} ({x['unidades']} de "
                                      f"{x['de']} unidades)" for x in colombia]
                                     if iso == "COL" else [])
                                  + ([f"{c} · {medidos[iso]['fuente']}"
                                      for c in medidos[iso]["categorias"]]
                                     if iso in medidos else [])
                                  + ([f"{propia['categoria']} · {propia['fuente']} "
                                      f"({propia['unidades']} {propia['nombre_unidad']}s)"]
                                     if propia and propia["cuenta_para_el_umbral"] else []),
            "de_su_propio_estado": propia,
        }

    minimo = 5  # más del 60 % de ocho categorías
    llegan = [r for r in por_estado.values() if r["cuantas"] >= minimo]
    umbral_estados = 24  # 70 % de treinta y tres, redondeado hacia arriba

    registros = sorted(por_estado.values(), key=lambda r: (-r["cuantas"], r["pais"]))
    vacios = [
        "ESTO NO ES UNA CAPA DE DATOS: es un censo de lo que se podría llegar a publicar "
        "por unidad. Que un Estado figure con eventos de conflicto por provincia NO lo "
        "convierte en un Estado con estadística de seguridad subnacional. Son cosas "
        "distintas y confundirlas sería el error que este registro evita.",
        f"EL UMBRAL SE MIDE CONTRA LAS {len(CATEGORIAS_SEGURIDAD)} CATEGORÍAS del eje "
        f"Seguridad tal como el lector las ve: más del 60 % son {minimo}, y el 70 % de los "
        f"Estados son {umbral_estados}. Hoy llegan {len(llegan)}.",
        "UN CERO DE UPSALA NO ES AUSENCIA DE VIOLENCIA. Esa base registra violencia "
        "ORGANIZADA por encima de un umbral de muertes: un Estado sin eventos puede tener "
        "mucha violencia común y ningún conflicto armado. Leerlo como «país en paz» sería "
        "un error grave.",
        "Las fuentes nacionales se cuentan una por una y a mano porque son acuerdos "
        "distintos con cada Estado: no hay una interfaz regional que las junte, y esa "
        "ausencia es en sí misma un dato sobre la región.",
    ]
    if colombia:
        vacios.append(
            "COLOMBIA SE MIDIÓ, NO SE RECOLECTÓ. De cada conjunto del portal de datos "
            "abiertos se consultó solo cuántos departamentos trae; ninguna cifra de delitos "
            "entra a este archivo. Una categoría cuenta si algún conjunto la cubre en "
            f"{MINIMO_UNIDADES_COL} de las 33 unidades o más.")
        raros = sum(x["codigos_que_no_son_departamento"] for x in colombia)
        if raros:
            vacios.append(
                f"LOS CONJUNTOS DE COLOMBIA TRAEN {raros} CÓDIGOS QUE NO SON DEPARTAMENTOS "
                "—como «1111»—. No se cuentan como unidad. Antes de publicar cualquier "
                "cifra habría que averiguar qué registran.")
    if "TTO" in medidos:
        vacios.append(
            "TRINIDAD Y TOBAGO SE MIDE POR DIVISIÓN POLICIAL, NO POR UNIDAD ADMINISTRATIVA. "
            f"El Servicio de Policía publica {medidos['TTO']['detalle']['divisiones']} "
            "divisiones, que no coinciden con las corporaciones regionales del país. Antes de "
            "publicar habría que declararlo en cada cifra.")
    if "BOL" in medidos:
        vacios.append(
            "BOLIVIA SE MIDIÓ SOBRE UN CUADRO DEL INE: se comprobó que nombra los "
            "departamentos y el homicidio, no se leyó fila por fila. Los cuadros de trata, "
            "droga incautada y tránsito por departamento existen pero no se abrieron: no "
            "se cuentan.")
    for ruta, motivo in FUERA_DE_CENSO.items():
        vacios.append(f"NO ENTRA AL CENSO «{ruta}»: {motivo}. Estaba en la primera versión "
                      "y fue un error de concepto: un tema sin unidad no puede medir "
                      "disponibilidad por unidad.")
    vacios.extend(caidos)

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Censo propio de disponibilidad subnacional — Fundación Sherman Kent, "
               "sobre la base georreferenciada de Upsala y la interfaz humanitaria de "
               "Naciones Unidas",
        url_fuente="https://ucdp.uu.se/downloads/",
        calificacion=comun.calificar(
            "B", 3, False,
            "Recuento propio sobre fuentes de terceros. Mide disponibilidad, no calidad: "
            "dice qué existe por unidad, no si sirve."),
        registros=registros,
        vacios=vacios,
        extra={
            "categorias_del_eje": CATEGORIAS_SEGURIDAD,
            "umbral": {
                "categorias_minimas": minimo,
                "estados_minimos": umbral_estados,
                "estados_que_llegan": len(llegan),
                "se_cumple": len(llegan) >= umbral_estados,
                "quienes_llegan": sorted(r["pais"] for r in llegan),
            },
            "por_tema_humanitario": por_tema,
            "colombia_por_conjunto": colombia,
            "medidos_por_archivo": medidos,
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
