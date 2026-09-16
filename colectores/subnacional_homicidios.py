# -*- coding: utf-8 -*-
"""Homicidios por unidad de primer orden — la columna vertebral de la capa subnacional.

QUÉ ES ESTO
-----------
No es un colector publicado en el mapa de los 33: es el DATO SUBNACIONAL crudo, por
provincia, departamento, región o entidad, para los Estados cuya fuente nacional lo
publica y se lee sola. Alimenta el prototipo de la capa de territorio de primer
orden, que la dirección todavía tiene que aprobar antes de encenderla.

DE DÓNDE SALE CADA UNO (las mismas fuentes que ya trae `estado_reciente`)
------------------------------------------------------------------------
  · Argentina — SNIC, planilla por provincia (24).
  · Colombia — Ministerio de Defensa (datos.gov.co), por departamento (33).
  · Ecuador — INEC, tabulado de Justicia y Crimen, por provincia (24).
  · México — Secretariado Ejecutivo (SESNSP), por entidad federativa (32).
  · Perú — indicador 30 del CEIC, ámbito regional (26).

REGLAS DE LA CASA QUE SE MANTIENEN
----------------------------------
  · Es RECUENTO de víctimas, no tasa: sin población por unidad no se calcula tasa,
    y por debajo del umbral de casos se muestra el recuento, nunca la tasa.
  · El año en curso va marcado como provisional y aparte del último año cerrado.
  · No se compara entre países: cada Estado define y registra a su manera.
  · Los nombres de unidad se dejan como los publica cada fuente; el cotejo contra
    un padrón geográfico es el paso siguiente, y se declara pendiente.
"""
from __future__ import annotations

import collections
import csv
import io
import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import comun
import estado_reciente as er
import geo

COLECTOR = "subnacional_homicidios"
CAPA = "publico"


def _ultimo_y_curso(por_unidad: dict) -> tuple:
    """Último año COMPLETO común y, aparte, el año en curso si lo hay."""
    anios = sorted({a for serie in por_unidad.values() for a in serie})
    if not anios:
        return None, None
    return anios[-1], None


# ── ARGENTINA ────────────────────────────────────────────────────────────────
def argentina() -> dict:
    filas = list(csv.reader(io.StringIO(er.pedir(er.SNIC_PROVINCIAS).decode("utf-8-sig", "replace")),
                            delimiter=";"))
    cab = [c.strip('"') for c in filas[0]]
    i = {c: n for n, c in enumerate(cab)}
    por = collections.defaultdict(dict)
    for f in filas[1:]:
        if len(f) < len(cab) or f[i["codigo_delito_snic_nombre"]].strip('"') != "Homicidios dolosos":
            continue
        por[f[i["provincia_nombre"]].strip('"')][int(f[i["anio"]])] = int(float(f[i["cantidad_victimas"]]))
    return {"unidad": "provincia", "por_unidad": dict(por), "en_curso": None,
            "organismo": "Ministerio de Seguridad — SNIC", "licencia": "CC BY 4.0"}


# ── COLOMBIA ─────────────────────────────────────────────────────────────────
def colombia() -> dict:
    q = urllib.parse.quote("departamento, date_extract_y(fecha_hecho) as anio, sum(cantidad) as t")
    filas = json.loads(er.pedir(f"{er.COLOMBIA}?$select={q}&$group=departamento,anio&$limit=5000"))
    por = collections.defaultdict(dict)
    for r in filas:
        if r.get("departamento") and r.get("anio"):
            por[r["departamento"].strip()][int(r["anio"])] = int(float(r["t"]))
    # El último año de Colombia suele estar en curso (mensual). Se separa.
    anios = sorted({a for s in por.values() for a in s})
    curso = None
    if anios:
        ultimo = anios[-1]
        # Se considera en curso si la fuente lo actualiza este año calendario.
        este = datetime.now(timezone.utc).year
        if ultimo == este:
            curso = {"anio": ultimo,
                     "por_unidad": {u: s.pop(ultimo) for u, s in por.items() if ultimo in s}}
    return {"unidad": "departamento", "por_unidad": {u: s for u, s in por.items() if s},
            "en_curso": curso, "organismo": "Ministerio de Defensa — Policía Nacional",
            "licencia": "CC BY-SA 4.0"}


