"""Ciberseguridad: qué se mide de la red, y qué no se puede concluir de eso.

POR QUÉ EXISTE
--------------
«Ciberseguridad» era otra de las seis materias que el registro nombraba y no
podía medir. Hasta hoy solo tenía «servidores de internet cifrados», que es
infraestructura, no incidente.

Este colector reúne tres cosas distintas —y las mantiene distintas—:

1. **Anomalías de red** (OONI). Mediciones hechas por voluntarios que prueban si
   un sitio responde. Distingue *anomalía* de *bloqueo confirmado*.
2. **Cortes de conectividad** (IODA). Caídas de tráfico de un país frente a su
   propio historial, con nivel de gravedad y hora.
3. **Equipos de respuesta a incidentes** (FIRST). Cuántos organismos de respuesta
   tiene cada Estado en el padrón internacional.

POR QUÉ NO ENTRA AL COMPUESTO, Y NO ES UN DESCUIDO
--------------------------------------------------
Ninguna de las tres ordena Estados, por tres razones distintas:

- **La muestra de OONI la hacen voluntarios.** Venezuela tiene 2,4 millones de
  mediciones en treinta días y Dominica puede tener cien. Un Estado con pocas
  sondas muestra pocas anomalías: eso NO significa que tenga menos censura,
  significa que hay menos gente midiendo. Ordenar por esto sería ordenar por
  cuántos voluntarios hay.
- **Un corte de IODA no distingue la causa.** Un cable cortado, una tormenta, un
  apagón y un apagón deliberado producen la misma curva. La curva es el hecho; la
  intención es un juicio, y el registro no emite juicios.
- **Contar equipos de respuesta premia al Estado grande.** Brasil tiene muchos
  porque es grande, no porque esté mejor protegido. Es el mismo error por el que
  Costa Rica, que no tiene ejército desde 1949, aparecía entre las peores en
  Defensa.

Por eso las tres se publican como **medición**, al lado del dato comparable y
nunca adentro, con la misma arquitectura que ya usa Defensa.
"""

from __future__ import annotations

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import comun
import geo

NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DIAS = 30   # la ventana de observación

# El padrón usa ISO de tres letras; estas tres fuentes, de dos.
DOS_LETRAS = {
    "ARG": "AR", "BOL": "BO", "BRA": "BR", "CHL": "CL", "COL": "CO", "CRI": "CR",
    "CUB": "CU", "DOM": "DO", "ECU": "EC", "SLV": "SV", "GTM": "GT", "HTI": "HT",
    "HND": "HN", "MEX": "MX", "NIC": "NI", "PAN": "PA", "PRY": "PY", "PER": "PE",
    "URY": "UY", "VEN": "VE", "BLZ": "BZ", "GUY": "GY", "SUR": "SR",
    "ATG": "AG", "BHS": "BS", "BRB": "BB", "DMA": "DM", "GRD": "GD", "JAM": "JM",
    "KNA": "KN", "LCA": "LC", "VCT": "VC", "TTO": "TT",
}


def _json(url: str, segundos: int = 60):
    peticion = urllib.request.Request(
        url, headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=segundos) as respuesta:
        return json.loads(respuesta.read(6_000_000).decode("utf-8", "replace"))


def _ooni(desde: str, hasta: str) -> dict:
    """Una sola consulta trae los 180 países agrupados. Se comprobó que el
    resultado agrupado coincide con el de la consulta país por país."""
    url = ("https://api.ooni.io/api/v1/aggregation"
           f"?since={desde}&until={hasta}&test_name=web_connectivity&axis_y=probe_cc")
    d = _json(url)
    return {x["probe_cc"]: x for x in (d.get("result") or []) if x.get("probe_cc")}


def _ioda(cc: str, desde: int, hasta: int) -> tuple:
    url = ("https://api.ioda.inetintel.cc.gatech.edu/v2/outages/alerts"
           f"?from={desde}&until={hasta}&entityType=country&entityCode={cc}")
    try:
        d = _json(url, 45)
    except Exception:  # noqa: BLE001 — la falla de un país no tumba la corrida
        return cc, None
    alertas = d.get("data")
    if isinstance(alertas, dict):
        alertas = alertas.get("alerts") or []
    alertas = alertas or []
    return cc, {
        "alertas": len(alertas),
        "criticas": sum(1 for a in alertas if a.get("level") == "critical"),
        "fuentes": sorted({a.get("datasource") for a in alertas if a.get("datasource")}),
    }


def _first(cc: str) -> tuple:
    url = f"https://api.first.org/data/v1/teams?limit=1&country={cc}"
    try:
        return cc, int(_json(url, 45).get("total") or 0)
    except Exception:  # noqa: BLE001
        return cc, None


