"""Comercio registrado de especies protegidas, y qué parte de él viene de decomisos.

POR QUÉ EXISTE
--------------
El registro nombraba **contrabando** como materia y no tenía ninguna fuente
propia para ella. Ésta no la cierra —y conviene decirlo antes que nada—, pero
aporta el único registro internacional, obligatorio por tratado y de acceso
libre, sobre movimiento de especies protegidas en los 33 Estados del padrón.

Es la primera fuente del registro con **cobertura completa del padrón**: los 33
Estados tienen asientos.

LO QUE MIDE, Y ES MUCHO MENOS DE LO QUE PARECE
-----------------------------------------------
**Lo que esta base registra es comercio LEGAL.** Cada asiento nace de un permiso
o de un informe anual que una Parte del tratado presentó. El tráfico ilegal, por
definición, no tiene permiso y **no entra acá**. Quien lea estas cifras como
«tráfico de fauna» va a leer exactamente al revés.

Hay un código que se le acerca —el origen `I`, «confiscaciones y decomisos»—,
pero tampoco es un recuento de operativos: marca **especímenes cuyo origen
declarado es una incautación**, y el asiento aparece cuando ese espécimen se
mueve después —a un centro de rescate, a un zoológico, a investigación—. Un
Estado con muchos asientos de ese tipo puede tener más control, más delito, o
simplemente más movimiento posterior de lo incautado. **Son tres explicaciones
distintas y esta fuente no elige entre ellas.**

POR QUÉ NO ORDENA ESTADOS Y NO ENTRA AL COMPUESTO
--------------------------------------------------
El volumen depende de la biodiversidad del país, del tamaño de su economía y de
su papel en el comercio de cueros, madera o mascotas. Y la proporción de
decomiso no está orientada: no se sabe si más es mejor o peor. Entra como
**magnitud declarada**, al lado del dato comparable y nunca adentro.

LA TRAMPA DEL INSTRUMENTO
-------------------------
Esta fuente **ignora en silencio los parámetros que no conoce** y devuelve el
total sin filtrar. Un filtro mal escrito —o renombrado río arriba— haría que el
registro publicara «todo es decomiso» en los 33 Estados sin enterarse. Por eso
antes de creerle un número a nadie se comprueba que el filtro **efectivamente
filtre**, además de la prueba de control de siempre.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import comun
import geo

BASE = "https://trade.cites.org"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# La base identifica países con el código de DOS letras; el padrón usa el de
# tres. La traducción va explícita: adivinarla es como se rompen los colectores.
DOS_LETRAS = {
    "ARG": "AR", "BOL": "BO", "BRA": "BR", "CHL": "CL", "COL": "CO", "CRI": "CR",
    "CUB": "CU", "DOM": "DO", "ECU": "EC", "SLV": "SV", "GTM": "GT", "HTI": "HT",
    "HND": "HN", "MEX": "MX", "NIC": "NI", "PAN": "PA", "PRY": "PY", "PER": "PE",
    "URY": "UY", "VEN": "VE", "BLZ": "BZ", "GUY": "GY", "SUR": "SR",
    "ATG": "AG", "BHS": "BS", "BRB": "BB", "DMA": "DM", "GRD": "GD", "JAM": "JM",
    "KNA": "KN", "LCA": "LC", "VCT": "VC", "TTO": "TT",
}

ORIGEN_DECOMISO = 109      # el código «I» de la fuente: confiscaciones y decomisos
VENTANA_ANIOS = 5
# UNA PROPORCION SOBRE TRES ASIENTOS NO ES UNA PROPORCION. Sin este minimo,
# Granada quedaba segunda de la region con 4 asientos sobre 6 y Santa Lucia
# tercera con 1 sobre 3, delante de Bahamas, que tiene 151 sobre 589. El numero
# se publica igual —esconderlo seria peor—, pero marcado como NO COMPARABLE.
MINIMO_PARA_PROPORCION = 100
MAXIMO_RETROCESO = 10      # hasta dónde se busca el último año con asiento
# Brasil tiene comercio registrado TODOS los anios. Si el control da cero, el
# que fallo es el instrumento, no el mundo.
CONTROL = "BRA"
TESTIGOS = ("BRA", "COL", "MEX")


def _json(url: str, intentos: int = 3):
    ultimo = None
    for numero in range(intentos):
        try:
            peticion = urllib.request.Request(
                url, headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
            with urllib.request.urlopen(peticion, timeout=90) as respuesta:
                return json.loads(respuesta.read().decode("utf-8", "replace"))
        except Exception as error:  # noqa: BLE001 — se reintenta y si no, se declara
            ultimo = error
            time.sleep(1.5 * (numero + 1))
    raise RuntimeError(f"La fuente no respondió tras {intentos} intentos: {ultimo}")


def _entidades() -> dict:
    datos = _json(f"{BASE}/api/v1/geo_entities?geo_entity_types_set=4&locale=en")
    tabla = {g["iso_code2"]: g["id"] for g in datos["geo_entities"] if g.get("iso_code2")}
    faltan = sorted(k for k, v in DOS_LETRAS.items() if v not in tabla)
    if faltan:
        raise RuntimeError(
            f"La fuente dejó de reconocer a {len(faltan)} Estados del padrón: "
            f"{', '.join(faltan)}. NO se publica una región incompleta sin advertirlo.")
    return tabla


def _contar(identificador: int, desde: int, hasta: int, origen: int | None = None) -> int:
    """Devuelve cuántos asientos hay. NO descarga los asientos.

    La interfaz de la fuente ofrece este recuento para avisar el tamaño de una
    descarga; acá es todo el dato que se necesita, y evita bajar 261 MB por noche.
    """
    parametros = [
        ("filters[time_range_start]", str(desde)),
        ("filters[time_range_end]", str(hasta)),
        ("filters[exporters_ids][]", str(identificador)),
        ("filters[importers_ids][]", "all_imp"),
        ("filters[sources_ids][]", str(origen) if origen else "all_sou"),
        ("filters[purposes_ids][]", "all_pur"),
        ("filters[terms_ids][]", "all_ter"),
        ("filters[taxon_concepts_ids][]", ""),
        ("filters[reset]", ""),
        ("filters[selection_taxon]", "taxonomic_cascade"),
    ]
    url = (f"{BASE}/en/cites_trade/exports/download.json?"
           + urllib.parse.urlencode(parametros))
    return int(_json(url)["total"])


def _ultimoAnioCompleto(tabla: dict) -> int:
    """El informe anual vence el 31 de octubre del año siguiente.

    No es una estimación: es el plazo del tratado. Pero se comprueba contra los
    testigos, porque una regla correcta aplicada a una fuente que cambió sigue
    dando un año vacío, y un año vacío publicado como completo diría que la
    región dejó de comerciar.
    """
    hoy = datetime.now(timezone.utc)
    candidato = hoy.year - 1 if hoy.month >= 11 else hoy.year - 2

    def testigo(anio: int) -> int:
        return sum(_contar(tabla[DOS_LETRAS[iso]], anio, anio) for iso in TESTIGOS)

    actual, anterior = testigo(candidato), testigo(candidato - 1)
    if anterior and actual < anterior * 0.2:
        raise RuntimeError(
            f"El año {candidato} debería estar completo según el plazo del tratado "
            f"—31 de octubre del año siguiente— y sin embargo los tres Estados "
            f"testigo suman {actual} asientos contra {anterior} del año anterior. "
            "La regla o la fuente cambiaron. NO se publica un año casi vacío como "
            "si fuera el último completo.")
    return candidato


def _delEstado(faena: tuple) -> tuple:
    iso, identificador, desde, hasta = faena
    total = _contar(identificador, desde, hasta)
    decomiso = _contar(identificador, desde, hasta, ORIGEN_DECOMISO)
    ultimo = None
    for anio in range(hasta, hasta - MAXIMO_RETROCESO, -1):
        if _contar(identificador, anio, anio) > 0:
            ultimo = anio
            break
    return iso, total, decomiso, ultimo


def recolectar():
    tabla = _entidades()
    hasta = _ultimoAnioCompleto(tabla)
    desde = hasta - VENTANA_ANIOS + 1

    # PRIMERA GUARDA: el instrumento. Antes de creerle un cero a nadie.
    control = tabla[DOS_LETRAS[CONTROL]]
    controlTotal = _contar(control, desde, hasta)
    if controlTotal <= 0:
        raise RuntimeError(
            f"La prueba del instrumento falló: {CONTROL} —que tiene comercio "
            f"registrado todos los años— no devolvió ningún asiento entre {desde} y "
            f"{hasta}. Eso NO significa que no haya comercio: significa que la "
            "consulta no sirve. NO se publican treinta y tres ceros.")

    # SEGUNDA GUARDA: el filtro. Esta fuente IGNORA EN SILENCIO los parámetros que
    # no conoce y devuelve el total. Si el filtro de origen dejara de existir, el
    # registro publicaría «todo es decomiso» en los 33 Estados sin advertirlo.
    controlDecomiso = _contar(control, desde, hasta, ORIGEN_DECOMISO)
    if controlDecomiso >= controlTotal:
        raise RuntimeError(
            f"La prueba del filtro falló: en {CONTROL} el recuento con origen en "
            f"decomiso ({controlDecomiso}) no es menor que el total ({controlTotal}). "
            "Esta fuente ignora en silencio los parámetros que no conoce, así que "
            "eso significa que el filtro de origen dejó de aplicarse. NO se publica "
            "un total disfrazado de decomiso.")

    faenas = [(pais["iso"], tabla[DOS_LETRAS[pais["iso"]]], desde, hasta)
              for pais in geo.padron() if pais["iso"] in DOS_LETRAS]
    with ThreadPoolExecutor(max_workers=5) as ejecutor:
        hallado = {iso: (t, d, u) for iso, t, d, u in ejecutor.map(_delEstado, faenas)}

    registros, conRegistro, rezagados = [], 0, []
    for pais in geo.padron():
        encontrado = hallado.get(pais["iso"])
        if encontrado is None:
            registros.append({
                "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
                "estado": "sin_equivalencia_en_la_fuente",
            })
            continue
        total, decomiso, ultimo = encontrado
        if decomiso > total:
            raise RuntimeError(
                f"En {pais['pais']} el recuento con origen en decomiso ({decomiso}) "
                f"supera al total ({total}), que es imposible. El filtro no está "
                "haciendo lo que dice. NO se publica.")
        if total:
            conRegistro += 1
        if ultimo and ultimo < hasta:
            rezagados.append({"pais": pais["pais"], "ultimo_anio": ultimo})
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": "con_registro" if total else "sin_registro_en_la_ventana",
            "comercio_registrado": total,
            "con_origen_decomiso": decomiso,
            "proporcion_decomiso_pct": round(decomiso * 100 / total, 2) if total else None,
            "proporcion_comparable": total >= MINIMO_PARA_PROPORCION,
            "ultimo_anio_con_asiento": ultimo,
        })

    vacios = [
        "LO QUE ESTA BASE REGISTRA ES COMERCIO LEGAL, NO TRAFICO. Cada asiento nace de "
        "un permiso o de un informe anual que una Parte del tratado presento. El trafico "
        "ilegal, por definicion, NO TIENE PERMISO Y NO ENTRA ACA. Este colector NO mide "
        "contrabando de fauna, y la materia de contrabando SIGUE SIN FUENTE PROPIA.",
        "«ORIGEN EN DECOMISO» NO ES «CANTIDAD DE DECOMISOS». El codigo marca especimenes "
        "cuyo ORIGEN DECLARADO es una incautacion, y el asiento aparece cuando ese "
        "especimen SE MUEVE DESPUES —a un centro de rescate, a un zoologico, a "
        "investigacion—. Un Estado con muchos asientos de ese tipo puede tener mas "
        "control, mas delito, o mas movimiento posterior de lo incautado: son tres "
        "explicaciones distintas y esta fuente NO ELIGE ENTRE ELLAS.",
        "MAS DECOMISO PUEDE SER MAS CONTROL, NO MAS DELITO. Es el mismo sesgo de "
        "deteccion que el registro ya declara en trata de personas: se cuenta lo que se "
        "detecta y se informa, no lo que ocurre. Un Estado sin capacidad de fiscalizar "
        "no incauta, y por eso aparece limpio.",
        "NO ORDENA ESTADOS Y NO ENTRA AL COMPUESTO. El volumen depende de la "
        "biodiversidad del pais, del tamanio de su economia y de su papel en el comercio "
        "de cueros, madera o mascotas. Y la proporcion de decomiso NO ESTA ORIENTADA: no "
        "se sabe si mas es mejor o peor. Entra como MAGNITUD, al lado del dato "
        "comparable y nunca adentro.",
        "NO SE PUEDE SABER QUIEN INFORMO. En esta consulta la base no distingue si el "
        "asiento lo declaro el exportador o el importador. Por eso el registro dice «no "
        "hay asientos de comercio con este Estado despues de tal anio» y NO dice «el "
        "Estado dejo de informar»: son dos afirmaciones distintas y solo la primera esta "
        "probada.",
        f"LA FUENTE LLEVA UN ANIO Y MEDIO DE REZAGO, y es del tratado, no de la fuente: "
        f"los informes anuales vencen el 31 de octubre del anio siguiente. El ultimo "
        f"anio completo es {hasta} y la ventana publicada va de {desde} a {hasta}. Esto "
        "NO sirve para seguir una crisis: sirve para ver un patron de cinco anios.",
        f"UNA PROPORCION SOBRE TRES ASIENTOS NO ES UNA PROPORCION. Los Estados con menos "
        f"de {MINIMO_PARA_PROPORCION} asientos en la ventana llevan su porcentaje MARCADO "
        "COMO NO COMPARABLE: sin ese minimo, Granada quedaba segunda de la region con 4 "
        "asientos sobre 6 y Santa Lucia tercera con 1 sobre 3, por delante de Bahamas, "
        "que tiene 151 sobre 589. El numero se publica igual —esconderlo seria peor—, "
        "pero NO SE ORDENA CONTRA LOS DEMAS.",
        "ANTES DE CREER UN NUMERO SE PRUEBA EL INSTRUMENTO Y SE PRUEBA EL FILTRO. Esta "
        "fuente IGNORA EN SILENCIO los parametros que no conoce y devuelve el total sin "
        "filtrar: un filtro renombrado rio arriba haria publicar «todo es decomiso» en "
        f"los 33 Estados sin advertirlo. Se comprueba que {CONTROL} tenga comercio y que "
        "su recuento de decomiso sea ESTRICTAMENTE MENOR que su total. Si alguna de las "
        "dos falla, la corrida se detiene entera.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=3,
        corroborado=False,
        nota=("Registro administrativo de la secretaria de un tratado internacional, "
              "compilado por el centro de vigilancia de la conservacion del programa "
              "ambiental de las Naciones Unidas. Fiabilidad A porque el productor "
              "administra el propio tratado. Credibilidad 3 porque lo que se verifica es "
              "QUE UNA PARTE PRESENTO ESE INFORME, no que el informe recoja todo el "
              "comercio: la base tiene discrepancias conocidas entre lo que declara el "
              "exportador y lo que declara el importador."),
    )

    return comun.escribir(
        colector="cites",
        capa="publico",
        fuente=("CITES — base de datos de comercio de especies protegidas "
                "(secretaría CITES / UNEP-WCMC)"),
        url_fuente="https://trade.cites.org/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "ventana_desde": desde,
                "ventana_hasta": hasta,
                "ultimo_anio_completo": hasta,
                "estados_con_registro": conRegistro,
                "estados_del_padron": len(registros),
                "asientos_en_la_region": sum(r.get("comercio_registrado") or 0
                                             for r in registros),
                "asientos_con_origen_decomiso": sum(r.get("con_origen_decomiso") or 0
                                                    for r in registros),
                "instrumento_probado": True,
                "filtro_probado": True,
                "consultado": comun.ahora(),
            },
            "sin_asiento_reciente": sorted(rezagados, key=lambda x: x["ultimo_anio"]),
        },
    )


if __name__ == "__main__":
    comun.correr("cites", recolectar)