# ── ECUADOR ──────────────────────────────────────────────────────────────────
def ecuador() -> dict:
    import re
    import zipfile

    pagina = er.pedir(er.ECUADOR_FICHA).decode("utf-8", "replace")
    enlaces = re.findall(r'href=["\']([^"\']*justicia_crimen[^"\']*Cifras_Seguridad\.zip)["\']', pagina)
    if not enlaces:
        raise RuntimeError("Ecuador: no se halló el tabulado")
    with zipfile.ZipFile(io.BytesIO(er.pedir(enlaces[-1]))) as z:
        interno = next(n for n in z.namelist() if n.lower().endswith(".xlsx"))
        filas = er._planilla(z.read(interno), "homicidios_prov")
    import datetime as _dt
    origen = _dt.date(1899, 12, 30)
    cabeza, cols = None, {}
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
            cabeza, cols = numero, posibles
            break
    if cabeza is None:
        raise RuntimeError("Ecuador: cambió la forma de la hoja")
    por = collections.defaultdict(dict)
    for numero in sorted(filas):
        if numero <= cabeza:
            continue
        etiqueta = None
        for col in sorted(filas[numero]):
            v = filas[numero][col]
            if isinstance(v, str) and len(v.strip()) > 2:
                etiqueta = v.strip()
                break
        if not etiqueta or etiqueta.lower().startswith(("total", "fuente", "nota", "elabor", "número", "numero")):
            continue
        for col, fecha in cols.items():
            try:
                n = int(float(filas[numero].get(col)))
            except (TypeError, ValueError):
                continue
            por[etiqueta][fecha.year] = por[etiqueta].get(fecha.year, 0) + n
    # El año en curso: el que no tiene 12 meses. Se detecta con «Total Nacional».
    return {"unidad": "provincia", "por_unidad": dict(por), "en_curso": None,
            "organismo": "INEC — Justicia y Crimen (Fiscalía y Ministerio del Interior)",
            "licencia": "estadística oficial publicada"}


# ── PERÚ ─────────────────────────────────────────────────────────────────────
def peru() -> dict:
    import re
    import zipfile

    pagina = er.pedir(er.PERU_FICHA).decode("utf-8", "replace")
    enlaces = re.findall(r'href="([^"]*DataSet_Ind_Plan_Acc_Segu_Ciud[^"]*\.zip)"', pagina)
    if not enlaces:
        raise RuntimeError("Perú: no se halló el ZIP")
    por = collections.defaultdict(dict)
    with zipfile.ZipFile(io.BytesIO(er.pedir(enlaces[0]))) as z:
        interno = max((n for n in z.namelist() if n.lower().endswith(".csv")),
                      key=lambda n: z.getinfo(n).file_size)
        texto = z.read(interno).decode("utf-8-sig", "replace")
    for f in csv.DictReader(io.StringIO(texto)):
        if f.get("INDICADOR") != er.PERU_INDICADOR or f.get("FUENTE") != er.PERU_FUENTE:
            continue
        if f.get("AMBITO") != "1":  # ámbito 1 = región
            continue
        ubigeo = (f.get("UBIGEO_DASH") or "").strip()
        if not ubigeo:
            continue
        por[ubigeo][int(f["ANIO"])] = int(float(f["VALORES"]))
    return {"unidad": "región (código ubigeo)", "por_unidad": dict(por), "en_curso": None,
            "organismo": "Ministerio del Interior — indicador 30 (CEIC)", "licencia": "ODC-BY",
            "nota": "Las regiones vienen por código ubigeo; el nombre se resuelve en el cotejo."}


# ── MÉXICO ───────────────────────────────────────────────────────────────────
def mexico() -> dict:
    import html as _html
    import re
    import zipfile

    pagina = er.pedir(er.MEXICO_FICHA).decode("utf-8", "replace")
    enlaces = []
    for href, cuerpo in re.findall(r'<a[^>]*href="([^"]*sharepoint[^"]*)"[^>]*>(.*?)</a>', pagina, re.S):
        rot = " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", cuerpo)).replace("\xa0", " ").split())
        m = re.search(r"/([A-Za-z0-9_\-]{30,})(?:\?|$)", href.split("?")[0] + "?")
        if m:
            enlaces.append((rot.lower(), m.group(1)))
    ident = next((i for r, i in enlaces if r.startswith(("2015",)) and "víctimas" in r
                  and "estatal" in r and "tablero" not in r), None)
    if not ident:
        raise RuntimeError("México: no se encontró la planilla estatal de víctimas")
    with zipfile.ZipFile(io.BytesIO(er.pedir(er.MEXICO_DESCARGA.format(id=ident)))) as z:
        crudo = z.read(next(n for n in z.namelist() if n.lower().endswith(".csv")))
    texto = None
    for c in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = crudo.decode(c)
            break
        except UnicodeDecodeError:
            continue
    por = collections.defaultdict(dict)
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
             "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    for f in csv.DictReader(io.StringIO(texto)):
        if (f.get("Subtipo de delito") or "").strip().lower() != "homicidio doloso":
            continue
        ent = (f.get("Entidad") or "").strip()
        try:
            anio = int(f["Año"])
        except (KeyError, ValueError):
            continue
        total = 0
        for m in meses:
            try:
                total += int(float(f.get(m) or 0))
            except ValueError:
                pass
        if ent:
            por[ent][anio] = por[ent].get(anio, 0) + total
    return {"unidad": "entidad federativa", "por_unidad": dict(por), "en_curso": None,
            "organismo": "Secretariado Ejecutivo (SESNSP)", "licencia": "libre uso gob.mx",
            "nota": "La serie llega a 2025 con la metodología anterior; 2026 estrenó otra."}


