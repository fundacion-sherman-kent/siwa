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
MAX_TITULARES_QUERY = 25      # titulares por búsqueda
MAX_TITULARES_FAM = 30        # titulares por familia que se le pasan al modelo
ANIO = HOY.year

# BÚSQUEDAS AMPLIAS por familia: traen muchos decomisos/operativos recientes de la
# región, y después Llama los mapea a los corredores conocidos. Es más productivo que
# buscar por corredor (demasiado angosto: volvía con 0). En castellano, con el año.
BROAD = {
    "narcotrafico": ["incautación de cocaína " + str(ANIO), "decomiso de droga " + str(ANIO) + " sudamérica",
                     "narcotráfico decomiso " + str(ANIO)],
    "armas": ["incautación de armas de fuego " + str(ANIO), "tráfico de armas decomiso " + str(ANIO)],
    "migracion": ["tráfico de migrantes operativo " + str(ANIO), "rescate de migrantes " + str(ANIO)],
    "minerales": ["oro ilegal decomiso " + str(ANIO), "minería ilegal operativo " + str(ANIO)],
    "especies": ["tráfico de especies decomiso " + str(ANIO), "incautación de fauna silvestre " + str(ANIO)],
    "contrabando": ["contrabando decomiso " + str(ANIO), "mercadería de contrabando incautación " + str(ANIO)],
    "trata": ["trata de personas rescate " + str(ANIO), "operativo trata de personas " + str(ANIO)],
}

SISTEMA = (
    "Sos un analista de inteligencia de fuentes abiertas de América Latina y el Caribe. Te paso una "
    "FAMILIA de flujo ilícito, una lista de CORREDORES conocidos (id: origen → destino) y una lista de "
    "TITULARES de prensa recientes. Por cada titular que describa un OPERATIVO o DECOMISO REAL y "
    "reciente de esa familia, devolvé en JSON a qué corredor corresponde (su id) o \"ninguno\" si no "
    "calza con ninguno (sería un corredor nuevo). Formato: {\"eventos\":[{\"indice\":int,\"corredor_id\":str,"
    "\"lugar\":str,\"fecha\":str|null,\"que\":str}]}. `indice` es la posición del titular en la lista "
    "(desde 0). Descartá lo que NO sea un decomiso/operativo real (opinión, política, condena judicial "
    "vieja, repetición). No inventes: no agregues titulares que no estén en la lista, ni ids que no estén "
    "en los corredores (salvo \"ninguno\"). Respondé sólo el JSON."
)

def rss(query: str, limite: int = MAX_TITULARES_QUERY) -> list[dict]:
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
    return out[:limite]

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
    corr_por_fam = {p["familia"]: p.get("corredores_a_refrescar", []) for p in cola.get("propuestas", [])}

    eventos, sin_corredor, titulares_totales = [], [], 0
    for fam, consultas in BROAD.items():
        # 1) MUCHOS titulares de la familia, de varias búsquedas amplias, deduplicados
        vistos, titulares = set(), []
        for q in consultas:
            for t in rss(q):
                if t["enlace"] in vistos:
                    continue
                vistos.add(t["enlace"]); titulares.append(t)
        titulares = titulares[:MAX_TITULARES_FAM]
        titulares_totales += len(titulares)
        if not titulares:
            continue
        # 2) Llama mapea cada decomiso real al corredor conocido (o "ninguno" = corredor nuevo)
        corrs = corr_por_fam.get(fam, [])
        ids_validos = {c["id"] for c in corrs}
        lista_corr = "\n".join(f"- {c['id']}: {c['corredor']}" for c in corrs) or "(sin corredores cargados)"
        lista_tit = "\n".join(f"{i}. {t['titular']} ({t['fuente']}, {t['fecha']})" for i, t in enumerate(titulares))
        usuario = f"Familia: {fam}.\nCorredores conocidos:\n{lista_corr}\n\nTitulares:\n{lista_tit}"
        try:
            _modelo, resp = bl.conversar(SISTEMA, usuario)
        except Exception as e:
            print(f"  {fam}: modelo no disponible ({e}); se omite")
            continue
        for ev in extraer_json(resp).get("eventos", []):
            i = ev.get("indice")
            if not isinstance(i, int) or i < 0 or i >= len(titulares):
                continue  # no inventado: apunta a un titular real de la lista
            cid = ev.get("corredor_id")
            if cid not in ids_validos and cid != "ninguno":
                continue  # no inventado: el id tiene que existir (o ser "ninguno")
            t = titulares[i]
            if not bl.comprobar(t["enlace"]).get("responde"):
                continue  # el enlace tiene que responder
            reg = {"familia": fam, "corredor_id": cid, "titular": t["titular"], "enlace": t["enlace"],
                   "fuente": t["fuente"], "fecha": t["fecha"], "lugar": ev.get("lugar"), "que": ev.get("que")}
            (sin_corredor if cid == "ninguno" else eventos).append(reg)

    salida.mkdir(parents=True, exist_ok=True)
    doc = {
        "que_es": "Candidatos de eventos recientes (operativos/decomisos) de flujos ilícitos, hallados por "
                  "búsqueda amplia por familia y mapeados por Llama a los corredores conocidos. Los que no calzan "
                  "con ninguno van aparte como candidatos a corredor NUEVO. NINGUNO está incorporado ni calificado: "
                  "dos fuentes o rótulo, décimo hombre y visto bueno antes de entrar al mapa.",
        "corrida": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "resumen": {"familias_miradas": len(BROAD), "titulares_mirados": titulares_totales,
                    "eventos_mapeados_a_corredor": len(eventos), "candidatos_corredor_nuevo": len(sin_corredor)},
        "eventos": eventos,
        "candidatos_corredor_nuevo": sin_corredor,
    }
    (salida / f"flujos-{HOY.isoformat()}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"flujos-{HOY}: {titulares_totales} titulares mirados, {len(eventos)} eventos mapeados a corredor, "
          f"{len(sin_corredor)} candidatos a corredor nuevo (en rama aparte, sin incorporar)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(RAIZ / "propuestas-flujos"))
    a = ap.parse_args()
    main(Path(a.salida))
