# -*- coding: utf-8 -*-
"""Lo último que publica cada Estado: homicidios según la estadística oficial del propio país.

POR QUÉ EXISTE
--------------
Dos analistas señalaron que SIWA mostraba homicidios de Argentina de 2023 cuando
el Ministerio de Seguridad ya publicaba 2025 (15/9/2026). La serie comparable de
la región es la de la UNODC, que llega por el Banco Mundial con dos o tres años de
retraso porque valida y homologa lo que le mandan los Estados. Los Estados, en
cambio, publican lo suyo mucho antes: Colombia mes a mes, Argentina al año
siguiente.

La dirección autorizó el 15/9/2026 publicar ESA cifra —la del propio Estado, con
su período— al lado de la serie comparable. Hasta entonces el registro solo
enlazaba a los portales (`reciente_oficial.py`).

LA REGLA QUE NO SE NEGOCIA
--------------------------
**ESTAS CIFRAS NO SE COMPARAN ENTRE PAÍSES NI SE SUMAN.** Cada Estado cuenta el
homicidio con su definición, su registro y su cadencia. La comparación entre
países se hace con la serie de la UNODC; esta materia sirve para ver la
evolución de cada país con su propia vara, y lo dice en cada ficha.

QUÉ PUBLICA, POR PAÍS
---------------------
  · Argentina — Ministerio de Seguridad, Sistema Nacional de Información
    Criminal (SNIC): víctimas de homicidio doloso por año, 2000 en adelante, y
    la tasa que publica el propio Ministerio. Licencia CC BY 4.0.
  · Colombia — Ministerio de Defensa, conjunto «HOMICIDIO» en datos.gov.co:
    víctimas de homicidio intencional y feminicidio por año, 2003 en adelante,
    y el año en curso hasta el último mes cargado. Licencia CC BY-SA 4.0.
  · Trinidad y Tobago — Servicio de Policía (TTPS): asesinatos denunciados por
    año, 2018 en adelante, y el año en curso hasta el último mes. Sin licencia
    declarada: son estadísticas oficiales publicadas para el público.

El año en curso NUNCA entra en la serie como si fuera un año entero: va aparte,
con los meses que cubre.
"""
from __future__ import annotations

import csv
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import comun
import geo

COLECTOR = "estado_reciente"
CAPA = "publico"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
MESES_EN = ["january", "february", "march", "april", "may", "june", "july", "august",
            "september", "october", "november", "december"]

SNIC = "https://cloud-snic.minseg.gob.ar/Bases/SNIC/snic-pais.csv"
COLOMBIA = "https://www.datos.gov.co/resource/m8fd-ahd9.json"
COLOMBIA_FICHA = "https://www.datos.gov.co/api/views/m8fd-ahd9.json"
TTPS = "https://ttps.gov.tt/statistics/download/?year={anio}"


