# -*- coding: utf-8 -*-
"""Sanciones según quien las dicta: Estados Unidos (OFAC) y Reino Unido (OFSI).

POR QUÉ EXISTE
--------------
El registro contaba sanciones por OpenSanctions, que RECOPILA listas de terceros
y tiene licencia no comercial. Estas son las listas PRIMARIAS de dos Estados que
sancionan, sin credencial: la lista SDN de la Oficina de Control de Activos
Extranjeros del Tesoro de EE. UU. y la lista consolidada de la Oficina de
Implementación de Sanciones Financieras del Reino Unido (Open Government
Licence v3). Autorizado por la dirección el 14/9/2026.

QUÉ CUENTA, Y QUÉ NO
--------------------
Cuenta PERSONAS Y ENTIDADES DISTINTAS con al menos un domicilio declarado en el
país. **No mide conducta del Estado**: una lista de sanciones dice a quién decidió
sancionar otro gobierno, con sus propios criterios y prioridades. Un número alto
puede reflejar crimen organizado con domicilio en el país, un régimen sancionado
o simplemente más atención de quien sanciona.
"""
from __future__ import annotations

import csv
import io
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "sanciones_primarias"
CAPA = "publico"
OFAC_ADD = "https://www.treasury.gov/ofac/downloads/add.csv"
OFSI = "https://ofsistorage.blob.core.windows.net/publishlive/2022format/ConList.csv"

EN_INGLES = {
    "Argentina": "ARG", "Bolivia": "BOL", "Brazil": "BRA", "Chile": "CHL", "Colombia": "COL",
    "Costa Rica": "CRI", "Cuba": "CUB", "Dominican Republic": "DOM", "Ecuador": "ECU",
    "El Salvador": "SLV", "Guatemala": "GTM", "Guyana": "GUY", "Haiti": "HTI", "Honduras": "HND",
    "Jamaica": "JAM", "Mexico": "MEX", "Nicaragua": "NIC", "Panama": "PAN", "Paraguay": "PRY",
    "Peru": "PER", "Suriname": "SUR", "Trinidad and Tobago": "TTO", "Uruguay": "URY",
    "Venezuela": "VEN", "Belize": "BLZ", "Bahamas": "BHS", "The Bahamas": "BHS",
    "Bahamas, The": "BHS", "Barbados": "BRB", "Antigua and Barbuda": "ATG", "Dominica": "DMA",
    "Grenada": "GRD", "Saint Kitts and Nevis": "KNA", "St. Kitts and Nevis": "KNA",
    "Saint Lucia": "LCA", "St. Lucia": "LCA", "Saint Vincent and the Grenadines": "VCT",
    "St. Vincent and the Grenadines": "VCT",
}


def pedir(url: str) -> str:
    peticion = urllib.request.Request(url, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=180) as respuesta:
        crudo = respuesta.read()
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            return crudo.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return crudo.decode("utf-8", "replace")


def ofac() -> dict:
    """Entidades distintas (número de registro SDN) con domicilio en cada país."""
    por_iso = {}
    for fila in csv.reader(io.StringIO(pedir(OFAC_ADD))):
        if len(fila) < 5:
            continue
        iso = EN_INGLES.get(fila[4].strip())
        if iso:
            por_iso.setdefault(iso, set()).add(fila[0].strip())
    if len(por_iso) < 15 or len(por_iso.get("MEX", ())) < 100:
        raise RuntimeError("La lista de la OFAC dejó muy pocos Estados de la región o a México con "
                           "menos de cien entradas: la lectura falló.")
    return {k: len(v) for k, v in por_iso.items()}


def ofsi() -> tuple:
    """Grupos distintos (Group ID) con domicilio en cada país, y la fecha de la lista."""
    texto = pedir(OFSI)
    lineas = texto.splitlines()
    fecha = lineas[0].split(",", 1)[1].strip() if lineas and lineas[0].startswith("Last Updated") else None
    lector = csv.DictReader(io.StringIO("\n".join(lineas[1:])))
    por_iso = {}
    for fila in lector:
        iso = EN_INGLES.get((fila.get("Country") or "").strip())
        grupo = (fila.get("Group ID") or "").strip()
        if iso and grupo:
            por_iso.setdefault(iso, set()).add(grupo)
    if len(por_iso) < 5:
        raise RuntimeError("La lista del Reino Unido dejó menos de cinco Estados de la región: la "
                           "lectura falló.")
    return {k: len(v) for k, v in por_iso.items()}, fecha