def recolectar():
    fin = datetime.now(timezone.utc).date()
    ini = fin - timedelta(days=DIAS)
    ooni = _ooni(ini.isoformat(), fin.isoformat())

    ccs = [DOS_LETRAS[p["iso"]] for p in geo.padron() if p["iso"] in DOS_LETRAS]
    desde = int(datetime(ini.year, ini.month, ini.day, tzinfo=timezone.utc).timestamp())
    hasta = int(datetime(fin.year, fin.month, fin.day, tzinfo=timezone.utc).timestamp())

    with ThreadPoolExecutor(max_workers=6) as ejecutor:
        cortes = dict(ejecutor.map(lambda c: _ioda(c, desde, hasta), ccs))
        equipos = dict(ejecutor.map(_first, ccs))

    registros = []
    conMedicion = conCorte = conEquipo = 0
    for pais in geo.padron():
        cc = DOS_LETRAS.get(pais["iso"])
        o = ooni.get(cc) or {}
        med = o.get("measurement_count") or 0
        ano = o.get("anomaly_count") or 0
        con = o.get("confirmed_count") or 0
        c = cortes.get(cc)
        e = equipos.get(cc)

        if med:
            conMedicion += 1
        if c and c["alertas"]:
            conCorte += 1
        if e:
            conEquipo += 1

        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "mediciones": med,
            "anomalias": ano,
            "bloqueos_confirmados": con,
            # La TASA, no el recuento: el recuento solo dice cuanta gente mide.
            "anomalias_pct": round(ano / med * 100, 2) if med else None,
            "cortes": (c or {}).get("alertas"),
            "cortes_criticos": (c or {}).get("criticas"),
            "cortes_sin_dato": c is None,
            "equipos_respuesta": e,
            "equipos_sin_dato": e is None,
        })

    vacios = [
        "LA MUESTRA DE OONI LA HACEN VOLUNTARIOS Y NO ES REPRESENTATIVA. Venezuela "
        "tuvo 2.392.574 mediciones en esta ventana; un Estado del Caribe puede tener "
        "unas pocas. UN ESTADO CON POCAS SONDAS MUESTRA POCAS ANOMALIAS, y eso NO "
        "significa que tenga menos censura: significa que hay menos gente midiendo. "
        "Por eso se publica la TASA y no el recuento, y aun asi NO SE ORDENAN ESTADOS "
        "con esta cifra.",
        "ANOMALIA NO ES BLOQUEO. Una anomalia es una medicion que no salio como se "
        "esperaba, y puede deberse a una caida del sitio, a un problema de la red o al "
        "propio metodo. El bloqueo CONFIRMADO se cuenta aparte y es una cifra mucho mas "
        "chica: es la unica que sostiene la palabra «bloqueo».",
        "UN CORTE DE CONECTIVIDAD NO DECLARA SU CAUSA. Un cable cortado, una tormenta, "
        "un apagon electrico y un apagon deliberado producen la misma curva de trafico. "
        "La curva es el hecho; la intencion es un juicio, y este registro no emite "
        "juicios.",
        "CONTAR EQUIPOS DE RESPUESTA PREMIA AL ESTADO GRANDE. Brasil tiene muchos "
        "porque es grande, no porque este mejor protegido. Es el mismo error por el que "
        "Costa Rica, sin ejercito desde 1949, aparecia entre las peores en Defensa. Es "
        "un recuento de organismos, NO una medida de capacidad.",
        f"LA VENTANA ES DE {DIAS} DIAS y se mueve con cada corrida: sirve para ver el "
        "presente, NO para comparar contra el mes pasado. Una serie historica exigiria "
        "guardar cada ventana, y este colector no lo hace.",
        "NINGUNA DE LAS TRES ENTRA AL COMPUESTO. Se publican al lado del dato "
        "comparable y nunca adentro, con la misma arquitectura que Defensa.",
    ]

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=2,
        corroborado=False,
        nota=("Tres mediciones tecnicas independientes entre si: OONI mide desde sondas "
              "de voluntarios, IODA mide trafico agregado desde la academia y FIRST "
              "publica su propio padron de miembros. Fiabilidad B porque ninguna es el "
              "organismo responsable del Estado medido. Credibilidad 2 porque se "
              "verifico la cifra que cada una publica, NO el hecho que la produjo."),
    )

    return comun.escribir(
        colector="ciber",
        capa="publico",
        fuente="OONI, IODA y FIRST — medición técnica de red y capacidad de respuesta",
        url_fuente="https://api.ooni.io/api/v1/aggregation",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "ventana_dias": DIAS,
                "desde": ini.isoformat(),
                "hasta": fin.isoformat(),
                "estados_con_medicion": conMedicion,
                "estados_con_corte": conCorte,
                "estados_con_equipo_declarado": conEquipo,
                "estados_del_padron": len(registros),
                "mediciones_en_la_region": sum(r["mediciones"] for r in registros),
                "bloqueos_confirmados_en_la_region":
                    sum(r["bloqueos_confirmados"] for r in registros),
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("ciber", recolectar)
