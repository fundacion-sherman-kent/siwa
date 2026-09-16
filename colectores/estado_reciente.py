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
  · Panamá — Procuraduría General de la Nación: informe estadístico de víctimas
    de homicidio, un conjunto por año desde 2017 y un avance semestral del año en
    curso. Una fila es una víctima. Licencia CC BY.
  · Perú — Ministerio del Interior, indicador 30 del Plan de Acción de Seguridad
    Ciudadana, contado por el Comité Estadístico Interinstitucional de la
    Criminalidad (INEI, Ministerio Público y Policía): 2014 en adelante, con la
    tasa que publica el propio tablero. Licencia ODC-BY.
  · Ecuador — INEC, tabulado mensual de Justicia y Crimen con datos de la Fiscalía
    y el Ministerio del Interior: homicidios intencionales mes a mes desde enero de
    2014, fila «Total Nacional», y el año en curso hasta el último mes publicado.

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


# ── PANAMÁ ──────────────────────────────────────────────────────────────────
#
# La Procuraduría General de la Nación publica UN CONJUNTO POR AÑO, y cada fila es
# UNA VÍCTIMA: el total del año es la cantidad de filas. No hay un archivo con la
# serie; se arma juntando los conjuntos del catálogo.
#
# EL AÑO DE LA FILA NO SE USA PARA CONTAR. El archivo de 2024 trae la columna «AÑO»
# rota desde la fila 291: dice 2027, 2028, 2029… —es un arrastre de planilla en el
# original—. Contar por esa columna perdería la mitad de las víctimas de 2024 y
# fabricaría años futuros. Se cuenta por el archivo, que es el informe de ese año,
# y la diferencia se declara.
PANAMA_CATALOGO = ("https://www.datosabiertos.gob.pa/api/3/action/package_search"
                   "?q=homicidio&rows=50")


def _anio_del_titulo(titulo: str) -> tuple:
    """Devuelve (año, hasta_mes) leído del título del conjunto. hasta_mes None si es anual."""
    import re
    t = titulo.lower()
    anios = re.findall(r"(20\d\d)", t)
    if not anios:
        return (None, None)
    anio = int(anios[-1])
    hasta = None
    for n, m in enumerate(MESES, start=1):
        if f" a {m}" in t or f"a {m} " in t:
            hasta = n
    return (anio, hasta)


def panama() -> dict:
    catalogo = json.loads(pedir(PANAMA_CATALOGO))
    por_anio, hasta_mes, licencias, discordancia = {}, {}, set(), {}
    for p in (catalogo.get("result") or {}).get("results") or []:
        org = ((p.get("organization") or {}).get("title") or "")
        if "procuradur" not in org.lower():
            continue
        anio, hasta = _anio_del_titulo(p.get("title") or "")
        if not anio:
            continue
        recurso = next((r for r in p.get("resources") or []
                        if (r.get("format") or "").upper() == "CSV" and r.get("url")), None)
        if not recurso:
            continue
        texto = pedir(recurso["url"]).decode("utf-8", "replace")
        filas = [l for l in texto.splitlines()[1:] if l.strip()]
        if not filas:
            continue
        distintos = sum(1 for l in filas
                        if (l.split(";")[1].strip() if len(l.split(";")) > 1 else "") != str(anio))
        por_anio[anio] = len(filas)
        hasta_mes[anio] = hasta
        if distintos:
            discordancia[anio] = distintos
        if p.get("license_id"):
            licencias.add(p["license_id"])
    if not por_anio:
        raise RuntimeError("el catálogo de Panamá no devolvió conjuntos de la Procuraduría")
    en_curso = None
    ultimo = max(por_anio)
    if hasta_mes.get(ultimo):
        en_curso = {"anio": ultimo, "hasta_mes": hasta_mes[ultimo], "valor": por_anio.pop(ultimo)}
    serie = [{"anio": a, "valor": v} for a, v in sorted(por_anio.items()) if not hasta_mes.get(a)]
    if not serie:
        raise RuntimeError("Panamá: ningún año completo en el catálogo")
    aviso = None
    if discordancia:
        detalle = "; ".join(f"{a}: {n} filas" for a, n in sorted(discordancia.items()))
        aviso = ("El original trae el año mal escrito en algunas filas y se cuenta por el archivo "
                 f"del año ({detalle})")
    return {"serie": serie, "en_curso": en_curso, "nota": aviso,
            "definicion": "víctimas de homicidio registradas por el Ministerio Público (una fila por "
                          "víctima en el informe estadístico anual)",
            "organismo": "Procuraduría General de la Nación — Informe Estadístico de Víctimas de Homicidio",
            "enlace": "https://www.datosabiertos.gob.pa/dataset?q=homicidio",
            "licencia": "CC BY 4.0" if "cc-by" in licencias else "según declara el catálogo de datos abiertos",
            "cadencia": "anual, con un avance semestral"}


