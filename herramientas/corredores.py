# -*- coding: utf-8 -*-
"""Motor de corredores: arma los pares origen→destino de flujos ilícitos para el mapa.

POR QUÉ EXISTE
--------------
La dirección pidió (29/9/2026) un mapa regional de corredores de tráfico comparables
entre sí, país→país, con los destinos fuera de la región marcados. Los datos de flujo
YA los recolecta el robot; falta transformarlos en pares dibujables. Este motor lo hace.

QUÉ HACE, Y QUÉ NO
------------------
Lee archivos de flujo YA publicados (hoy `armas.json`, que trae comercio bilateral
declarado en aduana, Comtrade cap. 93, nivel A) y emite `datos/publico/corredores.json`
con los pares {origen, destino, valor, sentido, si el destino sale de la región} y las
coordenadas de cada extremo, para que el mapa los dibuje. CALCULA (proceso), NO DECIDE
(juicio): sólo reordena dato ya calificado. No consulta internet, no incorpora fuentes,
no toca dato publicado — todo lo que usa ya está en el repositorio. Es un archivo
DERIVADO (como armonizacion.json): va en comun.TESTIGOS, exento de procedencia propia.

HONESTIDAD
----------
Cada corredor de armas es COMERCIO LEGAL declarado en aduana, no tráfico ilícito: sirve
para ver el flujo y, cruzado con la brecha espejo, señalar dónde no cierra. Se dice en
el propio archivo. Los otros flujos (narco, trata, especies, minerales, financiero) se
suman acá a medida que su fuente dura entra al robot; hoy van declarados como pendientes.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
PUBLICO = RAIZ / "datos" / "publico"
SALIDA = PUBLICO / "corredores.json"

# Centroides (lat, lon) del padrón regional. Tabla fija de referencia, como el M49.
REGION = {
    "ARG": (-38.4, -63.6), "BOL": (-16.3, -64.9), "BRA": (-10.8, -52.9),
    "CHL": (-35.7, -71.5), "COL": (4.6, -74.3), "CRI": (9.7, -83.8),
    "CUB": (21.5, -79.5), "DOM": (18.7, -70.2), "ECU": (-1.8, -78.2),
    "SLV": (13.8, -88.9), "GTM": (15.7, -90.2), "HND": (15.2, -86.2),
    "MEX": (23.6, -102.5), "NIC": (12.9, -85.2), "PAN": (8.5, -80.8),
    "PRY": (-23.4, -58.4), "PER": (-9.2, -75.0), "URY": (-32.5, -55.8),
    "VEN": (6.4, -66.6), "HTI": (19.0, -72.3), "JAM": (18.1, -77.3),
    "TTO": (10.7, -61.2), "GUY": (4.9, -58.9), "SUR": (4.0, -56.0),
    "BLZ": (17.2, -88.5), "BHS": (24.9, -77.4), "BRB": (13.2, -59.5),
    "ATG": (17.1, -61.8), "DMA": (15.4, -61.4), "GRD": (12.1, -61.7),
    "KNA": (17.3, -62.7), "LCA": (13.9, -61.0), "VCT": (13.0, -61.2),
}

# Destinos fuera de la región que aparecen como contraparte de armas.
HUBS = {
    "USA": (39.8, -98.6), "Canada": (56.1, -106.3), "Czechia": (49.8, 15.5),
    "Germany": (51.2, 10.4), "France": (46.2, 2.2), "Italy": (41.9, 12.6),
    "Spain": (40.5, -3.7), "United Kingdom": (55.4, -3.4), "Belgium": (50.5, 4.5),
    "Austria": (47.5, 14.6), "Switzerland": (46.8, 8.2), "Israel": (31.0, 34.8),
    "Russian Federation": (61.5, 105.3), "China": (35.9, 104.2),
    "Rep. of Korea": (35.9, 127.8), "Türkiye": (39.0, 35.2), "Turkey": (39.0, 35.2),
    "Netherlands": (52.1, 5.3), "Portugal": (39.4, -8.2), "Sweden": (60.1, 18.6),
    "Poland": (51.9, 19.1), "Japan": (36.2, 138.3), "Croatia": (45.1, 15.2),
    "Finland": (61.9, 25.7), "Norway": (60.5, 8.5), "Bulgaria": (42.7, 25.5),
    "United Arab Emirates": (23.4, 53.8), "Cyprus": (35.1, 33.4),
    "Malaysia": (4.2, 101.9), "Dem. Rep. of the Congo": (-4.0, 21.8),
    "South Africa": (-30.6, 22.9), "India": (22.0, 79.0), "Singapore": (1.35, 103.8),
}

# Nombre Comtrade → ISO del padrón (para reconocer la contraparte regional).
NOMBRE_ISO = {
    "Argentina": "ARG", "Bolivia (Plurinational State of)": "BOL", "Brazil": "BRA",
    "Chile": "CHL", "Colombia": "COL", "Costa Rica": "CRI", "Cuba": "CUB",
    "Dominican Rep.": "DOM", "Ecuador": "ECU", "El Salvador": "SLV",
    "Guatemala": "GTM", "Honduras": "HND", "Mexico": "MEX", "Nicaragua": "NIC",
    "Panama": "PAN", "Paraguay": "PRY", "Peru": "PER", "Uruguay": "URY",
    "Venezuela (Bolivarian Rep. of)": "VEN", "Haiti": "HTI", "Jamaica": "JAM",
    "Trinidad and Tobago": "TTO", "Guyana": "GUY", "Suriname": "SUR",
    "Belize": "BLZ", "Bahamas": "BHS", "Barbados": "BRB",
    "Antigua and Barbuda": "ATG", "Dominica": "DMA", "Grenada": "GRD",
    "Saint Kitts and Nevis": "KNA", "Saint Lucia": "LCA",
    "Saint Vincent and the Grenadines": "VCT",
}

# Contrapartes que la fuente no atribuye a un Estado: no se dibujan como corredor.
NO_DECLARADO = {"Areas, nes", "Other Asia, nes", "Bunkers", "Free Zones",
                "Special Categories", "Other Africa, nes", "Other Europe, nes",
                "Neutral Zone", "Br. Antr. Terr.", "World"}

TOPE_POR_SENTIDO = 3  # los mayores corredores por Estado y sentido, para no saturar


def _cargar(ruta: Path):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — sin el archivo, se degrada y se declara
        return None


def _ubicar(nombre: str):
    """Devuelve (iso_o_nombre, lat, lon, extra_region) o None si no se ubica."""
    if nombre in NOMBRE_ISO:
        iso = NOMBRE_ISO[nombre]
        lat, lon = REGION[iso]
        return iso, lat, lon, False
    if nombre in HUBS:
        lat, lon = HUBS[nombre]
        return nombre, lat, lon, True
    return None


def _corredores_comercio(archivo: str, flujo: str, fuente: str, nivel: str = "A") -> dict:
    """Deriva corredores de un archivo de comercio bilateral con la forma de armas.json
    (registros[].mayores_proveedores / mayores_clientes). Sirve para armas y minerales."""
    d = _cargar(PUBLICO / archivo)
    if not isinstance(d, dict):
        return {"disponible": False, "porque": f"no se encontró {archivo}"}
    anio = (d.get("resumen") or {}).get("anio")
    corredores, no_ubicados = [], set()

    def añadir(origen_iso, destino_nombre, valor, sentido):
        oi = REGION.get(origen_iso)
        dest = _ubicar(destino_nombre)
        if not oi or not dest:
            if not dest and destino_nombre not in NO_DECLARADO:
                no_ubicados.add(destino_nombre)
            return
        d_id, dlat, dlon, extra = dest
        corredores.append({
            "flujo": flujo, "sentido": sentido,
            "origen": origen_iso, "origen_lat": oi[0], "origen_lon": oi[1],
            "destino": d_id, "destino_lat": dlat, "destino_lon": dlon,
            "extra_region": extra, "valor_usd": round(valor),
        })

    for reg in d.get("registros", []) or []:
        iso = reg.get("iso")
        if iso not in REGION or reg.get("estado") != "declarado":
            continue
        # importa: proveedor → este país
        for x in (reg.get("mayores_proveedores") or [])[:TOPE_POR_SENTIDO]:
            soc, val = x.get("socio"), x.get("valor_usd") or 0
            if soc and val:
                dest = _ubicar(soc)
                if dest:
                    d_id, dlat, dlon, extra = dest
                    corredores.append({
                        "flujo": flujo, "sentido": "importa",
                        "origen": d_id, "origen_lat": dlat, "origen_lon": dlon,
                        "destino": iso, "destino_lat": REGION[iso][0], "destino_lon": REGION[iso][1],
                        "extra_region": False, "origen_extra_region": extra,
                        "valor_usd": round(val),
                    })
                elif soc not in NO_DECLARADO:
                    no_ubicados.add(soc)
        # exporta: este país → cliente
        for x in (reg.get("mayores_clientes") or [])[:TOPE_POR_SENTIDO]:
            soc, val = x.get("socio"), x.get("valor_usd") or 0
            if soc and val:
                añadir(iso, soc, val, "exporta")

    return {
        "disponible": True, "anio": anio, "nivel": nivel,
        "fuente": fuente,
        "calificacion": (d.get("calificacion") or {}),
        "advertencia": ("Comercio LEGAL declarado en aduana, no tráfico ilícito. Sirve para ver el "
                        "flujo y, cruzado con la brecha espejo, señalar dónde no cierra. Valores de "
                        "aduana en dólares, no cantidades."),
        "corredores": sorted(corredores, key=lambda c: -c["valor_usd"]),
        "contrapartes_no_ubicadas": sorted(no_ubicados),
    }


# Flujos cuya geometría de corredor todavía no tiene fuente dura en el robot.
PENDIENTES = {
    "narco": "UNODC World Drug Report — dato de país/incautación, corredor sólo narrativo (C)",
    "trata": "UNODC Global TIP (nacionalidad × detección) — pendiente de colector",
    "especies": "CITES Trade Database — file-drop anual, pendiente de licencia UNEP-WCMC",
    "financiero": "GFI/FSI/ICIJ — capa de «exposición», pendiente de licencia",
    "migrantes": "IOM Missing Migrants (CC BY 4.0) — pendiente de colector",
    "pesca": "Global Fishing Watch / IUU Index — pendiente de colector",
}


def construir() -> dict:
    armas = _corredores_comercio(
        "armas.json", "armas",
        "Comtrade de Naciones Unidas — capítulo 93 (armas, municiones y partes)")
    minerales = _corredores_comercio(
        "minerales_comercio.json", "minerales",
        "Comtrade de Naciones Unidas — oro, estaño y coltán (HS 7108/7112/2616/8001/2609/2615/8103)")
    flujos = {"armas": armas, "minerales": minerales}
    total = sum(len(f.get("corredores", [])) for f in flujos.values() if f.get("disponible"))
    vacios = []
    for nom, fx in flujos.items():
        if not fx.get("disponible"):
            vacios.append(f"{nom}: " + fx.get("porque", "sin dato."))
        elif fx.get("contrapartes_no_ubicadas"):
            vacios.append(f"{nom}: contrapartes sin coordenada (no se dibujan): "
                          + ", ".join(fx["contrapartes_no_ubicadas"]))
    for k, v in PENDIENTES.items():
        flujos[k] = {"disponible": False, "porque": v}
        vacios.append(f"{k}: {v}.")
    return {
        "que_es": "Corredores de flujos para el mapa regional: pares origen→destino con coordenadas, "
                  "valor y si el destino sale de la región. DERIVADO de los archivos de flujo ya "
                  "publicados y calificados; reordena, no incorpora. Hoy armas y minerales tienen "
                  "fuente dura (Comtrade, nivel A); el resto queda declarado como pendiente.",
        "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "resumen": {"corredores": total,
                    "flujos_con_dato": [k for k, v in flujos.items() if v.get("disponible")],
                    "flujos_pendientes": list(PENDIENTES)},
        "flujos": flujos,
        "vacios_declarados": vacios or ["Sin vacíos en esta corrida."],
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    salida = construir()
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8", newline="")
    r = salida["resumen"]
    print(f"[corredores] {r['corredores']} corredores · "
          f"con dato: {r['flujos_con_dato']} · pendientes: {len(r['flujos_pendientes'])}")
    for nom in r["flujos_con_dato"]:
        for c in salida["flujos"][nom].get("corredores", [])[:3]:
            print(f"   [{nom}] {c['origen']} → {c['destino']} · {c['sentido']} · "
                  f"USD {c['valor_usd']:,}{' · fuera de región' if c['extra_region'] else ''}")


if __name__ == "__main__":
    main()
