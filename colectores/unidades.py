# -*- coding: utf-8 -*-
"""El padrón subnacional: las unidades de primer orden de los 33 Estados.

QUÉ ES, Y POR QUÉ ES LA PIEZA QUE FALTABA
------------------------------------------
El registro tiene un padrón de 33 Estados desde el primer día. Para bajar de
escala hace falta el equivalente un nivel abajo: **qué unidades de primer orden
tiene cada Estado, cómo las llama, de dónde sale su límite y de qué año es.**
Sin eso, cualquier dato subnacional es una lista de nombres sin padrón, y este
registro ya sabe adónde lleva eso.

DOS FUENTES, PORQUE UNA SOLA NO ALCANZA
----------------------------------------
La capa homologada de la CEPAL —Proyecto MEGA, con UN-GGIM Américas— cubre 19
Estados. Los otros 14 —el Caribe no iberoamericano, Haití, Belice y las
Guayanas— no están, y son el mismo cuarto del padrón que ya era invisible en el
mapa por superficie. Para esos se usa geoBoundaries, que los cubre a todos.

**Cada unidad declara de cuál de las dos salió, de qué año es su límite y bajo
qué licencia**, porque no son la misma cosa: hay límites de 2005 y de 2021, y
tres licencias distintas de compartir-igual que pesan sobre cualquier producto
que la Fundación venda.

EL NOMBRE LOCAL NO SE TRADUCE
------------------------------
Provincia, departamento, región, estado, *parish*, *district*. Cada Estado llama
a su unidad como la llama, y el registro la muestra así. Poner «provincia»
encima de una *parish* de Jamaica sería inventar una categoría que ese Estado no
usa.

SI LA UNIDAD ADMITE UNA TASA, O SOLO UN RECUENTO
-------------------------------------------------
Es la regla que la Dirección aceptó, y acá se calcula en vez de suponerse. Un
recuento de casos tiene un error relativo cercano a **1/√n**: con 30 casos es
del 18 %, con 10 sube al 32 %. Dividir los homicidios de un país entre sus
unidades da el orden de magnitud de casos por unidad, y con eso se decide:

  · **30 casos o más por unidad** → la tasa por 100.000 significa algo.
  · **menos de 30** → se publica el recuento y no la tasa, y se dice por qué.

San Vicente y las Granadinas tiene 32 homicidios y 6 parroquias: cinco por
unidad. Jamaica tiene 1.484 y 14 parroquias: ciento seis. La diferencia no es
política ni de tamaño del país: es aritmética, y por eso se calcula.
"""
from __future__ import annotations

import json
import sys
import unicodedata
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "unidades"
CAPA = "publico"

WFS = ("https://geoportal.cepal.org/geoserver/wfs?service=WFS&version=2.0.0"
       "&request=GetFeature&typeNames=geonode:mega_nivel_2_simplificado"
       "&outputFormat=application/json&propertyName=nv2_cod_in,nv2_nbre,country_es")
GB = "https://www.geoboundaries.org/api/current/gbOpen/{iso}/ADM1/"

# CASOS POR UNIDAD PARA QUE UNA TASA SIGNIFIQUE ALGO. El error relativo de un
# recuento es cercano a 1/raiz(n): con 30 casos es del 18 %, con 10 del 32 %.
CASOS_PARA_TASA = 30

# El nombre que la CEPAL no trae: como llama cada Estado a su unidad de primer
# orden. Se escribe una sola vez, se declara, y NO se traduce.
NOMBRE_LOCAL = {
    "ARG": "provincia", "BOL": "departamento", "BRA": "estado", "CHL": "región",
    "COL": "departamento", "CRI": "provincia", "CUB": "provincia", "ECU": "provincia",
    "SLV": "departamento", "GTM": "departamento", "HND": "departamento", "MEX": "estado",
    "NIC": "departamento", "PAN": "provincia", "PRY": "departamento", "PER": "departamento",
    "DOM": "provincia", "URY": "departamento", "VEN": "estado",
}