# ── PERÚ ────────────────────────────────────────────────────────────────────
#
# El Estado peruano no publica un archivo rotulado «homicidios». Publica el tablero
# de indicadores del Plan de Acción de Seguridad Ciudadana, donde el indicador 30 es
# —así lo dice su propio diccionario— «Tasa de homicidios por cada 100 mil
# habitantes», y la fuente es el CEIC, el comité que reúne al INEI, al Ministerio
# Público y a la Policía para contar los homicidios del país. El ámbito 0 es el
# nacional: ahí VALORES es el recuento y VALORES_2 la tasa.
#
# EL NOMBRE DEL ARCHIVO CAMBIA TODOS LOS MESES («…Jul 2026.zip»). No se escribe a
# mano: se lee de la página del conjunto en cada corrida. Un enlace fijo se rompe
# solo el mes que viene y el registro se quedaría mostrando lo viejo sin avisar.
PERU_FICHA = ("https://www.datosabiertos.gob.pe/dataset/"
              "indicadores-de-seguridad-ciudadana-y-tendencias-territoriales-mininter")
PERU_INDICADOR, PERU_AMBITO_NACIONAL, PERU_FUENTE = "30", "0", "CEIC"


def peru() -> dict:
    import re
    import zipfile

    pagina = pedir(PERU_FICHA).decode("utf-8", "replace")
    enlaces = re.findall(r'href="([^"]*DataSet_Ind_Plan_Acc_Segu_Ciud[^"]*\.zip)"', pagina)
    if not enlaces:
        raise RuntimeError("la página del conjunto de Perú ya no ofrece el ZIP de indicadores")
    # EL ZIP TRAE UNA FOTO POR MES y ninguna dice en el nombre cuál llega más lejos:
    # la más pesada tiene más distritos, no más años. Se leen todas y gana la que
    # tiene el año más nuevo; elegir por tamaño dejaba la serie tres años atrás.
    serie, tasas = [], {}
    with zipfile.ZipFile(io.BytesIO(pedir(enlaces[0]))) as z:
        internos = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not internos:
            raise RuntimeError("el ZIP de Perú no trae ningún CSV")
        for interno in internos:
            texto = z.read(interno).decode("utf-8-sig", "replace")
            propia, sus_tasas = [], {}
            for f in csv.DictReader(io.StringIO(texto)):
                if (f.get("INDICADOR") != PERU_INDICADOR or f.get("AMBITO") != PERU_AMBITO_NACIONAL
                        or f.get("FUENTE") != PERU_FUENTE):
                    continue
                anio = int(f["ANIO"])
                propia.append({"anio": anio, "valor": int(float(f["VALORES"]))})
                sus_tasas[anio] = round(numero(f["VALORES_2"]), 2)
            if propia and (not serie or max(x["anio"] for x in propia) > max(x["anio"] for x in serie)):
                serie, tasas = propia, sus_tasas
    if not serie:
        raise RuntimeError("el tablero del Perú no trae el indicador 30 del CEIC en el ámbito nacional")
    serie.sort(key=lambda x: x["anio"])
    ultimo = serie[-1]["anio"]
    return {"serie": serie, "en_curso": None,
            "nota": f"{str(tasas[ultimo]).replace('.', ',')} víctimas cada 100.000 habitantes en "
                    f"{ultimo}, según el propio tablero",
            "definicion": "homicidios contados por el Comité Estadístico Interinstitucional de la "
                          "Criminalidad (INEI, Ministerio Público y Policía Nacional)",
            "organismo": "Ministerio del Interior — indicador 30 (CEIC) del Plan de Acción de "
                         "Seguridad Ciudadana",
            "enlace": PERU_FICHA, "licencia": "ODC-BY", "cadencia": "anual"}