def pedir(url: str) -> bytes:
    ultimo = None
    for intento in range(4):
        try:
            p = urllib.request.Request(url, headers={"User-Agent": comun.AGENTE})
            with urllib.request.urlopen(p, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                raise
            ultimo = e
        except Exception as e:  # noqa: BLE001 — se reintenta
            ultimo = e
        time.sleep(5 * (intento + 1))
    raise RuntimeError(f"No se pudo llegar a {url}: {type(ultimo).__name__}")


def numero(v: str) -> float:
    return float(str(v).replace(",", ".").strip())


# ── ARGENTINA ───────────────────────────────────────────────────────────────
def argentina() -> dict:
    filas = list(csv.reader(io.StringIO(pedir(SNIC).decode("utf-8-sig", "replace")), delimiter=";"))
    cabeza = [c.strip('"') for c in filas[0]]
    i = {c: n for n, c in enumerate(cabeza)}
    serie, tasas = [], {}
    for f in filas[1:]:
        if len(f) < len(cabeza) or f[i["codigo_delito_snic_nombre"]].strip('"') != "Homicidios dolosos":
            continue
        anio = int(f[i["anio"]])
        serie.append({"anio": anio, "valor": int(float(f[i["cantidad_victimas"]]))})
        tasas[anio] = round(numero(f[i["tasa_victimas"]]), 2)
    serie.sort(key=lambda x: x["anio"])
    if not serie:
        raise RuntimeError("el SNIC no trae la fila de homicidios dolosos: cambió la planilla")
    ultimo = serie[-1]["anio"]
    return {"serie": serie, "en_curso": None,
            "nota": f"{str(tasas[ultimo]).replace('.', ',')} víctimas cada 100.000 habitantes en {ultimo}, según el Ministerio",
            "definicion": "víctimas de homicidio doloso (SNIC, delitos registrados por las fuerzas de seguridad)",
            "organismo": "Ministerio de Seguridad Nacional — Sistema Nacional de Información Criminal (SNIC)",
            "enlace": "https://www.argentina.gob.ar/seguridad/estadisticascriminales/bases-de-datos",
            "licencia": "CC BY 4.0", "cadencia": "anual"}


# ── COLOMBIA ────────────────────────────────────────────────────────────────
def colombia() -> dict:
    q = urllib.parse.quote("date_extract_y(fecha_hecho) as anio, sum(cantidad) as total")
    anual = json.loads(pedir(f"{COLOMBIA}?$select={q}&$group=anio&$order=anio"))
    q = urllib.parse.quote("date_trunc_ym(fecha_hecho) as mes, sum(cantidad) as total")
    mensual = json.loads(pedir(f"{COLOMBIA}?$select={q}&$group=mes&$order=mes%20DESC&$limit=1"))
    ficha = json.loads(pedir(COLOMBIA_FICHA))
    ultimo_mes = datetime.fromisoformat(mensual[0]["mes"][:10])
    por_anio = {int(x["anio"]): int(float(x["total"])) for x in anual if x.get("anio")}
    en_curso = None
    if ultimo_mes.month < 12 and ultimo_mes.year in por_anio:
        en_curso = {"anio": ultimo_mes.year, "hasta_mes": ultimo_mes.month,
                    "valor": por_anio.pop(ultimo_mes.year)}
    serie = [{"anio": a, "valor": v} for a, v in sorted(por_anio.items())]
    cargado = datetime.fromtimestamp(ficha.get("rowsUpdatedAt", 0), timezone.utc).date().isoformat()
    return {"serie": serie, "en_curso": en_curso, "nota": None, "actualizado_por_la_fuente": cargado,
            "definicion": "víctimas de homicidio intencional y feminicidio registradas (Policía Nacional, "
                          "publicado por el Ministerio de Defensa)",
            "organismo": "Ministerio de Defensa Nacional — conjunto «HOMICIDIO» en datos.gov.co",
            "enlace": "https://www.datos.gov.co/d/m8fd-ahd9", "licencia": "CC BY-SA 4.0",
            "cadencia": "mensual"}


# ── TRINIDAD Y TOBAGO ───────────────────────────────────────────────────────
def trinidad() -> dict:
    este = datetime.now(timezone.utc).year
    por_anio, meses_del_anio = {}, {}
    for anio in range(2018, este + 1):
        try:
            texto = pedir(TTPS.format(anio=anio)).decode("utf-8-sig", "replace")
        except urllib.error.HTTPError:
            continue
        lineas = texto.splitlines()
        cabeza = next((n for n, l in enumerate(lineas) if l.startswith("Year,")), None)
        if cabeza is None:
            continue
        total, meses = 0, set()
        for f in csv.DictReader(io.StringIO("\n".join(lineas[cabeza:]))):
            if (f.get("Offence") or "").strip().lower() != "murders":
                continue
            total += int(float(f.get("Reported") or 0))
            mes = (f.get("Month") or "").strip().lower()
            if mes in MESES_EN:
                meses.add(MESES_EN.index(mes) + 1)
        if meses:
            por_anio[anio], meses_del_anio[anio] = total, max(meses)
    if not por_anio:
        raise RuntimeError("la policía de Trinidad y Tobago no devolvió ninguna planilla")
    en_curso = None
    ultimo = max(por_anio)
    if meses_del_anio[ultimo] < 12:
        en_curso = {"anio": ultimo, "hasta_mes": meses_del_anio[ultimo], "valor": por_anio.pop(ultimo)}
    serie = [{"anio": a, "valor": v} for a, v in sorted(por_anio.items())]
    return {"serie": serie, "en_curso": en_curso, "nota": None,
            "definicion": "asesinatos denunciados (murders reported), Servicio de Policía de Trinidad y Tobago",
            "organismo": "Trinidad and Tobago Police Service (TTPS) — Crime Statistics",
            "enlace": "https://ttps.gov.tt/statistics/",
            "licencia": "sin licencia declarada: estadística oficial publicada para el público",
            "cadencia": "mensual"}


PAISES = {"ARG": argentina, "COL": colombia, "TTO": trinidad}


def ficha(dato: dict) -> dict:
    serie = dato["serie"]
    ultimo = serie[-1]
    anterior = serie[-2] if len(serie) > 1 else None
    f = {"valor": ultimo["valor"], "anio": ultimo["anio"],
         "anio_anterior": anterior["anio"] if anterior else None,
         "valor_anterior": anterior["valor"] if anterior else None,
         "variacion_pct": (round((ultimo["valor"] - anterior["valor"]) / anterior["valor"] * 100, 1)
                           if anterior and anterior["valor"] else None),
         "anio_inicial": serie[0]["anio"], "valor_inicial": serie[0]["valor"], "serie": serie}
    partes = []
    if dato.get("en_curso"):
        c = dato["en_curso"]
        cifra = f"{c['valor']:,}".replace(",", ".")
        partes.append(f"{c['anio']}, de enero a {MESES[c['hasta_mes'] - 1]}: {cifra} "
                      "(año en curso, no entra en la serie)")
    if dato.get("nota"):
        partes.append(dato["nota"])
    partes.append(f"Fuente: {dato['organismo']}")
    f["nota"] = " · ".join(partes)
    f["en_curso"] = dato.get("en_curso")
    return f


def construir() -> Path:
    registros, cobertura, caidas, detalle = [], {}, [], {}
    for p in geo.padron():
        r = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        lector = PAISES.get(p["iso"])
        if lector:
            try:
                dato = lector()
                r["indicadores"]["homicidios_estado"] = ficha(dato)
                r["fuente_nacional"] = {k: dato.get(k) for k in
                                        ("organismo", "enlace", "licencia", "cadencia", "definicion",
                                         "actualizado_por_la_fuente")}
                detalle[p["iso"]] = r["fuente_nacional"]
                cobertura["homicidios_estado"] = cobertura.get("homicidios_estado", 0) + 1
            except Exception as error:  # noqa: BLE001 — la caída se declara
                caidas.append(f"{p['pais']}: {type(error).__name__}: {str(error)[:140]}")
        registros.append(r)

    if not cobertura:
        raise RuntimeError("Ningún Estado respondió: " + " | ".join(caidas))

    medida = {
        "clave": "homicidios_estado", "rotulo": "Homicidios según el propio Estado",
        "eje": "Seguridad", "unidad": "víctimas en el año", "unidad_singular": "víctima",
        "mas_es_peor": True, "no_comparable_entre_paises": True,
        "origen": "Estadística oficial de cada Estado (ministerios de seguridad y defensa, policías)",
        "cautela": ("NO SE COMPARA ENTRE PAÍSES NI SE SUMA. Es la cifra que publica cada Estado con su "
                    "propia definición: Argentina cuenta víctimas de homicidio doloso; Colombia, homicidio "
                    "intencional y feminicidio; Trinidad y Tobago, asesinatos denunciados. Sirve para ver "
                    "la evolución de cada país y el año más reciente, antes de que llegue la serie "
                    "comparable de la UNODC, que es la que se usa para comparar. El año en curso va aparte, "
                    "con los meses que cubre."),
    }
    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Estadística oficial de homicidios de cada Estado — Argentina (SNIC), Colombia (Ministerio "
               "de Defensa) y Trinidad y Tobago (Servicio de Policía)",
        url_fuente="https://www.argentina.gob.ar/seguridad/estadisticascriminales/bases-de-datos",
        calificacion=comun.calificar(
            "A", 2, False,
            "Registro administrativo oficial de cada Estado, leído en su fuente primaria. Credibilidad 2 "
            "y no 1: cada Estado define y registra a su manera, y las cifras del año en curso son "
            "provisionales hasta el cierre."),
        registros=registros,
        vacios=[
            "ESTAS CIFRAS NO SON COMPARABLES ENTRE PAÍSES Y NO SE SUMAN: cada Estado define el homicidio "
            "a su manera. Para comparar se usa la serie de la UNODC (Banco Mundial).",
            "PRIMERA ETAPA: tres Estados cuya estadística se lee sola —Argentina, Colombia y Trinidad y "
            "Tobago—. Perú, Bolivia, México, Costa Rica, Panamá, Chile, Brasil y Guatemala publican en "
            "archivos grandes, PDF o tableros y entran en la etapa siguiente. Venezuela, Cuba y Nicaragua "
            "no publican estadística de homicidios.",
            "LAS CIFRAS DEL AÑO EN CURSO SON PROVISIONALES: los Estados las corrigen hasta el cierre. Por "
            "eso no entran en la serie ni en la variación.",
            "TRINIDAD Y TOBAGO NO DECLARA LICENCIA para su estadística: se publica la cifra con su fuente "
            "y enlace, como estadística oficial publicada para el público.",
        ] + ([f"No respondieron en esta corrida: {' | '.join(caidas)}."] if caidas else []),
        extra={"indicadores": [medida], "cobertura": cobertura, "fuentes_nacionales": detalle,
               "resumen": {"estados": len(cobertura and detalle), "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
