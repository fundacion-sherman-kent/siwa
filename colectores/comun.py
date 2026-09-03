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
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
AGENTE = "SIWA/0.1 (Fundacion Sherman Kent; +https://fundacionkent.org)"
ESPERA = 30

FIABILIDAD = ("A", "B", "C", "D", "E", "F")

# La atribucion viaja DENTRO de cada archivo, no solo en la pantalla. Quien se
# lleve el dato crudo se lleva tambien de quien es el trabajo: es la unica forma
# de que el credito sobreviva a una descarga.
ATRIBUCION = {
    "obra": "SIWA — Reporte de situación de América Latina y el Caribe",
    "autor": "Fundación Sherman Kent — Oficina de Generación de Inteligencia",
    "sitio": "https://fundacion-sherman-kent.github.io/siwa/sitio/index.html",
    "uso": ("Acceso libre y gratuito. Se permite reproducir, redistribuir y "
            "derivar esta información CITANDO LA FUENTE de este modo: «SIWA, "
            "Fundación Sherman Kent». La recolección, la calificación de fuentes "
            "y la declaración de vacíos son trabajo de la Fundación; los datos "
            "de base pertenecen a los productores citados en cada indicador."),
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
CATEGORIAS = {
    "acceso_informacion": "capacidad",
    "actores_antidemocraticos": "integridad",
    "administracion_basica": "integridad",
    "agua_potable": "condiciones",
    "aprobacion_democracia": "integridad",
    "armas_exportadas": "material",
    "armas_importadas": "material",
    "asentamientos": "urbano",
    "autocensura": "entorno-informativo",
    "banda_ancha": "conectividad",
    "bosque": "ambiente",
    "calidad_regulatoria": "institucional",
    "censura_medios": "entorno-informativo",
    "conflicto_no_estatal": "grupos-armados",
    "corrupcion": "institucional",
    "corrupcion_politica": "democracia",
    "democracia_electoral": "democracia",
    "democracia_liberal": "democracia",
    "democracia_participativa": "democracia",
    "denuncia_agresion": "victimizacion",
    "denuncia_robo": "victimizacion",
    "desempleo_joven": "condiciones",
    "empleo_informal": "informalidad",
    "estabilidad": "institucional",
    "estado_derecho": "institucional",
    "gasto_militar": "presupuesto-defensa",
    "gasto_militar_dolares": "presupuesto-defensa",
    "gasto_militar_publico": "presupuesto-defensa",
    "gini": "condiciones",
    "homicidios": "violencia",
    "hostigamiento_periodistas": "entorno-informativo",
    "indice_gobernanza": "integridad",
    "industria": "industrial",
    "institucion_ddhh": "capacidad",
    "intensidad_conflicto": "control",
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
    "monopolio_fuerza": "control",
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
    "aeroespacial": "Capacidad aeroespacial",
    "ambiente": "Superficie forestal",
    "capacidad": "Capacidad del Estado",
    "ciber": "Ciberseguridad",
    "condiciones": "Condiciones de vida y desigualdad",
    "conectividad": "Conectividad",
    "contratación": "Contratación pública",
    "control": "Control territorial del Estado",
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
                   "en 214 países. Depende de la misma fuente que los efectivos.",
        "reemplazo": None,
    },
    "rentas_naturales": {
        "ultimo_en_la_fuente": 2021, "consultado": "2026-09-03",
        "detalle": "Se consultó al Banco Mundial y su dato más nuevo es de 2021, "
                   "en 244 países.",
        "reemplazo": None,
    },
    "terrorismo_muertes": {
        "ultimo_en_la_fuente": 2021, "consultado": "2026-09-03",
        "detalle": "La serie que publica Our World in Data termina en 2021: la Base "
                   "Global de Terrorismo dejó de actualizarse de forma pública.",
        "reemplazo": "ACLED cubre el mismo fenómeno con cadencia semanal y exige "
                     "credencial gratuita, todavía no gestionada.",
    },
    "terrorismo_atentados": {
        "ultimo_en_la_fuente": 2021, "consultado": "2026-09-03",
        "detalle": "La serie que publica Our World in Data termina en 2021, por la "
                   "misma razón que las muertes por atentado.",
        "reemplazo": "ACLED cubre el mismo fenómeno con cadencia semanal y exige "
                     "credencial gratuita, todavía no gestionada.",
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
    "solo_registro_publico":
        "GRATUITA PARA ESTE REGISTRO, QUE ES PUBLICO Y NO SE COBRA. La licencia de "
        "la fuente es de atribucion NO COMERCIAL: este dato NO PUEDE VIAJAR A UN "
        "PRODUCTO QUE LA FUNDACION VENDA sin tomar antes una licencia comercial.",
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
            "vaya a poner al día: SE LE PREGUNTO A LA FUENTE y no tiene nada más "
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

    destino.write_text(texto + "\n", encoding="utf-8")
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
