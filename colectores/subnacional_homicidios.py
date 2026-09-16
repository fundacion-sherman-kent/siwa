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


PAISES = {"ARG": argentina, "COL": colombia, "ECU": ecuador, "PER": peru, "MEX": mexico}


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
