"""Circulación en red social abierta.

Qué mide y qué NO mide
----------------------
Mide **cuánto se habla** de cada Estado del padrón en una red social abierta, y
**con qué palabras**. No mide qué ocurre, ni con qué signo, ni si lo que circula
es cierto. Una publicación en una red no es una fuente: es un indicio de
circulación, y así entra al registro.

Por qué Mastodon y no otra red
------------------------------
De las redes probadas el 31 de agosto de 2026, es la única que expone una
interfaz pública documentada, sin credencial y sin restricción de uso
automatizado:

- **X (Twitter)** — la interfaz devuelve 401 sin clave. No hay nivel gratuito de
  búsqueda: el más barato es pago y mensual. Queda fuera hasta que la Dirección
  resuelva contratarlo.
- **Reddit** — devuelve 403 al acceso automatizado anónimo. Exige registrar una
  aplicación y firmar condiciones de uso.
- **Telegram** — la vista web de canal público responde, pero leerla de forma
  sistemática es raspado y `doctrina/limites.md` lo condiciona a dictamen legal
  previo, que todavía no se emitió.
- **Bluesky** — la búsqueda pública devolvió 403 sin sesión.

**Sesgo declarado, y es grande.** Mastodon no es representativo de la
conversación pública de América Latina y el Caribe: su base de usuarios es
pequeña, europea y norteamericana en su mayoría, y de perfil técnico. Lo que
este colector observa es una **muestra sesgada y no probabilística**. Sirve para
detectar que un asunto empezó a circular; no sirve para medir cuánto importa.
Ningún juicio de la Fundación puede apoyarse solo en esto.
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import comun
import geo

# Cuatro instancias grandes e independientes entre sí. Se consultan todas y se
# unen los resultados: una sola instancia vería solo lo que federa.
INSTANCIAS = ("mastodon.social", "mstdn.social", "masto.ai", "mas.to")
HORAS = 48
POR_CONSULTA = 40
TOPE_PALABRAS = 25
MINIMO_PORTALES = 2   # una palabra debe salir de dos instancias distintas
NAVEGADOR = comun.AGENTE
PADRON_GENTILICIOS = Path(__file__).resolve().parent / "gentilicios.json"

VACIAS = {
    "para", "como", "pero", "porque", "cuando", "donde", "sobre", "entre", "desde",
    "hasta", "tambien", "todos", "todas", "este", "esta", "estos", "estas", "esto",
    "otro", "otra", "mismo", "hacer", "tiene", "tienen", "puede", "pueden", "https",
    "http", "www", "the", "and", "for", "with", "that", "this", "from", "have",
    "will", "they", "their", "what", "about", "which", "were", "been", "more",
    "para", "mais", "como", "pelo", "pela", "isso", "esse", "essa", "dos", "das",
    "muito", "quando", "sobre", "ainda", "apos", "seus", "suas", "nao", "por",
}


def _sin_marcas(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def _palabras(html: str) -> list:
    """Texto plano de una publicación, normalizado a minúsculas sin tildes."""
    texto = re.sub(r"<[^>]+>", " ", html or "")
    texto = re.sub(r"https?://\S+", " ", texto)
    return re.findall(r"[a-z0-9]{4,}", _sin_marcas(texto).lower())


def _buscar(tarea: tuple) -> tuple:
    """Trae la línea pública de una etiqueta en una instancia."""
    instancia, etiqueta = tarea
    url = (f"https://{instancia}/api/v1/timelines/tag/"
           f"{urllib.parse.quote(etiqueta)}?limit={POR_CONSULTA}")
    try:
        peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
        with urllib.request.urlopen(peticion, timeout=40) as respuesta:
            return instancia, etiqueta, json.loads(respuesta.read().decode("utf-8", "replace")), None
    except urllib.error.HTTPError as error:
        return instancia, etiqueta, [], f"HTTP {error.code}"
    except Exception as error:  # noqa: BLE001 — la falla se declara, no se oculta
        return instancia, etiqueta, [], type(error).__name__


def _etiquetas(padron: list) -> dict:
    """Una etiqueta por Estado: el nombre sin espacios ni tildes."""
    return {p["iso"]: _sin_marcas(p["pais"]).replace(" ", "").replace("-", "").lower()
            for p in padron}


def recolectar():
    padron = geo.padron()
    etiquetas = _etiquetas(padron)
    nombres = {p["iso"]: p["pais"] for p in padron}
    bloques = {p["iso"]: p["bloque"] for p in padron}

    tareas = [(i, e) for e in etiquetas.values() for i in INSTANCIAS]
    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        crudo = list(ejecutor.map(_buscar, tareas))

    caidas = Counter(f"{i}: {f}" for i, _, _, f in crudo if f)
    corte = datetime.now(timezone.utc) - timedelta(hours=HORAS)
    por_iso = {iso: [] for iso in etiquetas}
    inverso = {e: iso for iso, e in etiquetas.items()}

    vistos = set()
    for instancia, etiqueta, publicaciones, falla in crudo:
        if falla:
            continue
        iso = inverso.get(etiqueta)
        for pub in publicaciones:
            uri = pub.get("uri") or pub.get("url")
            # Las instancias federan entre sí: la misma publicación aparece en
            # varias. Se cuenta una sola vez, o el volumen quedaría inflado.
            if not uri or (iso, uri) in vistos:
                continue
            vistos.add((iso, uri))
            try:
                momento = datetime.fromisoformat(
                    (pub.get("created_at") or "").replace("Z", "+00:00"))
            except ValueError:
                momento = None
            if momento and momento < corte:
                continue
            cuenta = (pub.get("account") or {})
            por_iso[iso].append({
                "instancia": instancia,
                "cuenta": cuenta.get("acct", ""),
                "idioma": pub.get("language") or "?",
                "texto": pub.get("content", ""),
                "momento": momento.isoformat() if momento else None,
            })

    registros, sin_circulacion = [], []
    for iso, pubs in sorted(por_iso.items()):
        if not pubs:
            sin_circulacion.append(nombres[iso])
        contador, instancias_de = Counter(), {}
        for p in pubs:
            for palabra in set(_palabras(p["texto"])):
                if palabra in VACIAS or palabra == etiquetas[iso] or palabra.isdigit():
                    continue
                contador[palabra] += 1
                instancias_de.setdefault(palabra, set()).add(p["instancia"])
        palabras = [{"palabra": t, "publicaciones": n, "instancias": len(instancias_de[t])}
                    for t, n in contador.most_common(TOPE_PALABRAS * 4)
                    if n >= 2 and len(instancias_de[t]) >= MINIMO_PORTALES][:TOPE_PALABRAS]
        registros.append({
            "iso": iso,
            "pais": nombres[iso],
            "bloque": bloques[iso],
            "etiqueta": "#" + etiquetas[iso],
            "publicaciones": len(pubs),
            "cuentas_distintas": len({p["cuenta"] for p in pubs}),
            "instancias_que_lo_vieron": len({p["instancia"] for p in pubs}),
            "idiomas": sorted({p["idioma"] for p in pubs}),
            "palabras": palabras,
        })

    con_dato = sum(1 for r in registros if r["publicaciones"])
    vacios = [
        "Mastodon NO es representativo de la conversación pública de la región: su "
        "base de usuarios es pequeña, mayoritariamente europea y norteamericana y de "
        "perfil técnico. Lo que se observa es una muestra sesgada y no probabilística. "
        "Ningún juicio de la Fundación puede apoyarse solo en este registro.",
        f"Sin circulación en la ventana de {HORAS} h: "
        + (", ".join(sin_circulacion) if sin_circulacion else "ninguno")
        + ". Ausencia de publicaciones no es ausencia de hechos.",
        "X (Twitter) queda fuera: la interfaz devuelve 401 sin clave y no existe nivel "
        "gratuito de búsqueda. Incorporarlo exige contratar el servicio, que es pago y "
        "mensual: es una decisión de la Dirección, no un problema técnico.",
        "Reddit queda fuera: devuelve 403 al acceso anónimo automatizado y exige "
        "registrar una aplicación y aceptar sus condiciones de uso.",
        "Telegram queda fuera: la vista web de canal público responde, pero leerla de "
        "forma sistemática es raspado y doctrina/limites.md lo condiciona a dictamen "
        "legal previo, que no se emitió.",
        "Bluesky queda fuera: la búsqueda pública devolvió 403 sin sesión iniciada.",
    ]
    if caidas:
        vacios.append("Consultas que fallaron: "
                      + "; ".join(f"{k} ({n})" for k, n in caidas.most_common()))

    calificacion = comun.calificar(
        fiabilidad="F",
        credibilidad=4,
        corroborado=False,
        nota=("Publicaciones de personas sin identidad verificada. Se registra la "
              "CIRCULACIÓN, que sí se observa directamente, no el contenido, que no "
              "está verificado. Un término que circula mucho no es un hecho."),
    )

    return comun.escribir(
        colector="redes",
        capa="publico",
        fuente="Mastodon — instancias " + ", ".join(INSTANCIAS),
        url_fuente="https://docs.joinmastodon.org/methods/timelines/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "instancias_consultadas": len(INSTANCIAS),
                "estados_con_circulacion": con_dato,
                "estados_del_padron": len(registros),
                "publicaciones_unicas": len(vistos),
                "ventana_horas": HORAS,
            },
            "metodo": (
                "Se consulta la línea pública de la etiqueta de cada Estado en cuatro "
                "instancias independientes. Las instancias federan entre sí, de modo que "
                "cada publicación se cuenta UNA sola vez por su dirección única. Un "
                "término figura en el mapa solo si aparece en dos publicaciones y en dos "
                "instancias distintas: lo que sale de una sola instancia es eco, no "
                "circulación."
            ),
            "que_no_mide": (
                "No mide qué ocurre, ni con qué signo, ni si lo que circula es cierto. "
                "No es una encuesta ni una medición de opinión pública."
            ),
        },
    )


if __name__ == "__main__":
    comun.correr("redes", recolectar)
