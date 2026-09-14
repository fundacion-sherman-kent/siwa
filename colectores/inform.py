# -*- coding: utf-8 -*-
"""Riesgo de crisis humanitaria: índice INFORM (Centro Común de Investigación de la UE y OCHA).

POR QUÉ EXISTE
--------------
«Riesgo y ambiente» registraba lo que ocurre —sismos, desastres, fuego— pero no
cuán expuesto está cada Estado a que una amenaza se convierta en crisis. INFORM
lo mide para los 33, con método publicado y licencia CC BY 4.0. Autorizado por
la dirección el 14/9/2026.

QUÉ PUBLICA
-----------
El índice general, de 0 a 10, y sus tres dimensiones: exposición a amenazas,
vulnerabilidad y falta de capacidad para enfrentarlas. ES UN ÍNDICE DE TERCEROS,
armado con insumos de otros organismos: entra como materia propia, no como
segunda fuente de ninguno de esos insumos.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "inform"
CAPA = "publico"
BASE = "https://drmkc.jrc.ec.europa.eu/inform-index/API/InformAPI"
INDICADORES = {"INFORM": "riesgo_inform", "HA": "riesgo_inform_amenaza",
               "VU": "riesgo_inform_vulnerabilidad", "CC": "riesgo_inform_capacidad"}


def pedir(ruta: str):
    # El cortafuegos del organismo devuelve una página de verificación a quien se
    # presenta como navegador; al programa identificado le contesta los datos.
    peticion = urllib.request.Request(f"{BASE}/{ruta}", headers={
        "User-Agent": comun.AGENTE, "Accept": "application/json"})
    ultimo = None
    for intento in range(4):
        if intento:
            time.sleep(5 * intento)
        try:
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                return json.loads(respuesta.read())
        except Exception as error:  # noqa: BLE001 — el servidor corta conexiones sueltas: se reintenta
            ultimo = error
    raise RuntimeError(f"INFORM no respondió «{ruta}» en cuatro intentos: {ultimo}")


def edicion(anio: int):
    """El flujo principal de una edición: el que se llama «INFORM Risk AAAA», sin años atrás."""
    try:
        flujos = pedir(f"workflows/GetByWorkflowGroup/INFORM{anio}")
    except Exception:  # noqa: BLE001
        return None
    for w in flujos or []:
        if (w.get("Name") or "").strip() == f"INFORM Risk {anio}":
            return w["WorkflowId"]
    return None


def construir() -> Path:
    from datetime import datetime, timezone
    padron = geo.padron()
    isos = {p["iso"] for p in padron}
    ahora = datetime.now(timezone.utc).year
    ediciones = {}
    for anio in range(ahora - 4, ahora + 2):
        w = edicion(anio)
        if w:
            ediciones[anio] = w
    if not ediciones:
        raise RuntimeError("INFORM no lista ninguna edición reciente: la interfaz cambió o está caída.")
    valores = {}   # clave -> iso -> {anio: valor}
    for anio, w in sorted(ediciones.items()):
        filas = pedir(f"Countries/Scores/?WorkflowId={w}&IndicatorId={','.join(INDICADORES)}")
        for r in filas or []:
            clave = INDICADORES.get(r.get("IndicatorId"))
            if clave and r.get("Iso3") in isos and r.get("IndicatorScore") is not None:
                valores.setdefault(clave, {}).setdefault(r["Iso3"], {})[anio] = float(r["IndicatorScore"])
    if len(valores.get("riesgo_inform", {})) < 25:
        raise RuntimeError("INFORM dejó menos de 25 Estados con índice: la lectura falló. NO se publica.")

    registros, cobertura = [], {}
    for p in padron:
        f = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        for clave in INDICADORES.values():
            serie = sorted((valores.get(clave) or {}).get(p["iso"], {}).items())
            if not serie:
                continue
            anio, valor = serie[-1]
            ant = serie[-2] if len(serie) > 1 else None
            f["indicadores"][clave] = {"valor": valor, "anio": anio,
                                       "anio_anterior": ant[0] if ant else None,
                                       "valor_anterior": ant[1] if ant else None,
                                       "serie": [{"anio": a, "valor": v} for a, v in serie]}
            cobertura[clave] = cobertura.get(clave, 0) + 1
        registros.append(f)

    base = {"eje": "Desarrollo", "unidad": "índice de 0 a 10", "mas_es_peor": True,
            "origen": "INFORM — Centro Común de Investigación de la Comisión Europea y OCHA"}
    medidas = [
        dict(base, clave="riesgo_inform", rotulo="Riesgo de crisis humanitaria (INFORM)",
             cautela="ÍNDICE DE TERCEROS, de 0 a 10: combina exposición a amenazas naturales y "
                     "humanas, vulnerabilidad de la población y falta de capacidad para enfrentarlas. "
                     "No es un pronóstico de crisis: dice cuán expuesto está un Estado a que una "
                     "amenaza se convierta en una. Cada edición lleva el año en que se publica."),
        dict(base, clave="riesgo_inform_amenaza", rotulo="Exposición a amenazas (INFORM)",
             cautela="Dimensión del índice INFORM: amenazas naturales —sismos, inundaciones, "
                     "ciclones, sequía— y humanas —conflicto—."),
        dict(base, clave="riesgo_inform_vulnerabilidad", rotulo="Vulnerabilidad (INFORM)",
             cautela="Dimensión del índice INFORM: pobreza, desigualdad, dependencia de la ayuda y "
                     "grupos vulnerables."),
        dict(base, clave="riesgo_inform_capacidad", rotulo="Falta de capacidad para enfrentar crisis (INFORM)",
             cautela="Dimensión del índice INFORM: más alto es menos capacidad institucional e "
                     "infraestructura para responder."),
    ]
    publicables = [m for m in medidas if cobertura.get(m["clave"])]
    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="INFORM Risk — Centro Común de Investigación de la Comisión Europea y OCHA",
        url_fuente="https://drmkc.jrc.ec.europa.eu/inform-index",
        calificacion=comun.calificar(
            "A", 3, False,
            "Índice compuesto con método publicado por dos organismos internacionales. "
            "Credibilidad 3: es una construcción sobre insumos de terceros, sin segunda fuente "
            "que mida lo mismo."),
        registros=registros,
        vacios=[
            "ES UN ÍNDICE COMPUESTO DE TERCEROS: suma insumos de otros organismos, algunos de los "
            "cuales este registro también publica. No es segunda fuente de ninguno de ellos.",
            "NO ES UN PRONÓSTICO: un valor alto dice exposición a que una amenaza se vuelva crisis, "
            "no que la crisis vaya a ocurrir.",
            "EL AÑO ES EL DE LA EDICIÓN, que usa datos de años anteriores.",
            f"Ediciones leídas: {', '.join(str(a) for a in sorted(ediciones))}.",
        ],
        extra={"indicadores": publicables,
               "cobertura": {m["clave"]: cobertura.get(m["clave"], 0) for m in publicables},
               "resumen": {"ediciones": ediciones, "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
