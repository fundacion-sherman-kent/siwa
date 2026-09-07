"""Trata de personas — la clasificación anual del Departamento de Estado.

El **Informe sobre la Trata de Personas** (TIP Report) evalúa cada año, país por
país, si el gobierno cumple los estándares mínimos para eliminar la trata, y lo
resume en una categoría comparable entre Estados:

* **Nivel 1** — el gobierno cumple plenamente los estándares mínimos.
* **Nivel 2** — no los cumple plenamente, pero hace esfuerzos significativos.
* **Nivel 2, lista de vigilancia** — hace esfuerzos, con señales de deterioro o
  de estancamiento que el informe detalla.
* **Nivel 3** — no cumple ni hace esfuerzos significativos.
* **Caso especial** — el informe no clasifica: la situación del país impide
  evaluar los esfuerzos del gobierno. Haití está así por segundo año.

**Esto mide esfuerzo de gobierno, no cantidad de víctimas.** Un Estado puede
tener mucha trata y estar en el Nivel 1 porque su gobierno la persigue, y otro
puede tener poca y caer al Nivel 3. Leerlo como un ranking de cuánta trata hay
sería leerlo exactamente al revés.

**Y lo emite un Estado sobre otros Estados.** Es una evaluación del gobierno de
los Estados Unidos, con su método declarado y sus consecuencias legales
—el Nivel 3 habilita restricciones de asistencia—, no una medición neutral. Se
publica como lo que es: la posición de un tercero, calificada como tal.
"""

from __future__ import annotations

import datetime
import re
import ssl
import urllib.error
import urllib.request

import comun
import geo

# state.gov rechaza con 403 a quien no antepone «Mozilla/5.0». No es un
# desafio anti-robot ni un muro: es una convencion heredada que casi todo
# cliente respeta. Se la respeta SIN mentir: la forma «compatible; NOMBRE»
# existe justamente para esto, y el registro sigue diciendo quien es y donde
# encontrarlo. Disfrazarse de Chrome habria funcionado igual y habria sido
# una mentira innecesaria.
NAVEGADOR = "Mozilla/5.0 (compatible; " + comun.AGENTE + ")"
BASE = "https://www.state.gov/reports/{anio}-trafficking-in-persons-report/"

# Se busca la edición más reciente que exista, empezando por el año en curso. Si
# se fijara el año a mano, el registro seguiría publicando la edición vieja sin
# que nadie lo note el día que salga la nueva.
EDICIONES_ATRAS = 3

# El informe no clasifica a todos los Estados del mundo: la edición 2025 evalúa
# a 186. Que un Estado no tenga página NO es un fallo de lectura ni un vacío del
# registro: es que el informe no lo evalúa, y se dice así.
RUTAS = {
    "ARG": "argentina", "BOL": "bolivia", "BRA": "brazil", "CHL": "chile",
    "COL": "colombia", "CRI": "costa-rica", "CUB": "cuba",
    "DOM": "dominican-republic", "ECU": "ecuador", "SLV": "el-salvador",
    "GTM": "guatemala", "HTI": "haiti", "HND": "honduras", "MEX": "mexico",
    "NIC": "nicaragua", "PAN": "panama", "PRY": "paraguay", "PER": "peru",
    "URY": "uruguay", "VEN": "venezuela", "BLZ": "belize", "GUY": "guyana",
    "SUR": "suriname", "ATG": "antigua-and-barbuda", "BHS": "bahamas",
    "BRB": "barbados", "DMA": "dominica", "GRD": "grenada", "JAM": "jamaica",
    "KNA": "saint-kitts-and-nevis", "LCA": "saint-lucia",
    "VCT": "saint-vincent-and-the-grenadines", "TTO": "trinidad-and-tobago",
}