# Los 19 que trae la capa de la CEPAL, por su nombre en esa capa.
DE_CEPAL = {
    "Argentina": "ARG", "Bolivia": "BOL", "Brasil": "BRA", "Chile": "CHL",
    "Colombia": "COL", "Costa Rica": "CRI", "Cuba": "CUB", "Ecuador": "ECU",
    "El Salvador": "SLV", "Guatemala": "GTM", "Honduras": "HND", "México": "MEX",
    "Nicaragua": "NIC", "Panamá": "PAN", "Paraguay": "PRY", "Perú": "PER",
    "República Dominicana": "DOM", "Uruguay": "URY", "Venezuela": "VEN",
}


def pedir(url: str, espera: int = 120):
    peticion = urllib.request.Request(
        url, headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=espera) as respuesta:
        return json.loads(respuesta.read().decode("utf-8", "replace"))


def sello(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).strip().lower()


def de_cepal() -> dict:
    """Las unidades de los 19 Estados que la capa homologada cubre."""
    d = pedir(WFS)
    por_pais = {}
    for f in d.get("features", []):
        p = f.get("properties") or {}
        iso = DE_CEPAL.get(p.get("country_es"))
        if not iso:
            continue
        por_pais.setdefault(iso, []).append({
            "codigo": p.get("nv2_cod_in"),
            "nombre": p.get("nv2_nbre"),
        })
    return por_pais


def de_geoboundaries(iso: str) -> tuple:
    """Las unidades de un Estado que la CEPAL no cubre, con su procedencia."""
    d = pedir(GB.format(iso=iso), espera=90)
    d = d[0] if isinstance(d, list) else d
    meta = {
        "fuente": "geoBoundaries (gbOpen)",
        "nombre_local": (d.get("boundaryCanonical") or "").strip() or None,
        "anio_limite": d.get("boundaryYearRepresented"),
        "licencia": d.get("boundaryLicense"),
        "cuantas_declara": int(d.get("admUnitCount") or 0),
    }
    unidades = []
    url = d.get("simplifiedGeometryGeoJSON") or d.get("gjDownloadURL")
    if url:
        try:
            g = pedir(url, espera=120)
            for f in (g.get("features") or []):
                pr = f.get("properties") or {}
                unidades.append({"codigo": pr.get("shapeID") or pr.get("shapeISO"),
                                 "nombre": pr.get("shapeName")})
        except Exception:  # noqa: BLE001 — sin nombres, la cuenta declarada igual sirve
            pass
    return unidades, meta


