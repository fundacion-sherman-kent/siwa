# -*- coding: utf-8 -*-
"""Redes de influencia coordinada dadas de baja, según la plataforma que las dio de baja.

POR QUÉ EXISTE
--------------
La dirección pidió mirar los agentes digitales que se propagan y si pueden ser
un riesgo de injerencia de potencias de fuera del continente (autorizado el
13/9/2026). Se exploraron las fuentes y hay UNA sola que registra, red por red y
de forma regular, lo que da de baja: el boletín trimestral de Google sobre
operaciones de influencia coordinada (antes, boletín del Grupo de Análisis de
Amenazas). Cada entrada dice cuántos canales o dominios dio de baja, en qué
idioma publicaban, a quién apoyaban o criticaban y, cuando Google lo declara, a
qué país está vinculada la red.

LA REGLA QUE GOBIERNA ESTE COLECTOR
-----------------------------------
**La atribución no es de la Fundación: es de Google.** Este registro no afirma
que una red responda a un Estado. Publica que Google la dio de baja y a qué país
la vinculó, con su texto literal. Una atribución que la plataforma no muestra
cómo hizo no se puede verificar desde afuera, y se dice.

**Todos los orígenes cuentan igual.** Se registra la red vinculada a un Estado
de la propia región igual que la vinculada a Rusia, a China o a Canadá. Contar
solo a las potencias de fuera del continente sería tomar partido.

**Un cero no es ausencia de actividad.** Significa que Google no informó
ninguna red que mencione al país. Google mira YouTube, Blogger, sus anuncios y
sus noticias: no mira WhatsApp, Telegram, TikTok ni X, que pesan mucho en la
región.
"""
from __future__ import annotations

import html
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "influencia"
CAPA = "publico"
DESDE = 2022
RUTAS = [
    "https://blog.google/security/influence-operations-bulletin-q{q}-{y}/",
    "https://blog.google/threat-analysis-group/tag-bulletin-q{q}-{y}/",
]
NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# Cómo nombra Google a cada Estado del padrón, con sus gentilicios en inglés.
# Se buscan como palabra entera y con mayúscula: «Chile» no debe encontrarse en
# «chilli», ni «Dominica» en «Dominican Republic».
NOMBRES = {
    "ARG": r"\bArgentin\w*", "BOL": r"\bBolivia\w*", "BRA": r"\bBrazil\w*",
    "CHL": r"\bChile(?:an|ans|'s)?\b", "COL": r"\bColombia\w*", "CRI": r"\bCosta Ric\w*",
    "CUB": r"\bCuba(?:n|ns|'s)?\b", "DOM": r"\bDominican Republic", "ECU": r"\bEcuador\w*",
    "SLV": r"\bEl Salvador|\bSalvadoran", "GTM": r"\bGuatemala\w*", "GUY": r"\bGuyan\w*",
    "HTI": r"\bHaiti\w*", "HND": r"\bHondur\w*", "JAM": r"\bJamaica\w*", "MEX": r"\bMexic\w*",
    "NIC": r"\bNicaragu\w*", "PAN": r"\bPanam(?:a|anian)\w*", "PRY": r"\bParaguay\w*",
    "PER": r"\bPeru(?:vian|vians|'s)?\b", "SUR": r"\bSurinam\w*", "TTO": r"\bTrinidad",
    "URY": r"\bUruguay\w*", "VEN": r"\bVenezuel\w*", "BLZ": r"\bBeliz\w*",
    "BHS": r"\bBahamas|\bBahamian", "BRB": r"\bBarbad\w*", "ATG": r"\bAntigua",
    "DMA": r"\bDominica\b(?! Republic)", "GRD": r"\bGrenad(?:a|ian)\b",
    "KNA": r"\b(?:Saint|St\.?) Kitts", "LCA": r"\b(?:Saint|St\.?) Lucia",
    "VCT": r"\b(?:Saint|St\.?) Vincent",
}
REGION = r"\bLatin America\w*|\bthe Caribbean|\bCentral America\w*|\bSouth America\w*"


def pedir(url: str) -> str | None:
    peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
    try:
        with urllib.request.urlopen(peticion, timeout=60) as respuesta:
            return respuesta.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def entradas(pagina: str) -> list:
    """Cada «We terminated / blocked / removed N …» es una red dada de baja."""
    salida = []
    for bloque in re.findall(r"<(?:li|p)[^>]*>(.*?)</(?:li|p)>", pagina, flags=re.S):
        texto = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", bloque)).split())
        for frase in re.split(r"(?=We (?:terminated|blocked|removed) )", texto):
            if re.match(r"We (?:terminated|blocked|removed) \d", frase):
                salida.append(frase.strip())
    return salida