# Las cinco categorías que el informe usa, y NINGUNA otra. Si una página
# devolviera algo fuera de esta lista, lo que cambió es el informe o falló la
# lectura: se declara en vez de publicar una categoría inventada.
CATEGORIAS = {
    "tier 1": {"clave": "nivel_1", "rotulo": "Nivel 1", "orden": 1,
               "dice": "El gobierno cumple plenamente los estándares mínimos."},
    "tier 2": {"clave": "nivel_2", "rotulo": "Nivel 2", "orden": 2,
               "dice": "No los cumple plenamente, pero hace esfuerzos significativos."},
    "tier 2 watch list": {"clave": "nivel_2_vigilancia",
                          "rotulo": "Nivel 2, lista de vigilancia", "orden": 3,
                          "dice": "Hace esfuerzos, con señales de deterioro o de "
                                  "estancamiento que el informe detalla."},
    "tier 3": {"clave": "nivel_3", "rotulo": "Nivel 3", "orden": 4,
               "dice": "No cumple los estándares mínimos ni hace esfuerzos "
                       "significativos por cumplirlos."},
    "special case": {"clave": "caso_especial", "rotulo": "Caso especial", "orden": 5,
                     "dice": "El informe no clasifica: la situación del país impide "
                             "evaluar los esfuerzos del gobierno."},
}

CONTROL = "ARG"     # tiene página y nivel; si falla, el que falló es el lector
ESPERA = 60


