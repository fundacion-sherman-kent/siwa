# -*- coding: utf-8 -*-
"""Santa Fe (Argentina) — homicidios según su PROPIO observatorio. Segunda fuente.

POR QUÉ EXISTE — «la jurisdicción se consulta a sí misma»
---------------------------------------------------------
SIWA ya trae los homicidios de la provincia de Santa Fe desde la fuente NACIONAL
(SNIC). Esta provincia, además, publica su propio dato por su Observatorio de
Seguridad Pública (MPA + Ministerio de Justicia y Seguridad). Cruzar las dos —el
dato nacional y el que el propio Estado observado publica— es la regla de las dos
fuentes girada al eje vertical: si coinciden, sube la confianza; si difieren, se
muestran las dos sin promediar, y la diferencia misma es un hecho de transparencia.

CÓMO LEE EL DATO (grado 2, sin OCR)
-----------------------------------
El observatorio publica una infografía mensual en PDF. La cifra provincial
—homicidios acumulados en el año y del último mes— viene en la CAPA DE TEXTO del
PDF y se lee con `pypdf`, sin OCR. El desglose por departamento vive en la imagen
del gráfico y quedaría para OCR: es segundo orden, por debajo de lo que SIWA muestra,
así que no se persigue acá.

HONESTIDAD DEL PERÍODO
----------------------
La cifra provincial es ACUMULADA del 1 de enero al mes del informe (p. ej. «109
homicidios, enero–agosto 2026»). No es un año cerrado; se publica con su período
exacto y NO se compara a ciegas contra un año completo del SNIC. El cruce limpio se
hace sobre la cifra de diciembre (año cerrado) cuando el informe de diciembre existe.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun  # noqa: E402

COLECTOR = "subnacional_santafe"
CAPA = "publico"
OSP = "https://www.santafe.gob.ar/ms/osp/"
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def _hallar_pdf_provincial() -> str:
    """Ubica el PDF de la infografía provincial más reciente (dos saltos de WordPress)."""
    portada = comun.traer_crudo(OSP).decode("utf-8", "replace")
    # Página del informe provincial de homicidios (no Rosario ni La Capital).
    pags = re.findall(r'href="([^"]*infografia[^"]*homicidios[^"]*provincia-de-santa-fe[^"]*)"',
                      portada, re.I)
    if not pags:
        raise RuntimeError("Santa Fe: no se halló la infografía provincial en la portada del OSP")
    pagina = comun.traer_crudo(pags[0]).decode("utf-8", "replace")
    pdfs = re.findall(r'href="([^"]+\.pdf)"', pagina, re.I)
    pdfs = [u for u in pdfs if "provincia" in u.lower() or "homicid" in u.lower()] or pdfs
    if not pdfs:
        raise RuntimeError("Santa Fe: la página del informe no enlaza ningún PDF")
    return pdfs[0]


def _leer_cifras(pdf: bytes) -> dict:
    """Del texto del PDF: acumulado del año, mes del informe y homicidios del mes."""
    from pypdf import PdfReader
    import io
    texto = PdfReader(io.BytesIO(pdf)).pages[0].extract_text() or ""
    plano = re.sub(r"[ \t]+", " ", texto)
    # Mes del informe: «Reporte mensual acumulado a Agosto 2026»
    m_mes = re.search(r"acumulado a\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s+(20\d\d)", plano, re.I)
    mes = MESES.get(m_mes.group(1).lower()) if m_mes else None
    anio = int(m_mes.group(2)) if m_mes else None
    # Acumulado: la línea «Acumulado / <año> / <n>»
    m_ac = re.search(r"Acumulado\s+(20\d\d)\s+(\d{1,4})", plano)
    acumulado = int(m_ac.group(2)) if m_ac else None
    if acumulado is None:  # variante: el número puede quedar suelto tras el año del encabezado
        m_ac2 = re.search(r"\b(20\d\d)\s+(\d{2,4})\b", plano)
        if m_ac2:
            acumulado = int(m_ac2.group(2))
    # Homicidios del mes: el número grande junto al nombre del mes, arriba del todo.
    m_ult = re.search(r"^\s*([A-Za-zÁÉÍÓÚáéíóú]+)\s*\n\s*(\d{1,3})\s*\n\s*Homicidios", texto, re.I | re.M)
    del_mes = int(m_ult.group(2)) if m_ult else None
    return {"anio": anio, "mes": mes, "acumulado": acumulado, "del_mes": del_mes}


def construir() -> Path:
    url = _hallar_pdf_provincial()
    cifras = _leer_cifras(comun.traer_crudo(url))
    if cifras["acumulado"] is None or not cifras["anio"]:
        raise RuntimeError(f"Santa Fe: no se pudo leer la cifra del PDF ({url})")

    mes_nombre = next((k for k, v in MESES.items() if v == cifras["mes"]), "el mes")
    registro = {
        "iso": "ARG", "pais": "Argentina", "bloque": "Cono Sur",
        "unidad_de_primer_orden": "Santa Fe",
        "indicadores": {
            "homicidios_observatorio_provincial": {
                "valor": cifras["acumulado"], "anio": cifras["anio"],
                "hasta_mes": cifras["mes"], "del_ultimo_mes": cifras["del_mes"],
                "es_anio_cerrado": cifras["mes"] == 12,
                "detalle": (f"{cifras['acumulado']} homicidios acumulados de enero a "
                            f"{mes_nombre} de {cifras['anio']}, según el Observatorio provincial"),
            }
        },
    }
    medida = {
        "clave": "homicidios_observatorio_provincial", "eje": "Seguridad",
        "rotulo": "Homicidios según el observatorio provincial (Santa Fe)",
        "unidad": "homicidios acumulados en el año", "unidad_singular": "homicidio",
        "mas_es_peor": True,
        "origen": "Observatorio de Seguridad Pública de Santa Fe (MPA — Ministerio de Justicia y Seguridad)",
        "cautela": ("Es la cifra que la PROPIA provincia publica de sí misma, como SEGUNDA FUENTE "
                    "frente al SNIC nacional. Es un ACUMULADO de enero al mes del informe, no un año "
                    "cerrado salvo el informe de diciembre; se publica con su período y NO se compara "
                    "a ciegas contra el año completo del SNIC. Sirve para contrastar, no para "
                    "reemplazar la serie nacional."),
    }
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="Observatorio de Seguridad Pública de Santa Fe — infografía mensual de homicidios dolosos",
        url_fuente=OSP,
        calificacion=comun.calificar(
            "A", 2, False,
            "Organismo oficial de la propia provincia. Credibilidad 2: la cifra se lee de una "
            "infografía (grado 2), es un acumulado y no un año cerrado, y aún no se cotejó "
            "período a período contra el SNIC."),
        registros=[registro],
        vacios=[
            "ES UNA SEGUNDA FUENTE DE UNA SOLA UNIDAD (Santa Fe), no de toda la Argentina: contrasta "
            "el dato nacional del SNIC con el que publica la propia provincia.",
            "ES ACUMULADO, NO AÑO CERRADO (salvo diciembre): se publica con su período exacto.",
            "SOLO EL TOTAL PROVINCIAL: el desglose por departamento vive en la imagen del gráfico y "
            "necesitaría OCR; es segundo orden y no se persigue acá.",
        ],
        extra={"indicadores": [medida],
               "resumen": {"unidad": "Santa Fe", "pdf": url,
                           "acumulado": cifras["acumulado"], "anio": cifras["anio"],
                           "hasta_mes": cifras["mes"],
                           "es_segunda_fuente_vertical": True,
                           "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