# ── BOLIVIA ──────────────────────────────────────────────────────────────────
BOLIVIA_URL = "https://nube.ine.gob.bo/index.php/s/rb85ZWi9fyUJFHl/download"
_DEPTOS_BOL = {"chuquisaca", "la paz", "cochabamba", "oruro", "potosi",
               "tarija", "santa cruz", "beni", "pando"}


def _sin_acentos(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower().strip()


def _decodificar(raw: bytes) -> str:
    """Texto de un CSV que puede venir en UTF-8 o en CP1252 (gobierno de Panamá)."""
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            t = raw.decode(enc)
            if "�" not in t:
                return t
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1", "replace")


def bolivia() -> dict:
    """Denuncias de homicidio por departamento (INE Bolivia, datos de la Policía)."""
    import re as _re
    raw = comun.traer_crudo(BOLIVIA_URL)
    filas = er._planilla(raw, "3.08.02.13")
    col_anio = {}
    for num in sorted(filas):
        for c, v in filas[num].items():
            m = _re.match(r"(20\d\d)", str(v).strip())  # tolera «2024(p)» provisional
            if m:
                col_anio[c] = int(m.group(1))
        if col_anio:
            break
    por = collections.defaultdict(dict)
    dept = None
    for num in sorted(filas):
        b = filas[num].get("B")
        if not isinstance(b, str):
            continue
        clave = _sin_acentos(b)
        if clave in _DEPTOS_BOL:
            dept = b.strip()
            continue
        if dept and clave.startswith("homicidio"):
            for c, anio in col_anio.items():
                try:
                    por[dept][anio] = int(float(filas[num].get(c)))
                except (TypeError, ValueError):
                    continue
            dept = None  # una sola fila de homicidio por bloque
    return {"unidad": "departamento", "por_unidad": dict(por), "en_curso": None,
            "organismo": "INE Bolivia — denuncias registradas por la Policía Boliviana",
            "licencia": "estadística oficial publicada",
            "nota": "Es RECUENTO DE DENUNCIAS de homicidio, no de víctimas ni de hechos; "
                    "un mismo hecho puede generar más de una denuncia. Serie 2007 en adelante."}


# ── URUGUAY ──────────────────────────────────────────────────────────────────
URUGUAY_CSV = ("https://catalogodatos.gub.uy/dataset/999f2edc-5ef5-4d41-bed7-824a5635ea8d/"
               "resource/5ed98add-f127-4377-b529-aa8ad35b77e3/download/"
               "homicidios_dolosos_consumados.csv")


def uruguay() -> dict:
    """Homicidios dolosos consumados por departamento (Ministerio del Interior).

    El recurso es microdato: una fila por víctima. Se cuenta por departamento y año.
    """
    raw = comun.traer_crudo(URUGUAY_CSV)
    txt = raw.decode("utf-8-sig", "replace")
    cabecera = txt.splitlines()[0] if txt else ""
    delim = ";" if cabecera.count(";") > cabecera.count(",") else ","
    lector = csv.DictReader(io.StringIO(txt), delimiter=delim)
    # Ubicar las columnas de departamento y año tolerando acentos y mayúsculas.
    mapa = {_sin_acentos(c): c for c in (lector.fieldnames or [])}
    col_dep = mapa.get("departamento")
    col_anio = next((mapa[k] for k in mapa if k in ("ano", "anio", "year")), None)
    if not col_dep or not col_anio:
        raise RuntimeError(f"Uruguay: no se hallaron columnas dep/año en {lector.fieldnames}")
    por = collections.defaultdict(lambda: collections.defaultdict(int))
    for fila in lector:
        dep = (fila.get(col_dep) or "").strip()
        try:
            anio = int(str(fila.get(col_anio)).strip()[:4])
        except (TypeError, ValueError):
            continue
        if dep:
            por[dep][anio] += 1
    por = {d: dict(s) for d, s in por.items()}
    # El último año suele ser el corriente (parcial): se separa.
    anios = sorted({a for s in por.values() for a in s})
    curso = None
    if anios:
        este = datetime.now(timezone.utc).year
        if anios[-1] == este:
            u = anios[-1]
            curso = {"anio": u, "por_unidad": {d: s.pop(u) for d, s in por.items() if u in s}}
    return {"unidad": "departamento", "por_unidad": {d: s for d, s in por.items() if s},
            "en_curso": curso,
            "organismo": "Ministerio del Interior — Observatorio Nacional sobre Violencia y Criminalidad",
            "licencia": "Catálogo Nacional de Datos Abiertos (datos abiertos del Uruguay)",
            "nota": "Recuento de VÍCTIMAS de homicidio doloso consumado, agregado del microdato "
                    "oficial por departamento."}


# ── TRINIDAD Y TOBAGO ────────────────────────────────────────────────────────
TTPS_CSV = "https://ttps.gov.tt/statistics/download/?year={anio}"


def trinidad() -> dict:
    """Homicidios (murders) por división policial (Trinidad and Tobago Police Service)."""
    por = collections.defaultdict(dict)
    este = datetime.now(timezone.utc).year
    curso_anio, curso = None, None
    for anio in range(2018, este + 1):
        try:
            raw = comun.traer_crudo(TTPS_CSV.format(anio=anio))
        except Exception:  # noqa: BLE001 — un año que falta no voltea al resto
            continue
        lineas = raw.decode("utf-8-sig", "replace").splitlines()
        # El CSV arranca con dos líneas de título; el encabezado real empieza en «Year,».
        cab = next((i for i, l in enumerate(lineas) if l.lower().startswith("year,")), None)
        if cab is None:
            continue
        txt = "\n".join(lineas[cab:])
        acum = collections.defaultdict(int)
        hubo = False
        for fila in csv.DictReader(io.StringIO(txt)):
            m = {_sin_acentos(k): k for k in fila if k}
            delito = (fila.get(m.get("offence", "")) or "").strip().lower()
            division = (fila.get(m.get("division", "")) or "").strip()
            rep = fila.get(m.get("reported", "")) or fila.get(m.get("count", "")) or "0"
            if "murder" in delito and division:
                try:
                    acum[division] += int(float(str(rep).strip() or 0))
                    hubo = True
                except ValueError:
                    continue
        if not hubo:
            continue
        for div, n in acum.items():
            por[div][anio] = n
    por = {d: s for d, s in por.items() if s}
    if por:
        anios = sorted({a for s in por.values() for a in s})
        if anios and anios[-1] == este:
            u = anios[-1]
            curso = {"anio": u, "por_unidad": {d: s.pop(u) for d, s in por.items() if u in s}}
            por = {d: s for d, s in por.items() if s}
    return {"unidad": "división policial", "por_unidad": por, "en_curso": curso,
            "organismo": "Trinidad and Tobago Police Service (TTPS) — Crime and Problem Analysis",
            "licencia": "datos públicos del TTPS",
            "nota": "Recuento de homicidios (murders) por DIVISIÓN POLICIAL —no por corporación "
                    "regional—, que es la geografía con que la policía publica. Serie desde 2018."}


# ── PANAMÁ ───────────────────────────────────────────────────────────────────
PANAMA_API = ("https://www.datosabiertos.gob.pa/api/3/action/package_search"
              "?q=v%C3%ADctimas+de+homicidio&rows=40")


def panama() -> dict:
    """Homicidios por provincia (Procuraduría General de la Nación, PGN).

    Un dataset por año en el portal de datos abiertos; cada CSV es microdato
    (una fila por víctima). Se cuenta por área geográfica (provincia) y año.
    """
    d = json.loads(er.pedir(PANAMA_API).decode("utf-8", "replace"))
    urls = []
    for p in (d.get("result") or {}).get("results") or []:
        if "homicidio" not in (p.get("title") or "").lower():
            continue
        for r in p.get("resources") or []:
            if (r.get("format") or "").upper() == "CSV" and r.get("url"):
                urls.append(r["url"])
    if not urls:
        raise RuntimeError("Panamá: el portal no devolvió CSV de homicidios")
    import re as _re
    por = collections.defaultdict(lambda: collections.defaultdict(int))
    display = {}  # clave sin acentos -> nombre lindo de la provincia
    for url in urls:
        # El año sale del NOMBRE DE ARCHIVO (cada CSV es un año); se toma el último
        # 20XX del basename para no confundirlo con números del UUID de la ruta.
        anios_url = _re.findall(r"20\d\d", url.rsplit("/", 1)[-1])
        if not anios_url:
            continue
        anio = int(anios_url[-1])
        try:
            txt = _decodificar(er.pedir(url))
        except Exception:  # noqa: BLE001 — un año que falla no voltea al resto
            continue
        head = txt.splitlines()[0] if txt else ""
        delim = ";" if head.count(";") > head.count(",") else ","
        lector = csv.DictReader(io.StringIO(txt), delimiter=delim)
        mapa = {_sin_acentos(c): c for c in (lector.fieldnames or []) if c}
        col_area = next((mapa[k] for k in mapa if "area geograf" in k or k == "provincia"), None)
        if not col_area:
            continue
        for fila in lector:
            prov = (fila.get(col_area) or "").strip()
            if not prov or prov.isdigit():
                continue
            clave = _sin_acentos(prov)  # une «Panamá»/«Panama», «Colón»/«Colon»
            por[clave][anio] += 1
            # se conserva la grafía con más acentos (la más correcta)
            if clave not in display or sum(c > "~" for c in prov) > sum(c > "~" for c in display[clave]):
                display[clave] = prov
    por = {display.get(k, k): dict(s) for k, s in por.items()}
    por = {p: dict(s) for p, s in por.items() if s}
    curso = None
    anios = sorted({a for s in por.values() for a in s})
    if anios:
        este = datetime.now(timezone.utc).year
        if anios[-1] == este:
            u = anios[-1]
            curso = {"anio": u, "por_unidad": {p: s.pop(u) for p, s in por.items() if u in s}}
            por = {p: s for p, s in por.items() if s}
    return {"unidad": "provincia", "por_unidad": por, "en_curso": curso,
            "organismo": "Procuraduría General de la Nación (PGN) — Panamá",
            "licencia": "Portal Nacional de Datos Abiertos de Panamá",
            "nota": "Recuento de VÍCTIMAS de homicidio, agregado del microdato oficial por "
                    "provincia (incluye la comarca donde la fuente la registra)."}


# ── BRASIL ───────────────────────────────────────────────────────────────────
BRASIL_XLSX = ("https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/"
               "estatistica/download/dnsp-base-de-dados/bancovde-{anio}.xlsx/@@download/file")


def _brasil_un_anio(raw: bytes) -> dict:
    """{UF: víctimas de homicídio doloso} de un archivo BancoVDE anual."""
    import re
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(raw))
    data = z.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace")

    def valor(celda: str) -> str:
        v = re.search(r"<v>(.*?)</v>", celda, re.S)
        if v:
            return v.group(1)
        t = re.search(r"<t[^>]*>(.*?)</t>", celda, re.S)
        return t.group(1) if t else ""

    colmap, por = {}, {}
    for fila in re.finditer(r"<row[^>]*>(.*?)</row>", data, re.S):
        celdas = re.findall(r'(<c\b[^>]*\br="[A-Z]+\d+".*?(?:/>|</c>))', fila.group(1), re.S)
        d = {}
        for c in celdas:
            ref = re.search(r'\br="([A-Z]+)\d+"', c)
            if ref:
                d[ref.group(1)] = valor(c)
        if not colmap:  # primera fila = encabezado
            colmap = {v.strip().lower(): k for k, v in d.items()}
            continue
        if d.get(colmap.get("evento", "")) == "Homicídio doloso":
            uf = d.get(colmap.get("uf", ""), "")
            try:
                por[uf] = por.get(uf, 0) + int(float(d.get(colmap.get("total_vitima", ""), "0")))
            except (TypeError, ValueError):
                pass
    return por


