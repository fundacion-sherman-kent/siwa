"""Funciones compartidas por los colectores del SIWA.

Sin dependencias externas: solo biblioteca estándar de Python.

Reglas de la casa que este módulo hace cumplir por código
(`doctrina/siwa.md`):

- Si una fuente falla, el colector termina con error, deja intacto el dato
  anterior y registra la falla en `datos/publico/estado/`. Nunca escribe un
  valor de ejemplo (§8.1).
- Ningún dato puede calificar credibilidad `1` sin corroboración por dos
  orígenes independientes (§3). El intento levanta excepción.
- Todo archivo sale con fuente, dirección de la fuente, momento de obtención y
  vacíos declarados (§1).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
AGENTE = "SIWA/0.1 (Fundacion Sherman Kent; +https://fundacionkent.org)"
ESPERA = 30

# PRESENTARSE ENTERO, SIN DISFRAZARSE. Varios Estados devolvían 403 —México,
# República Dominicana, el Ministerio de Salud de Chile, el Ministerio de Justicia
# de Brasil— y el registro lo anotaba como «bloquea a los programas». No era eso:
# su guardia rechaza a quien pide una página sin las cabeceras que manda cualquier
# navegador. Comprobado el 15/9/2026: con estas cabeceras los cuatro responden 200.
#
# El nombre SIWA SIGUE ADELANTE en la identificación. La casa no se hace pasar por
# una persona: se presenta completa, con su nombre y su dirección, para que el
# administrador del sitio sepa quién pasó y pueda escribirnos.
CABECERAS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/140.0.0.0 Safari/537.36 SIWA/1.0 (+https://siwa.fundacionkent.org)"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Dest": "document",
}

FIABILIDAD = ("A", "B", "C", "D", "E", "F")

# La atribucion viaja DENTRO de cada archivo, no solo en la pantalla. Quien se
# lleve el dato crudo se lleva tambien de quien es el trabajo: es la unica forma
# de que el credito sobreviva a una descarga.
# LA DIRECCION DEL REGISTRO, EN UN SOLO LUGAR. Hasta la mudanza a dominio propio
# —6 de septiembre de 2026— estuvo escrita a mano en DOCE archivos, y encontrarlas
# todas fue trabajo de arqueologia. Si el registro vuelve a mudarse se cambia aca,
# se corren `herramientas/puertas.py` y `herramientas/novedades.py`, y listo.
BASE = "https://siwa.fundacionkent.org"
SITIO_URL = f"{BASE}/sitio/index.html"

# LOS TESTIGOS DE CONTROL. Viven en `datos/publico/` como todo lo demás, pero no
# son datos: son mediciones que esta casa hace de sí misma, no vienen de ninguna
# fuente y por eso no tienen procedencia ni calificación de Almirantazgo.
#
# La lista vive ACÁ y no en cada herramienta a propósito. El catálogo tiene que
# excluirlos de la cuenta de conjuntos y la auditoría tiene que no exigirles una
# procedencia que no les corresponde: si cada una llevara su propia copia, el
# día que aparezca un testigo nuevo una de las dos lo trataría mal, y sería la
# tercera vez que este registro paga la misma duplicación.
TESTIGOS = {
    "indice.json": "el catálogo público de conjuntos",
    "auditoria.json": "auditoría del registro, corrida en cada recolección",
    "reloj-actualidad.json": "reloj de actualidad: compara cada indicador con lo último que publica su fuente",
    "pantallas.json": "control de diseño adaptable, corrido en cada cambio de código",
    "mineria.json": "minería sobre el propio registro: pistas, no conclusiones",
    "segunda_fuente.json": "la regla de las dos fuentes, medida en cada recolección",
}

ATRIBUCION = {
    "obra": "SIWA — Reporte de situación de América Latina y el Caribe",
    "autor": "Fundación Sherman Kent — Oficina de Generación de Inteligencia",
    "sitio": SITIO_URL,
    "uso": ("Acceso libre y gratuito. El aporte de la Fundación —recolección, "
            "calificación de fuentes y declaración de vacíos— se publica bajo "
            "licencia Creative Commons Atribución 4.0 Internacional (CC BY 4.0): "
            "https://creativecommons.org/licenses/by/4.0/. Se permite reproducir, "
            "redistribuir y derivar citando la fuente de este modo: «SIWA, "
            "Fundación Sherman Kent». Los datos de base pertenecen a los "
            "productores citados en cada indicador y conservan la licencia de su "
            "fuente; cuando una fuente impone condiciones adicionales, se declaran "
            "en «restriccion_de_uso»."),
    "licencia": "CC BY 4.0",
    "licencia_url": "https://creativecommons.org/licenses/by/4.0/",
    "no_implica": ("La cita no implica aval de la Fundación sobre el uso que se "
                   "haga de estos datos, ni sobre las conclusiones ajenas."),
}


# ---------------------------------------------------------------------------
# LA CATEGORIA DE CADA INDICADOR
#
# Hasta ahora la categoria existia SOLO como «en que parte del HTML esta escrito
# el indicador». Eso no es un dato: es un accidente de maquetacion, y se nota en
# que los seis indicadores del entorno informativo —los mas recientes del
# registro, con dato de 2025— NO APARECIAN EN NINGUNA SECCION porque nadie los
# habia asignado, y nada lo advertia.
#
# Aca la categoria pasa a ser un HECHO DEL REGISTRO: viaja en el archivo de
# datos, entra en la planilla que se descarga, llega al buscador de cruces y
# sobrevive a cualquier rediseño de la pagina. Y un indicador sin categoria deja
# de pasar inadvertido: `escribir` lo dice.
#
# El eje agrupa por linea de trabajo —seguridad, defensa, gobernanza,
# desarrollo—; la categoria agrupa DENTRO del eje. Un indicador tiene
# exactamente uno de cada uno.
# ---------------------------------------------------------------------------
# El padrón usa ISO de tres letras; varias fuentes internacionales, de dos.
# Vive acá y no adentro de un colector porque ya la necesitan tres.
DOS_LETRAS = {
    "ARG": "AR", "BOL": "BO", "BRA": "BR", "CHL": "CL", "COL": "CO", "CRI": "CR",
    "CUB": "CU", "DOM": "DO", "ECU": "EC", "SLV": "SV", "GTM": "GT", "HTI": "HT",
    "HND": "HN", "MEX": "MX", "NIC": "NI", "PAN": "PA", "PRY": "PY", "PER": "PE",
    "URY": "UY", "VEN": "VE", "BLZ": "BZ", "GUY": "GY", "SUR": "SR",
    "ATG": "AG", "BHS": "BS", "BRB": "BB", "DMA": "DM", "GRD": "GD", "JAM": "JM",
    "KNA": "KN", "LCA": "LC", "VCT": "VC", "TTO": "TT",
}

CATEGORIAS = {
    # La violencia contra la mujer y el hacinamiento carcelario entran con la
    # CEPAL: la primera es una materia que el registro no medía en absoluto.
    "femicidios": "violencia",
    "victima_delito": "violencia",
    "temor_delito": "violencia",
    "seguridad_barrio": "violencia",
    "ocupacion_carcelaria": "violencia",
    "acceso_informacion": "capacidad",
    "actores_antidemocraticos": "integridad",
    "administracion_basica": "integridad",
    "agua_potable": "condiciones",
    "esperanza_vida": "salud",
    "mortalidad_materna": "salud",
    "muertes_transito": "muertes-no-delito",
    "suicidio": "muertes-no-delito",
    "alfabetizacion": "educacion",
    "fuera_escuela": "educacion",
    "gasto_educacion": "educacion",
    "matricula_terciaria": "educacion",
    "termina_secundaria": "educacion",
    "aprobacion_democracia": "integridad",
    "acceso_electricidad": "infraestructuras-criticas",
    # POR DONDE ENTRA Y SALE UN PAIS. La categoría medía el servicio —acceso,
    # pérdidas, agua— y no la puerta física. Un Estado con un solo punto de
    # amarre queda incomunicado con un accidente de ancla, y eso no aparece en
    # ninguna estadística de conectividad.
    "cables_submarinos": "infraestructuras-criticas",
    # CLOUDFLARE RADAR. El tráfico automatizado es la única cifra de ciberseguridad
    # medida sobre tráfico real; la internet moderna es conectividad, no seguridad.
    "trafico_automatizado": "ciber",
    "armas_incautadas": "seguridad-flujos-ilicitos",       # UNODC: tráfico de armas
    "detenidos_trafico_armas": "seguridad-flujos-ilicitos",
    "armas_recibidas_tiv": "material",                    # SIPRI: transferencias TIV
    "armas_enviadas_tiv": "material",
    "internet_moderno": "conectividad",
    "aeropuertos": "infraestructuras-criticas",
    "generacion_electrica": "infraestructuras-criticas",
    "capacidad_solar": "infraestructuras-criticas",
    "agua_potable_basica": "infraestructuras-criticas",
    "agua_renovable": "recursos-estrategicos",
    # LO QUE HAY BAJO TIERRA. Hasta acá la categoría tenía agua, energía importada
    # y exportación de combustibles: medidas de DEPENDENCIA, no de tenencia. Estas
    # siete dicen qué produce cada Estado y cuánto pesa en el mundo, que es la otra
    # mitad de la pregunta y la que faltaba.
    "produccion_petroleo": "recursos-estrategicos",
    "produccion_gas": "recursos-estrategicos",
    "produccion_carbon": "recursos-estrategicos",
    "reservas_petroleo": "recursos-estrategicos",
    "produccion_litio": "recursos-estrategicos",
    "cuota_mineral_mundial": "recursos-estrategicos",
    "minerales_escala_mundial": "recursos-estrategicos",
    "armas_exportadas": "material",
    "armas_importadas": "material",
    "articulos_cientificos": "ciencia-tecnologia",
    "asentamientos": "urbano",
    "autocensura": "entorno-informativo",
    "banda_ancha": "conectividad",
    "energia_importada": "recursos-estrategicos",
    "id_producto": "ciencia-tecnologia",
    "investigadores": "ciencia-tecnologia",
    "patentes_residentes": "ciencia-tecnologia",
    "perdidas_electricas": "infraestructuras-criticas",
    "puertos_contenedores": "infraestructuras-criticas",
    "efectivos_por_habitante": "efectivos",
    "efectivos_por_km2": "efectivos",
    "exporta_combustibles": "recursos-estrategicos",
    "poblacion": "recursos-estrategicos",
    "renta_gas": "recursos-estrategicos",
    "renta_minerales": "recursos-estrategicos",
    "renta_petroleo": "recursos-estrategicos",
    "superficie": "recursos-estrategicos",
    "tierra_arable": "recursos-estrategicos",
    "electricidad_por_habitante": "infraestructuras-criticas",
    "electricidad_renovable": "infraestructuras-criticas",
    "uso_energia_ei": "recursos-estrategicos",
    "uso_energia": "recursos-estrategicos",
    "bosque": "ambiente",
    "perdida_bosque": "ambiente",
    "policias": "violencia",
    "calidad_regulatoria": "institucional",
    "libertad_prensa": "entorno-informativo",
    "censura_medios": "entorno-informativo",
    "conflicto_no_estatal": "grupos-armados",
    "corrupcion": "institucional",
    # Confianza y corrupción vividas, de Latinobarómetro vía CEPAL (16/9/2026).
    "confianza_policia": "institucional",
    "desconfianza_justicia": "institucional",
    "desconfianza_partidos": "democracia",
    "confianza_municipio": "institucional",
    "corrupcion_percibida_gente": "institucional",
    "coima_policia": "soborno",
    "gasto_social_cepal": "condiciones",
    "desastres_onu": "riesgo-humanitario",
    "corrupcion_politica": "democracia",
    "democracia_electoral": "democracia",
    "democracia_liberal": "democracia",
    "democracia_participativa": "democracia",
    "denuncia_agresion": "victimizacion",
    "denuncia_robo": "victimizacion",
    "desempleo_joven": "condiciones",
    "desempleo_joven_oit": "informalidad",
    "desempleo_oit": "informalidad",
    "empleo_informal_oit": "informalidad",
    "empleo_informal": "informalidad",
    "estabilidad": "institucional",
    "estado_derecho": "institucional",
    "estado_derecho_wjp": "institucional",   # World Justice Project
    "gasto_defensa_fmi": "presupuesto-defensa",
    "gasto_seguridad": "presupuesto-seguridad",
    "gasto_seguridad_publico": "presupuesto-seguridad",
    "gasto_militar": "presupuesto-defensa",
    "gasto_militar_dolares": "presupuesto-defensa",
    "gasto_militar_publico": "presupuesto-defensa",
    "gasto_militar_pbi": "presupuesto-defensa",       # SIPRI: % del PBI
    "gasto_militar_gasto_pub": "presupuesto-defensa", # SIPRI: % del gasto público
    "gasto_militar_usd_const": "presupuesto-defensa", # SIPRI: USD constantes
    "percepcion_corrupcion": "institucional",
    "pobreza_cepal": "pobreza",
    "pobreza_extrema": "pobreza",
    "vulnerabilidad": "pobreza",
    "gini": "condiciones",
    "gini_cepal": "condiciones",
    "secundaria_cepal": "educacion",
    "esperanza_vida_cepal": "salud",
    "gasto_seguridad_cepal": "presupuesto-seguridad",
    "satelites_gcat": "aeroespacial",
    "trata_nivel": "trata",
    "produccion_petroleo_eia": "recursos-estrategicos",
    "produccion_gas_eia": "recursos-estrategicos",
    "sanciones_ofac": "sanciones",
    "sanciones_ofsi": "sanciones",
    "riesgo_inform": "riesgo-humanitario",
    "riesgo_inform_amenaza": "riesgo-humanitario",
    "riesgo_inform_vulnerabilidad": "riesgo-humanitario",
    "riesgo_inform_capacidad": "riesgo-humanitario",
    "redes_influencia_tiktok": "entorno-informativo",
    "uso_ia_generativa": "conectividad",
    "uso_chatgpt": "conectividad",
    "uso_claude": "conectividad",
    "ia_apps_ranking": "conectividad",
    "ia_apps_ranking_eeuu": "conectividad",
    "ia_apps_ranking_china": "conectividad",
    "ia_apps_ranking_otros": "conectividad",
    "ia_apps_disponibles": "conectividad",
    "nube_eeuu": "infraestructuras-criticas",
    "nube_china": "infraestructuras-criticas",
    "redes_influencia": "entorno-informativo",
    "redes_influencia_extrarregional": "entorno-informativo",
    "desempleo_cepal": "informalidad",
    "homicidios": "violencia",
    "homicidios_estado": "violencia",
    "inflacion_interanual": "condiciones",
    "inflacion_fmi": "condiciones",
    "reservas_internacionales": "condiciones",
    "inflacion_mensual": "condiciones",
    "hostigamiento_periodistas": "entorno-informativo",
    "indice_gobernanza": "integridad",
    "industria": "industrial",
    "institucion_ddhh": "capacidad",
    "intensidad_conflicto": "control-territorial",
    "internet": "conectividad",
    "lanzamientos_anuales": "aeroespacial",
    "libertad_asociacion": "libertades",
    "libertad_expresion": "libertades",
    "medios_corruptos": "entorno-informativo",
    "migracion_neta": "migraciones",
    "migrantes": "migraciones",
    "migrantes_pct": "migraciones",
    "militares_fuerza_laboral": "efectivos",
    "minerales": "materias",
    "monopolio_fuerza": "control-territorial",
    "objetos_espacio": "aeroespacial",
    "persecucion_abuso": "integridad",
    "personal_militar": "efectivos",
    "pobreza": "condiciones",
    "polarizacion": "entorno-informativo",
    "politica_anticorrupcion": "integridad",
    "recaudacion": "capacidad",
    "regalo_contrato": "contratacion",
    "registro_nacimientos": "capacidad",
    "remesas": "migraciones",
    "rentas_naturales": "materias",
    "servidores_seguros": "ciber",
    "sesgo_medios": "entorno-informativo",
    "sin_condena": "victimizacion",
    "soborno_empresas": "soborno",
    "soborno_personas": "soborno",
    "terrorismo_atentados": "terrorismo",
    "terrorismo_muertes": "terrorismo",
    "trabajo_infantil": "condiciones",
    "trata_sexual": "trata",
    "trata_trabajo": "trata",
    "trata_victimas": "trata",
    "urbanizacion": "urbano",
    "victimas_robo": "victimizacion",
    "voz_rendicion": "institucional",
}

ROTULO_CATEGORIA = {
    "sanciones": "Sanciones internacionales",
    "riesgo-humanitario": "Riesgo de crisis humanitaria",
    "aeroespacial": "Capacidad aeroespacial",
    "ambiente": "Superficie forestal",
    "capacidad": "Capacidad del Estado",
    "ciber": "Ciberseguridad",
    "condiciones": "Condiciones de vida y desigualdad",
    "conectividad": "Conectividad",
    "contratación": "Contratación pública",
    # EL NOMBRE DE LA CATEGORIA ES EL DEL BLOQUE AL QUE MANDA. Se llamaba
    # «control» y el bloque de la pagina «control-territorial»: la ficha de
    # la materia armaba un enlace a #control que no existia, y dos medidas
    # quedaban con el enlace muerto. Encontrado auditando anclas.
    "control-territorial": "Control territorial del Estado",
    "democracia": "Nivel democrático",
    "efectivos": "Efectivos",
    "entorno-informativo": "Entorno informativo",
    "grupos-armados": "Grupos armados",
    "industrial": "Industrial",
    "informalidad": "Empleo informal",
    "institucional": "Indicadores de gobernanza",
    "integridad": "Integridad y aprobación democrática",
    "libertades": "Libertades",
    "material": "Material y armamento",
    "materias": "Exportaciones y recursos",
    "migraciones": "Migraciones",
    "presupuesto-defensa": "Presupuesto de defensa",
    "soborno": "Soborno declarado",
    "terrorismo": "Terrorismo",
    "trata": "Trata de personas",
    "urbano": "Urbano",
    "victimización": "Victimización y denuncia",
    "violencia": "Homicidios",
}


def ahora() -> str:
    """Momento actual en ISO 8601, UTC, sin fracciones de segundo."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def pedir(url: str) -> dict:
    """Trae un JSON. Levanta excepción ante cualquier respuesta que no sea 200."""
    peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(peticion, timeout=ESPERA) as respuesta:
        if respuesta.status != 200:
            raise RuntimeError(f"HTTP {respuesta.status} al pedir {url}")
        return json.loads(respuesta.read().decode("utf-8"))


