# -*- coding: utf-8 -*-
"""Scanner de eventos de flujos con Llama — propone, no incorpora (automejora, fase 2).

El motor hacia el dato en TIEMPO REAL de los corredores de flujos ilícitos. Levanta
la cola que arma `herramientas/propuestas-flujos.py` (datos/publico/propuestas-flujos.json)
y, por cada corredor atrasado, busca titulares RECIENTES en Google News RSS (gratis,
sin clave), le pide a un modelo de pesos abiertos —Llama por Cloudflare, o el que Groq
sirva gratis— que diga cuáles son operativos/decomisos reales de ese flujo en ese
corredor y extraiga evento, lugar, fecha y enlace. Comprueba cada enlace y deja los
candidatos en una rama aparte que el sitio NO publica.

LO QUE NO HACE: no incorpora nada al registro ni toca el sitio; no califica (eso es
juicio humano: dos fuentes o rótulo, décimo hombre, visto bueno); no inventa (sólo
titulares que el feed devolvió y enlaces que responden); no manda a ningún servicio
otra cosa que titulares públicos. Sin clave de modelo, no falla: avisa y termina.

Mismo criterio y misma infraestructura de modelo que `colectores/buscador_llama.py`,
cuya llamada al modelo (`conversar`) y verificación de enlaces (`comprobar`) se reusan.
"""
from __future__ import annotations
import argparse, datetime as dt, json, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import buscador_llama as bl  # reusa conversar(), comprobar(), pedir_json()

RAIZ = AQUI.parent
COLA = RAIZ / "datos" / "publico" / "propuestas-flujos.json"
HOY = dt.datetime.now(dt.timezone.utc).date()
MESES_RECIENTE = 14           # un titular es "reciente" si es de los últimos ~14 meses
MAX_CORREDORES = 14           # tope por corrida, para no abusar del modelo gratuito
MAX_TITULARES = 8             # titulares por corredor que se le pasan al modelo

SISTEMA = (
    "Sos un analista de inteligencia de fuentes abiertas. Te paso titulares de prensa y un "
    "corredor de un flujo ilícito (origen → destino) de América Latina y el Caribe. Decime, en "
    "JSON, SÓLO los titulares que describan un OPERATIVO o DECOMISO REAL y reciente de ese flujo "
    "en ese corredor o sus tramos. Formato: {\"eventos\":[{\"titular\":str,\"lugar\":str,"
    "\"fecha\":str|null,\"que\":str,\"indice\":int}]}. `indice` es la posición del titular en la "
    "lista (empezando en 0). Si ninguno sirve, devolvé {\"eventos\":[]}. No inventes: no agregues "
    "titulares que no estén en la lista. Respondé sólo el JSON."
)

def rss(query: str) -> list[dict]:
    """Titulares recientes de Google News RSS (gratis, sin clave)."""
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
           + "&hl=es-419&gl=AR&ceid=AR:es")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SIWA/automejora)"})
    try:
        xml = urllib.request.urlopen(req, timeout=30).read()
    except Exception:
        return []
    out = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    for it in root.iter("item"):
        titulo = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        fuente = ""
        s = it.find("source")
        if s is not None and s.text:
            fuente = s.text.strip()
        reciente = True
        try:
            fecha = dt.datetime.strptime(pub[:25], "%a, %d %b %Y %H:%M:%S").date()
            reciente = (HOY - fecha).days <= MESES_RECIENTE * 31
        except Exception:
            fecha = None
        if titulo and link and reciente:
            out.append({"titular": titulo, "enlace": link, "fuente": fuente,
                        "fecha": fecha.isoformat() if fecha else None})
    return out[:MAX_TITULARES]

def extraer_json(texto: str):
    m = re.search(r"\{.*\}", texto or "", re.S)
    if not m:
        return {"eventos": []}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"eventos": []}

def main(salida: Path):
    if not COLA.exists():
        print("No hay cola (propuestas-flujos.json). Corré antes herramientas/propuestas-flujos.py.")
        return
    cola = json.loads(COLA.read_text(encoding="utf-8"))
    # aplanar a corredores, priorizando familias en alta, los más viejos primero
    objetivos = []
    for p in sorted(cola.get("propuestas", []), key=lambda x: x["prioridad"] != "alta"):
        for c in p.get("corredores_a_refrescar", []):
            objetivos.append({**c, "familia": p["familia"]})
    objetivos = objetivos[:MAX_CORREDORES]

    propuestas = []
    for c in objetivos:
        titulares = rss(c["terminos_de_busqueda"])
        if not titulares:
            continue
        lista = "\n".join(f"{i}. {t['titular']} ({t['fuente']}, {t['fecha']})" for i, t in enumerate(titulares))
        usuario = (f"Flujo: {c['familia']}. Corredor: {c['corredor']} (ruta {c['id']}, registrada en "
                   f"{c.get('desde')}).\nTitulares:\n{lista}")
        try:
            _modelo, resp = bl.conversar(SISTEMA, usuario)
        except Exception as e:
            print(f"  {c['id']}: modelo no disponible ({e}); se omite")
            continue
        eventos = extraer_json(resp).get("eventos", [])
        confirmados = []
        for ev in eventos:
            i = ev.get("indice")
            if not isinstance(i, int) or i < 0 or i >= len(titulares):
                continue  # no inventado: tiene que apuntar a un titular real de la lista
            t = titulares[i]
            if not bl.comprobar(t["enlace"]).get("ok"):
                continue  # el enlace tiene que responder
            confirmados.append({"titular": t["titular"], "enlace": t["enlace"], "fuente": t["fuente"],
                                "fecha": t["fecha"], "lugar": ev.get("lugar"), "que": ev.get("que")})
        if confirmados:
            propuestas.append({"ruta": c["id"], "familia": c["familia"], "corredor": c["corredor"],
                               "registrada_en": c.get("desde"), "eventos_candidatos": confirmados})

    salida.mkdir(parents=True, exist_ok=True)
    doc = {
        "que_es": "Candidatos de eventos recientes (operativos/decomisos) para refrescar corredores de flujos "
                  "ilícitos atrasados. Los propone el scanner Llama desde titulares de prensa; NINGUNO está "
                  "incorporado ni calificado. Requieren dos fuentes o rótulo, décimo hombre y visto bueno.",
        "corrida": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "resumen": {"corredores_mirados": len(objetivos), "con_candidatos": len(propuestas),
                    "eventos": sum(len(p["eventos_candidatos"]) for p in propuestas)},
        "propuestas": propuestas,
    }
    (salida / f"flujos-{HOY.isoformat()}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"flujos-{HOY}: {doc['resumen']['con_candidatos']} corredores con candidatos, "
          f"{doc['resumen']['eventos']} eventos (en rama aparte, sin incorporar)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(RAIZ / "propuestas-flujos"))
    a = ap.parse_args()
    main(Path(a.salida))