def vinculo(frase: str) -> tuple:
    """El país al que Google vincula la red, en sus palabras, y de dónde es."""
    m = re.search(r"linked to (.+?)\.(?:\s|$)", frase)
    if not m:
        return None, "sin declarar"
    dicho = m.group(1).strip()
    resto = dicho
    for pat in list(NOMBRES.values()) + [REGION]:
        resto = re.sub(pat, " ", resto)
    resto = re.sub(r"\b(?:individuals|actors|entities|in|the|and|a|an|or|of|from|based)\b|[,;]",
                   " ", resto)
    # Lo que queda con mayúscula después de sacar los países de la región es un
    # lugar de fuera de ella.
    if re.search(r"[A-Z][a-z]", resto):
        return dicho, "fuera de la región"
    return dicho, "de la región"


def recolectar_boletines() -> list:
    ahora = datetime.now(timezone.utc)
    boletines = []
    for y in range(DESDE, ahora.year + 1):
        for q in range(1, 5):
            if (y, q) > (ahora.year, (ahora.month - 1) // 3 + 1):
                break
            for ruta in RUTAS:
                url = ruta.format(q=q, y=y)
                pagina = pedir(url)
                if pagina and re.search(r"We (?:terminated|blocked|removed) \d", pagina):
                    boletines.append({"anio": y, "trimestre": q, "url": url,
                                      "entradas": entradas(pagina)})
                    break
    return boletines


def construir() -> Path:
    padron = geo.padron()
    boletines = recolectar_boletines()
    if len(boletines) < 8 or sum(len(b["entradas"]) for b in boletines) < 200:
        raise RuntimeError(
            f"Se leyeron {len(boletines)} boletines con "
            f"{sum(len(b['entradas']) for b in boletines)} entradas: la forma de la página cambió o "
            "la lectura falló. NO se publica un recuento hueco.")
    ultimos = sorted({(b["anio"], b["trimestre"]) for b in boletines})[-4:]

    por_iso = {p["iso"]: {"anios": {}, "anios_ext": {}, "recientes": 0, "recientes_ext": 0,
                          "casos": []} for p in padron}
    regionales, total, idioma_sin_pais, idioma_ext = 0, 0, 0, 0
    con_pais = {"de la región": 0, "fuera de la región": 0, "sin declarar": 0}
    for b in boletines:
        reciente = (b["anio"], b["trimestre"]) in ultimos
        for frase in b["entradas"]:
            total += 1
            paises = [iso for iso, pat in NOMBRES.items() if re.search(pat, frase)]
            if not paises and re.search(REGION, frase):
                regionales += 1
            dicho, clase = vinculo(frase)
            # Las redes que publican en castellano o portugués sin nombrar a ningún
            # país de la región no se pueden asignar a uno: se cuentan aparte.
            if not paises and re.search(r"\b(?:Spanish|Portuguese)\b", frase):
                idioma_sin_pais += 1
                idioma_ext += clase == "fuera de la región"
            if paises:
                con_pais[clase] += 1
            for iso in paises:
                d = por_iso[iso]
                d["anios"][b["anio"]] = d["anios"].get(b["anio"], 0) + 1
                if clase == "fuera de la región":
                    d["anios_ext"][b["anio"]] = d["anios_ext"].get(b["anio"], 0) + 1
                if reciente:
                    d["recientes"] += 1
                    d["recientes_ext"] += clase == "fuera de la región"
                d["casos"].append({"anio": b["anio"], "trimestre": b["trimestre"], "url": b["url"],
                                   "vinculada_segun_google": dicho, "clase_de_vinculo": clase,
                                   "texto_de_google": frase})

    anios = list(range(DESDE, max(b["anio"] for b in boletines) + 1))
    periodo = f"{ultimos[0][1]}.º trimestre de {ultimos[0][0]} al {ultimos[-1][1]}.º de {ultimos[-1][0]}"
    registros = []
    for p in padron:
        d = por_iso[p["iso"]]
        indicadores = {}
        for clave, reciente, por_anio in (("redes_influencia", d["recientes"], d["anios"]),
                                          ("redes_influencia_extrarregional", d["recientes_ext"],
                                           d["anios_ext"])):
            indicadores[clave] = {
                "valor": reciente, "anio": ultimos[-1][0], "periodo": periodo,
                "anio_anterior": None, "valor_anterior": None,
                "serie": [{"anio": a, "valor": por_anio.get(a, 0)} for a in anios],
            }
        registros.append({"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"),
                          "indicadores": indicadores,
                          "casos": sorted(d["casos"], key=lambda c: (c["anio"], c["trimestre"]),
                                          reverse=True)})

    medidas = [
        {"clave": "redes_influencia",
         "rotulo": "Redes de influencia dadas de baja por Google que mencionan al país",
         "eje": "Gobernanza", "unidad": "redes en los últimos cuatro trimestres",
         "unidad_singular": "red", "mas_es_peor": True, "sin_direccion": True,
         "origen": "Google — boletín trimestral de operaciones de influencia coordinada",
         "cautela": "SEGÚN GOOGLE, no según la Fundación. Cuenta las redes que Google informa haber "
                    "dado de baja en YouTube, Blogger, sus anuncios o sus noticias y cuyo texto "
                    "nombra al país —como origen, como tema o como destinatario—. Un número alto "
                    "puede reflejar más actividad o más atención de Google; un CERO no prueba "
                    "ausencia de actividad. No mira WhatsApp, Telegram, TikTok ni X."},
        {"clave": "redes_influencia_extrarregional",
         "rotulo": "De ellas, vinculadas por Google a un país de fuera de la región",
         "eje": "Gobernanza", "unidad": "redes en los últimos cuatro trimestres",
         "unidad_singular": "red", "mas_es_peor": True, "sin_direccion": True,
         "origen": "Google — boletín trimestral de operaciones de influencia coordinada",
         "cautela": "LA ATRIBUCIÓN ES DE GOOGLE y la Fundación no puede verificarla: la empresa no "
                    "publica la evidencia técnica. Cuenta las redes que Google vincula, con sus "
                    "palabras, a un país de fuera de América Latina y el Caribe —Rusia, China, Irán, "
                    "Canadá o cualquier otro—, sin distinguir cuál. Cada caso se publica con el "
                    "texto literal de Google en el archivo de datos."},
    ]
    vacios = [
        "LA ATRIBUCIÓN ES DE LA PLATAFORMA, NO DE LA FUNDACIÓN. Este registro publica que Google dio "
        "de baja una red y a qué país la vinculó; no afirma que la red responda a ese Estado.",
        "TODOS LOS ORÍGENES CUENTAN IGUAL: la red vinculada a un país de la región se registra igual "
        f"que la vinculada a uno de fuera. De las {sum(con_pais.values())} redes que nombran a un país "
        f"de la región, Google vincula {con_pais['de la región']} a la propia región, "
        f"{con_pais['fuera de la región']} a un país de fuera de ella y no declara origen en "
        f"{con_pais['sin declarar']}.",
        "UN CERO NO ES AUSENCIA DE ACTIVIDAD: Google solo informa lo que detecta en sus propios "
        "servicios. WhatsApp, Telegram, TikTok y X no publican registros comparables; X dejó de "
        "hacerlo.",
        "UNA SOLA EMPRESA, DE ESTADOS UNIDOS. Detecta lo que busca y lo que prioriza. No hay otra "
        "fuente abierta que registre redes de este modo para comparar.",
        f"SE LEEN LOS BOLETINES DESDE {DESDE}: {len(boletines)} boletines y {total} redes en total. "
        f"{regionales} redes nombran a la región en general —América Latina, el Caribe— sin nombrar "
        "un país, y no se asignan a ninguno.",
        f"OTRAS {idioma_sin_pais} REDES PUBLICABAN EN CASTELLANO O PORTUGUÉS SIN NOMBRAR A NINGÚN PAÍS "
        f"DE LA REGIÓN —de ellas, {idioma_ext} vinculadas por Google a un país de fuera de la región—. "
        "Pudieron dirigirse a la región, pero el texto de Google no permite asignarlas a un Estado: "
        "quedan fuera de las fichas por país y se cuentan acá.",
        "EL TEXTO DE GOOGLE ESTÁ EN INGLÉS y se publica literal en el archivo de datos, caso por "
        "caso, para que cualquiera pueda leer qué dijo la empresa.",
    ]
    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Google — boletín trimestral de operaciones de influencia coordinada (TAG Bulletin)",
        url_fuente=boletines[-1]["url"],
        calificacion=comun.calificar(
            "B", 3, False,
            "Una sola empresa informa sobre lo que ella misma dio de baja y no publica la evidencia "
            "de sus atribuciones. Fiabilidad B por la regularidad y el detalle del registro; "
            "credibilidad 3 porque no hay segunda fuente que lo corrobore."),
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": medidas,
            "cobertura": {m["clave"]: len(registros) for m in medidas},
            "resumen": {"boletines": [{"anio": b["anio"], "trimestre": b["trimestre"], "url": b["url"],
                                       "redes": len(b["entradas"])} for b in boletines],
                        "redes_en_total": total, "redes_que_nombran_la_region_sin_pais": regionales,
                        "redes_en_castellano_o_portugues_sin_pais": idioma_sin_pais,
                        "de_ellas_vinculadas_fuera_de_la_region": idioma_ext,
                        "redes_que_nombran_un_pais_por_vinculo": con_pais,
                        "ventana": periodo, "consultado": comun.ahora()},
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