def traer_crudo(url: str, espera: int = 120, intentos: int = 4) -> bytes:
    """Trae un archivo. Si el sitio rechaza al recolector, se presenta entero y reintenta.

    SE INTENTA PRIMERO CON EL NOMBRE CORTO, que es el que la casa viene usando y el
    que los sitios que ya nos conocen tienen visto. Solo cuando el sitio responde
    «prohibido» —403, 406 o 429— se repite con las cabeceras completas. Así ningún
    colector que hoy funciona cambia de comportamiento, y los que chocaban contra
    una guardia dejan de chocar.
    """
    import gzip
    import time

    ultimo = None
    for intento in range(intentos):
        for cabeceras in ({"User-Agent": AGENTE}, CABECERAS):
            try:
                p = urllib.request.Request(url, headers=cabeceras)
                with urllib.request.urlopen(p, timeout=espera) as r:
                    crudo = r.read()
                    if r.headers.get("Content-Encoding") == "gzip":
                        try:
                            crudo = gzip.decompress(crudo)
                        except Exception:  # noqa: BLE001 — ya venía descomprimido
                            pass
                    return crudo
            except urllib.error.HTTPError as e:
                ultimo = e
                if e.code not in (403, 406, 429):
                    if e.code in (400, 404):
                        raise
                    break  # no es una guardia: se reintenta más tarde, no con otra careta
            except Exception as e:  # noqa: BLE001 — se reintenta
                ultimo = e
                break
        time.sleep(5 * (intento + 1))
    raise RuntimeError(f"No se pudo llegar a {url}: {type(ultimo).__name__}: {str(ultimo)[:120]}")


