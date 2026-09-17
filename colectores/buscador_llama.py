"""Buscador de fuentes con Llama — propone, no incorpora.

Autorizado por la dirección el 17/9/2026 (acta, I-05). Reemplaza la búsqueda de
fuentes que hacía una tarea programada de Claude, apagada el 16/9 porque gastaba
el uso de la Fundación.

QUÉ HACE, EN ORDEN
1. Elige los portales oficiales de datos abiertos que tocan hoy, rotando entre los
   del padrón (`oficiales.json`), y les pide los conjuntos modificados más
   recientemente. Es la misma interfaz CKAN o Socrata que ya consulta
   `fuentes_oficiales.py`.
2. Descarta lo que ya propuso antes.
3. Le pasa a un modelo de pesos abiertos —Llama por Cloudflare si hay clave; si
   no, el que Groq sirva gratis— el título, la descripción y los recursos de cada conjunto, con la
   lista de temas de SIWA. Llama devuelve, por cada uno: si corresponde a un tema,
   a cuál, el último período que cubre, el formato y el motivo en una línea.
4. COMPRUEBA cada enlace que Llama dio por bueno: tiene que responder y tiene que
   ser un archivo o una interfaz que se pueda leer. Lo que no responde no se
   anota, por más convincente que sea la clasificación.
5. Deja las propuestas en `propuestas/` —en una rama aparte que el sitio no
   publica— con un resumen en castellano.

LO QUE NO HACE, Y NO DEBE HACER
· No incorpora nada al registro ni toca el sitio.
· No califica la fuente: la calificación es juicio y la hace una persona.
· No inventa. Si Llama propone un enlace que no está en los metadatos del
  portal, se descarta: sólo se aceptan direcciones que el portal publicó.
· No manda a ningún servicio otra cosa que metadatos públicos de portales
  públicos.

Llama es de Meta, con pesos abiertos bajo su propia licencia. Los nombres de
modelo se eligen en cada corrida, no se fijan: los fijos caducan.

AJUSTES DEL 17/9/2026, ORDENADOS POR LA DIRECCIÓN (acta)
· Perú y Paraguay entran: sus portales no tienen buscador, pero sí la lista de
  conjuntos ordenada del más reciente al más viejo.
· Llama primero: si están las claves de Cloudflare, clasifica Llama; Groq queda
  de respaldo.
· Una serie, una propuesta: los archivos que son la misma serie contada de otra
  manera (en unidades y en TEU, por tipo y por destino) se juntan.
"""

from __future__ import annotations

import argparse
import datetime as dt
import unicodedata
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
# EL PLAN GRATUITO TIENE TOPE DE TOKENS POR MINUTO. Con 30 conjuntos por portal y
# tandas de 8, Groq frenó el primer pedido (17/9/2026, error 429). Se mira menos por
# vuelta —la rotación diaria compensa— y se pide de a poco, con pausa.
POR_PORTAL = 15          # conjuntos recientes que se miran por portal
POR_LLAMADA = 4          # conjuntos por consulta
PAUSA_ENTRE_PEDIDOS = 25 # segundos
PORTALES_POR_CORRIDA = 2


# ─────────────────────────── utilidades de red ───────────────────────────

def pedir_json(url: str, cabeceras: dict | None = None, datos: dict | None = None, espera: int = 45):
    h = {"User-Agent": NAVEGADOR, "Accept": "application/json"}
    h.update(cabeceras or {})
    cuerpo = None
    if datos is not None:
        cuerpo = json.dumps(datos).encode("utf-8")
        h["Content-Type"] = "application/json"
    # LOS PORTALES TROPIEZAN. datos.gob.ar devolvió un error una vez y la siguiente
    # consulta, idéntica, anduvo. Tres intentos con espera creciente antes de dar
    # un portal por caído.
    import time
    for intento in range(5):
        try:
            req = urllib.request.Request(url, data=cuerpo, headers=h)
            with urllib.request.urlopen(req, timeout=espera) as r:
                return json.loads(r.read(6_000_000).decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 404) or intento == 4:
                raise
            if e.code == 429:
                # Groq dice cuánto esperar: se respeta, con un mínimo de 20 segundos.
                try:
                    espera_429 = float(e.headers.get("Retry-After") or 0)
                except ValueError:
                    espera_429 = 0
                time.sleep(min(max(espera_429, 20), 90))
                continue
        except (urllib.error.URLError, TimeoutError):
            if intento == 4:
                raise
        time.sleep(5 * (intento + 1))


