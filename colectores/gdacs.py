# -*- coding: utf-8 -*-
"""Alertas de desastres en tiempo real (GDACS): capa propia, no es desastres_onu.

QUE ES
------
GDACS (Global Disaster Alert and Coordination System, de la Comision Europea -JRC-
y la ONU) emite alertas AUTOMATICAS de amenaza -ciclon, sismo, inundacion, volcan,
sequia, incendio- con nivel naranja o rojo, geolocalizadas y por pais, y se
actualiza en el momento. Gratis, sin clave. Este colector cuenta, por cada Estado
del padron, cuantas alertas naranja/roja lo afectaron en los ultimos 12 meses, y
adjunta las alertas VIGENTES para la lectura en tiempo real.

POR QUE ES ASUNTO PROPIO Y NO SEGUNDA FUENTE DE `desastres_onu`
---------------------------------------------------------------
GDACS cuenta ALERTAS DE AMENAZA automaticas; `desastres_onu` (ReliefWeb/OCHA)
cuenta DESASTRES DECLARADOS/REPORTADOS por la ONU. Miden cosas parecidas pero no
iguales, asi que NO se cuenta como corroboracion de aquel -eso seria inventar una
segunda fuente donde no la hay-. Entra como asunto propio: "alertas de desastres
en tiempo real". La decision de comparabilidad es humana (direccion, 7/10/2026).

QUE NO HACE
-----------
No toca el mapa: emite su JSON a datos/publico y espera visto bueno para mostrarse.
Cuenta solo naranja y roja (lo significativo); el verde es ruido de fondo. Una
alerta no es un muerto ni un damnificado: es una senal de que algo paso, con su
nivel y su fecha, y asi se declara.
"""
from __future__ import annotations
import datetime as dt
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun
import geo

TIPOS = "EQ;TC;FL;VO;DR;WF"  # sismo, ciclon, inundacion, volcan, sequia, incendio
API = ("https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
       "?fromDate={desde}&toDate={hasta}&alertlevel=Orange;Red&country=&eventlist=" + TIPOS)


def contar(features: list, isos: set) -> tuple[dict, list]:
    """Devuelve ({iso: cantidad de alertas que lo afectan}, [alertas vigentes]).
    Un evento puede tocar varios paises: se cuenta en cada uno de los del padron."""
    por_pais: dict[str, int] = {}
    vigentes = []
    for f in features:
        p = f.get("properties") or {}
        afectados = [c.get("iso3") for c in (p.get("affectedcountries") or [])]
        # si no declara afectados, cae al pais principal
        if not afectados and p.get("iso3"):
            afectados = [p.get("iso3")]
        tocados = sorted({i for i in afectados if i in isos})
        for i in tocados:
            por_pais[i] = por_pais.get(i, 0) + 1
        if tocados and str(p.get("iscurrent")).lower() == "true":
            vigentes.append({
                "pais_iso3": tocados, "tipo": p.get("eventtype"), "nombre": p.get("eventname"),
                "alerta": p.get("alertlevel"), "desde": p.get("fromdate"), "hasta": p.get("todate"),
                "severidad": (p.get("severitydata") or {}).get("severitytext"),
                "enlace": ((p.get("url") or {}).get("report")),
            })
    return por_pais, vigentes


def main():
    hoy = dt.datetime.now(dt.timezone.utc).date()
    desde = hoy - dt.timedelta(days=365)
    url = API.format(desde=desde.isoformat(), hasta=hoy.isoformat())
    doc = comun.pedir(url, espera=60)
    features = doc.get("features") or []

    padron = geo.padron()
    isos = {p["iso"] for p in padron}
    por_pais, vigentes = contar(features, isos)

    registros = []
    for p in padron:
        n = por_pais.get(p["iso"], 0)
        registros.append({
            "iso": p["iso"], "pais": p.get("pais"),
            "indicadores": {
                "desastres_gdacs": {
                    "valor": n, "anio": hoy.year,
                    "ventana": f"{desde.isoformat()} a {hoy.isoformat()}",
                    "origen": "GDACS (Comision Europea JRC y ONU)",
                },
            },
        })

    calificacion = comun.calificar(
        fiabilidad="B", credibilidad=2, corroborado=False,
        nota=("GDACS: sistema de alerta de desastres de la Comision Europea (JRC) y la ONU. "
              "Fiabilidad B: operador institucional con historial. Credibilidad 2: son alertas "
              "AUTOMATICAS por modelo de amenaza, no un recuento verificado de danos. Cuenta "
              "alertas naranja y roja de los ultimos 12 meses por pais."),
    )
    vacios = [
        "Cuenta ALERTAS de amenaza, no desastres declarados por la ONU ni damnificados: es "
        "una senal de que algo significativo paso, con su nivel y fecha.",
        "Solo naranja y roja (lo significativo); las verdes se dejan afuera por ruido.",
        "Ventana movil de 12 meses: el numero sube y baja con la actividad reciente, no es un "
        "acumulado historico.",
        "Una alerta que toca varios paises se cuenta en cada uno: no es un total regional.",
    ]
    indicadores = [{
        "clave": "desastres_gdacs",
        "nombre": "Alertas de desastres (GDACS, 12 meses)",
        "unidad": "alertas naranja/roja",
        "origen": "GDACS (Comision Europea JRC y ONU)",
        "rotulo": "Alertas automaticas de amenaza, en tiempo real; no es desastres_onu",
    }]
    comun.escribir(
        colector="gdacs",
        capa="publico",
        fuente="GDACS -- Global Disaster Alert and Coordination System (Comision Europea JRC y Naciones Unidas)",
        url_fuente="https://www.gdacs.org/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": indicadores,
            "alertas_vigentes": vigentes,
            "ventana": {"desde": desde.isoformat(), "hasta": hoy.isoformat()},
            "licencia": "GDACS: datos de libre acceso de la Comision Europea y la ONU. Se cita la fuente.",
        },
    )
    print(f"[gdacs] {sum(por_pais.values())} alertas naranja/roja sobre {len(por_pais)} paises de ALC "
          f"en 12 meses; {len(vigentes)} vigentes ahora")


if __name__ == "__main__":
    main()