def construir() -> Path:
    padron = geo.padron()
    anio = datetime.now(timezone.utc).year
    caidos = []
    try:
        us = ofac()
    except Exception as error:  # noqa: BLE001
        caidos.append(f"OFAC: {type(error).__name__}: {error}")
        us = {}
    try:
        uk, fecha_uk = ofsi()
    except Exception as error:  # noqa: BLE001
        caidos.append(f"OFSI: {type(error).__name__}: {error}")
        uk, fecha_uk = {}, None
    if not us and not uk:
        raise RuntimeError("No se pudo leer ninguna de las dos listas. NO se publica.")

    def ficha(v):
        return {"valor": v, "anio": anio, "anio_anterior": None, "valor_anterior": None,
                "serie": [{"anio": anio, "valor": v}]}

    registros = []
    for p in padron:
        f = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        # UN CERO ES UN DATO: las listas son del mundo entero y se leyeron completas.
        if us:
            f["indicadores"]["sanciones_ofac"] = ficha(us.get(p["iso"], 0))
        if uk:
            f["indicadores"]["sanciones_ofsi"] = ficha(uk.get(p["iso"], 0))
        registros.append(f)

    cautela = ("Cuenta personas y entidades distintas con al menos un domicilio declarado en el "
               "país. NO MIDE CONDUCTA DEL ESTADO: dice a quién decidió sancionar otro gobierno, "
               "con sus criterios y prioridades. Un número alto puede reflejar crimen organizado "
               "con domicilio en el país, un régimen sancionado o más atención de quien sanciona.")
    medidas = []
    if us:
        medidas.append({"clave": "sanciones_ofac",
                        "rotulo": "Sancionados por Estados Unidos con domicilio en el país",
                        "eje": "Gobernanza", "unidad": "personas y entidades", "mas_es_peor": True,
                        "sin_direccion": True,
                        "origen": "Oficina de Control de Activos Extranjeros (OFAC), Tesoro de EE. UU.",
                        "cautela": cautela})
    if uk:
        medidas.append({"clave": "sanciones_ofsi",
                        "rotulo": "Sancionados por el Reino Unido con domicilio en el país",
                        "eje": "Gobernanza", "unidad": "personas y entidades", "mas_es_peor": True,
                        "sin_direccion": True,
                        "origen": "Oficina de Implementación de Sanciones Financieras (OFSI), Reino Unido",
                        "cautela": cautela})
    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Listas primarias de sanciones: OFAC (EE. UU.) y OFSI (Reino Unido)",
        url_fuente="https://sanctionssearch.ofac.treas.gov/",
        calificacion=comun.calificar(
            "A", 2, True,
            "Registros oficiales de los gobiernos que sancionan: son la fuente primaria de su "
            "propia decisión. Dos gobiernos distintos, con criterios distintos."),
        registros=registros,
        vacios=[
            "UNA SANCIÓN ES LA DECISIÓN DE OTRO GOBIERNO, no un hecho sobre el país. Estados Unidos "
            "y el Reino Unido sancionan con sus propios criterios; ninguna lista es neutral.",
            "SE CUENTA EL DOMICILIO DECLARADO, no la nacionalidad: una empresa pantalla registrada "
            "en un país suma a ese país.",
            "UNA MISMA PERSONA PUEDE TENER DOMICILIOS EN VARIOS PAÍSES y suma en cada uno.",
            f"La lista del Reino Unido declara su última actualización: {fecha_uk or 'no informada'}.",
        ] + caidos,
        extra={"indicadores": medidas,
               "cobertura": {m["clave"]: len(registros) for m in medidas},
               "resumen": {"lista_uk_actualizada": fecha_uk, "consultado": comun.ahora()}},
        )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
