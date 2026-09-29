# -*- coding: utf-8 -*-
"""Pesca: presión de pesca sospechosa por país, de Global Fishing Watch.

DE DÓNDE SALE
-------------
De la API de Global Fishing Watch (eventos satelitales de buques, vía AIS). Se usa el
endpoint de estadísticas de eventos (POST /v3/events/stats), que devuelve conteos
agrupados por bandera del buque. Requiere una clave, guardada como secreto del robot
en la variable de entorno GFW_API_TOKEN (ver direccion/instructivos/clave-gfw-pesca-siwa.md).

QUÉ MIDE
--------
Dos señales de pesca no declarada o de riesgo, contadas por país de bandera del buque:
 - ENCUENTROS en altamar (dos buques que se juntan; proxy de transbordo de captura), y
 - AIS APAGADO (GAPs: el buque deja de emitir su posición; proxy de actividad oculta).
Es una MAGNITUD DE PAÍS (una capa de mapa, no un corredor). No prueba ilegalidad: son
indicios de comportamiento de riesgo, y así se declara. Cita obligatoria a GFW.

HONESTIDAD Y ESTADO
-------------------
La clave es un secreto del robot y NO se puede probar desde la Oficina; el primer
resultado real lo confirma la corrida del robot. Si falta la clave o la API no responde,
el colector se degrada y lo declara (no bloquea el robot).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request

import comun
import geo

BASE = "https://gateway.api.globalfishingwatch.org/v3/events/stats"
DATASETS = {
    "encuentros": "public-global-encounters-events:latest",
    "ais_off": "public-global-gaps-events:latest",
}
# ISO3 del padrón, para quedarnos con las banderas de la región.
ISO3 = None  # se llena del padrón en recolectar()


def _consultar(token: str, dataset: str, desde: str, hasta: str, flag: str) -> int:
    """Cuenta de eventos de un dataset para UNA bandera, en la ventana dada.

    El endpoint /v3/events/stats NO agrupa por bandera: devuelve el agregado de lo que
    pida el filtro. Para tener el dato por país se consulta bandera por bandera con el
    campo `flags`. El cuerpo va en camelCase (startDate/endDate); la forma hifenada
    (start-date) es sólo para el GET de /v3/events y acá devolvía 422. `timeseriesInterval`
    admite HOUR/DAY/MONTH/YEAR. La respuesta trae numEvents en la raíz.
    """
    cuerpo = json.dumps({
        "datasets": [dataset],
        "startDate": desde,
        "endDate": hasta,
        "timeseriesInterval": "YEAR",
        "flags": [flag],
    }).encode("utf-8")
    pet = urllib.request.Request(BASE, data=cuerpo, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": comun.AGENTE,
    })
    try:
        with urllib.request.urlopen(pet, timeout=120) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        return int(d.get("numEvents") or 0)
    except urllib.error.HTTPError as error:
        # El token es secreto y no se prueba en la Oficina: que el robot cuente EXACTAMENTE
        # qué rechaza —código y cuerpo— para arreglar el pedido a ciegas.
        import sys
        try:
            detalle = error.read().decode("utf-8", "replace")[:400]
        except Exception:  # noqa: BLE001
            detalle = "(sin cuerpo)"
        print(f"[pesca_gfw] GFW HTTP {error.code} en {dataset} ({flag}): {detalle}", file=sys.stderr)
        raise


def recolectar():
    token = os.environ.get("GFW_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Falta la clave GFW_API_TOKEN (secreto del robot). Sin la clave no se consulta "
            "Global Fishing Watch. Ver direccion/instructivos/clave-gfw-pesca-siwa.md.")

    padron = geo.padron()
    isos = {p["iso"] for p in padron}
    hoy = dt.date.today()
    desde = (hoy - dt.timedelta(days=730)).isoformat()  # dos años móviles
    hasta = hoy.isoformat()

    porpais = {p["iso"]: {"iso": p["iso"], "pais": p["pais"], "bloque": p["bloque"],
                          "encuentros": 0, "ais_off": 0} for p in padron}
    isos_ordenados = sorted(isos)
    faltantes = []
    for clave, dataset in DATASETS.items():
        # el endpoint no agrupa por bandera: se consulta país por país con el filtro flags.
        # si los primeros pedidos fallan (token vencido, API caída), se corta la señal y se
        # declara —no se dispara 33 veces contra una API que no responde.
        errores_seguidos = 0
        caido = False
        for iso in isos_ordenados:
            try:
                porpais[iso][clave] = _consultar(token, dataset, desde, hasta, iso)
                errores_seguidos = 0
            except Exception as error:  # noqa: BLE001
                errores_seguidos += 1
                if errores_seguidos >= 3:
                    faltantes.append(f"{clave}: {type(error).__name__} (cortada tras 3 fallos)")
                    caido = True
                    break
        if caido:
            continue

    if len(DATASETS) == len(faltantes):
        raise RuntimeError("La API de GFW no respondió ninguna de las señales: "
                           + "; ".join(faltantes) + ". NO se publica.")

    registros = sorted(porpais.values(),
                       key=lambda r: -(r["encuentros"] + r["ais_off"]))
    con_dato = sum(1 for r in registros if r["encuentros"] or r["ais_off"])

    vacios = [
        "Son INDICIOS de comportamiento de riesgo, no prueba de ilegalidad: un encuentro en "
        "altamar puede ser un transbordo legal, y un AIS apagado puede tener causas técnicas.",
        "Se cuentan por PAÍS DE BANDERA del buque, no por dónde ocurren: mide la flota de cada "
        "Estado, no la presión extranjera en sus aguas (eso se agrega después con REGION_EEZ).",
        "Ventana de dos años móviles hasta la fecha de corrida. Faltan los buques sin AIS o con "
        "AIS manipulado, que por definición no aparecen.",
    ]
    if faltantes:
        vacios.append("En esta corrida no respondió: " + "; ".join(faltantes) + ".")

    calificacion = comun.calificar(
        fiabilidad="B", credibilidad=2, corroborado=False,
        nota=("Global Fishing Watch, sobre AIS satelital y modelos de comportamiento. Fiabilidad B "
              "porque es una inferencia de actividad, no un registro oficial. Credibilidad 2 porque "
              "el evento (encuentro, apagado) se detecta con método publicado pero su carácter "
              "ilícito no se prueba."),
    )
    return comun.escribir(
        colector="pesca_gfw",
        capa="publico",
        fuente="Global Fishing Watch — estadísticas de eventos (encuentros y AIS apagado) por bandera",
        url_fuente="https://globalfishingwatch.org/our-apis/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados_con_evento": con_dato,
                "ventana": {"desde": desde, "hasta": hasta},
                "consultado": comun.ahora(),
            },
            "licencia": ("Global Fishing Watch, uso no comercial con ATRIBUCIÓN OBLIGATORIA a GFW. "
                         "El mapa lleva la cita al pie de la capa de pesca."),
        },
    )


if __name__ == "__main__":
    comun.correr("pesca_gfw", recolectar)
