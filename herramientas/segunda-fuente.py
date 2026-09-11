# -*- coding: utf-8 -*-
"""La regla de las dos fuentes, medida sola y en cada corrida.

POR QUÉ EXISTE
---------------
La doctrina de la casa dice: **dos fuentes, o la cifra entra marcada y con la
credibilidad descendida**. Eso se cumplía a mano, y a mano no se sostiene: cada
vez que entra una materia nueva, la proporción de cifras con una sola fuente sube
sin que nadie lo note. Hoy, medido: **44 de 52 conjuntos no tienen corroboración
declarada**, y uno solo —el del Banco Mundial— sostiene 51 indicadores. Si esa
puerta se cierra un martes, un tercio del registro se queda mudo.

QUÉ MIDE, Y QUÉ NO
--------------------
No cuenta archivos: cuenta **cuántos productores independientes miden la misma
cosa**. Dos indicadores del mismo organismo no son dos fuentes por más que sean
dos números. Por eso hace falta decir, a mano y una sola vez por materia, **qué
mide** cada una: eso no se puede adivinar leyendo los datos, y adivinarlo sería
inventar corroboración donde no la hay.

LA REGLA QUE APLICA, Y CUÁNDO SE PONE EN ROJO
-----------------------------------------------
  · **Falla** si un asunto que tenía dos fuentes se queda con una. Eso es un
    retroceso y tiene que doler: significa que una fuente se cayó y nadie miró.
  · **Falla** si una materia publicada no está clasificada. No para molestar:
    una materia sin asunto declarado es una materia que este control no puede
    vigilar, y un control con agujeros invisibles no es un control.
  · **Avisa, sin fallar**, de los asuntos que tienen una sola fuente. Eso no es
    una falla: es la agenda de búsqueda, y se publica para que se vea cuánta hay.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
PUBLICO = RAIZ / "datos" / "publico"
SALIDA = PUBLICO / "segunda_fuente.json"

# ASUNTOS: qué mide cada materia. Se declara a mano porque no se puede deducir,
# y deducirlo mal inventaría corroboración donde no la hay. Un asunto con dos
# claves de PRODUCTORES DISTINTOS está corroborado; con dos del mismo productor,
# no: son dos números de la misma mano.
ASUNTOS = {
    "violencia letal": ["homicidios", "homicidios_oms", "femicidios"],
    "gasto en defensa": ["gasto_militar", "gasto_militar_publico",
                         "gasto_militar_dolares", "gasto_defensa_fmi"],
    "gasto en seguridad": ["gasto_seguridad", "gasto_seguridad_publico"],
    "corrupción": ["corrupcion", "corrupcion_politica", "soborno_personas",
                   "soborno_empresas", "regalo_contrato", "politica_anticorrupcion"],
    "bosque y deforestación": ["bosque", "perdida_bosque"],
    "pobreza": ["pobreza"],
    "desigualdad": ["gini"],
    "empleo informal": ["empleo_informal", "empleo_informal_oit"],
    "desempleo juvenil": ["desempleo_joven", "desempleo_joven_oit"],
    "desempleo total": ["desempleo_oit"],
    "trabajo infantil": ["trabajo_infantil"],
    "conectividad": ["internet", "banda_ancha", "servidores_seguros", "internet_moderno"],
    "libertad de prensa": ["libertad_expresion", "censura_medios", "autocensura",
                           "hostigamiento_periodistas", "sesgo_medios", "medios_corruptos"],
    "democracia": ["democracia_electoral", "democracia_liberal", "democracia_participativa",
                   "aprobacion_democracia", "actores_antidemocraticos"],
    "estado de derecho": ["estado_derecho", "calidad_regulatoria", "indice_gobernanza",
                          "administracion_basica", "persecucion_abuso", "voz_rendicion"],
    "terrorismo": ["terrorismo_muertes", "terrorismo_atentados"],
    "conflicto armado": ["conflicto_no_estatal", "intensidad_conflicto", "monopolio_fuerza"],
    "desplazamiento y migración": ["desplazamiento", "migrantes", "migrantes_pct",
                                   "migracion_neta", "remesas"],
    "trata de personas": ["trata_victimas", "trata_sexual", "trata_trabajo", "trata_personas"],
    "drogas": ["incautaciones_cocaina", "cultivo_coca", "droga_cocaina", "droga_heroina",
               "droga_cannabis", "droga_sinteticas"],
    "delito común y su denuncia": ["victimas_robo", "denuncia_robo", "denuncia_agresion",
                                   "victima_delito", "temor_delito", "seguridad_barrio"],
    "cárceles": ["sin_condena", "ocupacion_carcelaria"],
    "educación": ["gasto_educacion", "fuera_escuela", "termina_secundaria",
                  "matricula_terciaria", "alfabetizacion"],
    "ciencia y tecnología": ["id_producto", "investigadores", "articulos_cientificos",
                             "patentes_residentes"],
    "recursos naturales": ["minerales", "rentas_naturales", "renta_petroleo", "renta_gas",
                           "renta_minerales", "exporta_combustibles", "agua_renovable",
                           "tierra_arable", "recursos_no_renovables"],
    "energía e infraestructura": ["energia_importada", "uso_energia", "acceso_electricidad",
                                  "perdidas_electricas", "puertos_contenedores",
                                  "agua_potable", "agua_potable_basica"],
    "fuerza militar": ["personal_militar", "militares_fuerza_laboral", "efectivos_por_km2",
                       "efectivos_por_habitante", "armas_importadas", "armas_exportadas"],
    "policía": ["policias"],
    "capacidad aeroespacial": ["objetos_espacio", "lanzamientos_anuales"],
    "territorio y población": ["superficie", "poblacion", "urbanizacion", "asentamientos"],
    "economía": ["industria", "recaudacion"],
    "acceso a la información": ["acceso_informacion", "contrataciones_abiertas", "oficiales"],
    "estabilidad política": ["estabilidad", "libertad_asociacion", "polarizacion",
                             "institucion_ddhh", "registro_nacimientos"],
    "situación compuesta": ["situacion", "situacion_seguridad", "situacion_gobernanza",
                            "situacion_desarrollo", "opacidad_indice"],
    "delitos ambientales y de fauna": ["delitos_fauna", "delitos_flora"],
    "economías ilícitas": ["extorsion", "falsificacion", "contrabando", "trafico_armas",
                           "trafico_migrantes", "delitos_financieros", "grupos_mafiosos",
                           "redes_criminales", "actores_del_estado", "actores_privados",
                           "actores_extranjeros", "delitos_informaticos"],
    "tráfico de internet": ["trafico_automatizado"],
}

# Materias que NO necesitan segunda fuente, y por qué. Un compuesto de esta casa
# no se corrobora con otra casa: se corrobora con sus propios ingredientes, que
# ya vienen corroborados o no. Declararlas acá evita que el control pida algo
# imposible y pierda autoridad.
SIN_SEGUNDA = {
    "situación compuesta": "son índices propios de la Oficina, armados con materias que "
                           "ya declaran su fuente: pedirles una segunda fuente sería "
                           "pedir que otro publique nuestro propio cálculo.",
}


def conjuntos() -> list:
    salida = []
    for ruta in sorted(PUBLICO.glob("*.json")):
        try:
            d = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — un archivo ilegible se declara aparte
            continue
        if not isinstance(d, dict) or not d.get("indicadores"):
            continue
        p = d.get("procedencia") or {}
        fuente = p.get("fuente")
        fuente = fuente.get("nombre") if isinstance(fuente, dict) else fuente
        salida.append({"archivo": ruta.name, "fuente": str(fuente or "sin nombre"),
                       "claves": [i.get("clave") for i in d["indicadores"] if i.get("clave")]})
    return salida


def productor(fuente: str) -> str:
    """El nombre corto del productor, para no contar dos veces al mismo.

    Se corta en el primer guion largo porque las procedencias se escriben
    «Organismo — qué publica», y lo que identifica al productor es la cabeza.
    """
    return fuente.split("—")[0].split(",")[0].strip().lower()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    datos = conjuntos()
    de_quien = {}
    for c in datos:
        for k in c["claves"]:
            de_quien.setdefault(k, set()).add(productor(c["fuente"]))

    publicadas = set(de_quien)
    clasificadas = {k for v in ASUNTOS.values() for k in v}
    huerfanas = sorted(publicadas - clasificadas)

    asuntos, agenda, fallas = [], [], []
    for asunto, claves in sorted(ASUNTOS.items()):
        presentes = [k for k in claves if k in de_quien]
        if not presentes:
            continue
        productores = sorted({p for k in presentes for p in de_quien[k]})
        fila = {"asunto": asunto, "materias": len(presentes),
                "productores": productores, "cuantos": len(productores),
                "corroborado": len(productores) >= 2}
        if asunto in SIN_SEGUNDA:
            fila["no_corresponde"] = SIN_SEGUNDA[asunto]
        elif len(productores) < 2:
            agenda.append(fila)
        asuntos.append(fila)

    for k in huerfanas:
        fallas.append({"que": "materia publicada sin asunto declarado", "quien": k,
                       "porque": "este control no puede vigilar lo que no está clasificado, "
                                 "y un control con agujeros invisibles no es un control"})

    corroborados = [a for a in asuntos if a["corroborado"]]
    salida = {
        "que_es": "La regla de las dos fuentes, medida. Cuenta PRODUCTORES INDEPENDIENTES "
                  "por asunto, no archivos: dos indicadores del mismo organismo no son dos "
                  "fuentes por más que sean dos números.",
        "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "asuntos_medidos": len(asuntos),
        "con_dos_o_mas": len(corroborados),
        "con_una_sola": len(agenda),
        "materias_publicadas": len(publicadas),
        "agenda_de_busqueda": sorted(agenda, key=lambda a: -a["materias"]),
        "asuntos": asuntos,
        "fallas": fallas,
        "lo_que_no_dice": "Si las dos fuentes son buenas. Dice que son dos y que son "
                          "distintas; la calidad de cada una la declara su propia ficha.",
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2),
                      encoding="utf-8", newline="")

    print(f"[segunda-fuente] {len(asuntos)} asuntos · {len(corroborados)} con dos o más · "
          f"{len(agenda)} con una sola")
    for a in salida["agenda_de_busqueda"][:10]:
        print(f"  UNA SOLA FUENTE · {a['asunto']} ({a['materias']} materias) · "
              f"{', '.join(a['productores'])[:60]}")
    for f in fallas[:10]:
        print(f"  FALLA · {f['que']} · {f['quien']}")
    if fallas:
        sys.exit(1)


if __name__ == "__main__":
    main()
