# -*- coding: utf-8 -*-
"""CEPAL: femicidios, cárceles y lo que la gente siente sobre su seguridad.

POR QUÉ EXISTE
--------------
El registro no medía **nada** de violencia de género. Ninguna de sus 40 fuentes
la publica de forma comparable para los 33, y por eso la materia no existía: ni
como dato ni como vacío del que se pudiera decir dónde buscarlo.

La CEPAL sí la publica, y con la autoridad de ser el organismo estadístico de
Naciones Unidas para la región: su **Observatorio de Igualdad de Género de
América Latina y el Caribe** recopila la cifra que cada Estado informa, y la
sirve por una interfaz abierta con el código ISO de cada país adentro.

QUÉ ENTRA, Y POR QUÉ ESTOS
---------------------------
- **Tasa de femicidios o feminicidios** por cada 100.000 mujeres. Es la única
  medida comparable de la forma más extrema de esa violencia.
- **Ocupación carcelaria** sobre la capacidad oficial. El registro tenía presos
  sin condena, que dice quién espera juicio; no tenía hacinamiento, que dice en
  qué condiciones espera.

LO QUE ESTA CIFRA NO ES, Y SE DECLARA
--------------------------------------
El femicidio **no se define igual en todos los Estados**. Algunos cuentan solo
el homicidio cometido por la pareja o expareja; otros incluyen todo asesinato de
una mujer por razones de género. La CEPAL lo advierte y este registro lo repite:
la comparación entre Estados es indicativa, no exacta, y una cifra baja puede
significar menos casos o una definición más estrecha.

CÓMO SE LEE LA INTERFAZ
------------------------
Cada indicador trae sus dimensiones —país, año y a veces alguna más— y sus
filas apuntan a los miembros por identificador. El colector arma el diccionario
de cada dimensión y traduce. **Si un indicador tiene una dimensión que el
colector no sabe resolver, no se publica a medias: se descarta y se declara.**
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

import comun
import geo

BASE = "https://api-cepalstat.cepal.org/cepalstat/api/v1"
INTENTOS = 3

# Los indicadores elegidos, con la clave con que viajan al registro.
INDICADORES = [
    {"id": 2812, "clave": "femicidios",
     "rotulo": "Femicidios o feminicidios",
     "unidad": "por cada 100.000 mujeres", "mas_es_peor": True,
     "cautela": ("Cada Estado define el femicidio en su propia ley y no todos cuentan lo mismo: "
                 "unos registran solo el crimen cometido por la pareja o la expareja y otros, "
                 "toda muerte violenta de una mujer por razones de género. Una cifra más baja "
                 "puede venir de una definición más angosta o de un registro que recién empieza, "
                 "no de menos crímenes.")},
    {"id": 4143, "clave": "ocupacion_carcelaria",
     "rotulo": "Ocupación carcelaria sobre la capacidad oficial",
     "unidad": "% de la capacidad oficial", "mas_es_peor": True,
     "cautela": ("Se compara contra la capacidad que declara cada Estado, y esa capacidad la fija "
                 "cada uno con su propio criterio. Un Estado que recalcula hacia arriba lo que "
                 "entra en sus cárceles baja este número sin mover un solo preso. Dice cuán "
                 "llena está la cárcel según su propia vara, no cuánta gente hay presa.")},
    # LO QUE LA GENTE SIENTE, que no es lo mismo que lo que la policia cuenta.
    # Un Estado puede tener pocos homicidios y una poblacion que no sale de
    # noche, y al reves. Para quien vive en un pais —o va a visitarlo— esto
    # dice tanto como la tasa.
    {"id": 5651, "clave": "victima_delito",
     "rotulo": "Personas que fueron víctimas de un delito en el último año",
     "unidad": "% de las personas", "mas_es_peor": True,
     "cautela": ("Sale de preguntarle a la gente, no de los registros de la policía: dice lo que "
                 "las personas DECLARAN haber vivido. No están los 33 Estados y el año de la "
                 "encuesta no es el mismo en todos, así que dos países se comparan con cuidado. "
                 "Suele ser más alto que la denuncia policial, porque mucho delito no se denuncia.")},
    {"id": 3259, "clave": "temor_delito",
     "rotulo": "Personas que temen ser víctimas de un delito",
     "unidad": "% de las personas", "mas_es_peor": True,
     "cautela": ("Mide MIEDO, no delito. El temor sube con la cobertura de los medios y con la "
                 "experiencia del barrio, y puede ser alto donde el delito baja y al revés. No "
                 "están los 33 Estados y el año de la encuesta cambia de país a país.")},
    {"id": 5549, "clave": "seguridad_barrio",
     "rotulo": "Personas que se sienten seguras en su barrio",
     "unidad": "% de las personas", "mas_es_peor": False,
     "cautela": ("Es una sensación declarada en una encuesta, no una medición de lo que pasa en "
                 "la calle, y se refiere al barrio propio, no al país. La gente suele sentir su "
                 "barrio más seguro que su ciudad. No están los 33 Estados y el año de la "
                 "encuesta cambia de país a país.")},
    # SEGUNDA FUENTE DE DOS COSAS QUE EL REGISTRO MEDÍA CON UNA SOLA. La
    # desigualdad la medía solo el Banco Mundial, y el desempleo total solo la
    # OIT. La CEPAL mide las dos con su propia manera de contar, y es el
    # organismo de la región: si difiere, la diferencia se ve, no se esconde.
    {"id": 3289, "clave": "gini_cepal", "eje": "Desarrollo",
     "rotulo": "Desigualdad · índice de Gini · segunda fuente",
     "unidad": "0 igualdad, 100 desigualdad máxima", "mas_es_peor": True,
     # La CEPAL lo publica de 0 a 1; el registro lo muestra de 0 a 100, igual que
     # el Banco Mundial, para que las dos cifras se puedan poner lado a lado.
     "escala": 100, "decimales": 1,
     "cautela": "SEGUNDA MEDICIÓN de algo que el registro ya publica con el Banco Mundial. "
                "La CEPAL lo calcula sobre el ingreso per cápita de las personas, con sus "
                "propios ajustes a las encuestas de hogares; si las dos cifras difieren, la "
                "diferencia dice cómo se mide, no quién se equivoca. La CEPAL lo publica de "
                "0 a 1 y acá se muestra multiplicado por 100."},
    {"id": 127, "clave": "desempleo_cepal", "eje": "Desarrollo",
     "rotulo": "Desempleo · segunda fuente",
     "unidad": "% de la población activa", "mas_es_peor": True,
     "cautela": "SEGUNDA MEDICIÓN de algo que el registro ya publica con la OIT, y NO mide "
                "exactamente lo mismo. Es la cifra oficial que informa cada Estado, y la "
                "CEPAL advierte que en muchos es desempleo URBANO —de las ciudades o de "
                "algunas de ellas— y no nacional. La OIT, en cambio, estima una tasa "
                "nacional comparable. Si difieren, la cobertura explica buena parte."},
    # CUARTA VUELTA (autorizada el 13/9/2026): tres asuntos más que tenían una
    # sola fuente.
    {"id": 2119, "clave": "secundaria_cepal", "eje": "Desarrollo",
     "rotulo": "Jóvenes de 20 a 24 con secundaria completa · segunda fuente",
     "unidad": "% de los jóvenes de 20 a 24", "mas_es_peor": False, "decimales": 1,
     "cautela": "SEGUNDA MEDICIÓN, y no de la misma pregunta. La UNESCO mide cuántos "
                "terminan la secundaria en la cohorte de edad que corresponde; la CEPAL, "
                "cuántos jóvenes de 20 a 24 años declaran tenerla completa en la encuesta "
                "de hogares. Las dos hablan de lo mismo desde dos fuentes distintas: "
                "registros escolares y encuestas."},
    {"id": 4784, "clave": "esperanza_vida_cepal", "eje": "Desarrollo",
     "rotulo": "Esperanza de vida al nacer · segunda fuente",
     "unidad": "años", "mas_es_peor": False, "decimales": 1,
     # La serie llega a 2100: desde 2024 es proyección y no estimación. Se corta
     # en el último año estimado de la edición 2024 de la ONU.
     "hasta": 2023,
     "cautela": "SEGUNDA MEDICIÓN con independencia PARCIAL. La calcula el Centro "
                "Latinoamericano y Caribeño de Demografía de la CEPAL con la División de "
                "Población de la ONU; la OMS usa en parte esos mismos insumos para sus "
                "tablas de vida. Que coincidan corrobora menos de lo que parece. Se "
                "publica hasta 2023: lo posterior es proyección."},
    {"id": 4410, "clave": "gasto_seguridad_cepal", "eje": "Seguridad",
     "rotulo": "Gasto en orden público y seguridad · segunda fuente",
     "unidad": "% del producto", "mas_es_peor": False, "sin_direccion": True,
     "decimales": 2,
     "fijar": {"función": "Orden público y seguridad",
               "Cobertura institucional": "Gobierno central"},
     "cautela": "SEGUNDA MEDICIÓN de algo que el registro ya publica con el FMI. La CEPAL "
                "toma el gasto del gobierno central según la clasificación por funciones; "
                "no incluye provincias ni municipios, que en los Estados federales pagan "
                "buena parte de la policía. LA SERIE TERMINA EN 2020 en casi todos los "
                "Estados: sirve para contrastar niveles, no para el año corriente."},
    # CONFIANZA EN LAS INSTITUCIONES Y CORRUPCIÓN VIVIDA (barrido de CEPALSTAT del
    # 16/9/2026). Capa de gobernanza que el registro no tenía: no cuánta corrupción
    # miden los expertos —eso ya está con el WGI y Transparencia— sino cuánto confía
    # y qué vive la gente. Fuente base: Latinobarómetro vía CEPAL, que la dirección
    # autorizó a publicar como porcentaje. Dieciocho Estados.
    {"id": 3257, "clave": "confianza_policia", "eje": "Gobernanza",
     "rotulo": "Personas que confían en la policía",
     "unidad": "% de las personas", "mas_es_peor": False, "decimales": 1,
     "cautela": "CUÁNTO CONFÍA LA GENTE en la policía, no cuán buena es. Sale de la encuesta Latinobarómetro, que compila la CEPAL: dice lo que las personas DECLARAN, no un registro. Son 18 Estados de América Latina —no está el Caribe— y el año de la encuesta no es el mismo en todos, así que dos países se comparan con cuidado."},
    {"id": 5528, "clave": "desconfianza_justicia", "eje": "Gobernanza",
     "rotulo": "Personas que desconfían del poder judicial",
     "unidad": "% de las personas", "mas_es_peor": True, "decimales": 1,
     "cautela": "Es desconfianza DECLARADA en la justicia, no una medida de su independencia "
                "—esa está en «Estado de derecho»—. Sale de la encuesta Latinobarómetro, que compila la CEPAL: dice lo que las personas DECLARAN, no un registro. Son 18 Estados de América Latina —no está el Caribe— y el año de la encuesta no es el mismo en todos, así que dos países se comparan con cuidado."},
    {"id": 995, "clave": "desconfianza_partidos", "eje": "Gobernanza",
     "rotulo": "Personas que desconfían de los partidos y el congreso",
     "unidad": "% de las personas", "mas_es_peor": True, "decimales": 1,
     "cautela": "Mide desconfianza DECLARADA en los partidos políticos y el congreso. Sale de la encuesta Latinobarómetro, que compila la CEPAL: dice lo que las personas DECLARAN, no un registro. Son 18 Estados de América Latina —no está el Caribe— y el año de la encuesta no es el mismo en todos, así que dos países se comparan con cuidado."},
    {"id": 5653, "clave": "confianza_municipio", "eje": "Gobernanza",
     "rotulo": "Personas que confían en su municipalidad",
     "unidad": "% de las personas", "mas_es_peor": False, "decimales": 1,
     "cautela": "Confianza DECLARADA en el gobierno local, el más cercano. Sale de la encuesta Latinobarómetro, que compila la CEPAL: dice lo que las personas DECLARAN, no un registro. Son 18 Estados de América Latina —no está el Caribe— y el año de la encuesta no es el mismo en todos, así que dos países se comparan con cuidado."},
    {"id": 5548, "clave": "corrupcion_percibida_gente", "eje": "Gobernanza",
     "rotulo": "Personas que creen que la corrupción está muy generalizada",
     "unidad": "% de las personas", "mas_es_peor": True, "decimales": 1,
     "cautela": "Es lo que la gente CREE sobre los funcionarios públicos, y suma a los índices "
                "de expertos de Transparencia y el WGI la vivencia ciudadana. Sale de la encuesta Latinobarómetro, que compila la CEPAL: dice lo que las personas DECLARAN, no un registro. Son 18 Estados de América Latina —no está el Caribe— y el año de la encuesta no es el mismo en todos, así que dos países se comparan con cuidado."},
    {"id": 5655, "clave": "coima_policia", "eje": "Gobernanza",
     "rotulo": "Personas a las que un policía pidió una coima en el último año",
     "unidad": "% de las personas", "mas_es_peor": True, "decimales": 1,
     "cautela": "Es corrupción VIVIDA, no percibida: la persona declara que un agente le pidió "
                "una coima. Suele ser más baja que la percepción, porque no todos la sufren. Sale de la encuesta Latinobarómetro, que compila la CEPAL: dice lo que las personas DECLARAN, no un registro. Son 18 Estados de América Latina —no está el Caribe— y el año de la encuesta no es el mismo en todos, así que dos países se comparan con cuidado."},
]
# Los Estados que la fuente agrega —«América Latina», «El Caribe»— no son
# Estados: se descartan por no estar en el padrón, sin ruido.
CONTROL = "femicidios"


def _pedir(ruta: str) -> dict:
    ultimo = None
    for intento in range(INTENTOS):
        if intento:
            time.sleep(2 * intento)
        try:
            peticion = urllib.request.Request(
                f"{BASE}/{ruta}", headers={"User-Agent": comun.AGENTE,
                                           "Accept": "application/json"})
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                return json.loads(respuesta.read().decode("utf-8", "replace"))
        except Exception as error:  # noqa: BLE001 — se reintenta y, si no, se declara
            ultimo = f"{type(error).__name__}: {error}"
    raise RuntimeError(f"CEPALSTAT no respondió «{ruta}» en {INTENTOS} intentos: {ultimo}. "
                       "NO se publica una serie vacía: la anterior queda intacta.")


def _anios(dimensiones: list) -> tuple:
    """El diccionario {id de miembro: año} y el nombre de su dimensión."""
    for d in dimensiones:
        nombre = str(d.get("name") or "")
        if "Años" in nombre or "Anios" in nombre or "Year" in nombre:
            mapa = {}
            for m in d.get("members") or []:
                texto = str(m.get("name") or "")
                if texto.isdigit():
                    mapa[m.get("id")] = int(texto)
            return mapa, d.get("dim_id") or d.get("id")
    return {}, None


def _serie(indicador: dict, isos: set) -> tuple:
    """{iso: [{anio, valor}]} para un indicador, y lo que no se pudo resolver."""
    cuerpo = _pedir(f"indicator/{indicador['id']}/data?lang=es&format=json").get("body") or {}
    dims = cuerpo.get("dimensions") or []
    porAnio, _ = _anios(dims)
    if not porAnio:
        return {}, "no se halló la dimensión de años"

    # Las dimensiones que no son país ni año: solo se aceptan si la fila trae el
    # miembro que agrega el total. Si no se puede resolver, no se publica.
    otras = []
    fijar = indicador.get("fijar") or {}
    for d in dims:
        nombre = str(d.get("name") or "")
        if "País" in nombre or "Pais" in nombre or "Años" in nombre:
            continue
        # Las dimensiones que el indicador FIJA por nombre —una función del gasto,
        # una cobertura— se resuelven por el rótulo exacto del miembro. Si el rótulo
        # no está, no se adivina otro: se descarta y se declara.
        pedido = next((v for k, v in fijar.items() if k.lower() in nombre.lower()), None)
        if pedido:
            elegidos = {m.get("id") for m in (d.get("members") or [])
                        if str(m.get("name") or "").strip() == pedido}
            if not elegidos:
                return {}, f"en «{nombre}» no figura «{pedido}»"
            otras.append(elegidos)
            continue
        totales = {m.get("id") for m in (d.get("members") or [])
                   if str(m.get("name") or "").strip().lower() in
                   ("total", "ambos sexos", "total nacional", "ambos", "nacional")}
        if not totales:
            return {}, f"tiene la dimensión «{nombre}» y ningún miembro que agregue el total"
        otras.append(totales)

    salida = {}
    for fila in cuerpo.get("data") or []:
        iso = fila.get("iso3")
        if iso not in isos:
            continue
        anio = next((porAnio[v] for k, v in fila.items()
                     if k.startswith("dim_") and v in porAnio), None)
        if anio is None or anio > indicador.get("hasta", 9999):
            continue
        if otras:
            valores = {v for k, v in fila.items() if k.startswith("dim_")}
            if not all(valores & t for t in otras):
                continue
        try:
            valor = float(str(fila.get("value")).replace(",", "."))
        except (TypeError, ValueError):
            continue
        valor = valor * indicador.get("escala", 1)
        salida.setdefault(iso, {})[anio] = round(valor, indicador.get("decimales", 2))
    return ({iso: [{"anio": a, "valor": v} for a, v in sorted(por.items())]
             for iso, por in salida.items()}, None)


def recolectar():
    padron = geo.padron()
    isos = {p["iso"] for p in padron}
    series, descartados = {}, []
    for ind in INDICADORES:
        serie, porque = _serie(ind, isos)
        if porque:
            descartados.append(f"{ind['rotulo']}: {porque}")
            continue
        series[ind["clave"]] = serie

    # SE PRUEBA EL LECTOR ANTES DE CREERLE UN VACÍO A NADIE.
    if len(series.get(CONTROL, {})) < 10:
        raise RuntimeError(
            "La prueba del lector falló: se leyeron menos de diez Estados con tasa de "
            "femicidios, y la fuente publica muchos más. La interfaz cambió de forma. "
            "NO se publica una lectura a ciegas.")

    registros, conAlguno = [], 0
    for p in padron:
        fila = {"iso": p["iso"], "pais": p["pais"], "bloque": p["bloque"], "indicadores": {}}
        for ind in INDICADORES:
            serie = series.get(ind["clave"], {}).get(p["iso"])
            if not serie:
                continue
            fila["indicadores"][ind["clave"]] = {
                "valor": serie[-1]["valor"], "anio": serie[-1]["anio"], "serie": serie,
                "valor_anterior": serie[-2]["valor"] if len(serie) > 1 else None,
                "anio_anterior": serie[-2]["anio"] if len(serie) > 1 else None,
            }
        fila["estado"] = "con_dato" if fila["indicadores"] else "sin_dato"
        if fila["indicadores"]:
            conAlguno += 1
        registros.append(fila)

    cobertura = {ind["clave"]: sum(1 for r in registros if ind["clave"] in r["indicadores"])
                 for ind in INDICADORES}
    publicables = [i for i in INDICADORES if cobertura.get(i["clave"], 0) > 0]
    if not publicables:
        raise RuntimeError("Ningún indicador quedó con un solo Estado. NO se publica un "
                           "archivo hueco: el anterior queda intacto.")

    calificacion = comun.calificar(
        fiabilidad="A", credibilidad=2, corroborado=False,
        nota=("Comisión Económica para América Latina y el Caribe, organismo estadístico de "
              "Naciones Unidas para la región, sobre lo que informa cada Estado a su "
              "Observatorio de Igualdad de Género. Fiabilidad A por el organismo y su "
              "metodología publicada. Credibilidad 2 porque el dato lo produce cada Estado "
              "con su propia definición legal, y la CEPAL lo recopila sin homologarlo."),
    )
    vacios = [
        "LO QUE LA GENTE SIENTE NO ES LO QUE LA POLICÍA CUENTA. Las tres medidas de "
        "victimización, temor y sensación de seguridad salen de encuestas de hogares: "
        "dicen lo que las personas declaran, no lo que ocurrió. Un Estado puede tener "
        "pocos homicidios y una población que no sale de noche, y al revés.",
        "EL FEMICIDIO NO SE DEFINE IGUAL EN TODOS LOS ESTADOS. Algunos cuentan solo el "
        "homicidio cometido por la pareja o la expareja; otros, todo asesinato de una mujer "
        "por razones de género. La comparación entre Estados es indicativa, no exacta: una "
        "cifra baja puede significar menos casos o una definición más estrecha.",
        "Es la cifra que cada Estado informa. Donde el sistema judicial no tipifica el "
        "femicidio, o no lo registra aparte del homicidio, la cifra no existe o queda corta.",
        "EL DESEMPLEO DE LA CEPAL ES, EN MUCHOS ESTADOS, URBANO. Es la cifra oficial "
        "de cada país, y la propia CEPAL advierte que se refiere a las zonas urbanas —o a "
        "algunas ciudades— salvo que se indique cobertura nacional. No se compara sin "
        "mirar eso con la tasa nacional que estima la OIT.",
        "EL GINI SE PUBLICA DE 0 A 100. La CEPAL lo da de 0 a 1; se multiplica por 100 "
        "para que se lea en la misma escala que el del Banco Mundial.",
        "DEL GINI SE TOMA SOLO EL NACIONAL. Donde la CEPAL publica únicamente el urbano "
        "—es el caso de la Argentina, cuya encuesta cubre solo ciudades— el Estado queda "
        "sin esta segunda cifra: el urbano no se hace pasar por nacional.",
        "Serie anual con rezago: no es un dato en vivo.",
        f"Cobertura del padrón: " + " · ".join(
            f"{i['rotulo']}, {cobertura.get(i['clave'], 0)} de {len(registros)} Estados"
            for i in publicables) + ".",
    ] + ([f"Indicadores que la fuente publica y este colector NO pudo leer: "
          + "; ".join(descartados) + "."] if descartados else [])

    return comun.escribir(
        colector="cepal",
        capa="publico",
        fuente="CEPALSTAT — Comisión Económica para América Latina y el Caribe (CEPAL): "
               "Observatorio de Igualdad de Género y estadísticas de seguridad ciudadana",
        url_fuente="https://statistics.cepal.org/portal/cepalstat",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": [{"clave": i["clave"], "rotulo": i["rotulo"], "unidad": i["unidad"],
                             "mas_es_peor": i["mas_es_peor"], "eje": i.get("eje", "Seguridad"),
                             "origen": "CEPAL, CEPALSTAT",
                             **({"cautela": i["cautela"]} if i.get("cautela") else {}),
                             **({"sin_direccion": True} if i.get("sin_direccion") else {}),
                             "cepalstat_id": i["id"]}
                            for i in publicables],
            "resumen": {
                "estados_con_algun_dato": conAlguno,
                "estados_del_padron": len(registros),
                "cobertura": cobertura,
                "lector_probado": True,
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("cepal", recolectar)
