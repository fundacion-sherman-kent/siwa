# -*- coding: utf-8 -*-
"""Reservas internacionales e inflación mensual de los 33 Estados, según el FMI.

POR QUÉ EXISTE
--------------
La dirección pidió el 15/9/2026 que SIWA tenga, en todas las materias donde
exista, el dato más actual publicado. La auditoría de herramientas de ese día
encontró que la nueva interfaz de datos del Fondo Monetario Internacional (SDMX
3.0, sin credencial) entrega, mes a mes y para toda la región:

  · las reservas internacionales totales, en dólares (flujo «IL», indicador
    TRGMV_REVS: reservas totales con el oro a valor de mercado);
  · la inflación interanual del índice de precios al consumidor (flujo «CPI»,
    transformación YOY_PCH_PA_PT).

SIWA no tenía reservas. La inflación ya se publica con el índice que compila la
CEPAL (colector «inflacion», porcentaje calculado por la Fundación); esta es la
cifra que calcula el FMI con el índice que le informa cada país. Si difieren, la
diferencia suele ser de redondeo o de mes.

QUÉ NO ES
---------
Las reservas son un stock en dólares corrientes: sube y baja con el precio del
oro y con las monedas en que están invertidas, no solo con lo que hace el banco
central. Un país con reservas altas no es necesariamente un país sin problemas de
divisas: pueden estar comprometidas.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import comun
import geo

COLECTOR = "fmi_mensual"
CAPA = "publico"
BASE = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
ATRASO_MAXIMO_MESES = 12
OBSERVACIONES = 150   # doce años y medio de meses, para la serie anual


def pedir(url: str) -> dict:
    ultimo = None
    for intento in range(5):
        try:
            p = urllib.request.Request(url, headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
            with urllib.request.urlopen(p, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001 — se reintenta
            ultimo = e
            time.sleep(6 * (intento + 1))
    raise RuntimeError(f"El FMI no respondió: {type(ultimo).__name__} {getattr(ultimo, 'code', '')}")


def series(flujo: str, clave_resto: str, isos: list) -> dict:
    """{iso: [(año, mes, valor), ...]} leído del formato SDMX-JSON del FMI."""
    url = (f"{BASE}/{flujo}/+/{'+'.join(isos)}.{clave_resto}?lastNObservations={OBSERVACIONES}"
           "&dimensionAtObservation=TIME_PERIOD&attributes=none&measures=all")
    d = pedir(url)
    estructura = d["data"]["structures"][0]
    dim_series = estructura["dimensions"]["series"]
    pos_pais = next(i for i, x in enumerate(dim_series) if x["id"] == "COUNTRY")
    paises = [v["id"] for v in dim_series[pos_pais]["values"]]
    periodos = [v.get("value") or v.get("id") for v in estructura["dimensions"]["observation"][0]["values"]]
    salida: dict = {}
    for clave, s in d["data"]["dataSets"][0]["series"].items():
        iso = paises[int(clave.split(":")[pos_pais])]
        filas = []
        for k, v in (s.get("observations") or {}).items():
            per = periodos[int(k)]           # «2026-M07»
            try:
                anio, mes = int(per[:4]), int(per.split("-M")[1])
                valor = float(v[0])
            except (ValueError, IndexError, TypeError):
                continue
            filas.append((anio, mes, valor))
        salida[iso] = sorted(filas)
    return salida


def construir() -> Path:
    padron = geo.padron()
    isos = [p["iso"] for p in padron]
    hoy = datetime.now(timezone.utc)
    reservas = series("IL", "TRGMV_REVS.USD.M", isos)
    inflacion = series("CPI", "CPI._T.YOY_PCH_PA_PT.M", isos)

    registros, cobertura, viejos = [], {}, []

    def atraso(anio, mes):
        return (hoy.year - anio) * 12 + hoy.month - mes

    for p in padron:
        r = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        s = reservas.get(p["iso"]) or []
        if s:
            a, m, v = s[-1]
            if atraso(a, m) <= ATRASO_MAXIMO_MESES:
                hace_un_anio = next((x for x in s if x[0] == a - 1 and x[1] == m), None)
                # La serie anual: el dato de diciembre de cada año cerrado.
                serie = [{"anio": x[0], "valor": round(x[2])} for x in s if x[1] == 12 and x[0] < a]
                serie.append({"anio": a, "valor": round(v)})
                r["indicadores"]["reservas_internacionales"] = {
                    "valor": round(v), "anio": a,
                    "anio_anterior": a - 1 if hace_un_anio else None,
                    "valor_anterior": round(hace_un_anio[2]) if hace_un_anio else None,
                    "serie": serie, "periodo": f"{MESES[m - 1]} de {a}",
                    "nota": f"a fin de {MESES[m - 1]} de {a}"
                            + ("; un año antes, " + f"{round(hace_un_anio[2] / 1e6):,}".replace(",", ".")
                               + " millones de dólares" if hace_un_anio else ""),
                }
                cobertura["reservas_internacionales"] = cobertura.get("reservas_internacionales", 0) + 1
            else:
                viejos.append(f"{p['pais']} (reservas: {MESES[m - 1]} de {a})")
        s = inflacion.get(p["iso"]) or []
        if s:
            a, m, v = s[-1]
            if atraso(a, m) <= ATRASO_MAXIMO_MESES:
                hace_un_anio = next((x for x in s if x[0] == a - 1 and x[1] == m), None)
                serie = [{"anio": x[0], "valor": round(x[2], 1)} for x in s if x[1] == 12 and x[0] < a]
                serie.append({"anio": a, "valor": round(v, 1)})
                r["indicadores"]["inflacion_fmi"] = {
                    "valor": round(v, 1), "anio": a,
                    "anio_anterior": a - 1 if hace_un_anio else None,
                    "valor_anterior": round(hace_un_anio[2], 1) if hace_un_anio else None,
                    "serie": serie, "periodo": f"{MESES[m - 1]} de {a}",
                    "nota": f"{MESES[m - 1]} de {a} contra el mismo mes del año anterior",
                }
                cobertura["inflacion_fmi"] = cobertura.get("inflacion_fmi", 0) + 1
            else:
                viejos.append(f"{p['pais']} (inflación: {MESES[m - 1]} de {a})")
        registros.append(r)

    if cobertura.get("reservas_internacionales", 0) < 20:
        raise RuntimeError(f"Solo {cobertura.get('reservas_internacionales', 0)} Estados con reservas: "
                           "la lectura del FMI falló. No se publica.")

    medidas = [
        {"clave": "reservas_internacionales", "rotulo": "Reservas internacionales",
         "eje": "Desarrollo", "unidad": "dólares corrientes", "mas_es_peor": False, "sin_direccion": True,
         "origen": "Fondo Monetario Internacional — liquidez internacional (SDMX)",
         "cautela": "Reservas internacionales totales del banco central, con el oro a valor de mercado, en "
                    "dólares corrientes, a fin del último mes informado. Es un stock que sube y baja "
                    "también con el precio del oro y el tipo de cambio de las monedas en que está invertido. "
                    "No dice cuánto está comprometido. La serie es el dato de diciembre de cada año."},
        {"clave": "inflacion_fmi", "rotulo": "Inflación de doce meses, según el FMI",
         "eje": "Desarrollo", "unidad": "%", "mas_es_peor": True,
         "origen": "Fondo Monetario Internacional — índice de precios al consumidor (SDMX)",
         "cautela": "Variación del índice de precios al consumidor del último mes informado contra el mismo "
                    "mes del año anterior, calculada por el FMI con el índice que le informa cada país. Es otra "
                    "compilación del mismo índice nacional que usa la CEPAL: sirve para contrastar, no es una "
                    "medición independiente del costo de vida."},
    ]
    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Fondo Monetario Internacional — datos estadísticos (SDMX 3.0): liquidez internacional (IL) e "
               "índice de precios al consumidor (CPI)",
        url_fuente="https://data.imf.org/",
        calificacion=comun.calificar(
            "A", 2, False,
            "Estadística oficial que los bancos centrales e institutos informan al FMI. Credibilidad 2: los "
            "últimos meses se revisan y cada país informa con su propio atraso."),
        registros=registros,
        vacios=[
            "EL ÚLTIMO MES NO ES EL MISMO EN TODOS LOS PAÍSES: cada uno informa al FMI con su propio atraso. "
            "Cada ficha dice de qué mes es.",
            "LAS RESERVAS NO DICEN CUÁNTO ESTÁ DISPONIBLE: incluyen oro, depósitos y otros activos, y no descuentan "
            "compromisos de corto plazo.",
            f"NO SE PUBLICA UN DATO CON MÁS DE {ATRASO_MAXIMO_MESES} MESES DE ATRASO como si fuera el último: "
            + (", ".join(viejos) if viejos else "en esta corrida no hubo ninguno") + ".",
            "Cuba no informa inflación al FMI y Venezuela dejó de informar hace años: no tienen dato vigente.",
        ],
        extra={"indicadores": medidas, "cobertura": cobertura, "resumen": {"consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