# ── ECUADOR ─────────────────────────────────────────────────────────────────
#
# El conjunto mejor rotulado —«Homicidios Intencionales» del Ministerio del
# Interior— vive en datosabiertos.gob.ec, que rechaza a los programas con 403 en
# todas sus rutas (comprobado el 15/9/2026, siete rutas). El mismo dato, producido
# por la Fiscalía y el Ministerio del Interior, lo publica el INEC en su tabulado
# mensual de Justicia y Crimen, en un dominio que sí responde.
#
# La planilla trae una columna por MES desde enero de 2014 y una fila «Total
# Nacional». Se usa esa fila, que es la que declara el Estado: sumar provincias a
# mano daría lo mismo hoy y una cifra distinta el día que el INEC agregue una fila.
ECUADOR_FICHA = "https://www.ecuadorencifras.gob.ec/justicia-y-crimen/"


def _planilla(crudo: bytes, contiene: str) -> dict:
    """Lee una hoja de un .xlsx sin librerías: {fila: {columna: valor}}.

    La casa no instala dependencias para leer una planilla; el resto de los
    colectores hace lo mismo (ver `bti.py`). Las cadenas repetidas viven aparte
    y el formato puede partir una en pedazos: se juntan, porque contar cada
    pedazo como una cadena corre todos los índices y la planilla se lee entera
    pero mal.
    """
    import re
    import zipfile

    z = zipfile.ZipFile(io.BytesIO(crudo))
    comp = []
    if "xl/sharedStrings.xml" in z.namelist():
        texto = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
        comp = ["".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)).strip()
                for si in re.findall(r"<si>(.*?)</si>", texto, re.S)]
    libro = z.read("xl/workbook.xml").decode("utf-8", "replace")
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8", "replace")
    destino = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels))
    archivo = None
    for nombre, rid in re.findall(r'<sheet[^>]*name="([^"]*)"[^>]*r:id="([^"]+)"', libro):
        if contiene in nombre:
            archivo = "xl/" + destino.get(rid, "").lstrip("/")
            break
    if not archivo or archivo not in z.namelist():
        raise RuntimeError(f"la planilla no trae la hoja «{contiene}»")
    hoja = z.read(archivo).decode("utf-8", "replace")
    filas = {}
    for numero, cuerpo in re.findall(r"<row[^>]*r=\"(\d+)\"[^>]*>(.*?)</row>", hoja, re.S):
        celdas = {}
        for col, atributos, valor in re.findall(r'<c r="([A-Z]+)\d+"([^>]*)>(.*?)</c>', cuerpo, re.S):
            v = re.search(r"<v>(.*?)</v>", valor, re.S)
            if not v:
                continue
            if 't="s"' in atributos:
                try:
                    celdas[col] = comp[int(v.group(1))]
                except (ValueError, IndexError):
                    continue
            else:
                celdas[col] = v.group(1)
        if celdas:
            filas[int(numero)] = celdas
    return filas