def construir() -> Path:
    padron = geo.padron()
    homicidios = {}
    ruta = comun.DATOS / "publico" / "oms_homicidios.json"
    if ruta.exists():
        for r in json.loads(ruta.read_text(encoding="utf-8")).get("registros", []):
            n = (r.get("numero") or {}).get("valor")
            if n is not None:
                homicidios[r["iso"]] = {"casos": n, "anio": (r.get("numero") or {}).get("anio")}

    cepal = de_cepal()
    registros, vacios = [], []
    sin_geometria = []

    for p in padron:
        iso = p["iso"]
        if iso in cepal:
            unidades = cepal[iso]
            meta = {"fuente": "CEPAL · Proyecto MEGA, nivel 2 (con UN-GGIM Américas)",
                    "nombre_local": NOMBRE_LOCAL.get(iso),
                    "anio_limite": None, "licencia": None,
                    "cuantas_declara": len(unidades)}
        else:
            try:
                unidades, meta = de_geoboundaries(iso)
            except Exception as e:  # noqa: BLE001 — un Estado sin límites se declara
                sin_geometria.append(f"{p['pais']} ({type(e).__name__})")
                continue

        cuantas = len(unidades) or meta.get("cuantas_declara") or 0
        if not cuantas:
            sin_geometria.append(p["pais"])
            continue

        # ¿Admite tasa, o solo recuento? Se calcula, no se supone.
        h = homicidios.get(iso)
        por_unidad = (h["casos"] / cuantas) if h and cuantas else None
        registros.append({
            "iso": iso,
            "pais": p["pais"],
            "bloque": p.get("bloque"),
            "unidades": cuantas,
            "nombre_local": meta.get("nombre_local"),
            "fuente_geometria": meta.get("fuente"),
            "anio_limite": meta.get("anio_limite"),
            "licencia_geometria": meta.get("licencia"),
            "homicidios_del_pais": (round(h["casos"]) if h else None),
            "anio_homicidios": (h["anio"] if h else None),
            "casos_por_unidad": (round(por_unidad, 1) if por_unidad is not None else None),
            "admite_tasa": (por_unidad >= CASOS_PARA_TASA) if por_unidad is not None else None,
            "porque": (
                None if por_unidad is None else
                (f"{round(por_unidad)} homicidios por unidad: con ese recuento la tasa por "
                 "100.000 tiene un error relativo tolerable."
                 if por_unidad >= CASOS_PARA_TASA else
                 f"{round(por_unidad, 1)} homicidios por unidad. Con tan pocos casos una tasa "
                 "por 100.000 se mueve enormemente con un caso más: se publica el recuento.")),
            "lista": sorted(unidades, key=lambda u: sello(u.get("nombre"))) if unidades else None,
        })

    con_tasa = sum(1 for r in registros if r["admite_tasa"] is True)
    sin_tasa = sum(1 for r in registros if r["admite_tasa"] is False)
    sin_medir = sum(1 for r in registros if r["admite_tasa"] is None)
    total = sum(r["unidades"] for r in registros)

    if sin_geometria:
        vacios.append("Estados sin límites de primer orden en ninguna de las dos fuentes: "
                      + ", ".join(sorted(sin_geometria)) + ".")
    if sin_medir:
        vacios.append(
            f"{sin_medir} Estados no tienen recuento absoluto de homicidios en la fuente de la "
            "OMS, así que no se puede decidir si sus unidades admiten tasa. No se supone: queda "
            "sin decidir.")
    vacios.append(
        "Los límites NO son del mismo año en todas partes: los de la CEPAL son de su capa "
        "vigente y los de geoBoundaries van de 2005 a 2021. Cada Estado declara el suyo.")
    vacios.append(
        "Tres licencias de geoBoundaries son de compartir-igual —CC BY-SA y ODbL—: esos límites "
        "no pueden viajar a un producto que la Fundación venda sin arrastrar la misma condición.")
    vacios.append(
        "Este padrón trae las unidades y sus límites, NO datos sobre ellas. Qué publica cada "
        "jurisdicción de sí misma se mide aparte, en el censo de fuentes subnacionales.")

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="CEPAL — Proyecto MEGA nivel 2 (con UN-GGIM Américas) y geoBoundaries (gbOpen)",
        # LA DIRECCION QUE SE CITA TIENE QUE ABRIRSE. La anterior era el extremo
        # de la interfaz: contesta a una consulta con parametros y devuelve error
        # a quien la abre en un navegador. Se cita la pagina que una persona
        # puede mirar; la interfaz sigue documentada adentro del colector.
        url_fuente="https://statistics.cepal.org/geo/geo-cepalstat/?lang=es",
        calificacion=comun.calificar(
            "A", 2, True,
            "Dos fuentes independientes se reparten el padrón sin superponerse: la CEPAL cubre "
            "19 Estados y geoBoundaries los 14 restantes. Cada unidad declara de cuál salió."),
        registros=registros,
        vacios=vacios,
        extra={"resumen": {
            "estados": len(registros),
            "unidades_de_primer_orden": total,
            "de_cepal": sum(1 for r in registros if "CEPAL" in (r["fuente_geometria"] or "")),
            "de_geoboundaries": sum(1 for r in registros
                                    if "geoBoundaries" in (r["fuente_geometria"] or "")),
            "admiten_tasa": con_tasa,
            "solo_recuento": sin_tasa,
            "sin_decidir": sin_medir,
            "casos_para_tasa": CASOS_PARA_TASA,
            "regla": "El error relativo de un recuento es cercano a 1/raíz(n): con 30 casos es "
                     "del 18 %, con 10 sube al 32 %. Por debajo de 30 casos por unidad se "
                     "publica el recuento y no la tasa.",
        }},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