def comprobar(url: str) -> dict:
    """¿Responde el enlace? Se pide el comienzo del archivo, no el archivo entero."""
    req = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR, "Range": "bytes=0-2047"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            r.read(2048)
            return {"responde": True, "estado": r.status,
                    "tipo": r.headers.get("Content-Type", "").split(";")[0]}
    except urllib.error.HTTPError as e:
        return {"responde": e.code in (206, 416), "estado": e.code, "tipo": ""}
    except Exception as e:  # noqa: BLE001
        return {"responde": False, "estado": type(e).__name__, "tipo": ""}


# ─────────────────────────── 1 · los portales ───────────────────────────

FORMATOS_DE_DATOS = {"CSV", "XLSX", "XLS", "EXCEL", "JSON", "ODS", "XML", "API", "ZIP"}


def elegir_recursos(recursos: list[dict]) -> list[dict]:
    """LOS PRIMEROS RECURSOS SUELEN SER EL DICCIONARIO Y LOS METADATOS. En Perú, un
    conjunto de empleo tenía 48 archivos: el diccionario primero y el mes más nuevo
    al final. Se prefieren archivos de datos, y de ellos los últimos publicados."""
    limpios = []
    for x in recursos or []:
        if not x.get("url"):
            continue
        formato = (x.get("format") or "").upper().lstrip(".")
        nombre = x.get("name") or ""
        limpios.append({"url": x["url"], "formato": formato, "nombre": nombre[:80],
                        "_datos": formato in FORMATOS_DE_DATOS
                        and not re.search(r"diccionario|metadato", nombre, re.I)})
    datos = [x for x in limpios if x["_datos"]]
    elegidos = datos[-3:] if datos else limpios[:3]
    return [{k: v for k, v in x.items() if k != "_datos"} for x in elegidos]

def recientes(portal: dict) -> list[dict]:
    base = portal["base"].rstrip("/")
    salida = []
    if portal["tipo"] == "CKAN":
        d = pedir_json(f"{base}/api/3/action/package_search?sort=metadata_modified%20desc&rows={POR_PORTAL}")
        for p in (d.get("result") or {}).get("results", []):
            salida.append({
                "id": f"{portal['iso']}:{p.get('name')}",
                "pais": portal["iso"],
                "titulo": p.get("title") or p.get("name"),
                "descripcion": re.sub(r"\s+", " ", (p.get("notes") or ""))[:250],
                "organismo": (p.get("organization") or {}).get("title", ""),
                "modificado": p.get("metadata_modified", ""),
                "pagina": f"{base}/dataset/{p.get('name')}",
                "recursos": elegir_recursos(p.get("resources")),
            })
    elif portal["tipo"] == "Socrata":
        dominio = urllib.parse.urlparse(base).netloc
        d = pedir_json(f"https://api.us.socrata.com/api/catalog/v1?domains={dominio}"
                       f"&order=updatedAt&limit={POR_PORTAL}&only=datasets")
        for x in d.get("results", []):
            r = x.get("resource", {})
            rid = r.get("id")
            salida.append({
                "id": f"{portal['iso']}:{rid}",
                "pais": portal["iso"],
                "titulo": r.get("name"),
                "descripcion": re.sub(r"\s+", " ", r.get("description") or "")[:250],
                "organismo": r.get("attribution") or "",
                "modificado": r.get("updatedAt", ""),
                "pagina": x.get("permalink") or f"{base}/d/{rid}",
                "recursos": [{"url": f"{base}/resource/{rid}.csv", "formato": "CSV", "nombre": "API CSV"}],
            })
    elif portal["tipo"] == "CKAN-lista":
        # PERÚ Y PARAGUAY no tienen buscador (package_search da 404 o una página), pero
        # sí la lista de conjuntos con sus recursos, ordenada del más reciente al más
        # viejo. Comprobado en vivo el 17/9/2026 en los dos portales.
        d = pedir_json(f"{base}/api/3/action/current_package_list_with_resources?limit={POR_PORTAL}",
                       espera=90)
        lista = d.get("result") or []
        if lista and isinstance(lista[0], list):  # estos portales la devuelven anidada
            lista = lista[0]
        for p in lista[:POR_PORTAL]:
            grupos = p.get("groups") or []
            salida.append({
                "id": f"{portal['iso']}:{p.get('name')}",
                "pais": portal["iso"],
                "titulo": p.get("title") or p.get("name"),
                "descripcion": re.sub(r"<[^>]+>|\s+", " ", (p.get("notes") or ""))[:250],
                "organismo": (grupos[0].get("title") if grupos and isinstance(grupos[0], dict) else "") or "",
                "modificado": p.get("metadata_modified", ""),
                "pagina": f"{base}/dataset/{urllib.parse.quote(p.get('name') or '')}",
                "recursos": elegir_recursos(p.get("resources")),
            })
    return salida


