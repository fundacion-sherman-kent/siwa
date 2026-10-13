# -*- coding: utf-8 -*-
"""Vigia de ediciones nuevas de CICAD/OID, por noticias (no por oas.org).

POR QUE EXISTE
--------------
El reporte de la CICAD (Report on Drug Supply / Drug Use in the Americas) es la
segunda fuente de decomisos de cocaina (colector `cicad_decomisos`, file-drop). Como
oas.org tiene muro anti-bot, NO se puede vigilar la pagina para saber si salio una
edicion nueva. En cambio, cuando la OEA publica una edicion, la prensa la cubre: este
vigia mira Google News (gratis, sin clave) y avisa si aparece una edicion mas NUEVA
que la que SIWA tiene montada, para que una persona la baje y haga el file-drop.

NO INCORPORA NADA. Solo mide y declara: escribe datos/publico/vigia-cicad.json y, si
detecta una posible edicion nueva, lo marca `a_revisar` y deja el titular y el enlace.
La edicion montada se lee del propio file-drop, asi que el dia que se cargue la 2024,
el vigia sube su linea de base solo.
"""
from __future__ import annotations
import datetime as dt
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
FILE_DROP = RAIZ / "fuentes" / "entrada-manual" / "cicad_cocaina.json"
SALIDA = RAIZ / "datos" / "publico" / "vigia-cicad.json"
HOY = dt.datetime.now(dt.timezone.utc).date()
MESES_RECIENTE = 18

# Busquedas: el nombre de los reportes de CICAD/OID, en los dos idiomas.
TERMINOS = [
    '"Report on Drug Supply in the Americas"',
    '"Report on Drug Use in the Americas"',
    'CICAD informe "oferta de drogas" Americas',
    'Observatorio Interamericano sobre Drogas informe',
]
# Un titular habla de una edicion de estos reportes si menciona CICAD/OEA/OID o el
# nombre del reporte. Evita falsos positivos con cualquier noticia de drogas.
CONTEXTO = re.compile(r"cicad|oea\b|oas\b|observatorio interamericano|drug supply|drug use|"
                      r"oferta de drogas|supply in the americas|use in the americas", re.I)


def edicion_montada() -> int:
    """El anio de la edicion que SIWA ya tiene (del titulo del file-drop)."""
    try:
        d = json.loads(FILE_DROP.read_text(encoding="utf-8"))
        titulo = (d.get("fuente") or {}).get("titulo", "")
        anios = [int(a) for a in re.findall(r"\b(20\d\d)\b", titulo)]
        if anios:
            return max(anios)
    except Exception:  # noqa: BLE001
        pass
    return 2022  # ultima conocida


def rss(query: str, limite: int = 20) -> list[dict]:
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
           + "&hl=es-419&gl=AR&ceid=AR:es")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SIWA/vigia-cicad)"})
    try:
        xml = urllib.request.urlopen(req, timeout=30).read()
        root = ET.fromstring(xml)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for it in root.iter("item"):
        titulo = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        try:
            fecha = dt.datetime.strptime(pub[:25], "%a, %d %b %Y %H:%M:%S").date()
            reciente = (HOY - fecha).days <= MESES_RECIENTE * 31
        except Exception:  # noqa: BLE001
            fecha, reciente = None, True
        if titulo and link and reciente:
            out.append({"titular": titulo, "enlace": link, "fecha": fecha.isoformat() if fecha else None})
    return out[:limite]


def detectar(titulares: list[dict], anio_actual: int) -> list[dict]:
    """Titulares que mencionan una edicion de CICAD/OID de un anio MAS NUEVO que el
    montado. Conservador: pide el contexto (CICAD/OEA/OID o el nombre del reporte) y un
    anio > el actual y <= el proximo."""
    hallados = []
    for t in titulares:
        txt = t["titular"]
        if not CONTEXTO.search(txt):
            continue
        anios = [int(a) for a in re.findall(r"\b(20\d\d)\b", txt) if anio_actual < int(a) <= HOY.year + 1]
        if anios:
            hallados.append({**t, "anio_detectado": max(anios)})
    # dedup por enlace
    vistos, unico = set(), []
    for h in sorted(hallados, key=lambda x: -x["anio_detectado"]):
        if h["enlace"] in vistos:
            continue
        vistos.add(h["enlace"]); unico.append(h)
    return unico


def main():
    anio = edicion_montada()
    titulares = []
    for q in TERMINOS:
        titulares.extend(rss(q))
    candidatos = detectar(titulares, anio)
    doc = {
        "que_es": "Vigia de ediciones nuevas de los reportes de CICAD/OID, por noticias (oas.org tiene "
                  "muro anti-bot y no se puede vigilar la pagina). Avisa si la prensa menciona una edicion "
                  "mas nueva que la montada en SIWA, para bajarla a mano y hacer el file-drop. No incorpora.",
        "corrida": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "edicion_montada": anio,
        "titulares_mirados": len(titulares),
        "a_revisar": bool(candidatos),
        "posible_edicion_nueva": candidatos[:5],
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    if candidatos:
        c = candidatos[0]
        print(f"::notice::Posible edicion CICAD/OID {c['anio_detectado']} (tenemos {anio}): "
              f"{c['titular'][:90]} -> {c['enlace']}")
    print(f"[vigia-cicad] edicion montada {anio}; {len(titulares)} titulares mirados; "
          f"{len(candidatos)} posible(s) edicion(es) nueva(s)")


if __name__ == "__main__":
    main()
