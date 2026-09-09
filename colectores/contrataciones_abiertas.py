# -*- coding: utf-8 -*-
"""Contratación pública: quién publica sus compras en el formato común, y hasta cuándo.

POR QUÉ EXISTE
--------------
Es el hueco que el propio registro declara como el más grande y el más
remontable de las seis materias: «El expediente de cada licitación existe en los
portales de compras de cada Estado, pero en 33 formatos distintos».

El Estándar de Datos de Contrataciones Abiertas (OCDS) es exactamente ese
formato común, y la Open Contracting Partnership mantiene el registro de quién
lo publica. No da los 33, pero convierte «no se puede medir» en «se puede medir
en quince, y se dice en cuáles no».

QUÉ SE MIDE, Y POR QUÉ ASÍ
---------------------------
**La vigencia: cuántos días pasaron desde el último proceso publicado.** Es lo
único comparable entre un Estado grande y uno chico. Publicar al día es publicar
al día, tenga el Estado el tamaño que tenga.

Lo que NO se usa para ordenar:
- **La cantidad de publicadores.** México tiene dieciocho y Uruguay dos: eso
  mide el federalismo, no la transparencia. Ordenar por ahí sería premiar al
  Estado grande, el mismo error por el que Costa Rica —sin ejército desde
  1949— aparecía entre las peores en Defensa.
- **La cantidad de procesos.** Perú publica 2,7 millones porque es Perú.

Las dos viajan igual, como magnitud declarada y sin orientar, porque describen
el terreno.

Y una tercera medida que sí compara: **cuántas de las cuatro etapas del
expediente publica** —planificación, licitación, adjudicación, contrato—. Un
Estado que publica el contrato firmado dice más que uno que solo publica el
llamado, y eso no depende de su tamaño.

LO QUE ESTO NO ES
------------------
No mide corrupción, ni precios, ni sobreprecios: mide **si el expediente está
publicado en un formato que una máquina pueda leer**. Un Estado puede publicar
todo y contratar mal, y al revés.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

import comun
import geo

FUENTE = "https://data.open-contracting.org/en/publications.json"
INTENTOS = 3
# El nombre con que la fuente escribe cada Estado, llevado al padrón.
PAISES = {
    "Argentina": "ARG", "Bolivia": "BOL", "Brazil": "BRA", "Chile": "CHL",
    "Colombia": "COL", "Costa Rica": "CRI", "Cuba": "CUB", "Dominican Republic": "DOM",
    "Ecuador": "ECU", "El Salvador": "SLV", "Guatemala": "GTM", "Honduras": "HND",
    "Mexico": "MEX", "Nicaragua": "NIC", "Panama": "PAN", "Paraguay": "PRY",
    "Peru": "PER", "Uruguay": "URY", "Venezuela": "VEN", "Jamaica": "JAM",
    "Trinidad and Tobago": "TTO", "Guyana": "GUY", "Suriname": "SUR", "Haiti": "HTI",
    "Belize": "BLZ", "Bahamas": "BHS", "Barbados": "BRB", "Antigua and Barbuda": "ATG",
    "Dominica": "DMA", "Grenada": "GRD", "Saint Kitts and Nevis": "KNA",
    "Saint Lucia": "LCA", "Saint Vincent and the Grenadines": "VCT",
}
# Las cuatro etapas del expediente, y el campo del estándar que las delata.
ETAPAS = [("planificación", "/planning"), ("licitación", "/tender"),
          ("adjudicación", "/awards"), ("contrato", "/contracts")]
CONTROL = "PER"


def _traer() -> list:
    ultimo = None
    for intento in range(INTENTOS):
        if intento:
            time.sleep(2 * intento)
        try:
            peticion = urllib.request.Request(
                FUENTE, headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                crudo = json.loads(respuesta.read().decode("utf-8", "replace"))
            if isinstance(crudo, list) and crudo:
                return crudo
            ultimo = "la fuente respondió sin publicadores"
        except Exception as error:  # noqa: BLE001 — se reintenta y, si no, se declara
            ultimo = f"{type(error).__name__}: {error}"
    raise RuntimeError(f"El registro de contrataciones abiertas no respondió en {INTENTOS} "
                       f"intentos: {ultimo}. NO se publica un archivo vacío.")


def _fecha(t) -> date | None:
    try:
        return date.fromisoformat(str(t)[:10])
    except (TypeError, ValueError):
        return None


def recolectar():
    padron = geo.padron()
    crudo = _traer()
    hoy = datetime.now(timezone.utc).date()

    porIso = {}
    for p in crudo:
        iso = PAISES.get(str(p.get("country") or ""))
        if not iso:
            continue
        hasta = _fecha(p.get("date_to"))
        desde = _fecha(p.get("date_from"))
        cobertura = p.get("coverage") or {}
        etapas = [nombre for nombre, campo in ETAPAS if cobertura.get(campo)]
        porIso.setdefault(iso, []).append({
            "publicador": str(p.get("title") or "")[:120],
            "desde": desde.isoformat() if desde else None,
            "hasta": hasta.isoformat() if hasta else None,
            "procesos": cobertura.get("") or cobertura.get("/") or 0,
            "etapas": etapas,
            "frecuencia": p.get("update_frequency"),
            "url": p.get("source_url"),
        })

    # SE PRUEBA EL LECTOR ANTES DE CREERLE UN VACÍO A NADIE.
    if CONTROL not in porIso or not porIso[CONTROL][0]["hasta"]:
        raise RuntimeError(
            f"La prueba del lector falló: {CONTROL} publica a diario y no se leyó su fecha. "
            "El registro cambió de forma. NO se publica una lectura a ciegas.")

    registros, conPublicador = [], 0
    for pa in padron:
        suyos = porIso.get(pa["iso"], [])
        fila = {"iso": pa["iso"], "pais": pa["pais"], "bloque": pa["bloque"],
                "estado": "publica" if suyos else "sin_publicador"}
        if suyos:
            conPublicador += 1
            fechas = [_fecha(x["hasta"]) for x in suyos if x["hasta"]]
            ultima = max(fechas) if fechas else None
            etapas = sorted({e for x in suyos for e in x["etapas"]},
                            key=lambda e: [n for n, _ in ETAPAS].index(e))
            fila.update({
                "dias_desde_el_ultimo": (hoy - ultima).days if ultima else None,
                "ultimo_proceso": ultima.isoformat() if ultima else None,
                "publicadores": len(suyos),
                "procesos": sum(int(x["procesos"] or 0) for x in suyos),
                "etapas": etapas,
                "etapas_de_cuatro": len(etapas),
                "detalle": sorted(suyos, key=lambda x: x["hasta"] or "", reverse=True)[:5],
            })
        registros.append(fila)

    alDia = sum(1 for r in registros
                if isinstance(r.get("dias_desde_el_ultimo"), int) and r["dias_desde_el_ultimo"] <= 30)
    calificacion = comun.calificar(
        fiabilidad="A", credibilidad=2, corroborado=False,
        nota=("Registro de la Open Contracting Partnership sobre los portales de compras de "
              "cada Estado. Fiabilidad A: no interpreta nada, lista quién publica en el "
              "estándar común y desde cuándo. Credibilidad 2 porque la fecha y el volumen "
              "salen del propio portal de cada Estado, que es el único que los conoce."),
    )
    vacios = [
        "NO MIDE CORRUPCIÓN NI PRECIOS: mide si el expediente está publicado en un formato "
        "que una máquina pueda leer. Un Estado puede publicar todo y contratar mal, y al revés.",
        "La cantidad de publicadores y de procesos NO ordena a los Estados: México tiene "
        "dieciocho publicadores por su estructura federal y Perú publica millones de procesos "
        "por su tamaño. Lo comparable es la vigencia —cuántos días pasaron desde el último "
        "proceso publicado— y cuántas de las cuatro etapas del expediente se publican.",
        f"Solo {conPublicador} de los {len(registros)} Estados del padrón publican en el "
        "estándar común. En los demás el expediente puede existir en su portal nacional, pero "
        "no en un formato comparable: eso es el hueco, y es lo que este dato mide.",
        "Un portal que dejó de publicar hace años sigue figurando acá, con su fecha: el "
        "registro no lo borra, lo muestra viejo.",
    ]
    return comun.escribir(
        colector="contrataciones_abiertas",
        capa="publico",
        fuente="Registro de publicadores del Estándar de Datos de Contrataciones Abiertas — "
               "Open Contracting Partnership",
        url_fuente="https://data.open-contracting.org/en/publications",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados_que_publican": conPublicador,
                "estados_del_padron": len(registros),
                "estados_al_dia": alDia,
                "publicadores_en_la_region": sum(len(v) for v in porIso.values()),
                "etapas": [n for n, _ in ETAPAS],
                "lector_probado": True,
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("contrataciones_abiertas", recolectar)