# ─────────────────────────── 2 · Llama ───────────────────────────

def _version(nombre: str) -> float:
    m = re.findall(r"(\d+(?:\.\d+)?)", nombre)
    return float(m[0]) if m else 0.0


def elegir_groq(clave: str) -> str | None:
    ids = [m["id"] for m in pedir_json("https://api.groq.com/openai/v1/models",
                                       {"Authorization": "Bearer " + clave}).get("data", [])
           if m.get("active", True)]
    ids = [i for i in ids if not re.search(r"guard|prompt|whisper|tts|compound", i, re.I)]
    # LLAMA PRIMERO, Y SI NO ESTÁ, OTRO MODELO DE PESOS ABIERTOS. El 17/9/2026 Groq
    # tenía Llama sólo en su plan empresarial: con cuenta gratuita no aparece. En ese
    # caso se usa GPT-OSS (OpenAI, licencia Apache 2.0) o Qwen (Alibaba), que Groq sí
    # sirve gratis. Cada propuesta deja escrito qué modelo la clasificó.
    for patron in (r"llama-4", r"llama-3\.\d-70b", r"llama", r"gpt-oss-120b", r"gpt-oss", r"qwen"):
        hallados = [i for i in ids if re.search(patron, i, re.I)]
        if hallados:
            return sorted(hallados, key=_version, reverse=True)[0]
    print("  Groq no ofrece modelos abiertos a esta cuenta. Disponibles:", ", ".join(ids)[:300], file=sys.stderr)
    return None


def elegir_cloudflare(cuenta: str, token: str) -> str | None:
    d = pedir_json(f"https://api.cloudflare.com/client/v4/accounts/{cuenta}/ai/models/search?search=llama",
                   {"Authorization": "Bearer " + token})
    nombres = [m.get("name", "") for m in d.get("result", [])]
    nombres = [n for n in nombres if re.search(r"llama", n, re.I) and not re.search(r"guard|vision", n, re.I)]
    for patron in (r"llama-4", r"llama-3\.\d-70b", r"llama"):
        hallados = [n for n in nombres if re.search(patron, n, re.I)]
        if hallados:
            return sorted(hallados, key=_version, reverse=True)[0]
    return None


