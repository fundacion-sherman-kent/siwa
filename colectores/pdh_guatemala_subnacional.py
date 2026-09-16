# -*- coding: utf-8 -*-
"""Guatemala — denuncias de derechos humanos por departamento (PDH). PROTOTIPO.

POR QUÉ EXISTE
--------------
La Procuraduría de los Derechos Humanos de Guatemala (PDH) publica cuántas
denuncias recibe, y las muestra por departamento en un panel. El sitio de la PDH
bloquea el acceso automático (Cloudflare), pero el gráfico se alimenta de un dato
público alojado en la CDN de Flourish, que SÍ se alcanza desde la nube. De ahí se
recupera la serie: denuncias por departamento, mes a mes, acumuladas por año.

QUÉ ES Y QUÉ NO
---------------
Es un recuento de DENUNCIAS recibidas por la PDH —información conocida de oficio o
queja presentada—, no de violaciones comprobadas de derechos humanos. Mide la
actividad de la institución y la propensión a denunciar, tanto como el problema de
fondo. Es SUBNACIONAL (por departamento) y de un eje —gobernanza / derechos
humanos— que SIWA todavía no baja a la unidad: por eso entra como PROTOTIPO, no al
mapa, hasta que la dirección lo apruebe.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun  # noqa: E402

COLECTOR = "pdh_guatemala_subnacional"
CAPA = "publico"
VIZ = "28522578"
EMBED = f"https://flo.uri.sh/visualisation/{VIZ}/embed"


def _extraer_objeto(html: str, nombre: str):
    """Extrae `<nombre> = { ... };` inline por balance de llaves."""
    marca = nombre + " = "
    i = html.find(marca)
    if i < 0:
        raise RuntimeError(f"PDH: no se encontró {nombre} en el embed")
    j = i + len(marca)
    if html[j] not in "{[":
        raise RuntimeError(f"PDH: {nombre} no arranca en objeto")
    abre, cierra = html[j], "}" if html[j] == "{" else "]"
    prof, k, en_str, esc = 0, j, False, False
    while k < len(html):
        c = html[k]
        if en_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                en_str = False
        else:
            if c == '"':
                en_str = True
            elif c == abre:
                prof += 1
            elif c == cierra:
                prof -= 1
                if prof == 0:
                    return json.loads(html[j:k + 1])
        k += 1
    raise RuntimeError(f"PDH: no cerró {nombre}")


def _meses(etiquetas: list) -> list:
    """De ['Ene-23',...,'Dic-23','','Ene-24',...] a [(anio, mes, col_idx)] sin separadores."""
    MES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
           "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
    out = []
    for idx, e in enumerate(etiquetas):
        e = (e or "").strip().lower()
        m = re.match(r"([a-z]{3})-(\d{2})", e)
        if m and m.group(1) in MES:
            out.append((2000 + int(m.group(2)), MES[m.group(1)], idx))
    return out


def construir() -> Path:
    html = comun.traer_crudo(EMBED).decode("utf-8", "replace")
    datos = _extraer_objeto(html, "_Flourish_data")
    cols = _extraer_objeto(html, "_Flourish_data_column_names")
    etiquetas = (cols.get("data") or {}).get("values") or []
    meses = _meses(etiquetas)
    if not meses:
        raise RuntimeError("PDH: no se pudieron leer los meses")

    # Último mes de cada año (denuncias acumuladas del año) y el año en curso, provisional.
    por_anio_cols = {}
    for anio, mes, idx in meses:
        por_anio_cols.setdefault(anio, []).append((mes, idx))
    cierre_de_anio = {a: max(v)[1] for a, v in por_anio_cols.items()}   # col del último mes cargado
    ultimo_mes = {a: max(v)[0] for a, v in por_anio_cols.items()}
    anios = sorted(cierre_de_anio)
    anio_curso = anios[-1]

    filas = (datos.get("data") or [])
    unidades = []
    for f in filas:
        nombre = (f.get("label") or "").strip()
        valores = f.get("values") or []
        if not nombre:
            continue
        serie = []
        for a in anios:
            col = cierre_de_anio[a]
            if col < len(valores):
                try:
                    v = int(float(valores[col]))
                except (TypeError, ValueError):
                    continue
                serie.append({"anio": a, "valor": v,
                              "meses_cargados": ultimo_mes[a],
                              "provisional": a == anio_curso})
        if serie:
            unidades.append({"nombre": nombre,
                             "ultimo": serie[-1],
                             "serie": serie})

    if not unidades:
        raise RuntimeError("PDH: no se recuperó ninguna unidad")

    registro = {
        "iso": "GTM", "pais": "Guatemala", "bloque": "Centroamérica",
        "nombre_unidad": "departamento", "cuantas": len(unidades),
        "organismo": "Procuraduría de los Derechos Humanos (PDH)",
        "licencia": "dato público del panel institucional (recuperado de la CDN de Flourish)",
        "en_curso": {"anio": anio_curso, "meses_cargados": ultimo_mes[anio_curso]},
        "unidades": unidades,
    }

    medida = {
        "clave": "denuncias_ddhh_pdh", "eje": "Gobernanza",
        "rotulo": "Denuncias de derechos humanos por departamento (PDH)",
        "unidad": "denuncias recibidas", "unidad_singular": "denuncia",
        "mas_es_peor": None,  # más denuncias puede ser más problema o más acceso a la PDH
        "origen": "Procuraduría de los Derechos Humanos de Guatemala (PDH)",
        "cautela": ("Son DENUNCIAS recibidas por la PDH —de oficio o por queja—, no violaciones "
                    "comprobadas. Más denuncias puede reflejar más vulneración O más confianza y "
                    "acceso a la institución. El valor de cada año es ACUMULADO; el año en curso es "
                    "provisional (solo los meses ya cargados). No se compara entre países."),
    }
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="Procuraduría de los Derechos Humanos de Guatemala (PDH) — panel «PDH en cifras», "
               "denuncias por departamento",
        url_fuente="https://pdh.org.gt/",
        calificacion=comun.calificar(
            "B", 3, False,
            "Institución pública de derechos humanos. Credibilidad 3: el dato es de denuncias "
            "recibidas, no de hechos comprobados, y se recuperó de la visualización pública porque "
            "el sitio bloquea el acceso directo."),
        registros=[registro],
        vacios=[
            "SON DENUNCIAS, NO VIOLACIONES COMPROBADAS: mide actividad de la PDH y propensión a "
            "denunciar, no solo el problema de fondo.",
            "ES ACUMULADO POR AÑO y el año en curso es PROVISIONAL (solo los meses cargados).",
            "SUBNACIONAL Y PROTOTIPO: es un eje que SIWA no baja a la unidad; no va al mapa sin "
            "aprobación de la dirección.",
            "Recuperado del panel público (CDN de Flourish) porque el sitio de la PDH bloquea el "
            "acceso automático; la serie estructurada completa de la PDH sigue siendo PDF o pedido "
            "formal de información pública.",
        ],
        extra={"indicadores": [medida],
               "resumen": {"departamentos": len(unidades),
                           "anios": anios, "anio_en_curso": anio_curso,
                           "meses_del_anio_en_curso": ultimo_mes[anio_curso],
                           "es_prototipo": True,
                           "capa_subnacional": "APAGADA — alimenta el prototipo, no el mapa",
                           "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
