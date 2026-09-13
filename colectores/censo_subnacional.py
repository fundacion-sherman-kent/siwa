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
NACIONALES = {
    "COL": [("Violencia y víctimas", "Policía Nacional — homicidios por departamento")],
    "ARG": [("Violencia y víctimas", "SNIC — homicidios dolosos por provincia")],
    "URY": [("Violencia y víctimas", "Ministerio del Interior — microdatos por departamento")],
}


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
    por_estado = {}
    for iso, p in del_padron.items():
        categorias = set()
        for cat, _ in NACIONALES.get(iso, []):
            categorias.add(cat)
        u = upsala.get(iso)
        if u and u["con_unidad"]:
            categorias.add("Grupos y territorio")
        categorias |= humanitaria.get(iso, set())
        por_estado[iso] = {
            "iso": iso, "pais": p["pais"], "bloque": p.get("bloque"),
            "categorias_alcanzables": sorted(categorias),
            "cuantas": len(categorias),
            "de_upsala": {k: v for k, v in (u or {}).items()} or None,
            "de_fuente_nacional": [f"{c} · {d}" for c, d in NACIONALES.get(iso, [])],
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
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
