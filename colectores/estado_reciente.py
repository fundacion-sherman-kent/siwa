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
  · México — Secretariado Ejecutivo del Sistema Nacional de Seguridad Pública:
    víctimas de homicidio doloso por entidad y por mes. La serie llega a 2025 con
    la metodología vieja; 2026 estrenó otra y va aparte, como avisa el propio
    Secretariado.

El año en curso NUNCA entra en la serie como si fuera un año entero: va aparte,
con los meses que cubre.
"""
from __future__ import annotations

import csv
import io
import json
import urllib.error
import urllib.parse
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
SNIC_PROVINCIAS = "https://cloud-snic.minseg.gob.ar/Bases/SNIC/snic-provincias.csv"
COLOMBIA = "https://www.datos.gov.co/resource/m8fd-ahd9.json"
COLOMBIA_FICHA = "https://www.datos.gov.co/api/views/m8fd-ahd9.json"
TTPS = "https://ttps.gov.tt/statistics/download/?year={anio}"


def pedir(url: str) -> bytes:
    """Un solo lugar para pedir. Si el sitio rechaza al recolector, se presenta entero."""
    return comun.traer_crudo(url)


def numero(v: str) -> float:
    return float(str(v).replace(",", ".").strip())


def _texto(crudo: bytes) -> str:
    """La Procuraduría de Panamá publica unos años en UTF-8 y otros en cp1252.

    Leerlos todos como UTF-8 no rompe la lectura: la ensucia. «Chiriquí» queda como
    «Chiriqu�» y pasa a contar como una provincia distinta de «Chiriquí». Se
    prueba en orden y gana la primera codificación que entra entera.
    """
    for codigo in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return crudo.decode(codigo)
        except UnicodeDecodeError:
            continue
    return crudo.decode("utf-8", "replace")


def _llave(nombre: str) -> str:
    """El mismo lugar escrito de ocho maneras tiene que contar como uno.

    Panamá trae «BOCAS DEL TORO», «Bocas Del Toro», «Bocas del Toro», «Chiriqui»,
    «Chiriquí» y una versión con el acento roto: 38 etiquetas para unos 13 lugares.
    Contarlas como distintas multiplicaría por tres las provincias del país.
    """
    import unicodedata
    limpio = unicodedata.normalize("NFKD", str(nombre or ""))
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    limpio = limpio.replace("�", "")
    return " ".join(limpio.lower().split())


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
        # LA TASA ES DEL MINISTERIO, NO DE LA CASA. El SNIC publica la columna
        # «tasa_victimas» por año, cada 100.000 habitantes: no hay que calcularla
        # ni hay motivo para decir que no existe. Va con cada punto de la serie,
        # que es lo que permite dibujarla al lado de la serie comparable de la ONU.
        tasa = round(numero(f[i["tasa_victimas"]]), 2)
        serie.append({"anio": anio, "valor": int(float(f[i["cantidad_victimas"]])), "tasa": tasa})
        tasas[anio] = tasa
    serie.sort(key=lambda x: x["anio"])
    if not serie:
        raise RuntimeError("el SNIC no trae la fila de homicidios dolosos: cambió la planilla")
    ultimo = serie[-1]["anio"]
    # El desglose por provincia vive en otra planilla de la misma base. Si ese día
    # no está, la cifra nacional NO se cae: el censo se queda sin ese renglón y se
    # declara, que es distinto de decir que Argentina no publica por provincia.
    provincias = set()
    try:
        crudo = list(csv.reader(io.StringIO(pedir(SNIC_PROVINCIAS).decode("utf-8-sig", "replace")),
                                delimiter=";"))
        cab = [c.strip('"') for c in crudo[0]]
        j = {c: n for n, c in enumerate(cab)}
        for f in crudo[1:]:
            if len(f) >= len(cab) and f[j["codigo_delito_snic_nombre"]].strip('"') == "Homicidios dolosos":
                provincias.add(f[j["provincia_nombre"]].strip('"'))
    except Exception:  # noqa: BLE001 — se declara con el ausente, no se inventa
        provincias = set()
    return {"serie": serie, "en_curso": None,
            "nota": f"{str(tasas[ultimo]).replace('.', ',')} víctimas cada 100.000 habitantes en {ultimo}, según el Ministerio",
            "definicion": "víctimas de homicidio doloso (SNIC, delitos registrados por las fuerzas de seguridad)",
            "organismo": "Ministerio de Seguridad Nacional — Sistema Nacional de Información Criminal (SNIC)",
            "enlace": "https://www.argentina.gob.ar/seguridad/estadisticascriminales/bases-de-datos",
            "licencia": "CC BY 4.0", "cadencia": "anual",
            "unidad_tasa": "por cada 100.000 habitantes",
            "quien_calcula_la_tasa": "el propio Ministerio de Seguridad",
            "unidades": {"nombre": "provincia", "cuantas": len(provincias)} if provincias else None}


# ── COLOMBIA ────────────────────────────────────────────────────────────────
def colombia() -> dict:
    q = urllib.parse.quote("date_extract_y(fecha_hecho) as anio, sum(cantidad) as total")
    anual = json.loads(pedir(f"{COLOMBIA}?$select={q}&$group=anio&$order=anio"))
    q = urllib.parse.quote("date_trunc_ym(fecha_hecho) as mes, sum(cantidad) as total")
    mensual = json.loads(pedir(f"{COLOMBIA}?$select={q}&$group=mes&$order=mes%20DESC&$limit=1"))
    ficha = json.loads(pedir(COLOMBIA_FICHA))
    departamentos = set()
    try:
        q3 = urllib.parse.quote("departamento, count(*) as n")
        for x in json.loads(pedir(f"{COLOMBIA}?$select={q3}&$group=departamento&$limit=200")):
            if x.get("departamento"):
                departamentos.add(x["departamento"].strip())
    except Exception:  # noqa: BLE001 — se declara con el ausente
        departamentos = set()
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
            "cadencia": "mensual",
            "unidades": {"nombre": "departamento", "cuantas": len(departamentos)}
                        if departamentos else None}


# ── TRINIDAD Y TOBAGO ───────────────────────────────────────────────────────
def trinidad() -> dict:
    este = datetime.now(timezone.utc).year
    por_anio, meses_del_anio, divisiones = {}, {}, set()
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
            if (f.get("Division") or "").strip():
                divisiones.add(_llave(f["Division"]))
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
            "cadencia": "mensual",
            # NO ES LA UNIDAD CENSAL. Son divisiones de la policía, que no coinciden
            # con las «regional corporations» y para las que nadie publica población.
            # Se anota lo que es, para que el censo no las cuente como provincias.
            "unidades": {"nombre": "división policial", "cuantas": len(divisiones),
                         "coincide_con_la_unidad_censal": False} if divisiones else None}


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
    por_anio, hasta_mes, licencias, discordancia, areas = {}, {}, set(), {}, set()
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
        texto = _texto(pedir(recurso["url"]))
        filas = [l for l in texto.splitlines()[1:] if l.strip()]
        if not filas:
            continue
        distintos = 0
        for l in filas:
            campos = l.split(";")
            if len(campos) > 1 and campos[1].strip() != str(anio):
                distintos += 1
            if len(campos) > 3 and campos[3].strip():
                areas.add(_llave(campos[3]))
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
            "cadencia": "anual, con un avance semestral",
            # EL CONTEO ES APROXIMADO Y SE DICE. El original escribe el mismo lugar de
            # varias maneras —«Chiriquí», «Chiriqui», «Chiriqu¡»— y en algunos años los
            # acentos se perdieron enteros («panam», «darin», «cocl»): quedan 26
            # etiquetas para unas 14 unidades reales. Juntarlas a ojo sería inventar
            # una precisión que el archivo no tiene. Se cuentan las etiquetas, se avisa,
            # y el cotejo contra el padrón es el paso siguiente.
            "unidades": {"nombre": "provincia o comarca", "etiquetas_distintas": len(areas),
                         "cuantas": None,
                         "hay_que_cotejar_los_nombres": True} if areas else None}


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
    serie, tasas, regiones = [], {}, set()
    with zipfile.ZipFile(io.BytesIO(pedir(enlaces[0]))) as z:
        internos = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not internos:
            raise RuntimeError("el ZIP de Perú no trae ningún CSV")
        for interno in internos:
            texto = z.read(interno).decode("utf-8-sig", "replace")
            propia, sus_tasas, sus_regiones = [], {}, set()
            for f in csv.DictReader(io.StringIO(texto)):
                if f.get("INDICADOR") != PERU_INDICADOR or f.get("FUENTE") != PERU_FUENTE:
                    continue
                # De paso, sin descargar nada más: el mismo archivo trae el ámbito
                # regional. Es lo que el censo subnacional necesita para medir el
                # umbral con lo que hay y no con dos fuentes internacionales.
                if f.get("AMBITO") == "1" and f.get("UBIGEO_DASH"):
                    sus_regiones.add(f["UBIGEO_DASH"])
                if f.get("AMBITO") != PERU_AMBITO_NACIONAL:
                    continue
                anio = int(f["ANIO"])
                tasa = round(numero(f["VALORES_2"]), 2)
                propia.append({"anio": anio, "valor": int(float(f["VALORES"])), "tasa": tasa})
                sus_tasas[anio] = tasa
            if propia and (not serie or max(x["anio"] for x in propia) > max(x["anio"] for x in serie)):
                serie, tasas, regiones = propia, sus_tasas, sus_regiones
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
            "enlace": PERU_FICHA, "licencia": "ODC-BY", "cadencia": "anual",
            "unidad_tasa": "por cada 100.000 habitantes",
            "quien_calcula_la_tasa": "el propio tablero del Ministerio del Interior",
            "unidades": {"nombre": "región", "cuantas": len(regiones)} if regiones else None}


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
    # Las provincias son las filas con etiqueta entre la cabecera y «Total Nacional»:
    # el conteo sale de la misma planilla, sin pedir nada más.
    provincias = set()
    for numero_fila in sorted(filas):
        if numero_fila <= cabeza:
            continue
        if filas[numero_fila] is total:
            break
        for v in filas[numero_fila].values():
            if isinstance(v, str) and len(v.strip()) > 2 and not v.strip().lower().startswith(
                    ("total", "fuente", "nota", "elabor", "número", "numero")):
                provincias.add(v.strip())
                break
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
            "cadencia": "mensual",
            "unidades": {"nombre": "provincia", "cuantas": len(provincias)} if provincias else None}


# ── MÉXICO ──────────────────────────────────────────────────────────────────
#
# El Secretariado Ejecutivo del Sistema Nacional de Seguridad Pública publica las
# víctimas de homicidio doloso por entidad y por mes. El registro lo daba por
# inaccesible: la página devolvía 403 y los archivos viven en un repositorio de
# Microsoft que responde con una página de redirección en vez del archivo. Las dos
# cosas tenían arreglo y ninguna era un bloqueo real:
#   · la página responde apenas uno se presenta con las cabeceras completas;
#   · el archivo se baja por la puerta «download.aspx?share=», que es la que usa
#     el propio botón de descarga.
#
# DOS METODOLOGÍAS, DOS ARCHIVOS. En 2026 México estrenó el Registro Nacional de
# Incidencia Delictiva y su propio ministerio advierte que no se compara con la
# serie anterior. Por eso la serie llega hasta 2025 con el archivo viejo y el año
# en curso sale del nuevo, declarado aparte. Pegarlos sería fabricar una caída.
MEXICO_FICHA = "https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva"
MEXICO_DESCARGA = ("https://sspcgob-my.sharepoint.com/personal/cni_sspc_gob_mx/"
                   "_layouts/15/download.aspx?share={id}")
MESES_MX = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
            "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _victimas_mexico(identificador: str) -> tuple:
    """Devuelve (víctimas de homicidio doloso por año, último mes con actividad)."""
    import zipfile

    with zipfile.ZipFile(io.BytesIO(pedir(MEXICO_DESCARGA.format(id=identificador)))) as z:
        interno = next((n for n in z.namelist() if n.lower().endswith(".csv")), None)
        if not interno:
            raise RuntimeError("el archivo de México no trae planilla de texto")
        crudo = z.read(interno)
    texto = None
    for codigo in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = crudo.decode(codigo)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        raise RuntimeError("no se pudo leer la planilla de México")
    por_anio, ultimo_mes, entidades = {}, {}, set()
    for f in csv.DictReader(io.StringIO(texto)):
        try:
            anio = int(f["Año"])
        except (KeyError, TypeError, ValueError):
            continue
        if (f.get("Entidad") or "").strip():
            entidades.add(f["Entidad"].strip())
        homicidio = (f.get("Subtipo de delito") or "").strip().lower() == "homicidio doloso"
        for n, mes in enumerate(MESES_MX, start=1):
            try:
                cantidad = int(float(f.get(mes) or 0))
            except ValueError:
                continue
            # EL ÚLTIMO MES SE MIDE CON TODOS LOS DELITOS, no con los homicidios:
            # un mes sin homicidios en una entidad no quiere decir que el mes no
            # esté cargado, y México tiene delitos todos los meses en todo el país.
            if cantidad > 0:
                ultimo_mes[anio] = max(ultimo_mes.get(anio, 0), n)
            if homicidio:
                por_anio[anio] = por_anio.get(anio, 0) + cantidad
    if not por_anio:
        raise RuntimeError("la planilla de México ya no trae «Homicidio doloso»")
    return por_anio, ultimo_mes, entidades


def mexico() -> dict:
    import html as _html
    import re

    pagina = pedir(MEXICO_FICHA).decode("utf-8", "replace")
    enlaces = []
    for href, cuerpo in re.findall(r'<a[^>]*href="([^"]*sharepoint[^"]*)"[^>]*>(.*?)</a>', pagina, re.S):
        rotulo = _html.unescape(re.sub(r"<[^>]+>", " ", cuerpo)).replace("\xa0", " ")
        rotulo = " ".join(rotulo.split())
        identificador = re.search(r"/([A-Za-z0-9_\-]{30,})(?:\?|$)", href.split("?")[0] + "?")
        if identificador:
            enlaces.append((rotulo, identificador.group(1)))
    if not enlaces:
        raise RuntimeError("la página del Secretariado de México ya no ofrece archivos")

    def elegir(patron):
        for rotulo, ident in enlaces:
            bajo = rotulo.lower()
            if "tablero" in bajo or "municipal" in bajo or "federal -" in bajo:
                continue
            if "víctimas" not in bajo or "estatal" not in bajo:
                continue
            if re.search(patron, bajo):
                return rotulo, ident
        return None, None

    rot_serie, id_serie = elegir(r"^\s*\d{4}\s*-\s*\d{4}\b")
    rot_curso, id_curso = elegir(r"^\s*\w+\s*-\s*\w+\s+\d{4}\b")
    if not id_serie:
        raise RuntimeError("no se encontró la planilla histórica de víctimas por entidad de México")
    por_anio, _, entidades = _victimas_mexico(id_serie)
    en_curso, aviso = None, None
    if id_curso:
        curso, meses, _ = _victimas_mexico(id_curso)
        anio = max(curso)
        if meses.get(anio) and meses[anio] < 12:
            en_curso = {"anio": anio, "hasta_mes": meses[anio], "valor": curso[anio]}
            aviso = ("El año en curso sale del Registro Nacional de Incidencia Delictiva, que estrenó "
                     "otra metodología en 2026: el propio Secretariado advierte que no se compara con "
                     "la serie anterior, y por eso va aparte y no se pega a la serie")
    serie = [{"anio": a, "valor": v} for a, v in sorted(por_anio.items())]
    return {"serie": serie, "en_curso": en_curso, "nota": aviso,
            "definicion": "víctimas de homicidio doloso en las carpetas de investigación abiertas por "
                          "las fiscalías de los estados (fuero común)",
            "organismo": "Secretariado Ejecutivo del Sistema Nacional de Seguridad Pública — "
                         "incidencia delictiva estatal",
            "enlace": MEXICO_FICHA,
            "licencia": "Términos de libre uso de la información de gob.mx",
            "cadencia": "mensual",
            "unidades": {"nombre": "entidad federativa", "cuantas": len(entidades)}
                        if entidades else None}


PAISES = {"ARG": argentina, "COL": colombia, "TTO": trinidad, "PAN": panama, "PER": peru,
          "ECU": ecuador, "MEX": mexico}


def ficha(dato: dict) -> dict:
    serie = dato["serie"]
    ultimo = serie[-1]
    anterior = serie[-2] if len(serie) > 1 else None
    f = {"valor": ultimo["valor"], "anio": ultimo["anio"],
         "tasa": ultimo.get("tasa"),
         "tasa_anterior": anterior.get("tasa") if anterior else None,
         "unidad_tasa": dato.get("unidad_tasa"),
         "quien_calcula_la_tasa": dato.get("quien_calcula_la_tasa"),
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
                # «unidades» viaja con la ficha: es lo que el censo subnacional necesita
                # para medir el umbral con lo que de verdad hay. Se mide de paso, con el
                # archivo ya abierto, y no se publica ninguna cifra por unidad: la capa
                # sigue apagada. Esto dice cuán lejos está de poder encenderse.
                r["fuente_nacional"] = {k: dato.get(k) for k in
                                        ("organismo", "enlace", "licencia", "cadencia", "definicion",
                                         "actualizado_por_la_fuente", "unidades")}
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
            "Se comprobó el 15/9/2026, portal por portal: Chile y Ecuador rechazan al recolector en el "
            "portal donde está el dato, y el tablero chileno no abre ni con un navegador de verdad; "
            "Brasil esconde el archivo detrás de una página que no lo enseña; República Dominicana "
            "publica robos y feminicidios, pero no la serie de homicidios; Costa Rica tenía todo el "
            "dominio del Poder Judicial caído; Uruguay "
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
