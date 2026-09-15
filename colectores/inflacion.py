# -*- coding: utf-8 -*-
"""Inflación mensual de los 33 Estados, con el índice de precios al consumidor que compila la CEPAL.

POR QUÉ EXISTE
--------------
La auditoría de actualidad del 15/9/2026 encontró que SIWA no tenía ninguna
medida de precios, que es lo que más rápido cambia en la vida de la gente y lo
que los institutos de estadística publican cada mes. La dirección autorizó ese
día sumar inflación, empleo y reservas de alta frecuencia.

La CEPAL publica en su interfaz abierta (sin credencial) el índice de precios al
consumidor MENSUAL de los 33 Estados, tal como lo informa cada instituto
nacional: el indicador 365 de CEPALSTAT. Con ese índice se calculan dos cifras.

QUÉ PUBLICA
-----------
  · Inflación interanual: cuánto subieron los precios en los últimos doce meses
    (último mes publicado contra el mismo mes del año anterior).
  · Inflación del último mes: último mes contra el mes anterior.
  · La serie: la inflación de diciembre a diciembre de cada año cerrado.

LAS CUENTAS LAS HACE LA FUNDACIÓN, y así se declara: la CEPAL publica el índice,
no el porcentaje. Si entre los dos meses que se comparan la fuente cambió de
informante (otra base del índice), la cifra NO se calcula: dividir índices de
bases distintas da un número sin sentido.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import comun
import geo

COLECTOR = "inflacion"
CAPA = "publico"
BASE = "https://api-cepalstat.cepal.org/cepalstat/api/v1"
INDICADOR = 365
MESES = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7,
         "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
NOMBRE_MES = {v: k.lower() for k, v in MESES.items()}
ANIOS_SERIE = 10
ATRASO_MAXIMO_MESES = 9   # un índice que no se actualiza hace más de esto no es «el último mes»


def pedir(ruta: str) -> dict:
    ultimo = None
    for intento in range(5):
        try:
            p = urllib.request.Request(f"{BASE}/{ruta}",
                                       headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
            with urllib.request.urlopen(p, timeout=240) as r:
                d = json.loads(r.read())
                return d.get("body", d)
        except Exception as e:  # noqa: BLE001 — la CEPAL responde 500 de a ratos: se reintenta
            ultimo = e
            time.sleep(8 * (intento + 1))
    raise RuntimeError(f"CEPALSTAT no respondió: {type(ultimo).__name__} {getattr(ultimo, 'code', '')}")


def pct(nuevo: float, viejo: float) -> float | None:
    if not viejo or viejo <= 0 or nuevo <= 0:
        return None
    return round((nuevo / viejo - 1) * 100, 1)


def construir() -> Path:
    dims = pedir(f"indicator/{INDICADOR}/dimensions?lang=es&format=json")["dimensions"]
    nombre = {m["id"]: m["name"] for d in dims for m in d.get("members", [])}
    id_anio = next(d["id"] for d in dims if d["name"].lower().startswith("años"))
    id_mes = next(d["id"] for d in dims if d["name"].lower().startswith("mes"))
    datos = pedir(f"indicator/{INDICADOR}/data?lang=es&format=json")["data"]

    padron = geo.padron()
    isos = {p["iso"] for p in padron}
    por_pais: dict = {}
    for o in datos:
        iso = o.get("iso3")
        if iso not in isos:
            continue
        try:
            anio = int(nombre[o[f"dim_{id_anio}"]])
            mes = MESES[nombre[o[f"dim_{id_mes}"]]]
            valor = float(o["value"])
        except (KeyError, TypeError, ValueError):
            continue
        por_pais.setdefault(iso, {})[(anio, mes)] = (valor, o.get("source_id"))

    hoy = datetime.now(timezone.utc)
    registros, cobertura, viejos, cortes = [], {}, [], []

    def misma_base(a, b):
        return a[1] == b[1]

    for p in padron:
        r = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        serie_mensual = por_pais.get(p["iso"], {})
        if serie_mensual:
            ultimo = max(serie_mensual)
            atraso = (hoy.year - ultimo[0]) * 12 + hoy.month - ultimo[1]
            hace_un_anio = (ultimo[0] - 1, ultimo[1])
            anterior = (ultimo[0], ultimo[1] - 1) if ultimo[1] > 1 else (ultimo[0] - 1, 12)
            periodo = f"{NOMBRE_MES[ultimo[1]]} de {ultimo[0]}"
            if atraso > ATRASO_MAXIMO_MESES:
                viejos.append(f"{p['pais']} (último índice: {periodo})")
            # La serie: diciembre contra diciembre de cada año cerrado.
            serie = []
            for anio in range(ultimo[0] - ANIOS_SERIE, ultimo[0]):
                a, b = serie_mensual.get((anio, 12)), serie_mensual.get((anio - 1, 12))
                if a and b and misma_base(a, b):
                    v = pct(a[0], b[0])
                    if v is not None:
                        serie.append({"anio": anio, "valor": v})
            u, h = serie_mensual[ultimo], serie_mensual.get(hace_un_anio)
            if h and misma_base(u, h) and atraso <= ATRASO_MAXIMO_MESES:
                interanual = pct(u[0], h[0])
                previo = serie_mensual.get((hace_un_anio[0], hace_un_anio[1]))
                hace_dos = serie_mensual.get((hace_un_anio[0] - 1, hace_un_anio[1]))
                interanual_previo = (pct(previo[0], hace_dos[0])
                                     if previo and hace_dos and misma_base(previo, hace_dos) else None)
                if interanual is not None:
                    r["indicadores"]["inflacion_interanual"] = {
                        "valor": interanual, "anio": ultimo[0],
                        "anio_anterior": ultimo[0] - 1 if interanual_previo is not None else None,
                        "valor_anterior": interanual_previo,
                        "serie": serie + [{"anio": ultimo[0], "valor": interanual}],
                        "periodo": periodo,
                        "nota": f"{periodo} contra {NOMBRE_MES[ultimo[1]]} de {ultimo[0] - 1}"
                                + (f"; un año antes era {str(interanual_previo).replace('.', ',')} %"
                                   if interanual_previo is not None else ""),
                    }
                    cobertura["inflacion_interanual"] = cobertura.get("inflacion_interanual", 0) + 1
            elif h and not misma_base(u, h):
                cortes.append(p["pais"])
            m = serie_mensual.get(anterior)
            if m and misma_base(u, m) and atraso <= ATRASO_MAXIMO_MESES:
                mensual = pct(u[0], m[0])
                if mensual is not None:
                    r["indicadores"]["inflacion_mensual"] = {
                        "valor": mensual, "anio": ultimo[0], "anio_anterior": None, "valor_anterior": None,
                        "serie": [{"anio": ultimo[0], "valor": mensual}], "periodo": periodo,
                        "nota": f"{periodo} contra {NOMBRE_MES[anterior[1]]} de {anterior[0]}",
                    }
                    cobertura["inflacion_mensual"] = cobertura.get("inflacion_mensual", 0) + 1
        registros.append(r)

    if cobertura.get("inflacion_interanual", 0) < 20:
        raise RuntimeError(f"Solo {cobertura.get('inflacion_interanual', 0)} Estados con inflación: "
                           "la lectura de CEPALSTAT falló. No se publica.")

    base = {"eje": "Desarrollo", "unidad": "%", "mas_es_peor": True,
            "origen": "CEPALSTAT (índice de precios al consumidor de cada instituto nacional); "
                      "porcentaje calculado por la Fundación"}
    medidas = [
        dict(base, clave="inflacion_interanual", rotulo="Inflación de los últimos doce meses",
             cautela="Cuánto subieron los precios al consumidor entre el último mes publicado y el mismo mes "
                     "del año anterior. La CEPAL publica el índice de cada instituto nacional; el porcentaje lo "
                     "calcula la Fundación. Cada país tiene su canasta: sirve para ver cuánto sube cada uno, no "
                     "para comparar el costo de vida. El último mes publicado no es el mismo en todos los países: "
                     "cada ficha dice cuál es. La serie es de diciembre a diciembre."),
        dict(base, clave="inflacion_mensual", rotulo="Inflación del último mes",
             cautela="Cuánto subieron los precios al consumidor en el último mes publicado respecto del anterior. "
                     "Un mes solo es ruidoso: sube y baja por estacionalidad (alimentos, tarifas, turismo). "
                     "Porcentaje calculado por la Fundación sobre el índice que publica la CEPAL."),
    ]
    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="CEPALSTAT — Índice de precios al consumidor mensual (indicador 365), Comisión Económica para "
               "América Latina y el Caribe",
        url_fuente="https://statistics.cepal.org/portal/cepalstat/dashboard.html?indicator_id=365&lang=es",
        calificacion=comun.calificar(
            "A", 2, False,
            "Índices oficiales de cada instituto nacional, compilados por la CEPAL. Credibilidad 2: el "
            "porcentaje es un cálculo de la Fundación y los institutos cambian de base de tanto en tanto."),
        registros=registros,
        vacios=[
            "EL PORCENTAJE LO CALCULA LA FUNDACIÓN sobre el índice que publica la CEPAL. No es la cifra "
            "oficial de inflación que difunde cada instituto, aunque debería coincidir salvo redondeo o "
            "revisión.",
            "EL ÚLTIMO MES NO ES EL MISMO EN TODOS LOS PAÍSES: la CEPAL carga cada índice cuando lo recibe. "
            "Cada ficha dice de qué mes es.",
            "NO SE COMPARA EL COSTO DE VIDA ENTRE PAÍSES: cada índice tiene su propia canasta y su propia base.",
            f"CUANDO LA FUENTE CAMBIA DE BASE DEL ÍNDICE entre los dos meses comparados, no se calcula: "
            f"{', '.join(cortes) if cortes else 'en esta corrida no pasó en ningún Estado'}.",
        ] + ([f"Índices sin actualizar hace más de {ATRASO_MAXIMO_MESES} meses, no publicados: "
              f"{', '.join(viejos)}."] if viejos else []),
        extra={"indicadores": medidas, "cobertura": cobertura,
               "resumen": {"consultado": comun.ahora(), "indicador_cepalstat": INDICADOR}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