def brasil() -> dict:
    """Homicídios dolosos por unidade federativa (SINESP/MJSP — BancoVDE)."""
    este = datetime.now(timezone.utc).year
    por = collections.defaultdict(dict)
    logrados = []
    for anio in (este, este - 1, este - 2):
        if len(logrados) >= 2:
            break
        try:
            datos = _brasil_un_anio(comun.traer_crudo(BRASIL_XLSX.format(anio=anio)))
        except Exception:  # noqa: BLE001 — un año que falta no voltea al resto
            continue
        if datos:
            for uf, n in datos.items():
                por[uf][anio] = n
            logrados.append(anio)
    por = {u: s for u, s in por.items() if s}
    curso = None
    if logrados and max(logrados) == este:
        u = este
        curso = {"anio": u, "por_unidad": {uf: s.pop(u) for uf, s in por.items() if u in s}}
        por = {uf: s for uf, s in por.items() if s}
    return {"unidad": "unidade federativa (UF)", "por_unidad": por, "en_curso": curso,
            "organismo": "Ministério da Justiça e Segurança Pública (MJSP/SENASP) — Sinesp VDE",
            "licencia": "dados abertos do governo federal do Brasil",
            "nota": "Recuento de VÍCTIMAS de homicídio doloso, sumado del microdato municipal a la "
                    "unidade federativa. La UF va por su sigla (AC, BA, RJ…); el nombre se cruza "
                    "después. El año en curso es provisional."}