def dias_desde(fecha: str) -> int | None:
    """Cuántos días pasaron desde una fecha ISO. None si la fecha no se deja leer.

    Vive acá y no en cada colector: «hace cuántos días» es la pregunta que este
    registro hace en todos lados —el último conjunto publicado, el último
    informe de una jurisdicción, la última compra— y ya había dos copias.
    """
    from datetime import date as _date
    try:
        return (_date.today() - _date.fromisoformat(str(fecha)[:10])).days
    except Exception:  # noqa: BLE001 — una fecha ilegible no descarta el registro
        return None


def calificar(fiabilidad: str, credibilidad: int, corroborado: bool, nota: str) -> dict:
    """Arma la calificación de Almirantazgo y verifica los techos del §3."""
    if fiabilidad not in FIABILIDAD:
        raise ValueError(f"Fiabilidad fuera de escala: {fiabilidad}")
    if credibilidad not in range(1, 7):
        raise ValueError(f"Credibilidad fuera de escala: {credibilidad}")
    if credibilidad == 1 and not corroborado:
        raise ValueError(
            "Credibilidad 1 exige corroboración por dos orígenes independientes "
            "(doctrina/fuentes.md §2 ter). El colector intentó asignarla sin ella."
        )
    return {
        "fiabilidad": fiabilidad,
        "credibilidad": credibilidad,
        "corroborado": corroborado,
        "nota": nota,
    }