def ecuador() -> dict:
    import datetime as _dt
    import re
    import zipfile

    pagina = pedir(ECUADOR_FICHA).decode("utf-8", "replace")
    enlaces = re.findall(r'href=["\']([^"\']*justicia_crimen[^"\']*Cifras_Seguridad\.zip)["\']', pagina)
    if not enlaces:
        raise RuntimeError("el INEC de Ecuador ya no ofrece el tabulado de Cifras de Seguridad")
    with zipfile.ZipFile(io.BytesIO(pedir(enlaces[-1]))) as z:
        interno = next((n for n in z.namelist() if n.lower().endswith(".xlsx")), None)
        if not interno:
            raise RuntimeError("el tabulado del INEC de Ecuador no trae planilla")
        filas = _planilla(z.read(interno), "homicidios_prov")

    # LOS MESES VIENEN COMO NÚMERO DE SERIE de la planilla —45658 es el 1/1/2026—
    # y la unidad de esa cuenta es el día desde el 30/12/1899. Se toman los que caen
    # entre 2000 y 2100: así, si el INEC pone un texto en la cabecera, no se
    # convierte en una fecha inventada.
    origen = _dt.date(1899, 12, 30)
    cabeza, columnas = None, {}
    for numero in sorted(filas):
        posibles = {}
        for col, v in filas[numero].items():
            try:
                serie_dia = int(float(v))
            except (TypeError, ValueError):
                continue
            if 36526 <= serie_dia <= 73050:
                posibles[col] = origen + _dt.timedelta(days=serie_dia)
        if len(posibles) > 10:
            cabeza, columnas = numero, posibles
            break
    if cabeza is None:
        raise RuntimeError("la hoja de homicidios del INEC de Ecuador cambió de forma")
    total = None
    for numero in sorted(filas):
        if numero <= cabeza:
            continue
        if any(isinstance(v, str) and v.strip().lower().startswith("total nacional")
               for v in filas[numero].values()):
            total = filas[numero]
            break
    if total is None:
        raise RuntimeError("la hoja de homicidios del INEC de Ecuador ya no trae «Total Nacional»")
    por_anio, meses = {}, {}
    for col, fecha in columnas.items():
        v = total.get(col)
        try:
            cantidad = int(float(v))
        except (TypeError, ValueError):
            continue
        por_anio[fecha.year] = por_anio.get(fecha.year, 0) + cantidad
        meses.setdefault(fecha.year, set()).add(fecha.month)
    if not por_anio:
        raise RuntimeError("el tabulado del INEC de Ecuador no trae ningún mes con dato")
    en_curso = None
    ultimo = max(por_anio)
    if len(meses[ultimo]) < 12:
        en_curso = {"anio": ultimo, "hasta_mes": max(meses[ultimo]), "valor": por_anio.pop(ultimo)}
    serie = [{"anio": a, "valor": v} for a, v in sorted(por_anio.items()) if len(meses[a]) == 12]
    if not serie:
        raise RuntimeError("Ecuador: ningún año completo en el tabulado")
    return {"serie": serie, "en_curso": en_curso, "nota": None,
            "definicion": "homicidios intencionales registrados, según el tabulado mensual del INEC con "
                          "datos de la Fiscalía General del Estado y el Ministerio del Interior",
            "organismo": "Instituto Nacional de Estadística y Censos — tabulado de Justicia y Crimen",
            "enlace": ECUADOR_FICHA,
            "licencia": "sin licencia declarada junto al tabulado: estadística oficial publicada para "
                        "el público",
            "cadencia": "mensual"}


PAISES = {"ARG": argentina, "COL": colombia, "TTO": trinidad, "PAN": panama, "PER": peru,
          "ECU": ecuador}


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

    # QUÉ CUENTA CADA UNO, EN LA MISMA ADVERTENCIA. Se arma con los Estados que
    # respondieron hoy: escrita a mano, la lista envejece el día que entra uno más
    # y queda nombrando países que ya no están o callando los que sí.
    nombres = {p["iso"]: p["pais"] for p in geo.padron()}
    definiciones = "; ".join(f"{nombres.get(iso, iso)} cuenta {d['definicion']}"
                             for iso, d in sorted(detalle.items(), key=lambda x: nombres.get(x[0], x[0])))
    con_dato = ", ".join(sorted(nombres.get(i, i) for i in detalle))

    medida = {
        "clave": "homicidios_estado", "rotulo": "Homicidios según el propio Estado",
        "eje": "Seguridad", "unidad": "víctimas en el año", "unidad_singular": "víctima",
        "mas_es_peor": True, "no_comparable_entre_paises": True,
        "origen": "Estadística oficial de cada Estado (ministerios de seguridad y defensa, policías)",
        "cautela": ("NO SE COMPARA ENTRE PAÍSES NI SE SUMA. Es la cifra que publica cada Estado con su "
                    "propia definición, su propio registro y su propia cadencia: " + definiciones + ". "
                    "Sirve para ver la evolución de cada país y el año más reciente, antes de que llegue "
                    "la serie comparable de la UNODC, que es la que se usa para comparar. El año en curso "
                    "va aparte, con los meses que cubre."),
    }
    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Estadística oficial de homicidios de cada Estado, leída en la fuente primaria de cada "
               "país: " + con_dato,
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
            f"NO ESTÁN LOS 33: hoy hay {len(detalle)} Estados cuya estadística se lee sola ({con_dato}). "
            "Se comprobó el 15/9/2026, portal por portal: Chile, México, Ecuador en su portal de datos "
            "abiertos, República Dominicana y Brasil rechazan a los programas o esconden el archivo "
            "detrás de un tablero; Costa Rica tenía todo el dominio del Poder Judicial caído; Uruguay "
            "difunde su cifra en informe PDF y en un visualizador, y en su catálogo abierto solo hay "
            "imputados, que no son víctimas; El Salvador dejó de publicar la estadística policial en "
            "2022. Venezuela, Cuba y Nicaragua no publican estadística de homicidios. Que un Estado no "
            "figure acá no dice nada sobre su violencia: dice que su cifra todavía no se lee sola.",
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
