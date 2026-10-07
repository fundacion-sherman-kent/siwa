# -*- coding: utf-8 -*-
"""Scanner de eventos de flujos con Llama — propone, no incorpora (automejora, fase 2).

El motor hacia el dato en TIEMPO REAL de los corredores de flujos ilícitos. Levanta
la cola que arma `herramientas/propuestas-flujos.py` (datos/publico/propuestas-flujos.json)
y, por familia, busca titulares RECIENTES en DOS feeds independientes y gratuitos sin
clave —Google News RSS y GDELT DOC 2.0 (prensa mundial, se actualiza cada 15 min)—, le
pide a un modelo de pesos abiertos —Llama por Cloudflare, o el que Groq sirva gratis—
que diga cuáles son operativos/decomisos reales de ese flujo y a qué corredor conocido
corresponden. Comprueba cada enlace y deja los candidatos en una rama aparte que el
sitio NO publica. Que un corredor aparezca en los dos feeds es la señal de dos fuentes.

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

# GDELT indexa TODO traducido al inglés, así que se le busca con términos en INGLÉS y se
# filtra por idioma de la fuente (sourcelang) para quedarnos con prensa de la región. Las
# frases en español con acento le daban 0; en inglés contra sourcelang:spanish trae las
# mismas notas en castellano/portugués. Un bloque por familia, que se combinan con OR.
BROAD_EN = {
    "narcotrafico": ["cocaine seizure", "drug seizure", "drug trafficking"],
    "armas": ["firearms seizure", "weapons trafficking", "arms seized"],
    "migracion": ["migrant smuggling", "migrants rescued"],
    "minerales": ["illegal mining", "illegal gold"],
    "especies": ["wildlife trafficking", "wildlife seizure"],
    "contrabando": ["smuggling seized", "contraband seizure"],
    "trata": ["human trafficking rescue", "trafficking victims rescued"],
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
                        "fecha": fecha.isoformat() if fecha else None, "feed": "google"})
    return out[:limite]

GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"

def gdelt(consultas: list[str], limite: int = MAX_TITULARES_FAM) -> list[dict]:
    """Segundo feed de titulares, INDEPENDIENTE de Google News: GDELT DOC 2.0 (gratis,
    sin clave, prensa mundial que se actualiza cada 15 min, con ventana de 3 meses).
    Es la segunda fuente que a los eventos de flujos les faltaba: hasta hoy el scanner
    miraba un solo agregador. Un pedido por familia, respetando el límite de GDELT de
    un pedido cada 5 segundos. Castellano y portugués (por Brasil)."""
    import time
    frase = " OR ".join('"' + c.strip() + '"' for c in consultas if c.strip())
    q = "(" + frase + ") (sourcelang:spanish OR sourcelang:portuguese)"
    url = GDELT_DOC + "?" + urllib.parse.urlencode(
        {"query": q, "mode": "ArtList", "format": "json",
         "maxrecords": "50", "sortby": "datedesc", "timespan": "3m"})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SIWA/automejora)"})
    d = None
    for intento in range(3):
        time.sleep(6)  # GDELT pide un llamado cada 5 segundos; se respeta con margen
        try:
            crudo = urllib.request.urlopen(req, timeout=40).read()
            d = json.loads(crudo.decode("utf-8", "replace"))
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento < 2:
                time.sleep(10)  # límite de ritmo: se espera y se reintenta
                continue
            return []
        except Exception:
            return []  # GDELT a veces devuelve HTML de error ante una consulta rara: se ignora
    if d is None:
        return []
    out = []
    for a in d.get("articles", []):
        titulo = (a.get("title") or "").strip()
        link = (a.get("url") or "").strip()
        dom = (a.get("domain") or "").strip()
        try:
            fecha = dt.datetime.strptime((a.get("seendate") or "")[:15], "%Y%m%dT%H%M%S").date()
        except Exception:
            fecha = None
        if titulo and link:
            out.append({"titular": titulo, "enlace": link, "fuente": dom,
                        "fecha": fecha.isoformat() if fecha else None, "feed": "gdelt"})
    return out[:limite]

def extraer_json(texto: str):
    """Saca el objeto {"eventos":[...]} de la respuesta del modelo. Tolera cercos
    markdown y texto de razonamiento alrededor (gpt-oss es un modelo de razonamiento y
    suele envolver el JSON), y acepta que devuelva directamente la lista."""
    if not texto:
        return {"eventos": []}
    s = re.sub(r"```(?:json)?", "", texto).strip()
    # 1) intento directo (objeto o lista pelada)
    try:
        d = json.loads(s)
        if isinstance(d, dict):
            return d
        if isinstance(d, list):
            return {"eventos": d}
    except Exception:  # noqa: BLE001
        pass
    # 2) el objeto que contiene "eventos"
    m = re.search(r"\{[^{}]*\"eventos\"\s*:\s*\[.*?\]\s*\}", s, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:  # noqa: BLE001
            pass
    # 3) último recurso: del primer { al último }
    m = re.search(r"\{.*\}", s, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:  # noqa: BLE001
            pass
    return {"eventos": []}

VACIAS = set("para como desde entre sobre contra tras este esta estos estas aqui alli pais paises "
             "mientras cuando donde mismo misma "
             # sustantivos geográficos comunes: que el cruce se apoye en nombres propios, no en estos
             "puerto puertos ciudad aeropuerto region regiones provincia departamento municipio "
             "norte sur oeste frontera costa golfo valle sierra estado capital zona barrio terminal "
             "portuaria portuario nacional internacional centro "
             # rellenos que el modelo pone cuando NO sabe el lugar: no son nombre propio y no corroboran
             "especificado especificada especifica determinado determinada indeterminado desconocido "
             "desconocida varios varias diversos diversas multiple multiples lugar lugares".split())

def tokens_lugar(lugar: str) -> list[str]:
    """Palabras de lugar de 4+ letras, sin conectores, para cruzar entre feeds."""
    toks = re.findall(r"[a-záéíóúñ]{4,}", (lugar or "").lower())
    return [t for t in toks if t not in VACIAS]

def dias_entre(a: str | None, b: str | None):
    try:
        return abs((dt.date.fromisoformat(a) - dt.date.fromisoformat(b)).days)
    except Exception:
        return None

def corroborar_evento(reg: dict, otros: list[dict]) -> dict | None:
    """Coteja un operativo con los operativos que el OTRO feed confirmó en la MISMA familia
    (no con titulares crudos: así el segundo respaldo es también un decomiso/operativo, no
    una nota temática del mismo lugar). Pide tokens de lugar compartidos —nombres propios—
    y, si ambos tienen fecha, ventana de ~2 semanas. Es señal 'a confirmar': que dos feeds
    independientes den el mismo hecho es la regla de dos fuentes a nivel evento; confirmar
    que es el mismo decomiso sigue siendo juicio humano (dos fuentes o rótulo, décimo hombre)."""
    toks = set(tokens_lugar(reg.get("lugar")))
    if not toks:
        return None
    for o in otros:
        if not (toks & set(tokens_lugar(o.get("lugar")))):
            continue
        d = dias_entre(reg.get("fecha"), o.get("fecha"))
        if d is not None and d > 16:
            continue
        return {"feed": o.get("feed"), "titular": o["titular"], "enlace": o["enlace"],
                "fuente": o.get("fuente"), "fecha": o.get("fecha"), "corredor_id": o.get("corredor_id")}
    return None

def main(salida: Path):
    if not COLA.exists():
        print("No hay cola (propuestas-flujos.json). Corré antes herramientas/propuestas-flujos.py.")
        return
    cola = json.loads(COLA.read_text(encoding="utf-8"))
    corr_por_fam = {p["familia"]: p.get("corredores_a_refrescar", []) for p in cola.get("propuestas", [])}

    eventos, sin_corredor, titulares_totales = [], [], 0
    por_feed = {"google": 0, "gdelt": 0}
    for fam, consultas in BROAD.items():
        # 1) MUCHOS titulares de la familia, de DOS feeds independientes, deduplicados.
        #    Google News RSS y GDELT se piden por separado y se topea cada uno, para que
        #    GDELT —la segunda fuente nueva— no quede afuera por el tope de la familia.
        vistos, google, gd = set(), [], []
        for q in consultas:
            for t in rss(q):
                if t["enlace"] in vistos:
                    continue
                vistos.add(t["enlace"]); google.append(t)
        for t in gdelt(BROAD_EN.get(fam, consultas)):
            if t["enlace"] in vistos:
                continue
            vistos.add(t["enlace"]); gd.append(t)
        titulares = google[:MAX_TITULARES_FAM] + gd[:MAX_TITULARES_FAM]
        por_feed["google"] += len(google[:MAX_TITULARES_FAM])
        por_feed["gdelt"] += len(gd[:MAX_TITULARES_FAM])
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
            resp, _modelo = bl.conversar(SISTEMA, usuario)  # conversar devuelve (texto, etiqueta)
        except Exception as e:
            print(f"  {fam}: modelo no disponible ({e}); se omite")
            continue
        crudos = extraer_json(resp).get("eventos", [])
        desc = {"indice": 0, "id": 0, "enlace": 0}
        regs_fam = []
        for ev in crudos:
            i = ev.get("indice")
            if not isinstance(i, int) or i < 0 or i >= len(titulares):
                desc["indice"] += 1
                continue  # no inventado: apunta a un titular real de la lista
            cid = ev.get("corredor_id")
            if cid not in ids_validos and cid != "ninguno":
                desc["id"] += 1
                continue  # no inventado: el id tiene que existir (o ser "ninguno")
            t = titulares[i]
            if not bl.comprobar(t["enlace"]).get("responde"):
                desc["enlace"] += 1
                continue  # el enlace tiene que responder
            regs_fam.append({"familia": fam, "corredor_id": cid, "titular": t["titular"], "enlace": t["enlace"],
                             "fuente": t["fuente"], "feed": t.get("feed"), "fecha": t["fecha"],
                             "lugar": ev.get("lugar"), "que": ev.get("que")})
        # CORROBORACIÓN EVENTO-A-EVENTO: cada operativo se coteja con los operativos que el
        # OTRO feed confirmó en esta familia (no con titulares crudos). Si coinciden en lugar
        # y ventana, lleva la posible segunda fuente, 'a confirmar'.
        ev_feed = {"google": [r for r in regs_fam if r.get("feed") == "google"],
                   "gdelt":  [r for r in regs_fam if r.get("feed") == "gdelt"]}
        for r in regs_fam:
            otros = ev_feed["gdelt" if r.get("feed") == "google" else "google"]
            corr = corroborar_evento(r, otros)
            r["corroborado_a_confirmar"] = bool(corr)
            r["posible_segunda_fuente"] = corr
            (sin_corredor if r["corredor_id"] == "ninguno" else eventos).append(r)
        suman = len(regs_fam)
        print(f"  {fam} [{_modelo}]: {len(titulares)} titulares, modelo devolvió {len(crudos)} eventos crudos, "
              f"{suman} válidos (descartados: índice {desc['indice']}, id {desc['id']}, enlace {desc['enlace']})")
        if not crudos:  # para diagnosticar un parseo o un prompt que no rinde
            print(f"    (muestra de respuesta: {str(resp)[:200]!r})", file=sys.stderr)

    # CORROBORADOS A CONFIRMAR: los eventos (mapeados o candidatos) a los que la corroboración
    # activa les encontró el mismo hecho en el OTRO feed. Es la señal de dos fuentes a nivel
    # evento; el curador confirma que es el mismo decomiso (dos fuentes o rótulo, décimo hombre).
    corroborados = [e for e in (eventos + sin_corredor) if e.get("corroborado_a_confirmar")]
    corroborados.sort(key=lambda e: (e["familia"], e.get("fecha") or ""))

    salida.mkdir(parents=True, exist_ok=True)
    doc = {
        "que_es": "Candidatos de eventos recientes (operativos/decomisos) de flujos ilícitos, hallados por "
                  "búsqueda amplia por familia en DOS feeds independientes (Google News RSS y GDELT) y mapeados "
                  "por Llama a los corredores conocidos. Los que no calzan con ninguno van aparte como candidatos "
                  "a corredor NUEVO. Cada evento se corrobora contra el OTRO feed: si el mismo hecho (mismo lugar, "
                  "misma ventana) aparece allí, lleva 'corroborado_a_confirmar' y la 'posible_segunda_fuente'. "
                  "NADA está incorporado ni calificado: dos fuentes o rótulo, décimo hombre y visto bueno antes "
                  "de entrar al mapa; la corroboración es señal, no confirmación.",
        "corrida": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "resumen": {"familias_miradas": len(BROAD), "titulares_mirados": titulares_totales,
                    "titulares_por_feed": por_feed,
                    "eventos_mapeados_a_corredor": len(eventos), "candidatos_corredor_nuevo": len(sin_corredor),
                    "corroborados_por_dos_feeds_a_confirmar": len(corroborados)},
        "corroborados_a_confirmar": corroborados,
        "eventos": eventos,
        "candidatos_corredor_nuevo": sin_corredor,
    }
    (salida / f"flujos-{HOY.isoformat()}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"flujos-{HOY}: {titulares_totales} titulares mirados "
          f"(Google {por_feed['google']} + GDELT {por_feed['gdelt']}), {len(eventos)} eventos mapeados a corredor, "
          f"{len(sin_corredor)} candidatos a corredor nuevo, {len(corroborados)} corroborados por los dos feeds "
          f"(a confirmar) (en rama aparte, sin incorporar)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(RAIZ / "propuestas-flujos"))
    a = ap.parse_args()
    main(Path(a.salida))