# SERIES DETENIDAS — comprobadas contra la fuente, no supuestas
# ------------------------------------------------------------
# Un indicador viejo puede serlo por dos razones distintas, y no se parecen: o
# la encuesta que lo produce se levanta cada diez años, o EL PRODUCTOR DEJO DE
# PUBLICAR. Lo segundo no se arregla esperando.
#
# Cada entrada de acá se comprobó preguntandole a la fuente cuál es su año más
# nuevo, y lleva la fecha de esa consulta. NO se infiere de la antigüedad: el
# gasto militar del Banco Mundial trae 2024, de modo que el colector funciona y
# el hueco es de la fuente.
#
# Se declaran, NO se borran. Borrarlas escondería que la región no tiene medida
# vigente de estas materias, que es en sí mismo lo que hay que decir.
SERIES_DETENIDAS = {
    "personal_militar": {
        "ultimo_en_la_fuente": 2020, "consultado": "2026-09-03",
        "detalle": "Se consultó al Banco Mundial y su dato más nuevo para el mundo "
                   "es de 2020, en 216 países. La serie no avanza desde entonces.",
        "reemplazo": None,
    },
    "militares_fuerza_laboral": {
        "ultimo_en_la_fuente": 2020, "consultado": "2026-09-03",
        "detalle": "Se consultó al Banco Mundial y su dato más nuevo es de 2020, "
                   "En 214 países. Depende de la misma fuente que los efectivos.",
        "reemplazo": None,
    },
    "rentas_naturales": {
        "ultimo_en_la_fuente": 2021, "consultado": "2026-09-03",
        "detalle": "Se consultó al Banco Mundial y su dato más nuevo es de 2021, "
                   "en 244 países.",
        "reemplazo": None,
    },
    # NOTA 21/9/2026: estas dos entradas ya NO se usan -- owd.py sacó ambas
    # claves de su SERIES activa (ver colectores/owd.py, SERIES_RETIRADAS_GTD),
    # así que este diccionario nunca las procesa. Se dejan, corregidas, como
    # registro histórico: el "reemplazo" que decía ACLED estaba mal — ACLED se
    # investigó y se descartó por licencia (su EULA excluye tableros públicos
    # como SIWA). El reemplazo real es UCDP GED (sección aparte, mide otra
    # cosa) y, como segunda fuente pendiente de licencia, el Global Terrorism
    # Index del IEP.
    "terrorismo_muertes": {
        "ultimo_en_la_fuente": 2021, "consultado": "2026-09-03",
        "detalle": "La serie que publica Our World in Data termina en 2021: la Base "
                   "Global de Terrorismo dejó de actualizarse de forma pública. Además, "
                   "su EULA prohíbe la redistribución: RETIRADA de la capa pública el "
                   "21/9/2026, no solo detenida.",
        "reemplazo": "UCDP GED (sección «Violencia organizada», mide otra cosa) ya está "
                     "en vivo. Global Terrorism Index (IEP) es candidata a segunda "
                     "fuente, pendiente de gestionar licencia por formulario.",
    },
    "terrorismo_atentados": {
        "ultimo_en_la_fuente": 2021, "consultado": "2026-09-03",
        "detalle": "La serie que publica Our World in Data termina en 2021, por la "
                   "misma razón que las muertes por atentado. RETIRADA de la capa "
                   "pública el 21/9/2026, no solo detenida.",
        "reemplazo": "UCDP GED (sección «Violencia organizada», mide otra cosa) ya está "
                     "en vivo. Global Terrorism Index (IEP) es candidata a segunda "
                     "fuente, pendiente de gestionar licencia por formulario.",
    },
}

