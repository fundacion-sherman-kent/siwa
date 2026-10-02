# -*- coding: utf-8 -*-
"""Vigía de fuentes: avisa cuando la página de una fuente CAMBIA (automejora).

Es la idea de changedetection.io (Apache-2.0) hecha a la medida de la casa y
alojada donde ya viven los robots de SIWA: GitHub Actions, gratis y con la
biblioteca estándar. No se aloja el servicio Docker de changedetection.io porque
pediría un servidor persistente que la casa no tiene gratis (SiteGround es shared;
Oracle se descartó). Esto hace lo mismo que importa para el registro, sin host nuevo.

QUÉ MIRA, Y POR QUÉ ESTAS Y NO TODAS
------------------------------------
Las fuentes que NO se refrescan solas: ediciones ANUALES (USGS MCS, Energy
Institute, BTI, CPI), file-drops y portales gated. Las APIs que el robot ya golpea
cada hora (Banco Mundial, OMS, CEPAL) no hacen falta acá: su frescura ya la mide
`frescura.py`. Acá el valor es enterarse de que salió una edición nueva ANTES de
que alguien lo note a mano.

CÓMO DETECTA EL CAMBIO
----------------------
Por vuelta, pide cada URL y guarda tres señales: `Last-Modified`, `ETag` y un hash
del cuerpo. Marca "cambió" si cambió el `Last-Modified`/`ETag` (señal fuerte y sin
ruido) o, si la fuente no los da, si cambió el hash del cuerpo. El estado anterior
vive en el propio `datos/publico/vigia-fuentes.json` (se compara contra la vuelta
pasada). NO publica ni decide: deja el parte para que la Oficina revise si hay
edición nueva y actualice el colector (compuerta humana).
"""
from __future__ import annotations
import hashlib, json, sys, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
try:
    import comun  # para AGENTE si existe
    AGENTE = getattr(comun, "AGENTE", "Mozilla/5.0 (SIWA vigia-fuentes)")
except Exception:
    AGENTE = "Mozilla/5.0 (SIWA vigia-fuentes)"

SALIDA = AQUI.parent / "datos" / "publico" / "vigia-fuentes.json"

# Fuentes de edición anual / file-drop / gated que no se refrescan solas.
FUENTES = [
    {"clave": "usgs_mcs", "que_es": "USGS Mineral Commodity Summaries (minerales, tierras raras)",
     "url": "https://www.sciencebase.gov/catalog/item/69837e43b66b01367d7ec7c7?format=json"},
    {"clave": "energy_institute", "que_es": "Energy Institute — Statistical Review of World Energy",
     "url": "https://www.energyinst.org/statistical-review"},
    {"clave": "ti_cpi", "que_es": "Transparency International — Índice de Percepción de la Corrupción",
     "url": "https://www.transparency.org/en/cpi"},
    {"clave": "bti", "que_es": "Bertelsmann — Transformation Index (BTI)",
     "url": "https://bti-project.org/en/downloads"},
    {"clave": "wjp", "que_es": "World Justice Project — Rule of Law Index",
     "url": "https://worldjusticeproject.org/rule-of-law-index/downloads"},
    {"clave": "latinobarometro", "que_es": "Latinobarómetro — datos",
     "url": "https://www.latinobarometro.org/latContents.jsp"},
    {"clave": "unodc_portal", "que_es": "UNODC — Data Portal (homicidios, personal de justicia, trata)",
     "url": "https://dataunodc.un.org/"},
    {"clave": "sipri_milex", "que_es": "SIPRI — Military Expenditure Database",
     "url": "https://www.sipri.org/databases/milex"},
    {"clave": "wipo_ipstats", "que_es": "WIPO — IP Statistics (patentes)",
     "url": "https://www.wipo.int/en/web/ip-statistics"},
    {"clave": "fao_aquastat", "que_es": "FAO AQUASTAT — agua renovable",
     "url": "https://data.apps.fao.org/aquastat/?lang=en"},
    {"clave": "who_gho_road", "que_es": "OMS GHO — seguridad vial (muertes de tránsito)",
     "url": "https://www.who.int/data/gho/data/themes/road-safety"},
    {"clave": "oisevi", "que_es": "OISEVI — Informe Iberoamericano de seguridad vial",
     "url": "https://www.oisevi.org/"},
]

def mirar(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            cuerpo = r.read()
            h = r.headers
            return {"ok": True, "estado": r.status,
                    "last_modified": h.get("Last-Modified"), "etag": h.get("ETag"),
                    "largo": len(cuerpo), "hash": hashlib.sha256(cuerpo).hexdigest()[:16]}
    except urllib.error.HTTPError as e:
        return {"ok": False, "estado": e.code, "last_modified": None, "etag": None, "largo": None, "hash": None}
    except Exception as e:
        return {"ok": False, "estado": None, "error": type(e).__name__, "last_modified": None,
                "etag": None, "largo": None, "hash": None}

def cambio(ant: dict | None, act: dict) -> bool:
    if ant is None:
        return False  # primera vez: se establece la línea de base, no es "cambio"
    if not act.get("ok"):
        return False  # un error de red no es un cambio de la fuente
    # señal fuerte: Last-Modified o ETag distintos
    for k in ("last_modified", "etag"):
        if ant.get(k) and act.get(k) and ant[k] != act[k]:
            return True
    # si no hay esos encabezados, el hash del cuerpo (con algo de ruido posible)
    if not (act.get("last_modified") or act.get("etag")):
        return ant.get("hash") and act.get("hash") and ant["hash"] != act["hash"]
    return False

def main():
    prev = {}
    if SALIDA.exists():
        try:
            prev = {f["clave"]: f for f in json.loads(SALIDA.read_text(encoding="utf-8")).get("fuentes", [])}
        except Exception:
            prev = {}
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fuentes, cambiaron = [], []
    for f in FUENTES:
        act = mirar(f["url"])
        ant = prev.get(f["clave"])
        cambio_detectado = cambio(ant, act)
        if cambio_detectado:
            cambiaron.append(f["clave"])
        fuentes.append({**f, **act, "cambio_desde_la_ultima": cambio_detectado,
                        "visto_por_ultima_vez": ahora,
                        "cambio_visto_en": ahora if cambio_detectado else (ant or {}).get("cambio_visto_en")})
    doc = {
        "que_es": "Vigía de fuentes de edición anual / file-drop / gated que no se refrescan solas. Avisa "
                  "cuando la página de una fuente cambió respecto de la vuelta anterior, para revisar si salió "
                  "una edición nueva y actualizar el colector. Mide y declara; no publica ni decide solo.",
        "corrida": ahora,
        "resumen": {"fuentes_miradas": len(fuentes),
                    "respondieron": sum(1 for f in fuentes if f.get("ok")),
                    "cambiaron_esta_vuelta": len(cambiaron), "cuales": cambiaron},
        "fuentes": fuentes,
    }
    SALIDA.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    print(f"vigia-fuentes.json: {doc['resumen']['respondieron']}/{len(fuentes)} respondieron, "
          f"{len(cambiaron)} cambiaron ({', '.join(cambiaron) or 'ninguna'})")

if __name__ == "__main__":
    main()
