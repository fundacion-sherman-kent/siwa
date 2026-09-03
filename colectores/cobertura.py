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
import geo

TOPE_PALABRAS = 40   # términos por ámbito en el mapa de palabras
PADRON_MEDIOS = Path(__file__).resolve().parent / "medios.json"
PADRON_FRONTERAS = Path(__file__).resolve().parent / "fronteras.json"
PADRON_TEMAS = Path(__file__).resolve().parent / "temas.json"
PADRON_GENTILICIOS = Path(__file__).resolve().parent / "gentilicios.json"
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
                     "Accept": "applicatión/rss+xml, applicatión/xml, text/xml, */*"},
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
            "tipo": medio.get("tipo", "prensa"),
        })
    return (medio, notas, None)


def _paises_mencionados(texto: str, mapa: dict) -> list:
    """Estados del padrón nombrados en el título.

    Se busca el nombre y sus gentilicios sobre el texto normalizado. Es un
    reconocimiento por diccionario, no por comprensión: un asunto que nombre al
    país con un giro que no figure en la lista queda sin atribuir, y uno que lo
    nombre al pasar queda atribuido igual. Ambas fallas se declaran.
    """
    plano = " " + " ".join(_normalizar_crudo(texto)) + " "
    hallados = []
    for iso, formas in mapa.items():
        if any(f" {f} " in plano for f in formas):
            hallados.append(iso)
    return hallados


