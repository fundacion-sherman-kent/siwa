# -*- coding: utf-8 -*-
"""Ecuador — Reservas internacionales del Banco Central (BCE), dato mensual fresco.

POR QUÉ EXISTE
--------------
El portal de datos abiertos del Ecuador bloquea el acceso desde la nube, pero el
Banco Central publica su Información Estadística Mensual (IEM) en archivos Excel
estáticos que SÍ se alcanzan. De ahí se toma la Reserva Internacional —el mismo
tipo de dato que SIWA ya trae para México desde Banxico—, actualizada cada mes.

CÓMO ENCUENTRA EL DATO
----------------------
El catálogo del IEM lista los boletines con su número en la URL (m2094 = agosto
2026). Se toma el número más alto —el boletín más nuevo— y se arma la URL del
cuadro de reservas (IEM-121), sin número fijo: así sigue andando mes a mes.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun  # noqa: E402
import estado_reciente as er  # noqa: E402

COLECTOR = "bce_ecuador"
CAPA = "publico"
CATALOGO = "https://contenido.bce.fin.ec/iem-publicaciones/"
DATOS = "https://contenido.bce.fin.ec/documentos/PublicacionesNotas/Catalogo/IEMensual/m{n}/IEM-121-e.xlsx"
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
         "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
MES_NOMBRE = {v: k for k, v in MESES.items()}


def _ultimo_boletin() -> int:
    html = comun.traer_crudo(CATALOGO).decode("utf-8", "replace")
    nums = [int(n) for n in re.findall(r"/m(\d{3,4})\d{6}\.html", html)]
    nums += [int(n) for n in re.findall(r"IEMensual/m(\d{3,4})", html)]
    if not nums:
        raise RuntimeError("BCE: no se pudo leer el número del último boletín")
    return max(nums)


def _col_a_indice(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n


def _num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def construir() -> Path:
    n = _ultimo_boletin()
    raw = comun.traer_crudo(DATOS.format(n=n))
    filas = er._planilla(raw, "IEM-121-e")

    # Fila de meses (varias celdas con abreviatura de mes) y fila de años (4 dígitos).
    fila_mes = fila_anio = None
    for num in sorted(filas):
        vals = [str(v).strip().lower()[:3] for v in filas[num].values() if isinstance(v, str)]
        if sum(1 for v in vals if v in MESES) >= 3:
            fila_mes = num
            break
    for num in sorted(filas):
        if num >= (fila_mes or 10):
            break
        if sum(1 for v in filas[num].values() if isinstance(v, (int, float)) and 1990 <= v <= 2100) >= 1 \
           or sum(1 for v in filas[num].values() if isinstance(v, str) and re.fullmatch(r"20\d\d", v.strip())) >= 1:
            fila_anio = num
    if fila_mes is None:
        raise RuntimeError("BCE: no se encontró la fila de meses en el cuadro de reservas")

    # col -> (anio, mes): se camina la fila de meses; el año arranca del primero declarado
    # y sube cada vez que el mes vuelve a enero.
    anio_ini = None
    if fila_anio is not None:
        for v in filas[fila_anio].values():
            s = str(v).strip()
            if re.fullmatch(r"20\d\d", s):
                anio_ini = int(s)
                break
    if anio_ini is None:
        from datetime import datetime, timezone
        anio_ini = datetime.now(timezone.utc).year - 1

    col_periodo = {}
    anio = anio_ini
    prev_mes = 0
    for col, v in sorted(filas[fila_mes].items(), key=lambda kv: _col_a_indice(kv[0])):
        s = str(v).strip().lower()[:3]
        if s in MESES:
            mes = MESES[s]
            if mes < prev_mes:  # volvió a un mes anterior -> nuevo año
                anio += 1
            col_periodo[col] = (anio, mes)
            prev_mes = mes

    # Fila del total de reservas
    fila_res = None
    for num in sorted(filas):
        a = filas[num].get("A")
        if isinstance(a, str) and a.strip().lower().startswith("reservas internacional"):
            fila_res = num
            break
    if fila_res is None:
        raise RuntimeError("BCE: no se encontró la fila de Reservas Internacionales")

    # Último valor numérico, por índice de columna
    ultimo = None
    for col, v in filas[fila_res].items():
        num_v = _num(v)
        if col in col_periodo and num_v is not None:
            idx = _col_a_indice(col)
            if ultimo is None or idx > ultimo[0]:
                ultimo = (idx, col, num_v)
    if ultimo is None:
        raise RuntimeError("BCE: no se pudo leer el valor de reservas")

    _, col, valor = ultimo
    anio, mes = col_periodo[col]
    registro = {
        "iso": "ECU", "pais": "Ecuador", "bloque": "Andina",
        "indicadores": {
            "reservas_bce_ecuador": {
                "valor": round(valor, 1), "anio": anio, "mes": mes,
                "unidad": "millones de USD",
                "detalle": f"{round(valor,1)} millones de USD al final de {MES_NOMBRE[mes]}. {anio}",
            }
        },
    }
    medida = {
        "clave": "reservas_bce_ecuador", "eje": "Desarrollo",
        "rotulo": "Reservas internacionales (Banco Central del Ecuador)",
        "unidad": "millones de USD", "unidad_singular": "millón de USD",
        "mas_es_peor": False,
        "origen": "Banco Central del Ecuador — Información Estadística Mensual, cuadro IEM-121",
        "cautela": ("Es el saldo de Reserva Internacional al final del mes, en millones de USD. "
                    "Mide liquidez externa del país; no es comparable como ranking entre economías "
                    "de tamaño muy distinto. Dato mensual, del último boletín publicado."),
    }
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="Banco Central del Ecuador (BCE) — Información Estadística Mensual (IEM-121, reservas)",
        url_fuente=CATALOGO,
        calificacion=comun.calificar(
            "A", 2, False,
            "Banco central, autoridad monetaria del país: fuente oficial primaria. Credibilidad 2 "
            "y no 1 porque entra con una sola fuente; con una segunda fuente (FMI/CEPAL) subiría."),
        registros=[registro],
        vacios=[
            "ES SOLO ECUADOR: este colector trae la reserva internacional del BCE, no un panel "
            "regional. Otros bancos centrales se suman por separado.",
            "ES SALDO, NO FLUJO: es el nivel de reservas al cierre del mes, no su variación.",
        ],
        extra={"indicadores": [medida],
               "resumen": {"boletin": n, "anio": anio, "mes": mes,
                           "reservas_millones_usd": round(valor, 1),
                           "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
