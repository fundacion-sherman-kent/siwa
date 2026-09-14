# -*- coding: utf-8 -*-
"""Petróleo y gas según la Administración de Información Energética de EE. UU.

POR QUÉ EXISTE
--------------
Los hidrocarburos tenían UNA sola fuente: el Energy Institute, vía Our World in
Data. La EIA publica su propia estadística internacional, en descarga masiva,
sin credencial y en dominio público (eia.gov/about/copyrights_reuse.php, leída
el 13/9/2026). Es la segunda fuente que pide la regla de la casa, autorizada por
la dirección el 14/9/2026.

QUÉ PUBLICA
-----------
  · Producción de petróleo crudo, incluido el condensado, en miles de barriles
    por día.
  · Producción de gas natural seco, en miles de millones de metros cúbicos.

Las unidades NO son las del Energy Institute, que publica energía. Se comparan
tendencias y órdenes de magnitud, no cifras una contra otra.
"""
from __future__ import annotations

import io
import json
import re
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "eia"
CAPA = "publico"
URL = "https://api.eia.gov/bulk/INTL.zip"
HASTA = datetime.now(timezone.utc).year - 1
VENTANA = 1990

SERIES = {
    "produccion_petroleo_eia": re.compile(r"^INTL\.57-1-([A-Z]{3})-TBPD\.A$"),
    "produccion_gas_eia": re.compile(r"^INTL\.26-1-([A-Z]{3})-BCM\.A$"),
}


def construir() -> Path:
    padron = geo.padron()
    isos = {p["iso"] for p in padron}
    peticion = urllib.request.Request(URL, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=300) as respuesta:
        z = zipfile.ZipFile(io.BytesIO(respuesta.read()))
    datos = {c: {} for c in SERIES}
    unidades = {}
    with z.open(z.namelist()[0]) as archivo:
        for linea in archivo:
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            sid = d.get("series_id") or ""
            for clave, patron in SERIES.items():
                m = patron.match(sid)
                if not m or m.group(1) not in isos:
                    continue
                unidades[clave] = d.get("units")
                puntos = []
                for anio, valor in d.get("data") or []:
                    try:
                        a, v = int(anio), float(valor)
                    except (TypeError, ValueError):
                        continue   # la EIA marca «--» o «NA» donde no hay dato
                    if VENTANA <= a <= HASTA:
                        puntos.append((a, round(v, 2)))
                if puntos:
                    datos[clave][m.group(1)] = sorted(puntos)
    if len(datos["produccion_petroleo_eia"]) < 20:
        raise RuntimeError(
            f"La EIA dejó solo {len(datos['produccion_petroleo_eia'])} Estados con serie de "
            "petróleo: cambió la forma del archivo o falló la lectura. NO se publica.")

    registros, cobertura = [], {}
    for p in padron:
        f = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        for clave in SERIES:
            serie = datos[clave].get(p["iso"])
            if not serie:
                continue
            anio, valor = serie[-1]
            ant = serie[-2] if len(serie) > 1 else None
            f["indicadores"][clave] = {
                "valor": valor, "anio": anio,
                "anio_anterior": ant[0] if ant else None, "valor_anterior": ant[1] if ant else None,
                "serie": [{"anio": a, "valor": v} for a, v in serie],
            }
            cobertura[clave] = cobertura.get(clave, 0) + 1
        registros.append(f)

    medidas = [
        {"clave": "produccion_petroleo_eia", "rotulo": "Producción de petróleo · segunda fuente",
         "eje": "Defensa", "unidad": "miles de barriles por día", "mas_es_peor": False,
         "sin_direccion": True, "origen": "Administración de Información Energética de EE. UU. (EIA)",
         "cautela": "SEGUNDA MEDICIÓN de lo que el registro ya publica con el Energy Institute, en "
                    "otra unidad: la EIA cuenta barriles por día de crudo con condensado; el Energy "
                    "Institute, energía. Se comparan tendencias y órdenes de magnitud, no cifras. Un "
                    "cero es un Estado que no produce según la EIA."},
        {"clave": "produccion_gas_eia", "rotulo": "Producción de gas natural · segunda fuente",
         "eje": "Defensa", "unidad": "miles de millones de metros cúbicos", "mas_es_peor": False,
         "sin_direccion": True, "origen": "Administración de Información Energética de EE. UU. (EIA)",
         "cautela": "SEGUNDA MEDICIÓN de lo que el registro ya publica con el Energy Institute, en "
                    "otra unidad: gas natural seco en volumen. Se comparan tendencias, no cifras."},
    ]
    publicables = [m for m in medidas if cobertura.get(m["clave"])]
    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Administración de Información Energética de los Estados Unidos (EIA) — "
               "estadística energética internacional",
        url_fuente="https://www.eia.gov/international/data/world",
        calificacion=comun.calificar(
            "A", 2, True,
            "Organismo estadístico oficial con método publicado. Credibilidad 2: coincide en "
            "orden de magnitud con el Energy Institute, que es productor independiente, pero "
            "en otra unidad y con años distintos."),
        registros=registros,
        vacios=[
            "LA EIA Y EL ENERGY INSTITUTE NO USAN LA MISMA UNIDAD. Este conjunto cuenta barriles "
            "por día y metros cúbicos; el otro, energía. No se restan una de otra.",
            f"LA SERIE SE CORTA EN {HASTA}: el año en curso no se publica.",
            "LA EIA PUEDE TOMAR INSUMOS DE ORGANISMOS REGIONALES para América Latina; no se "
            "verificó si alguno coincide con los del Energy Institute.",
        ],
        extra={"indicadores": publicables,
               "cobertura": {m["clave"]: cobertura.get(m["clave"], 0) for m in publicables},
               "resumen": {"unidades_en_la_fuente": unidades, "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