def _normalizar_crudo(texto: str) -> list:
    """Como _normalizar pero conserva las palabras vacías: los nombres las usan."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.findall(r"[a-z0-9]+", t)


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


def _fronteras(notas: list, zonas: list, gentilicios: dict) -> list:
    """Cuánto se habla de cada zona de frontera, y con qué corroboración.

    NO mide qué ocurre en la zona: ninguna fuente publica estadística comparable
    a esa escala. Mide cuántas notas del corpus la nombran.

    Una nota entra a una zona por dos caminos. **Por topónimo** —Darién, Cúcuta,
    Ciudad del Este—, que es el reconocimiento preciso. O **por palabra de
    frontera más dos de los Estados que la comparten**: la primera versión solo
    miraba topónimos y dejaba afuera titulares como *«Entre fronteiras e Estados:
    mineração ilegal na Amazônia»*, que es exactamente lo que hay que ver.
    """
    FRONTERA = ("frontera", "fronteras", "fronteira", "fronteiras", "border",
                "borders", "frontiere", "transfronteriza", "transfronterizo",
                "trifronteriza", "triple frontera")
    salida = []
    for zona in zonas:
        terminos = [" ".join(_normalizar_crudo(t)) for t in zona["terminos"]]
        formas = {iso: [" ".join(_normalizar_crudo(f)) for f in gentilicios.get(iso, [])]
                  for iso in zona["estados"]}
        halladas, por_toponimo = [], 0
        for n in notas:
            plano = " " + " ".join(_normalizar_crudo(n["titulo"])) + " "
            toponimo = any(f" {t} " in plano for t in terminos if t)
            if toponimo:
                halladas.append(n)
                por_toponimo += 1
                continue
            if any(f" {f} " in plano for f in FRONTERA):
                nombrados = sum(1 for iso, fs in formas.items()
                                if any(f" {f} " in plano for f in fs if f))
                if nombrados >= 2:
                    halladas.append(n)
        base = {k: zona[k] for k in ("clave", "nombre", "estados", "descripcion")}
        if not halladas:
            salida.append({**base, "notas": 0, "portales": 0, "jurisdicciones": [],
                           "idiomas": [], "por_toponimo": 0, "ambos_lados": False,
                           "ejemplos": []})
            continue
        paises = sorted({n["pais"] for n in halladas})
        salida.append({
            **base,
            "notas": len(halladas),
            "por_toponimo": por_toponimo,
            "portales": len({n["dominio"] for n in halladas}),
            "jurisdicciones": paises,
            "idiomas": sorted({n["idioma"] for n in halladas}),
            # Que la nombren medios de los dos lados es el dato fuerte: una sola
            # jurisdiccion puede estar contando su propia version.
            "ambos_lados": len([p for p in paises if p in zona["estados"]]) >= 2,
            "ejemplos": [{k: n[k] for k in ("titulo", "enlace", "medio", "pais")}
                         for n in halladas[:3]],
        })
    salida.sort(key=lambda z: -z["notas"])
    return salida


def _senal_reciente(notas: list, temas: list, gentilicios: dict,
                    nombres: dict, bloques: dict, isos: set) -> dict:
    """Qué se está publicando AHORA sobre cada materia, y en qué Estado.

    NO es un indicador y no se mezcla con ninguno. El registro publica series
    estructurales —UNODC, V-Dem, Bertelsmann— que llegan con años de rezago; esto
    dice, al lado y con su propia calificación, **que hay actividad reciente que
    esas series todavía no contaron**.

    Es exactamente la distinción de la casa entre el hecho acreditado y la
    indicación: la serie cuenta hechos verificados; esto cuenta menciones.

    La atribución por Estado se hace de dos maneras, y se declara cuál:

    - **Por mención**, cuando el título nombra al país. Es la fuerte.
    - **Por medio**, cuando el título no nombra ningún país y el medio es
      nacional. Un diario colombiano no escribe «en Colombia hubo un atentado»:
      escribe «atentado en Cali». Sin esta regla, la mayoría de la cobertura
      local quedaba sin atribuir. Es más débil y por eso va marcada aparte.
    """
    preparados = []
    for t in temas:
        preparados.append({
            **t,
            "_nucleo": [" ".join(_normalizar_crudo(x)) for x in t.get("nucleo", [])],
        })

    por_tema = {}
    for t in preparados:
        por_tema[t["clave"]] = {
            "clave": t["clave"], "rotulo": t["rotulo"],
            "indicadores": t.get("indicadores", []), "seccion": t.get("seccion"),
            "cautela": t.get("cautela", ""),
            "notas": 0, "por_mencion": 0, "por_medio": 0,
            "estados": {},
        }

    for n in notas:
        plano = " " + " ".join(_normalizar_crudo(n["titulo"])) + " "
        mencionados = [i for i, formas in gentilicios.items()
                       if any(f" {f} " in plano for f in formas if f)]
        if mencionados:
            destinos, modo = mencionados, "mencion"
        elif n["pais"] in isos:
            destinos, modo = [n["pais"]], "medio"
        else:
            destinos, modo = [], None

        for t in preparados:
            if not any(f" {x} " in plano for x in t["_nucleo"] if x):
                continue
            reg = por_tema[t["clave"]]
            reg["notas"] += 1
            for iso in destinos:
                e = reg["estados"].setdefault(iso, {
                    "iso": iso, "pais": nombres.get(iso, iso),
                    "bloque": bloques.get(iso, "—"),
                    "notas": 0, "por_mencion": 0, "por_medio": 0,
                    "portales": set(), "jurisdicciones": set(), "idiomas": set(),
                    "ejemplos": [],
                })
                e["notas"] += 1
                e["por_mencion" if modo == "mencion" else "por_medio"] += 1
                reg["por_mencion" if modo == "mencion" else "por_medio"] += 1
                e["portales"].add(n["dominio"])
                e["jurisdicciones"].add(n["pais"])
                e["idiomas"].add(n["idioma"])
                if len(e["ejemplos"]) < 4:
                    e["ejemplos"].append({
                        "titulo": n["titulo"][:190], "enlace": n["enlace"],
                        "medio": n["medio"], "pais": n["pais"],
                        "publicada": n.get("publicada"),
                        "atribución": "el título nombra al país" if modo == "mención"
                                      else "medio nacional, el título no nombra país",
                    })

    # Se cierra: los conjuntos pasan a cuenta, y cada Estado declara su fuerza.
    for reg in por_tema.values():
        lista = []
        for e in reg["estados"].values():
            portales, juris, idiomas = len(e["portales"]), len(e["jurisdicciones"]), len(e["idiomas"])
            if idiomas >= 2:
                fuerza, nota = "corroborado_fuerte", "Publicado en dos o más idiomas."
            elif juris >= 2:
                fuerza, nota = "corroborado", "Publicado desde dos o más jurisdicciones."
            elif e["por_mencion"] == 0:
                fuerza, nota = "origen_unico", (
                    "Atribuido por el medio y no por el título: la nota no nombra al "
                    "país. Es la atribución más débil.")
            else:
                fuerza, nota = "origen_unico", (
                    "Un solo origen: por más portales que sean, si son de la misma "
                    "jurisdicción y el mismo idioma cuentan como uno.")
            lista.append({k: e[k] for k in ("iso", "pais", "bloque", "notas",
                                            "por_mencion", "por_medio", "ejemplos")}
                         | {"portales": portales, "jurisdicciones": juris,
                            "idiomas": idiomas, "fuerza": fuerza, "nota_fuerza": nota})
        lista.sort(key=lambda x: -x["notas"])
        reg["estados"] = lista
        reg["estados_con_senal"] = len(lista)
    return por_tema


def _corroboracion(notas: list) -> dict:
    """Cuenta orígenes, no portales, y aplica la regla de cruce del §4.

    Un centro de estudio NO corrobora un hecho. Publica análisis sobre hechos que
    ya circulan, de modo que contarlo como jurisdicción independiente sería contar
    dos veces la misma noticia. Se registra aparte, como respaldo analítico.
    """
    prensa = [n for n in notas if n.get("tipo", "prensa") == "prensa"]
    centros = [n for n in notas if n.get("tipo") == "centro de estudio"]

    idiomas = {n["idioma"] for n in prensa}
    paises = {n["pais"] for n in prensa}
    origenes = {(n["pais"], n["idioma"]) for n in prensa}

    if len(idiomas) >= 2:
        estado, nota = "corroborado_fuerte", "Dos o más idiomas distintos."
    elif len(paises) >= 2:
        estado, nota = "corroborado", "Dos o más jurisdicciones, un solo idioma."
    elif not prensa:
        estado, nota = "origen_unico", (
            "Solo lo trataron centros de estudio. Es análisis, no cobertura: "
            "no corrobora que el hecho haya ocurrido."
        )
    else:
        estado, nota = "origen_unico", (
            "Todos los medios son del mismo país y del mismo idioma: cuentan como "
            "un solo origen, por más portales que sean."
        )
    if centros and estado != "origen_unico":
        nota += f" Con respaldo analítico de {len(centros)} centro(s) de estudio."
    return {
        "estado": estado,
        "nota": nota,
        "origenes_independientes": len(origenes),
        "portales": len({n["dominio"] for n in notas}),
        "idiomas": sorted(idiomas),
        "paises": sorted(paises),
        "centros_de_estudio": sorted({n["medio"] for n in centros}),
    }


def _palabras_clave(notas: list, gentilicios: dict, bloques: dict,
                    nombres: dict) -> dict:
    """Mapa de palabras: qué términos circulan hoy, por Estado, bloque y región.

    No es análisis de sentimiento ni de tendencia: es el recuento de los términos
    que efectivamente aparecen en los títulos recolectados en la ventana vigente.
    Se descartan las palabras vacías y los propios nombres de país, que aparecerían
    primeros y no dirían nada.
    """
    propios = set()
    for formas in gentilicios.values():
        for f in formas:
            propios.update(f.split())

    def cuenta(lista):
        c, dominios = Counter(), {}
        for n in lista:
            # Cada término se cuenta UNA VEZ por nota: si un título repite una
            # palabra, no vale por dos. Lo que se mide es en cuántas notas aparece.
            for palabra in set(_normalizar(n["titulo"])):
                if len(palabra) < 4 or palabra in propios or palabra.isdigit():
                    continue
                c[palabra] += 1
                dominios.setdefault(palabra, set()).add(n["dominio"])
        # Un término que sale de un solo portal NO es lo que circula: es lo que ese
        # portal repite. El pronóstico del tiempo de un diario, publicado a diario,
        # encabezaría el mapa de la región entera. Es la misma regla de corroboración
        # que rige el resto de la casa: dos orígenes o no entra.
        return [{"palabra": t, "notas": v, "portales": len(dominios[t])}
                for t, v in c.most_common(TOPE_PALABRAS * 3)
                if v >= 2 and len(dominios[t]) >= 2][:TOPE_PALABRAS]

    por_pais, por_bloque = {}, {}
    for n in notas:
        for iso in n.get("_isos", []):
            por_pais.setdefault(iso, []).append(n)
            b = bloques.get(iso)
            if b:
                por_bloque.setdefault(b, []).append(n)

    return {
        "region": cuenta(notas),
        "bloques": {b: cuenta(l) for b, l in sorted(por_bloque.items())},
        "paises": {i: {"pais": nombres.get(i, i), "bloque": bloques.get(i, "—"),
                       "notas": len(l), "palabras": cuenta(l)}
                   for i, l in sorted(por_pais.items())},
        "nota": ("Recuento de términos en los títulos recolectados en la ventana "
                 "vigente. Mide DE QUÉ SE HABLA, no qué ocurre ni con qué signo. "
                 "Un término ausente puede significar que el asunto no circula, o "
                 "que ningún canal del padrón lo cubre. Para figurar, un término "
                 "debe aparecer en dos notas de dos portales distintos: lo que "
                 "publica un solo portal no es circulación, es repetición."),
        "ventana_horas": HORAS,
        "minimo_para_figurar": "aparecer en 2 notas y en 2 portales distintos",
    }


def recolectar():
    padron = json.loads(PADRON_MEDIOS.read_text(encoding="utf-8"))["medios"]
    gentilicios = json.loads(PADRON_GENTILICIOS.read_text(encoding="utf-8"))["paises"]
    # Los gentilicios se comparan sobre texto ya normalizado, sin tildes.
    gentilicios = {iso: [" ".join(_normalizar_crudo(f)) for f in formas]
                   for iso, formas in gentilicios.items()}
    bloques = {p["iso"]: p["bloque"] for p in geo.padron()}
    nombres_pais = {p["iso"]: p["pais"] for p in geo.padron()}

    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        resultados = list(ejecutor.map(_traer_canal, padron))

    caidos = [f"{m['nombre']} ({m['pais']}): {f}" for m, _, f in resultados if f]
    notas = [n for _, lista, _ in resultados for n in lista]

    corte = datetime.now(timezone.utc) - timedelta(hours=HORAS)
    recientes = [n for n in notas if n["momento"] is None or n["momento"] >= corte]
    sin_fecha = sum(1 for n in recientes if n["momento"] is None)
    for n in recientes:
        n.pop("momento", None)

    # La atribución por país se calcula una vez por nota y se reutiliza: la usan
    # tanto los asuntos agrupados como el mapa de palabras.
    for n in recientes:
        n["_isos"] = _paises_mencionados(n["titulo"], gentilicios)
    mapa_palabras = _palabras_clave(recientes, gentilicios, bloques, nombres_pais)
    zonas = json.loads(PADRON_FRONTERAS.read_text(encoding="utf-8"))["zonas"]
    fronteras = _fronteras(recientes, zonas, gentilicios)
    for n in recientes:
        n.pop("_isos", None)

    temas_lexico = json.loads(PADRON_TEMAS.read_text(encoding="utf-8"))["temas"]
    senal = _senal_reciente(recientes, temas_lexico, gentilicios, nombres_pais,
                            bloques, set(bloques))

    grupos = _agrupar(recientes)
    eventos = []
    for grupo in grupos:
        lista = grupo["notas"]
        if len(lista) < 2:
            continue                      # una sola nota no es cobertura cruzada
        corr = _corroboracion(lista)
        asunto = max((n["titulo"] for n in lista), key=len)
        # Se buscan menciones en todos los títulos del grupo, no solo en el más largo.
        isos = sorted({i for n in lista for i in n.get("_isos", [])})
        eventos.append({
            "asunto": asunto,
            "paises": [{"iso": i, "pais": nombres_pais.get(i, i), "bloque": bloques.get(i, "—")} for i in isos],
            "bloques": sorted({bloques[i] for i in isos if i in bloques}),
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
    sin_pais = sum(1 for e in eventos if not e["paises"])
    por_pais = Counter(p["iso"] for e in eventos for p in e["paises"])

    # Infoxicación: asuntos muy repetidos que ningún segundo origen corrobora.
    # Es amplificación sin verificación, y se mide sobre lo que ya se recolectó.
    amplificados = [e for e in eventos
                    if e["corroboracion"]["estado"] == "origen_unico"
                    and e["corroboracion"]["portales"] >= 3]
    indice_infoxicacion = round(len(amplificados) / len(eventos) * 100, 1) if eventos else 0.0
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
        "La atribución de un asunto a un país es por DICCIONARIO de nombres y "
        "gentilicios, no por comprensión del texto. Un asunto que nombre al país con un "
        "giro que no figure en la lista queda sin atribuir; uno que lo nombre al pasar "
        "queda atribuido igual. La lista es editable por el equipo analítico.",
        f"{sin_pais} de {len(eventos)} asuntos no pudieron atribuirse a ningún Estado del "
        "padrón: en su mayoría son noticias internacionales sin mención regional.",
        "El índice de infoxicación mide la proporción de asuntos repetidos por tres o más "
        "portales que NINGÚN segundo origen independiente corrobora. Es amplificación sin "
        "verificación, no desinformación probada: no dice que el asunto sea falso, dice "
        "que se repite sin que nadie de otra jurisdicción o idioma lo confirme.",
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
                "asuntos_sin_pais": sin_pais,
                "indice_infoxicacion_pct": indice_infoxicacion,
                "asuntos_amplificados_sin_corroborar": len(amplificados),
            },
            "por_pais": [{"iso": i, "pais": nombres_pais.get(i, i), "asuntos": n}
                         for i, n in por_pais.most_common()],
            "mapa_palabras": mapa_palabras,
            "senal_reciente": {
                "temas": senal,
                "ventana_horas": HORAS,
                "estados_con_alguna_senal": len({e["iso"] for t in senal.values()
                                                 for e in t["estados"]}),
                "que_es": (
                    "Que se esta publicando AHORA sobre cada materia. NO ES UN "
                    "INDICADOR y no se mezcla con ninguno: las series estructurales "
                    "cuentan hechos verificados y llegan con años de rezago; esto "
                    "cuenta MENCIONES de las últimas horas. Se muestra al lado del "
                    "dato estructural para decir que hay actividad que esa serie "
                    "todavia no conto."),
                "que_no_es": (
                    "Mas notas NO significa mas hechos: puede significar mas "
                    "atención, o un solo hecho cubierto por muchos portales. Y menos "
                    "notas puede significar menos prensa libre, no menos hechos."),
                "atribucion": (
                    "Por MENCION cuando el titulo nombra al país —la fuerte— y por "
                    "MEDIO cuando el titulo no nombra ninguno y el medio es nacional. "
                    "Un diario colombiano no escribe «en Colombia hubo un atentado»: "
                    "escribe «atentado en Cali». Cada Estado declara cuantas notas "
                    "tiene de cada clase."),
            },
            "fronteras": {
                "zonas": fronteras,
                "con_mencion": sum(1 for z in fronteras if z["notas"]),
                "total": len(fronteras),
                "nota": ("Zonas de frontera y focos transfronterizos. NO son "
                         "indicadores: son lugares, y ninguna fuente publica "
                         "estadística comparable a esa escala. Se cuenta cuantas notas "
                         "del corpus las nombran, de cuantos portales y de cuantas "
                         "jurisdicciones. Que la nombren medios de los DOS LADOS de la "
                         "frontera es el dato fuerte: una sola jurisdicción puede estar "
                         "contando su propia versión."),
            },
            "padron_medios": {
                "prensa": sum(1 for m in padron if m.get("tipo", "prensa") == "prensa"),
                "centros_de_estudio": sum(1 for m in padron if m.get("tipo") == "centro de estudio"),
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
