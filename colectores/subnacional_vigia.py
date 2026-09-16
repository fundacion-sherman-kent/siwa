# -*- coding: utf-8 -*-
"""Vigía subnacional: busca sin descanso nuevas fuentes y datos por unidad.

QUÉ HACE, Y POR QUÉ
-------------------
La capa subnacional de SIWA crece país por país buscando la fuente NACIONAL que
publica un delito por unidad de primer orden. Muchas puertas están hoy cerradas:
portales bloqueados por firewall, descargas caídas, datos solo en PDF, o trámites
de acceso a la información en curso. Este vigía corre en el robot —sin gastar
tokens, solo con la biblioteca estándar— y en cada vuelta:

  1. Golpea cada PUERTA PENDIENTE conocida y registra si respondió, con qué estado
     y si CAMBIÓ respecto de la última vez. Cuando una se abre, lo dice: es la señal
     para construir ese colector.
  2. Mira la FRESCURA de las fuentes subnacionales que ya están activas: hasta qué
     año llega cada una, para detectar cuándo el productor publicó un año nuevo.

No publica nada en el sitio ni decide solo: deja un parte de situación en
`datos/publico/subnacional_vigia.json` para que la Oficina lo lea y actúe.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun  # noqa: E402

COLECTOR = "subnacional_vigia"
CAPA = "publico"

# PUERTAS PENDIENTES: fuentes subnacionales que hoy no se pudieron usar y que hay
# que reintentar de forma sostenida. `abierta_si` describe qué respuesta cuenta como
# "se abrió" (por defecto, HTTP 200 con cuerpo no vacío).
PUERTAS = [
    {"pais": "República Dominicana", "clave": "do_datos_gob",
     "que_es": "Portal CKAN nacional (homicidios por provincia)",
     "url": "https://datos.gob.do/api/3/action/package_search?q=homicidios&rows=5"},
    {"pais": "República Dominicana", "clave": "do_cadseci",
     "que_es": "CADSECI — indicadores territoriales de seguridad",
     "url": "https://cadseci.gob.do/"},
    {"pais": "Paraguay", "clave": "py_ine_ods",
     "que_es": "INE Paraguay ODS 16.1.1 — busca un archivo de datos (no metadatos)",
     "url": "https://ods.ine.gov.py/ine-main/ods/paz-justicias-e-instituciones-solidas-16/meta-16.1/indicador-284"},
    {"pais": "Costa Rica", "clave": "cr_oij",
     "que_es": "OIJ / Poder Judicial — datos abiertos de homicidios por provincia",
     "url": "https://pjenlinea3.poder-judicial.go.cr/estadisticasoij/"},
    {"pais": "Bolivia", "clave": "bo_fiscalia_roma",
     "que_es": "Fiscalía General — Ecosistema ROMA de datos abiertos (marzo 2026)",
     "url": "https://fiscalia.gob.bo/"},
    {"pais": "Guatemala", "clave": "gt_ine_pnc",
     "que_es": "INE Guatemala — dataset «Víctimas PNC» por departamento (XLSX)",
     "url": "https://datos.ine.gob.gt/api/3/action/package_search?q=v%C3%ADctimas&rows=5"},
    {"pais": "Barbados", "clave": "bb_tbps",
     "que_es": "The Barbados Police Service — estadísticas (dio 503)",
     "url": "https://www.tbps.gov.bb/"},
    {"pais": "Granada", "clave": "gd_rgpf",
     "que_es": "Royal Grenada Police Force — estadísticas (dio 500)",
     "url": "https://www.rgpf.gd/"},
    {"pais": "Surinam", "clave": "sr_abs",
     "que_es": "Algemeen Bureau voor de Statistiek — crimen por distrito (actualización)",
     "url": "https://statistics-suriname.org/en/statistics/"},
]

# FUENTES ACTIVAS: se mira hasta qué año publican, para detectar años nuevos.
# El vigía lee el JSON ya producido por `subnacional_homicidios`, sin re-descargar.
ACTIVAS_ARCHIVO = comun.DATOS / "publico" / "subnacional_homicidios.json"
PDH_ARCHIVO = comun.DATOS / "publico" / "pdh_guatemala_subnacional.json"


def _tocar(url: str, espera: int = 30) -> dict:
    """Golpea una URL y devuelve estado sin romper nunca."""
    pet = urllib.request.Request(url, headers=comun.CABECERAS)
    try:
        with urllib.request.urlopen(pet, timeout=espera) as r:
            cuerpo = r.read(4096)
            return {"ok": True, "http": getattr(r, "status", 200), "bytes": len(cuerpo)}
    except urllib.error.HTTPError as e:  # noqa: PERF203
        return {"ok": False, "http": e.code, "bytes": 0}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "http": None, "error": type(e).__name__}


def _estado_previo() -> dict:
    ruta = comun.DATOS / "publico" / f"{COLECTOR}.json"
    if ruta.exists():
        try:
            d = json.loads(ruta.read_text(encoding="utf-8"))
            return {p["clave"]: p for p in d.get("puertas", [])}
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _frescura_activas() -> list:
    salida = []
    for archivo, clave_ind in ((ACTIVAS_ARCHIVO, None), (PDH_ARCHIVO, "denuncias")):
        if not archivo.exists():
            continue
        try:
            d = json.loads(archivo.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for e in d.get("registros", []):
            anios = []
            for u in e.get("unidades", []):
                for s in u.get("serie", []):
                    if s.get("anio"):
                        anios.append(s["anio"])
            if e.get("en_curso"):
                anios.append(e["en_curso"].get("anio"))
            salida.append({"iso": e.get("iso"), "pais": e.get("pais"),
                           "unidad": e.get("nombre_unidad"), "unidades": e.get("cuantas"),
                           "hasta": max([a for a in anios if a], default=None)})
    return salida


def construir() -> Path:
    previo = _estado_previo()
    este = datetime.now(timezone.utc).year
    puertas, novedades = [], []
    for p in PUERTAS:
        r = _tocar(p["url"])
        abierta = bool(r.get("ok") and r.get("bytes", 0) > 0)
        antes = previo.get(p["clave"], {})
        cambio = abierta and not antes.get("abierta", False)
        fila = {**{k: p[k] for k in ("pais", "clave", "que_es", "url")},
                "abierta": abierta, "http": r.get("http"),
                "detalle": r.get("error") or f"HTTP {r.get('http')}, {r.get('bytes',0)} bytes",
                "revisado": comun.ahora()}
        puertas.append(fila)
        if cambio:
            novedades.append(f"{p['pais']}: SE ABRIÓ «{p['que_es']}» ({p['url']}) — a construir")

    activas = _frescura_activas()
    atrasadas = [a for a in activas if a.get("hasta") and a["hasta"] < este - 1]

    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="Vigía subnacional de SIWA — reintento sostenido de fuentes por unidad de primer orden",
        url_fuente="https://siwa.fundacionkent.org/",
        calificacion=comun.calificar(
            "A", 2, False,
            "Parte de situación interno de la propia Oficina sobre el estado de sus fuentes; "
            "no es un dato de terceros ni pretende confianza máxima: es el registro de qué "
            "puertas respondieron en cada vuelta del robot."),
        registros=[],
        vacios=[
            "NO ES UN DATO DE PAÍSES: es el estado de las fuentes subnacionales pendientes y la "
            "frescura de las activas. Sirve para saber cuándo construir o actualizar, no para publicar.",
            "Que una puerta responda HTTP 200 no garantiza que el dato esté ahí en formato usable: "
            "confirma acceso, no contenido. El colector se construye y se verifica aparte.",
        ],
        extra={
            "puertas": puertas,
            "activas": activas,
            "resumen": {
                "puertas_probadas": len(puertas),
                "puertas_abiertas": sum(1 for p in puertas if p["abierta"]),
                "novedades": novedades,
                "fuentes_activas": len(activas),
                "activas_atrasadas": [f"{a['pais']} (hasta {a['hasta']})" for a in atrasadas],
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
