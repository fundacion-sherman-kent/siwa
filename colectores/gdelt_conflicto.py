# -*- coding: utf-8 -*-
"""Pulso mediatico de conflicto por pais (GDELT): capa en tiempo real.

ARCHIVADO (14/10/2026, decision de la direccion). NO corre ni se publica: la version
por pais hacia 33 llamadas a GDELT y el limite de ritmo dejaba solo ~8 paises con dato
(y todos en 'baja', artefacto de series ralas). La direccion decidio NO hacer esta capa
hasta contar con mas fuentes o datos precisos. El codigo queda para revivirlo cuando se
rediseñe (una sola consulta amplia y conteo por pais, en vez de 33 llamadas).

QUE ES
------
Por cada Estado del padron, mide la INTENSIDAD de la cobertura de prensa sobre
protesta, disturbios, enfrentamientos, represion y violencia politica en los
ultimos 14 dias, segun GDELT (prensa mundial, gratis, sin clave, se actualiza c/15
min). Es un pulso en tiempo real de tension/inestabilidad: cuando algo pasa, sube.

QUE ES, Y QUE NO ES (se declara sin vueltas)
--------------------------------------------
Es un pulso MEDIATICO, NO un recuento de hechos verificados. Mide cuanto se habla de
conflicto en un pais, no cuantos hechos hubo: el recuento verificado de eventos de
violencia politica es ACLED (que SIWA ya tiene). Sirve como senal temprana y en vivo,
no como dato duro. Se usa la intensidad NORMALIZADA de GDELT (share de la cobertura),
asi es comparable entre paises grandes y chicos. Paises con poca prensa monitoreada
dan senal ruidosa: se declara.

NO TOCA EL MAPA: emite su JSON a datos/publico y espera visto bueno para mostrarse.
"""
from __future__ import annotations
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun
import geo

DIAS = 14
API = "https://api.gdeltproject.org/api/v2/doc/doc"
# Terminos en INGLES: GDELT indexa traducido, y en ingles contra sourcelang trae la
# prensa en castellano/portugues igual (lo aprendido con el scanner de flujos).
TERMINOS = '(protest OR unrest OR clashes OR repression OR riot OR crackdown OR "political violence")'


def consultar(pais: str) -> list[float]:
    """Serie de intensidad de cobertura de conflicto del pais, ultimos DIAS dias.
    Devuelve la lista de valores (share normalizado de GDELT). [] si no responde."""
    q = f'{TERMINOS} "{pais}" (sourcelang:spanish OR sourcelang:portuguese)'
    url = API + "?" + urllib.parse.urlencode(
        {"query": q, "mode": "timelinevol", "format": "json", "timespan": f"{DIAS}d"})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SIWA/pulso-conflicto)"})
    for intento in range(3):
        time.sleep(6)  # GDELT: un pedido cada 5 s
        try:
            crudo = urllib.request.urlopen(req, timeout=40).read()
            d = json.loads(crudo.decode("utf-8", "replace"))
            break
        except Exception:  # noqa: BLE001 — 429 (ritmo) o HTML de error; se reintenta
            if intento == 2:
                return []
            time.sleep(10)
    else:
        return []
    tl = d.get("timeline") or []
    if not tl:
        return []
    datos = tl[0].get("data") or []
    return [float(x.get("value", 0)) for x in datos if x.get("value") is not None]


def resumen(valores: list[float]) -> dict | None:
    """Pulso: intensidad media de la ventana (x100 para leerse), el ultimo valor y la
    tendencia (ultimo tercio vs. los dos primeros)."""
    if not valores:
        return None
    media = sum(valores) / len(valores)
    ultimo = valores[-1]
    corte = max(1, len(valores) // 3)
    base = valores[:-corte] or valores
    prom_base = sum(base) / len(base)
    if ultimo > prom_base * 1.3:
        tendencia = "sube"
    elif ultimo < prom_base * 0.7:
        tendencia = "baja"
    else:
        tendencia = "estable"
    return {"intensidad": round(media * 100, 3), "ultimo": round(ultimo * 100, 3), "tendencia": tendencia}


def main():
    hoy = dt.datetime.now(dt.timezone.utc).date()
    padron = geo.padron()
    registros, con_dato = [], 0
    for p in padron:
        r = resumen(consultar(p["pais"]))
        if r is None:
            registros.append({"iso": p["iso"], "pais": p["pais"],
                              "indicadores": {"conflicto_gdelt": {"valor": None, "anio": hoy.year,
                                              "estado": "sin_dato", "origen": "GDELT"}}})
            continue
        con_dato += 1
        registros.append({
            "iso": p["iso"], "pais": p["pais"],
            "indicadores": {
                "conflicto_gdelt": {
                    "valor": r["intensidad"], "anio": hoy.year,
                    "ultimo": r["ultimo"], "tendencia": r["tendencia"],
                    "ventana_dias": DIAS, "origen": "GDELT",
                },
            },
        })

    calificacion = comun.calificar(
        fiabilidad="C", credibilidad=3, corroborado=False,
        nota=("GDELT: intensidad NORMALIZADA de la cobertura de prensa sobre conflicto (protesta, "
              "disturbios, represión, violencia política) del país en los últimos 14 días. Fiabilidad "
              "C y credibilidad 3 a propósito: es una señal MEDIÁTICA en tiempo real, no un recuento "
              "de hechos —eso es ACLED—. Útil como alerta temprana, no como dato duro."),
    )
    vacios = [
        "Pulso MEDIÁTICO, no recuento de hechos: mide cuánto se HABLA de conflicto, no cuántos hubo. "
        "El dato de eventos de violencia política es ACLED, que ya se publica en este registro.",
        "Ventana móvil de 14 días: sube y baja con la actualidad, no es un acumulado.",
        "Intensidad normalizada (proporción de la cobertura) para comparar países grandes y chicos; los "
        "países con poca prensa monitoreada dan señal ruidosa.",
        "La búsqueda usa el nombre del país + términos de conflicto en prensa en castellano y portugués.",
    ]
    indicadores = [{
        "clave": "conflicto_gdelt",
        "nombre": "Pulso mediático de conflicto (GDELT, 14 días)",
        "unidad": "intensidad de cobertura (x100)",
        "origen": "GDELT",
        "rotulo": "Señal mediática en tiempo real; NO es recuento de hechos (eso es ACLED)",
    }]
    comun.escribir(
        colector="gdelt_conflicto",
        capa="publico",
        fuente="GDELT — The GDELT Project, intensidad de cobertura de prensa sobre conflicto",
        url_fuente="https://www.gdeltproject.org/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": indicadores,
            "ventana": {"dias": DIAS, "hasta": hoy.isoformat()},
            "licencia": "GDELT: datos de libre acceso. Se cita la fuente.",
        },
    )
    print(f"[gdelt_conflicto] pulso de conflicto en {con_dato}/{len(padron)} paises (ventana {DIAS}d)")


if __name__ == "__main__":
    main()
