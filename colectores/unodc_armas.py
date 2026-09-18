# -*- coding: utf-8 -*-
"""Tráfico de armas de fuego — UNODC (incautaciones y detenidos).

QUÉ AGREGA
----------
El flujo ILÍCITO de armas, que SIWA no medía: el comercio (Comtrade cap. 93) y el
gasto militar (SIPRI) cubren lo legal; esto cubre lo incautado. De la base de la
Oficina de las Naciones Unidas contra la Droga y el Delito (UNODC), dos indicadores
por país y año:

  · armas_incautadas         — «Arms seized» (total de armas de fuego incautadas).
  · detenidos_trafico_armas  — personas detenidas/sospechadas por tráfico ilícito
                                de armas.

CÓMO — sin navegador, sin file-drop manual
------------------------------------------
El portal de UNODC es una app JavaScript, pero el botón «Download data» apunta a un
Excel REAL en el servidor. Se baja directo con la biblioteca estándar y se lee con
openpyxl (que el robot instala, como en SIPRI). La carpeta del archivo lleva el mes
de publicación (p. ej. 2025-11); se descubre probando los meses recientes, así el
colector toma sola la actualización cuando UNODC publica una nueva.
"""
from __future__ import annotations

import io
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

import comun
import geo

COLECTOR = "unodc_armas"
CAPA = "publico"
UA = "Mozilla/5.0 (compatible; SIWA/1.0; +https://siwa.fundacionkent.org)"
PLANTILLA = ("https://data.unodc.org/sites/dataportal.unodc.org/files/"
             "{ym}/data_iafq_firearms_trafficking.xlsx")
HOJA = "data_iafq_firearms_trafficking"

# (Indicator, Dimension, Category) -> clave y rótulo en SIWA
INDICADORES = {
    ("Arms seized", "Total", "Total"): ("armas_incautadas", "Armas de fuego incautadas"),
    ("Individuals arrested/suspected for illicit trafficking in weapons", "Total", "Total"):
        ("detenidos_trafico_armas", "Detenidos por tráfico de armas"),
}


def _url_actual() -> str:
    hoy = date.today()
    meses = []
    for k in range(0, 30):  # de este mes hacia atrás, dos años y medio
        y, m = hoy.year, hoy.month - k
        while m <= 0:
            m += 12
            y -= 1
        meses.append(f"{y:04d}-{m:02d}")
    for ym in dict.fromkeys(meses):
        url = PLANTILLA.format(ym=ym)
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    return url
        except urllib.error.HTTPError:
            continue
        except Exception:  # noqa: BLE001 — red intermitente en un candidato no voltea la búsqueda
            continue
    raise RuntimeError("UNODC: no se encontró el Excel de armas en los meses recientes")


def construir():
    import openpyxl
    padron = geo.padron()
    isos = {p["iso"] for p in padron}
    nombres = {p["iso"]: p["pais"] for p in padron}
    bloques = {p["iso"]: p.get("bloque") for p in padron}

    url = _url_actual()
    wb = openpyxl.load_workbook(io.BytesIO(comun.traer_crudo(url)), read_only=True, data_only=True)
    sh = wb[HOJA]
    filas = list(sh.iter_rows(values_only=True))
    hdr = next(r for r in filas[:5] if r and "Iso3_code" in r)
    col = {c: n for n, c in enumerate(hdr)}

    # {iso: {clave: {anio: valor}}}
    datos = {}
    for r in filas[filas.index(hdr) + 1:]:
        iso = r[col["Iso3_code"]]
        if iso not in isos:
            continue
        llave = (r[col["Indicator"]], r[col["Dimension"]], r[col["Category"]])
        cfg = INDICADORES.get(llave)
        if not cfg:
            continue
        clave = cfg[0]
        try:
            anio = int(r[col["Year"]])
            valor = float(r[col["VALUE"]])
        except (TypeError, ValueError):
            continue
        datos.setdefault(iso, {}).setdefault(clave, {})[anio] = valor

    corte = datetime.now(timezone.utc).year - 12
    registros = []
    for p in padron:
        iso = p["iso"]
        ind = {}
        for (_llave, (clave, rotulo)) in INDICADORES.items():
            serie = (datos.get(iso) or {}).get(clave) or {}
            if not serie:
                continue
            ultimo = max(serie)
            recientes = {a: round(v, 2) for a, v in serie.items() if a >= corte}
            ind[clave] = {
                "rotulo": rotulo,
                "valor": round(serie[ultimo], 2),
                "anio": ultimo,
                "unidad": "casos" if clave == "detenidos_trafico_armas" else "armas de fuego",
                "no_comparable_entre_paises": True,
                "serie": [{"anio": a, "valor": recientes[a]} for a in sorted(recientes)],
            }
        registros.append({"iso": iso, "pais": nombres[iso], "bloque": bloques.get(iso),
                          "estado": "con_dato" if ind else "sin_dato_unodc", "indicadores": ind})

    con = sum(1 for r in registros if r["indicadores"])
    indicadores = [{"clave": c, "rotulo": rot,
                    "unidad": "casos" if c == "detenidos_trafico_armas" else "armas de fuego"}
                   for (_k, (c, rot)) in INDICADORES.items()]
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="UNODC — Oficina de las Naciones Unidas contra la Droga y el Delito: base de "
               "tráfico de armas de fuego (incautaciones y detenciones)",
        url_fuente="https://data.unodc.org/datareport/firearm-seizures",
        calificacion=comun.calificar(
            "A", 2, False,
            "Base oficial de Naciones Unidas, con metodología declarada. Credibilidad 2: cada "
            "Estado reporta según su capacidad de registro, y la incautación depende de la "
            "acción policial, no solo del flujo real."),
        registros=registros,
        vacios=[
            "NO SE COMPARA COMO RANKING: la incautación mide acción policial además de flujo; "
            "más incautaciones puede ser más control, no más tráfico.",
            "Varios Estados no reportan a UNODC en todos los años: el vacío se declara, no se rellena.",
        ],
        extra={"indicadores": indicadores,
               "resumen": {"estados_con_dato": con, "estados_del_padron": len(registros),
                           "archivo": url.rsplit("/", 2)[-2] + "/" + url.rsplit("/", 1)[-1],
                           "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