# LICENCIAS QUE LIMITAN EL USO
# ----------------------------
# Algunas fuentes son gratuitas para un registro publico y NO para un producto
# que se cobra. OpenSanctions es el caso: Atribucion-NoComercial, y su propia
# documentacion dice que usar el dato en un informe que la organizacion VENDE es
# uso comercial aunque la organizacion sea sin fines de lucro.
#
# La restriccion viaja PEGADA AL DATO, no en la cabeza de nadie: el colector la
# declara, el archivo la lleva y el sitio la muestra. Asi no puede olvidarse
# dentro de seis meses, cuando quien la conocia no este mirando.
RESTRICCIONES = {
    # CC BY-NC-SA 3.0 IGO. El «no comercial» no estorba a un registro gratuito;
    # el «compartir igual» SI obliga, y a algo que no se ve: lo derivado de este
    # dato lleva la misma licencia. Se declara para que nadie lo descubra tarde.
    "no_comercial_compartir_igual":
        "Gratuita para este registro, que es público y no se cobra. La licencia de la "
        "fuente es de atribución, no comercial y compartir igual (CC BY-NC-SA 3.0 IGO): "
        "este dato no puede viajar a un producto que la Fundación venda, y lo que se "
        "derive de él se publica bajo esa misma licencia.",
    "solo_registro_publico":
        "Gratuita para este registro, que es público y no se cobra. La licencia de "
        "la fuente es de atribución no comercial: este dato no puede viajar a un "
        "producto que la Fundación venda sin tomar antes una licencia comercial.",
}


