"""Cobertura noticiosa cruzada — padrón propio de medios.

**Esto no registra hechos: registra que algo se está publicando.** Un
acontecimiento cubierto por diez portales no está probado; está difundido. La
cobertura entra como señal de atención y como segundo origen para corroborar lo
que otra fuente ya registró, nunca como dato acreditado por sí sola.

Agrupa notas de distintos medios que hablan del mismo asunto y cuenta
**orígenes independientes**, no portales, conforme a `doctrina/fuentes.md` §2 y
a la regla de cruce de `doctrina/siwa.md` §4:

> Un hecho no alcanza corroboración plena si sus dos fuentes son del mismo
> idioma **y** del mismo país.

El agrupamiento se hace con estadística clásica —frecuencia de término,
frecuencia inversa de documento y similitud del coseno— escrita con biblioteca
estándar. **No interviene ningún modelo de lenguaje.**

El padrón de medios vive en `colectores/medios.json`, es editable por el equipo
analítico y no se toca desde el código.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import comun

PADRON_MEDIOS = Path(__file__).resolve().parent / "medios.json"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
UMBRAL = 0.32          # similitud mínima para considerar que dos notas hablan de lo mismo
POR_MEDIO = 40         # notas más recientes que se toman de cada canal
HORAS = 48
MINIMO_TOKENS = 3

# Palabras vacías de los cuatro idiomas del padrón vigente. No son un modelo:
# son una lista fija que el equipo puede editar.
VACIAS = set("""
de la el los las un una unos unas y o u en a al del con por para sin sobre entre
que se su sus lo le les es son fue fueron ser esta este estos estas ha han hay
como mas más pero ya no si sí tras desde hasta durante ante bajo cabe
da do das dos das em na no nas nos uma umas uns pelo pela pelos pelas ao aos
the of and to in for on with at from by as is are was were be been it its this
that these those has have had will would can could
le la les des du de et ou en un une dans pour par sur avec sans sous chez est
sont ete été a au aux ce ces cette il elle ils elles qui que quoi dont
""".split())


def _normalizar(texto: str) -> list:
    """Baja a minúsculas, quita tildes y devuelve palabras útiles."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    palabras = re.findall(r"[a-z0-9ñ]+", texto)
    return [p for p in palabras if len(p) > 2 and p not in VACIAS]


def _fecha(texto: str):
    if not texto:
        return None
    for formato in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                    "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            f = datetime.strptime(texto.strip(), formato)
            return f if f.tzinfo else f.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _traer_canal(medio: dict) -> tuple:
    """Lee un canal. Devuelve (medio, notas, falla)."""
    ATOM = "{http://www.w3.org/2005/Atom}"
    try:
        peticion = urllib.request.Request(
            medio["canal"],
            headers={"User-Agent": NAVEGADOR,
                     "Accept": "application/rss+xml, application/xml, text/xml, */*"},
        )
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            raiz = ET.fromstring(respuesta.read(600_000))
    except Exception as error:  # noqa: BLE001 — la falla del canal se declara, no se oculta
        return (medio, [], f"{type(error).__name__}")

    notas = []
    entradas = raiz.findall(".//item") or raiz.findall(f".//{ATOM}entry")
    for entrada in entradas[:POR_MEDIO]:
        titulo = entrada.findtext("title") or entrada.findtext(f"{ATOM}title") or ""
        enlace = entrada.findtext("link") or ""
        if not enlace:
            ref = entrada.find(f"{ATOM}link")
            enlace = ref.get("href") if ref is not None else ""
        publicada = _fecha(entrada.findtext("pubDate") or entrada.findtext(f"{ATOM}updated") or "")
        if not titulo.strip():
            continue
        notas.append({
            "titulo": titulo.strip(),
            "enlace": enlace.strip(),
            "publicada": publicada.isoformat() if publicada else None,
            "momento": publicada,
            "dominio": medio["dominio"],
            "medio": medio["nombre"],
            "pais": medio["pais"],
            "idioma": medio["idioma"],
            "fiabilidad": medio.get("fiabilidad", "F"),
        })
    return (medio, notas, None)


def _vectores(notas: list) -> list:
    """Frecuencia de término por frecuencia inversa de documento, normalizada."""
    documentos = [_normalizar(n["titulo"]) for n in notas]
    apariciones = Counter()
    for doc in documentos:
        apariciones.update(set(doc))
    total = len(documentos)
    vectores = []
    for doc in documentos:
        frecuencias = Counter(doc)
        vector = {}
        for palabra, veces in frecuencias.items():
            idf = math.log((1 + total) / (1 + apariciones[palabra])) + 1
            vector[palabra] = (veces / len(doc)) * idf
        norma = math.sqrt(sum(v * v for v in vector.values())) or 1.0
        vectores.append({p: v / norma for p, v in vector.items()})
    return vectores


def _coseno(a: dict, b: dict) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(peso * b.get(palabra, 0.0) for palabra, peso in a.items())


def _agrupar(notas: list) -> list:
    """Enlace simple: cada nota entra al primer grupo con el que supera el umbral."""
    vectores = _vectores(notas)
    grupos = []
    for i, nota in enumerate(notas):
        if len(vectores[i]) < MINIMO_TOKENS:
            continue
        destino = None
        for grupo in grupos:
            if any(_coseno(vectores[i], vectores[j]) >= UMBRAL for j in grupo["indices"]):
                destino = grupo
                break
        if destino is None:
            grupos.append({"indices": [i], "notas": [nota]})
        else:
            destino["indices"].append(i)
            destino["notas"].append(nota)
    return grupos