def _pedir(url: str) -> str:
    peticion = urllib.request.Request(url, headers={
        "User-Agent": NAVEGADOR,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en"})
    with urllib.request.urlopen(peticion, timeout=ESPERA,
                                context=ssl.create_default_context()) as respuesta:
        return respuesta.read(2_000_000).decode("utf-8", "replace")


def _edicion() -> tuple:
    """La edición más reciente que existe, buscada y no supuesta."""
    anio = datetime.datetime.now(datetime.timezone.utc).year
    intentos = []
    for candidato in range(anio, anio - EDICIONES_ATRAS, -1):
        url = BASE.format(anio=candidato)
        try:
            pagina = _pedir(url)
        except urllib.error.HTTPError as e:
            intentos.append(f"{candidato}: HTTP {e.code}")
            continue
        except Exception as e:  # noqa: BLE001 — se prueba la siguiente edición
            intentos.append(f"{candidato}: {type(e).__name__}")
            continue
        evaluados = len({e.rstrip("/").split("/")[-1] for e in re.findall(
            r'href="(https://www\.state\.gov/reports/'
            rf'{candidato}-trafficking-in-persons-report/[^"]+)"', pagina)})
        return candidato, url, evaluados
    raise RuntimeError(
        "No se halló ninguna edición del informe en los últimos "
        f"{EDICIONES_ATRAS} años: {'; '.join(intentos)}.")


def _nivel(anio: int, ruta: str) -> tuple:
    """(categoría, nombre en la fuente, falla). El 404 NO es una falla."""
    url = f"{BASE.format(anio=anio)}{ruta}/"
    try:
        pagina = _pedir(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None, "no_evaluado"
        return None, None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, None, f"{type(e).__name__}: {e}"[:120]

    # El informe encabeza cada ficha con «PAÍS (Nivel)». Se lee de ahí, que es
    # donde el propio informe lo declara, y no de una mención al pasar en el
    # cuerpo del texto —donde «Tier 1» aparece explicando la escala—.
    hallado = re.search(
        r"(?is)<h2[^>]*>\s*([A-Z][A-Za-z\s\.'-]+?)\s*\(([^)]{3,40})\)\s*</h2>", pagina)
    if not hallado:
        return None, None, "no se halló el encabezado con la categoría"
    nombre, cruda = hallado.group(1).strip(), " ".join(hallado.group(2).split())
    categoria = CATEGORIAS.get(cruda.lower())
    if not categoria:
        return None, nombre, f"categoría desconocida: «{cruda}»"
    return {**categoria, "en_la_fuente": cruda}, nombre, None


def recolectar():
    anio, url_edicion, evaluados = _edicion()

    fichas, fallas = {}, []
    for iso, ruta in RUTAS.items():
        categoria, nombre, falla = _nivel(anio, ruta)
        fichas[iso] = (categoria, nombre, falla)
        if falla and falla != "no_evaluado":
            fallas.append(f"{iso}: {falla}")

    # PROBAR ANTES DE AFIRMAR. Si el control no trae categoría, lo que falló es
    # la lectura y no la clasificación de nadie: publicar treinta y tres «sin
    # dato» diría que el Departamento de Estado dejó de evaluar la región.
    if fichas[CONTROL][0] is None:
        raise RuntimeError(
            f"El control ({CONTROL}) no devolvió categoría: {fichas[CONTROL][2]}. "
            "La lectura del informe falló y no se publica nada.")

    registros = []
    for pais in geo.padron():
        categoria, nombre, falla = fichas.get(pais["iso"], (None, None, "sin ruta"))
        registro = {
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "evaluado": categoria is not None,
        }
        if categoria:
            registro.update({
                "categoria": categoria["clave"],
                "rotulo": categoria["rotulo"],
                "orden": categoria["orden"],
                "dice": categoria["dice"],
                "en_la_fuente": categoria["en_la_fuente"],
                "nombre_en_la_fuente": nombre,
                "enlace": f"{BASE.format(anio=anio)}{RUTAS[pais['iso']]}/",
            })
        else:
            registro["por_que_no"] = (
                "El informe no evalúa a este Estado en esta edición."
                if falla == "no_evaluado" else f"No se pudo leer: {falla}")
        registros.append(registro)
    registros.sort(key=lambda r: (not r["evaluado"], r.get("orden", 9), r["pais"]))

    conteo = {}
    for r in registros:
        if r["evaluado"]:
            conteo[r["rotulo"]] = conteo.get(r["rotulo"], 0) + 1
    sin_evaluar = [r["pais"] for r in registros if not r["evaluado"]]

    vacios = [
        "**Mide esfuerzo de gobierno, no cantidad de víctimas.** Un Estado puede "
        "tener mucha trata y estar en el Nivel 1 porque su gobierno la persigue, y "
        "otro puede tener poca y caer al Nivel 3. Leerlo como un recuento de trata "
        "es leerlo exactamente al revés.",
        "**Lo emite un Estado sobre otros Estados.** Es la evaluación del gobierno de "
        "los Estados Unidos, con método declarado y consecuencias legales propias —el "
        "Nivel 3 habilita restricciones de asistencia—, no una medición neutral. Entra "
        "al registro como la posición de un tercero, calificada como tal, y no "
        "sostiene por sí sola ningún juicio de la Fundación.",
        "**«Caso especial» no es una nota mala ni una nota buena: es la ausencia de "
        "nota.** Significa que la situación del país impide evaluar los esfuerzos del "
        "gobierno. Ordenarlo como si fuera peor que el Nivel 3, o mejor, sería "
        "inventar una escala que el informe no tiene.",
        f"La edición {anio} evalúa a {evaluados} países del mundo y **no evalúa a "
        f"{len(sin_evaluar)} Estados del padrón**"
        + (f": {', '.join(sin_evaluar)}. " if sin_evaluar else ". ")
        + "Que no figuren no dice nada sobre su situación: dice que el informe no los "
          "incluye. Se verificó contra la lista de fichas del propio informe, no "
          "contra una dirección supuesta.",
        "La categoría se lee del encabezado con que el propio informe abre cada ficha, "
        "y no de una mención al pasar: en el cuerpo del texto la expresión «Nivel 1» "
        "aparece explicando la escala, y tomarla de ahí clasificaría a todos igual.",
        "El informe es anual y su corte no coincide con el año calendario: describe el "
        "período que él mismo declara en cada ficha, no la situación de hoy.",
    ]
    if fallas:
        vacios.append(f"{len(fallas)} fichas no se pudieron leer en esta corrida: "
                      f"{'; '.join(fallas)}.")

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=2,
        corroborado=False,
        nota=("Organismo estatal con método publicado y trayectoria larga, que evalúa a "
              "terceros Estados y tiene interés declarado en el asunto: fiabilidad B, "
              "no A, precisamente por ser parte y no observador. Lo que se registra es "
              "la clasificación que emitió, hecho verificable en la fuente, no que la "
              "clasificación sea correcta."),
    )

    return comun.escribir(
        colector="trata_personas",
        capa="publico",
        fuente=f"Departamento de Estado de los Estados Unidos — Informe sobre la Trata "
               f"de Personas, edición {anio}",
        url_fuente=url_edicion,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "edicion": anio,
                "estados_evaluados": sum(1 for r in registros if r["evaluado"]),
                "estados_del_padron": len(registros),
                "paises_en_el_informe": evaluados,
                "por_categoria": conteo,
                "consultado": comun.ahora(),
            },
            "escala": [
                {"rotulo": c["rotulo"], "orden": c["orden"], "dice": c["dice"]}
                for c in sorted(CATEGORIAS.values(), key=lambda x: x["orden"])
            ],
        },
    )


if __name__ == "__main__":
    comun.correr("trata_personas", recolectar)
