"""Base global de los Objetivos de Desarrollo Sostenible — Naciones Unidas.

Series **reportadas oficialmente por cada Estado** y validadas por el organismo
custodio de cada indicador. Sin clave y sin registro.

Aporta materias que ninguna otra fuente del catálogo cubría:

| Eje | Serie | Custodio |
|---|---|---|
| Seguridad | Víctimas detectadas de trata de personas | UNODC |
| Seguridad | Trata para explotación sexual y para trabajo forzoso | UNODC |
| Seguridad | Homicidios por 100.000, con serie desde 2000 | UNODC |
| Gobernanza | Prevalencia del soborno a personas y a empresas | UNODC y Banco Mundial |
| Desarrollo | Empleo informal — la economía en negro medida | OIT |
| Desarrollo | Población urbana en asentamientos precarios | ONU-Hábitat |

**Advertencia de método, y es grande.** La trata de personas se consigna por
**víctimas detectadas**: un Estado que detecta más aparece peor, y uno que no
busca aparece limpio. La cifra mide capacidad de detección tanto como magnitud
del delito. Lo mismo, en menor grado, vale para el soborno declarado en
encuestas. Se declara en cada archivo.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import comun
import geo

BASE = "https://unstats.un.org/sdgapi/v1/sdg"
PADRON_M49 = Path(__file__).resolve().parent / "m49.json"
DESDE = 2010

SERIES = [
    {"clave": "trata_victimas", "codigo": "VC_HTF_DETVR", "eje": "Seguridad",
     "rotulo": "Víctimas detectadas de trata de personas",
     "unidad": "por cada 100.000 habitantes", "mas_es_peor": True,
     "origen": "UNODC, vía la base global de los ODS",
     "cautela": "MIDE DETECCIÓN, NO MAGNITUD. Un Estado que investiga más detecta más y "
                "aparece peor; uno que no busca aparece limpio. La cifra baja puede "
                "significar poco delito o poca capacidad de detectarlo."},
    {"clave": "trata_sexual", "codigo": "VC_HTF_DETVSXR", "eje": "Seguridad",
     "rotulo": "Trata para explotación sexual", "unidad": "por cada 100.000 habitantes",
     "mas_es_peor": True, "origen": "UNODC, vía la base global de los ODS",
     "cautela": "Misma advertencia: mide víctimas detectadas, no víctimas existentes."},
    {"clave": "trata_trabajo", "codigo": "VC_HTF_DETVFLR", "eje": "Seguridad",
     "rotulo": "Trata para trabajo forzoso", "unidad": "por cada 100.000 habitantes",
     "mas_es_peor": True, "origen": "UNODC, vía la base global de los ODS",
     "cautela": "Misma advertencia que el resto de la trata: mide víctimas detectadas."},
    {"clave": "soborno_personas", "codigo": "IU_COR_BRIB", "eje": "Gobernanza",
     "rotulo": "Prevalencia del soborno a personas", "unidad": "% de la población",
     "mas_es_peor": True, "origen": "UNODC, vía la base global de los ODS",
     "cautela": "Sale de encuestas de victimización: mide lo que la gente declara haber "
                "pagado, no lo que se pagó."},
    {"clave": "soborno_empresas", "codigo": "IC_FRM_BRIB", "eje": "Gobernanza",
     "rotulo": "Empresas a las que se pidió un soborno", "unidad": "% de las empresas",
     "mas_es_peor": True, "origen": "Banco Mundial, vía la base global de los ODS",
     "cautela": "Encuesta a empresas, con muestra y año propios de cada Estado."},
    {"clave": "empleo_informal", "codigo": "SL_ISV_IFEM", "eje": "Desarrollo",
     "rotulo": "Empleo informal", "unidad": "% del empleo total", "mas_es_peor": True,
     "origen": "OIT, vía la base global de los ODS",
     "cautela": "Es la economía en negro medida sobre el empleo, no sobre el producto. "
                "No incluye la actividad ilícita, que no aparece en ninguna encuesta laboral."},
]

# Dimensiones que se conservan: total, ambos sexos, todas las edades.
TOTALES = {"BOTHSEX", "ALLAGE", "_T", "ALLAREA", "TOTAL", "15+", "ALLACT", ""}


def _traer(serie: dict, m49: list) -> dict:
    """Serie anual por país. Devuelve {m49: [(anio, valor)]}."""
    parametros = urllib.parse.urlencode({
        "seriesCode": serie["codigo"],
        "areaCode": ",".join(str(c) for c in m49),
        "pageSize": 20000,
    })
    peticion = urllib.request.Request(f"{BASE}/Series/Data?{parametros}",
                                      headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=180) as respuesta:
        crudo = json.loads(respuesta.read().decode("utf-8", "replace"))

    salida = defaultdict(dict)
    for fila in crudo.get("data", []):
        dimensiones = fila.get("dimensions") or {}
        # Se descartan los cortes por sexo, edad o sector: solo entra el total.
        if any(v not in TOTALES for k, v in dimensiones.items() if k != "Reporting Type"):
            continue
        try:
            anio = int(float(fila.get("timePeriodStart")))
            valor = float(fila.get("value"))
        except (TypeError, ValueError):
            continue
        if valor != valor or valor in (float("inf"), float("-inf")):
            continue          # la fuente manda «NaN» en algunos registros
        if anio < DESDE:
            continue
        salida[str(fila.get("geoAreaCode"))][anio] = round(valor, 4)
    return {codigo: sorted(anios.items()) for codigo, anios in salida.items()}


def recolectar():
    codigos = json.loads(PADRON_M49.read_text(encoding="utf-8"))["codigos"]
    padron = geo.padron()
    m49_a_iso = {str(v): k for k, v in codigos.items()}
    m49 = list(codigos.values())

    with ThreadPoolExecutor(max_workers=3) as ejecutor:
        crudos = list(ejecutor.map(lambda s: (s, _intento(s, m49)), SERIES))

    datos, fallidas = {}, []
    for serie, (resultado, falla) in crudos:
        datos[serie["clave"]] = resultado
        if falla:
            fallidas.append(f"{serie['rotulo']}: {falla}")

    if all(not v for v in datos.values()):
        raise RuntimeError("Ninguna serie devolvió datos. No se escribe nada.")

    registros, cobertura = [], {}
    for pais in padron:
        clave_m49 = str(codigos.get(pais["iso"], ""))
        ficha = {**pais, "indicadores": {}}
        for serie in SERIES:
            valores = datos[serie["clave"]].get(clave_m49, [])
            if not valores:
                continue
            anio, valor = valores[-1]
            ficha["indicadores"][serie["clave"]] = {
                "valor": valor, "anio": anio,
                "anio_inicial": valores[0][0], "valor_inicial": valores[0][1],
                "serie": [{"anio": a, "valor": v} for a, v in valores],
            }
            cobertura[serie["clave"]] = cobertura.get(serie["clave"], 0) + 1
        if ficha["indicadores"]:
            registros.append(ficha)
    registros.sort(key=lambda r: r["pais"])

    calificacion = comun.calificar(
        fiabilidad="A", credibilidad=2, corroborado=False,
        nota=("Serie reportada por cada Estado y validada por el organismo custodio del "
              "indicador. Fuente única: el reporte nacional. Declarado conforme a "
              "doctrina/fuentes.md §2 ter."),
    )

    vacios = [
        "LA TRATA DE PERSONAS SE MIDE POR VÍCTIMAS DETECTADAS. Un Estado que investiga "
        "más detecta más y aparece peor; uno que no busca aparece limpio. La cifra mide "
        "capacidad de detección tanto como magnitud del delito, y no debe leerse como "
        "un ranking de gravedad.",
        "Serie ANUAL con rezago y con huecos: los Estados reportan con distinta "
        "frecuencia y varios no reportan algunas series en absoluto.",
        "Se descartan los cortes por sexo, edad y sector: solo entra el total. Los "
        "desgloses existen en la fuente y pueden incorporarse cuando el equipo los pida.",
        "El soborno sale de encuestas de victimización: mide lo declarado, no lo ocurrido.",
        "Los flujos financieros ilícitos NO se publican. La serie existe en la base de "
        "la ONU pero tiene 35 observaciones en todo el mundo: no alcanza para una serie "
        "regional, y publicarla sería dar apariencia de medición a cuatro datos sueltos.",
        ("Cobertura por serie: " + ", ".join(
            f"{s['rotulo']} en {cobertura.get(s['clave'], 0)} de 33" for s in SERIES) + "."),
        "Licencia abierta de Naciones Unidas, con atribución. No restringe el uso comercial.",
    ]
    if fallidas:
        vacios.append(f"Series que no respondieron en esta corrida: {'; '.join(fallidas)}.")

    return comun.escribir(
        colector="onu-ods", capa="publico",
        fuente="Naciones Unidas — base global de indicadores de los ODS",
        url_fuente="https://unstats.un.org/sdgs/dataportal",
        calificacion=calificacion, registros=registros, vacios=vacios,
        extra={
            "indicadores": [{k: s[k] for k in
                             ("clave", "codigo", "rotulo", "eje", "unidad", "mas_es_peor",
                              "origen", "cautela")} for s in SERIES],
            "cobertura": cobertura, "serie_desde": DESDE,
        },
    )


def _intento(serie: dict, m49: list) -> tuple:
    try:
        return (_traer(serie, m49), None)
    except Exception as error:  # noqa: BLE001 — la serie caída se declara
        return ({}, f"{type(error).__name__}")


if __name__ == "__main__":
    comun.correr("onu-ods", recolectar)