def _corroboracion(notas: list) -> dict:
    """Cuenta orígenes, no portales, y aplica la regla de cruce del §4."""
    idiomas = {n["idioma"] for n in notas}
    paises = {n["pais"] for n in notas}
    origenes = {(n["pais"], n["idioma"]) for n in notas}

    if len(idiomas) >= 2:
        estado, nota = "corroborado_fuerte", "Dos o más idiomas distintos."
    elif len(paises) >= 2:
        estado, nota = "corroborado", "Dos o más jurisdicciones, un solo idioma."
    else:
        estado, nota = "origen_unico", (
            "Todos los medios son del mismo país y del mismo idioma: cuentan como "
            "un solo origen, por más portales que sean."
        )
    return {
        "estado": estado,
        "nota": nota,
        "origenes_independientes": len(origenes),
        "portales": len({n["dominio"] for n in notas}),
        "idiomas": sorted(idiomas),
        "paises": sorted(paises),
    }


def recolectar():
    padron = json.loads(PADRON_MEDIOS.read_text(encoding="utf-8"))["medios"]

    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        resultados = list(ejecutor.map(_traer_canal, padron))

    caidos = [f"{m['nombre']} ({m['pais']}): {f}" for m, _, f in resultados if f]
    notas = [n for _, lista, _ in resultados for n in lista]

    corte = datetime.now(timezone.utc) - timedelta(hours=HORAS)
    recientes = [n for n in notas if n["momento"] is None or n["momento"] >= corte]
    sin_fecha = sum(1 for n in recientes if n["momento"] is None)
    for n in recientes:
        n.pop("momento", None)

    grupos = _agrupar(recientes)
    eventos = []
    for grupo in grupos:
        lista = grupo["notas"]
        if len(lista) < 2:
            continue                      # una sola nota no es cobertura cruzada
        corr = _corroboracion(lista)
        eventos.append({
            "asunto": max((n["titulo"] for n in lista), key=len),
            "corroboracion": corr,
            "notas": [
                {k: n[k] for k in ("titulo", "enlace", "medio", "dominio", "pais", "idioma", "publicada")}
                for n in lista
            ],
        })

    orden = {"corroborado_fuerte": 0, "corroborado": 1, "origen_unico": 2}
    eventos.sort(key=lambda e: (orden[e["corroboracion"]["estado"]],
                                -e["corroboracion"]["origenes_independientes"]))

    conteo = Counter(e["corroboracion"]["estado"] for e in eventos)
    idiomas_padron = Counter(m["idioma"] for m in padron)
    paises_padron = {m["pais"] for m in padron}

    calificacion = comun.calificar(
        fiabilidad="F",
        credibilidad=3,
        corroborado=False,
        nota=(
            "Fiabilidad NO EVALUADA: ningún medio del padrón tiene todavía calificación "
            "asignada por el equipo analítico. Credibilidad 3 —posiblemente cierta, sin "
            "corroboración— porque lo registrado es la existencia de cobertura, no el "
            "hecho cubierto. Este material no sostiene juicio alguno."
        ),
    )

    vacios = [
        "LO REGISTRADO ES COBERTURA, NO HECHOS. Que diez portales publiquen algo no "
        "prueba que haya ocurrido: prueba que se está publicando. Sirve como señal de "
        "atención y como segundo origen, nunca como dato acreditado.",
        "La fiabilidad de cada medio está sin evaluar. Hasta que el equipo analítico "
        "asigne la letra del Almirantazgo a cada dominio, ninguna nota puede sostener "
        "un juicio.",
        "El agrupamiento es por similitud de texto y falla en los dos sentidos: puede "
        "unir dos asuntos distintos que comparten palabras, y puede separar el mismo "
        "asunto contado con vocabulario diferente.",
        (
            f"El padrón tiene {len(padron)} medios verificados en "
            f"{len(paises_padron)} jurisdicciones. **{33 - len({p for p in paises_padron if len(p) == 3})} "
            "Estados del padrón no tienen medio propio en el registro**, y el Caribe "
            "angloparlante es el bloque peor cubierto."
        ),
        (
            "Idiomas presentes: "
            + ", ".join(f"{i} ({n})" for i, n in sorted(idiomas_padron.items()))
            + ". Faltan el neerlandés de Surinam y el criollo haitiano, exigidos por "
            "doctrina/siwa.md §4.1."
        ),
        f"Ventana de {HORAS} horas. {sin_fecha} notas llegaron sin fecha de publicación "
        "y se conservaron sin poder verificar su antigüedad.",
        "Un grupo de una sola nota no se publica: sin cruce no hay cobertura cruzada.",
    ]
    if caidos:
        vacios.append(
            f"{len(caidos)} canales no respondieron en esta corrida: {'; '.join(caidos)}."
        )

    return comun.escribir(
        colector="cobertura",
        capa="publico",
        fuente="Padrón de medios de la Fundación Sherman Kent",
        url_fuente="colectores/medios.json",
        calificacion=calificacion,
        registros=eventos,
        vacios=vacios,
        extra={
            "resumen": {
                "medios_consultados": len(padron),
                "medios_que_respondieron": len(padron) - len(caidos),
                "notas_leidas": len(notas),
                "notas_en_ventana": len(recientes),
                "asuntos_con_cruce": len(eventos),
                "corroborado_fuerte": conteo.get("corroborado_fuerte", 0),
                "corroborado": conteo.get("corroborado", 0),
                "origen_unico": conteo.get("origen_unico", 0),
            },
            "umbral_similitud": UMBRAL,
            "metodo": (
                "Frecuencia de término por frecuencia inversa de documento y similitud "
                "del coseno sobre los títulos, con enlace simple. Sin modelos de lenguaje."
            ),
        },
    )


if __name__ == "__main__":
    comun.correr("cobertura", recolectar)