def conversar(sistema: str, usuario: str) -> tuple[str, str]:
    """Devuelve (texto, «servicio · modelo»). LLAMA PRIMERO: la dirección pidió Llama
    (17/9/2026) y Groq sólo lo da en plan pago. Si están las claves de Cloudflare,
    clasifica Llama ahí; Groq queda de respaldo."""
    groq = os.environ.get("GROQ_API_KEY")
    cuenta, token = os.environ.get("CLOUDFLARE_ACCOUNT_ID"), os.environ.get("CLOUDFLARE_API_TOKEN")
    if cuenta and token:
        try:
            modelo = elegir_cloudflare(cuenta, token)
            if modelo:
                d = pedir_json(f"https://api.cloudflare.com/client/v4/accounts/{cuenta}/ai/run/{modelo}",
                               {"Authorization": "Bearer " + token},
                               {"messages": [{"role": "system", "content": sistema},
                                             {"role": "user", "content": usuario}],
                                "temperature": 0, "max_tokens": 2048}, espera=120)
                respuesta = (d.get("result") or {}).get("response", "")
                if not isinstance(respuesta, str):  # algunos modelos ya devuelven el objeto
                    respuesta = json.dumps(respuesta, ensure_ascii=False)
                if respuesta:
                    return respuesta, "Cloudflare · " + modelo
            else:
                print("  Cloudflare no ofrece Llama a esta cuenta.", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print("  Cloudflare no respondió:", type(e).__name__, str(e)[:120], file=sys.stderr)
    if groq:
        try:
            modelo = elegir_groq(groq)
            if modelo:
                cuerpo = {"model": modelo, "temperature": 0, "response_format": {"type": "json_object"},
                          "messages": [{"role": "system", "content": sistema},
                                       {"role": "user", "content": usuario}]}
                try:
                    d = pedir_json("https://api.groq.com/openai/v1/chat/completions",
                                   {"Authorization": "Bearer " + groq}, cuerpo, espera=120)
                except urllib.error.HTTPError as e:
                    if e.code != 400:
                        raise
                    # Hay modelos que no aceptan el modo JSON: se pide igual, sin él.
                    cuerpo.pop("response_format")
                    d = pedir_json("https://api.groq.com/openai/v1/chat/completions",
                                   {"Authorization": "Bearer " + groq}, cuerpo, espera=120)
                return d["choices"][0]["message"]["content"], "Groq · " + modelo
        except Exception as e:  # noqa: BLE001
            print("  Groq no respondió:", type(e).__name__, str(e)[:120], file=sys.stderr)
    if not groq and not (cuenta and token):
        raise RuntimeError("No hay clave de Groq ni de Cloudflare cargada en el repositorio.")
    raise RuntimeError("Hay clave, pero ningún servicio ofreció un modelo abierto que responda. Ver el detalle arriba.")


SISTEMA = """Sos un asistente de catalogación de datos públicos. Trabajás para SIWA, un
registro público de indicadores de los 33 Estados de América Latina y el Caribe.
Tu tarea es SOLO clasificar conjuntos de datos que ya existen en portales oficiales.

Reglas estrictas:
- No inventes nada. Si un dato no está en lo que se te da, poné null.
- El campo "enlace" tiene que ser EXACTAMENTE una de las direcciones de "recursos"
  del conjunto. Si ninguna sirve, poné null.
- Marcá "sirve": true sólo si el conjunto mide algo de uno de los temas de la lista,
  con alcance nacional o por provincia/departamento, y trae cifras (no sólo texto).
- "tema" tiene que ser una "clave" de la lista de temas, o null.
- "periodo" es el último año o mes que cubre, sólo si surge del título, la
  descripción o los recursos; si no, null.

Respondé SOLO un objeto JSON con esta forma:
{"conjuntos": [{"id": "...", "sirve": true|false, "tema": "clave"|null,
  "periodo": "..."|null, "formato": "..."|null, "enlace": "..."|null,
  "motivo": "una línea en castellano"}]}"""


def normalizar(respuesta) -> list[dict]:
    """LOS MODELOS NO SIEMPRE RESPETAN LA FORMA PEDIDA. El 17/9/2026 una tanda volvió
    con la lista de conjuntos como textos en vez de objetos, y el robot se cayó entero.
    Se aceptan las formas razonables —lista de objetos, objetos escritos como texto,
    objeto con los identificadores como claves— y lo que no se entiende se descarta
    y se declara, sin tirar abajo la corrida."""
    items = respuesta.get("conjuntos", respuesta) if isinstance(respuesta, dict) else respuesta
    if isinstance(items, dict):
        items = [dict(v, id=v.get("id", k)) if isinstance(v, dict) else v for k, v in items.items()]
    salida = []
    for x in items if isinstance(items, list) else []:
        if isinstance(x, str):
            try:
                x = json.loads(x)
            except Exception:  # noqa: BLE001
                continue
        if isinstance(x, dict) and x.get("id"):
            salida.append(x)
    if not salida:
        print("  una tanda no trajo conjuntos con forma legible", file=sys.stderr)
    return salida


def clasificar(conjuntos: list[dict], temas: list[dict]) -> tuple[list[dict], str]:
    lista_temas = "\n".join(f"{t['clave']} = {t['nombre']} ({t['grupo']})" for t in temas)
    todos, servicio = [], ""
    for i in range(0, len(conjuntos), POR_LLAMADA):
        tanda = conjuntos[i:i + POR_LLAMADA]
        usuario = ("TEMAS DE SIWA (clave = nombre):\n" + lista_temas +
                   "\n\nCONJUNTOS A CLASIFICAR:\n" +
                   json.dumps([{k: c[k] for k in ("id", "pais", "titulo", "descripcion", "organismo",
                                                   "modificado", "recursos")} for c in tanda],
                              ensure_ascii=False))
        if i:
            import time
            time.sleep(PAUSA_ENTRE_PEDIDOS)
        texto, servicio = conversar(SISTEMA, usuario)
        try:
            bloque = texto[texto.index("{"): texto.rindex("}") + 1]
            todos.extend(normalizar(json.loads(bloque)))
        except Exception:  # noqa: BLE001 — una tanda ilegible se declara y se sigue
            print("  respuesta ilegible en la tanda", i // POR_LLAMADA + 1, "·", texto[:200].replace(chr(10), " "),
                  file=sys.stderr)
    return todos, servicio


# ─────────────────────────── 3 · una serie, una propuesta ───────────────────────────

_VACIAS = set("""de del la las el los en y o por a al con para sobre segun e u
enero febrero marzo abril mayo junio julio agosto septiembre setiembre octubre noviembre diciembre
teu unidades unidad total totales mensual anual trimestral semestral periodo""".split())


def raiz_de_serie(titulo: str) -> str:
    """El 17/9/2026 salieron cinco propuestas que eran una sola serie: movimiento de
    contenedores de Panamá en TEU y en unidades, por tipo y por destino. La raíz es el
    comienzo del título sin fechas, meses, unidades ni desagregaciones."""
    t = unicodedata.normalize("NFKD", titulo or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", t)
    t = re.split(r"\bpor\b", t)[0]
    palabras = [w for w in re.findall(r"[a-z]+", t) if w not in _VACIAS and len(w) > 1]
    return " ".join(palabras[:4])


def agrupar(propuestas: list[dict]) -> list[dict]:
    grupos: dict[tuple, dict] = {}
    for x in propuestas:
        clave = (x["pais"], x["tema"], raiz_de_serie(x["titulo"]))
        if clave not in grupos:
            grupos[clave] = {**x, "variantes": []}
        else:
            grupos[clave]["variantes"].append({k: x[k] for k in ("titulo", "pagina", "enlace", "periodo")})
    return list(grupos.values())


# ─────────────────────────── 4 · la corrida ───────────────────────────

def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="propuestas")
    ap.add_argument("--sin-ia", action="store_true", help="prueba del circuito sin llamar a Llama")
    ap.add_argument("--portal", help="ISO de un portal puntual, para probar")
    a = ap.parse_args()

    oficiales = json.loads((AQUI / "oficiales.json").read_text(encoding="utf-8"))
    temas = json.loads((AQUI / "temas_siwa.json").read_text(encoding="utf-8"))["temas"]
    claves = {t["clave"] for t in temas}
    nombre_tema = {t["clave"]: t["nombre"] for t in temas}

    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    vistos_f = salida / "vistos.json"
    vistos = set(json.loads(vistos_f.read_text(encoding="utf-8"))) if vistos_f.exists() else set()

    leibles = ("CKAN", "Socrata", "CKAN-lista")
    buscables = [p for p in oficiales["portales"] if p["tipo"] in leibles]
    no_cubiertos = [p["iso"] for p in oficiales["portales"] if p["tipo"] not in leibles]
    hoy = dt.date.today()
    if a.portal:
        elegidos = [p for p in buscables if p["iso"] == a.portal]
    else:
        arranque = hoy.toordinal() % len(buscables)
        elegidos = [buscables[(arranque + k) % len(buscables)] for k in range(PORTALES_POR_CORRIDA)]

    candidatos, fallas = [], []
    for p in elegidos:
        try:
            nuevos = [c for c in recientes(p) if c["id"] not in vistos]
            candidatos.extend(nuevos)
            print(f"{p['iso']}: {len(nuevos)} conjuntos nuevos para mirar")
        except Exception as e:  # noqa: BLE001
            fallas.append(f"{p['iso']} ({p['base']}): {type(e).__name__}")

    propuestas, descartadas, servicio = [], 0, "sin IA (prueba)"
    if candidatos and not a.sin_ia:
        clasif, servicio = clasificar(candidatos, temas)
        por_id = {c["id"]: c for c in candidatos}
        for k in clasif:
            c = por_id.get(k.get("id"))
            if not c or not k.get("sirve"):
                descartadas += 1
                continue
            permitidos = {r["url"] for r in c["recursos"]}
            enlace = k.get("enlace")
            tema = k.get("tema")
            # Lo que Llama no puede hacer pasar: un enlace que el portal no publicó
            # o un tema que SIWA no tiene.
            if enlace not in permitidos or tema not in claves:
                descartadas += 1
                continue
            prueba = comprobar(enlace)
            if not prueba["responde"]:
                descartadas += 1
                continue
            propuestas.append({**{x: c[x] for x in ("pais", "titulo", "organismo", "modificado", "pagina")},
                               "tema": tema, "tema_nombre": nombre_tema[tema], "periodo": k.get("periodo"),
                               "formato": k.get("formato"), "enlace": enlace, "motivo": k.get("motivo"),
                               "comprobacion": prueba, "calificacion": "SIN CALIFICAR — la hace una persona"})
    elif a.sin_ia:
        # En la prueba sin IA sólo se comprueban los enlaces, para validar el circuito.
        for c in candidatos[:5]:
            if c["recursos"]:
                print("  comprobación", c["recursos"][0]["url"][:90], "→", comprobar(c["recursos"][0]["url"]))

    archivos = len(propuestas)
    propuestas = agrupar(propuestas)
    sello = hoy.isoformat()
    if not a.sin_ia:
        vistos.update(c["id"] for c in candidatos)
        vistos_f.write_text(json.dumps(sorted(vistos), ensure_ascii=False, indent=0), encoding="utf-8")
    # Dos corridas el mismo día (la programada y una a mano) no se pisan: el archivo
    # lleva también los países mirados.
    archivo = f"{sello}-{'-'.join(p['iso'] for p in elegidos)}"
    (salida / f"{archivo}.json").write_text(json.dumps(
        {"fecha": sello, "servicio": servicio, "portales": [p["iso"] for p in elegidos],
         "mirados": len(candidatos), "archivos_aceptados": archivos, "propuestas": propuestas, "descartadas": descartadas,
         "fallas": fallas, "no_cubiertos": no_cubiertos}, ensure_ascii=False, indent=1), encoding="utf-8")

    renglones = [f"# Propuestas de fuentes · {sello}", "",
                 f"Portales mirados: {', '.join(p['iso'] for p in elegidos)} · conjuntos nuevos: {len(candidatos)} · "
                 f"clasificó: {servicio}", "",
                 f"**{len(propuestas)} propuestas** ({archivos} archivos: los que son la misma serie van juntos), "
                 f"{descartadas} descartadas. Ninguna está incorporada ni calificada.", ""]
    for x in propuestas:
        renglones += [f"- **{x['pais']} · {x['tema_nombre']}** — {x['titulo']}",
                      f"  {x['organismo']} · período {x['periodo'] or 's/d'} · {x['formato'] or 's/d'}",
                      f"  {x['enlace']}", f"  Motivo: {x['motivo']}"]
        for v in x["variantes"]:
            renglones.append(f"  · misma serie: {v['titulo']} — {v['enlace']}")
        renglones.append("")
    if fallas:
        renglones += ["**Portales que no respondieron:** " + "; ".join(fallas), ""]
    if no_cubiertos:
        renglones += [f"Sin cobertura en esta etapa: {', '.join(no_cubiertos)}."]
    (salida / f"{archivo}.md").write_text("\n".join(renglones) + "\n", encoding="utf-8")
    print(f"{len(propuestas)} propuestas ({archivos} archivos) · {descartadas} descartadas · {servicio}")


if __name__ == "__main__":
    principal()