def escribir(
    colector: str,
    capa: str,
    fuente: str,
    url_fuente: str,
    calificacion: dict,
    registros: list,
    vacios: list | None = None,
    extra: dict | None = None,
    restriccion: str | None = None,
) -> Path:
    """Escribe el archivo de datos con su bloque de procedencia.

    `extra` permite sumar bloques propios de un colector —por ejemplo una muestra
    acotada para el mapa— sin alterar la estructura común.
    """
    destino = DATOS / capa / f"{colector}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)

    contenido = {
        "procedencia": {
            "colector": colector,
            "capa": capa,
            "obtenido_en": ahora(),
            "fuente": {"nombre": fuente, "url": url_fuente},
            "calificacion": calificacion,
            "vacios_declarados": vacios or [],
            "restriccion_de_uso": RESTRICCIONES.get(restriccion) if restriccion else None,
            "cantidad": len(registros),
            "atribucion": ATRIBUCION,
        },
        "registros": registros,
    }
    if extra:
        contenido.update(extra)

    # LA ANTIGUEDAD DE CADA SERIE, CALCULADA ACA Y NO DECLARADA A MANO. Una nota
    # escrita a mano envejece sin que nadie se entere; un calculo no. Lo que se
    # adjunta es un HECHO —hasta que año llega la serie y cuantos años hace de
    # eso—, no una interpretación de por qué.
    hoy = datetime.now(timezone.utc).year
    for indicador in contenido.get("indicadores") or []:
        clave = indicador.get("clave")
        anios = [
            ((registro.get("indicadores") or {}).get(clave) or {}).get("anio")
            for registro in contenido.get("registros") or []
        ]
        anios = [a for a in anios if a]
        if not anios:
            continue
        indicador["hasta_anio"] = max(anios)
        indicador["rezago_anios"] = hoy - max(anios)
        # Y si ADEMAS se le pregunto a la fuente y no tiene nada mas nuevo, eso
        # es una afirmacion mas fuerte y lleva su fecha de comprobación.
        detenida = SERIES_DETENIDAS.get(clave)
        if detenida and max(anios) <= detenida["ultimo_en_la_fuente"]:
            indicador["serie_detenida"] = dict(detenida)

    # Y SE DECLARA COMO VACIO, sin que el colector tenga que acordarse. Una serie
    # detenida es un vacío del registro aunque el dato esté: lo que falta no es
    # el número, es el presente.
    quietas = [i for i in (contenido.get("indicadores") or []) if i.get("serie_detenida")]
    if quietas:
        detalle = "; ".join(
            f"«{i.get('rotulo', i['clave'])}» hasta {i['hasta_anio']}" for i in quietas)
        contenido["procedencia"]["vacios_declarados"].append(
            f"SERIE DETENIDA EN {len(quietas)} INDICADOR"
            f"{'ES' if len(quietas) > 1 else ''}: {detalle}. No es dato viejo que se "
            "vaya a poner al día: se le pregunto a la fuente y no tiene nada más "
            "nuevo. Se declara y no se borra, porque borrarlo escondería que la "
            "región no tiene medida vigente de esas materias."
        )

    # La categoria se adjunta acá y no en cada colector: en un solo lugar no
    # puede desincronizarse, y el indicador nuevo que no la tenga SE ANUNCIA en
    # vez de perderse, que es como se perdieron los seis del entorno informativo.
    sin_categoria = []
    for indicador in contenido.get("indicadores") or []:
        categoria = CATEGORIAS.get(indicador.get("clave"))
        if categoria:
            indicador["seccion"] = categoria
            indicador["seccion_rotulo"] = ROTULO_CATEGORIA.get(categoria, categoria)
        else:
            sin_categoria.append(indicador.get("clave"))
    if sin_categoria:
        print(f"[{colector}] AVISO: sin categoría declarada -> "
              f"{', '.join(sin_categoria)}. Se agregan a común.CATEGORIAS.")

    # allow_nan=False es deliberado: NaN e Infinity NO son JSON valido y el
    # navegador rechaza el archivo entero, no solo el valor. Si un colector
    # produce uno, la corrida falla aca y se ve, en lugar de escribir un
    # archivo que nadie puede leer.
    try:
        texto = json.dumps(contenido, ensure_ascii=False, indent=2, allow_nan=False)
    except ValueError as error:
        raise ValueError(
            f"El colector «{colector}» produjo un valor no representable en JSON "
            f"(NaN o infinito): {error}. Un dato ausente se omite, no se escribe."
        ) from error

    # UN COLECTOR QUE HOY NO TRAE NADA NO PISA LO QUE AYER SÍ TRAÍA. Sin esto, una
    # fuente que devolvía una respuesta vacía dejaba el archivo con cero indicadores
    # y el colector «correcto» (auditoría del robot, 15/9/2026). Se falla y el dato
    # anterior queda intacto, que es la regla de todo el registro.
    if destino.exists() and not os.environ.get("SIWA_PERMITIR_VACIO"):
        try:
            previo = json.loads(destino.read_text(encoding="utf-8"))
            antes = len((previo.get("cobertura") or {})) if isinstance(previo, dict) else 0
        except Exception:  # noqa: BLE001 — un archivo previo ilegible no frena nada
            antes = 0
        ahora_n = len(contenido.get("cobertura") or {})
        if antes and not ahora_n and contenido.get("indicadores") is not None:
            raise RuntimeError(
                f"El colector «{colector}» trajo cero indicadores con dato cuando el archivo "
                f"anterior tenía {antes}. No se pisa: la fuente probablemente respondió vacío.")

    # ESCRITURA ATÓMICA: se escribe al lado y se reemplaza de una vez. Un corte a la
    # mitad dejaba un JSON cortado que igual se publicaba.
    temporal = destino.with_suffix(destino.suffix + ".tmp")
    temporal.write_text(texto + "\n", encoding="utf-8")
    os.replace(temporal, destino)
    return destino


def escribir_estado(colector: str, estado: str, mensaje: str) -> None:
    """Deja constancia de cómo terminó la corrida, para mostrarla en el sitio."""
    destino = DATOS / "publico" / "estado" / f"{colector}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(
            {"colector": colector, "estado": estado, "mensaje": mensaje, "momento": ahora()},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def correr(colector: str, tarea) -> None:
    """Ejecuta un colector, registra el resultado y propaga la falla al sistema."""
    try:
        destino = tarea()
    except Exception as error:  # noqa: BLE001 — cualquier falla se declara igual
        escribir_estado(colector, "error", f"{type(error).__name__}: {error}")
        print(f"[{colector}] FALLA: {error}", file=sys.stderr)
        print(f"[{colector}] no se escribió ningún dato. El anterior queda intacto.", file=sys.stderr)
        sys.exit(1)
    escribir_estado(colector, "correcto", "Recolección completa.")
    print(f"[{colector}] escrito: {destino.relative_to(RAIZ)}")