PAISES = {"ARG": argentina, "COL": colombia, "ECU": ecuador, "PER": peru,
          "MEX": mexico, "BOL": bolivia, "URY": uruguay, "TTO": trinidad,
          "PAN": panama, "BRA": brasil}


def construir() -> Path:
    nombres = {p["iso"]: p["pais"] for p in geo.padron()}
    bloques = {p["iso"]: p.get("bloque") for p in geo.padron()}
    estados, caidas = [], []
    for iso, lector in PAISES.items():
        try:
            dato = lector()
            por = dato["por_unidad"]
            if not por:
                caidas.append(f"{nombres.get(iso, iso)}: sin unidades")
                continue
            ultimo, _ = _ultimo_y_curso(por)
            unidades = []
            for u, serie in sorted(por.items()):
                unidades.append({
                    "nombre": u,
                    "ultimo": {"anio": ultimo, "valor": serie.get(ultimo)} if ultimo in serie else None,
                    "serie": [{"anio": a, "valor": v} for a, v in sorted(serie.items())],
                })
            estados.append({
                "iso": iso, "pais": nombres.get(iso, iso), "bloque": bloques.get(iso),
                "nombre_unidad": dato["unidad"], "cuantas": len(unidades),
                "organismo": dato["organismo"], "licencia": dato["licencia"],
                "nota": dato.get("nota"),
                "en_curso": dato.get("en_curso"),
                "unidades": unidades,
            })
        except Exception as e:  # noqa: BLE001 — la caída se declara, no rompe a los demás
            caidas.append(f"{nombres.get(iso, iso)}: {type(e).__name__}: {str(e)[:100]}")

    if not estados:
        raise RuntimeError("Ningún Estado devolvió desglose por unidad: " + " | ".join(caidas))

    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="Homicidios por unidad de primer orden, de la fuente nacional de cada Estado "
               "(Argentina SNIC, Colombia MinDefensa, Ecuador INEC, Perú CEIC, México SESNSP)",
        url_fuente="https://www.argentina.gob.ar/seguridad/estadisticascriminales/bases-de-datos",
        calificacion=comun.calificar(
            "A", 2, False,
            "Registro administrativo oficial de cada Estado, desagregado por su unidad de primer "
            "orden. Credibilidad 2: cada Estado define y registra a su manera, y el nombre de la "
            "unidad todavía no se cotejó contra un padrón geográfico común."),
        registros=estados,
        vacios=[
            "ES RECUENTO POR UNIDAD, NO TASA: sin la población de cada provincia o departamento no "
            "se calcula tasa. Comparar recuentos entre unidades de tamaño muy distinto engaña.",
            "NO SON LOS 33 NI TODAS LAS UNIDADES: solo los Estados cuya fuente publica el desglose y "
            "se lee sola. Falta el resto de la región, y el cotejo de nombres contra un padrón.",
            "NO SE COMPARA ENTRE PAÍSES: cada Estado define el homicidio a su manera.",
        ] + ([f"No se pudo desagregar: {' | '.join(caidas)}."] if caidas else []),
        extra={"resumen": {"estados_con_desglose": len(estados),
                           "unidades_totales": sum(e["cuantas"] for e in estados),
                           "es_prototipo": True,
                           "capa_subnacional": "APAGADA — este dato alimenta el prototipo, no el mapa",
                           "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
