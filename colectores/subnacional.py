# -*- coding: utf-8 -*-
"""El censo de fuentes por unidad de primer orden. Santa Fe es el caso de prueba.

QUÉ CONTESTA, Y POR QUÉ ES UN PRODUCTO EN SÍ MISMO
---------------------------------------------------
Nadie en la región tiene el mapa de **qué provincia mide su propio territorio,
con qué método y con qué calidad**. Este colector lo arma. No publica cifras de
criminalidad: publica **quién publica**, en qué formato, desde cuándo y con qué
frescura. Esa es la materia prima del contraste vertical y, además, una
medición de transparencia que hoy no existe.

LA REGLA QUE LO GOBIERNA, Y NO ES NEGOCIABLE
---------------------------------------------
`NO SE PUBLICA NINGUNA CIFRA QUE NO SE HAYA PODIDO LEER DE LA FUENTE.` Si el
dato de la jurisdicción está adentro de una infografía —una imagen—, se declara
que existe, se enlaza y **no se transcribe a ojo**. Copiar un número leyéndolo
de un dibujo es exactamente lo que este registro no hace.

Es la misma regla de `brecha.py`: la distancia entre lo que se publica y lo que
se puede leer es un hecho **sobre la publicación**, no sobre el fenómeno.

EL GRADO DE APERTURA ES UN ACTO, NO UNA OPINIÓN
------------------------------------------------
Del 5 al 0, y cada escalón se comprueba repitiendo la consulta:

    5  serie descargable y legible por una máquina
    4  tabla en una página, sin archivo
    3  informe en PDF con las cifras adentro
    2  infografía: la cifra existe, la lee una persona y no un robot
    1  solo comunicados o notas de prensa
    0  no publica nada de sí misma

**Grado 2 no es un reproche.** Santa Fe publica homicidios dolosos todos los
meses —provincia y dos departamentos—, con triangulación de fuentes policiales,
judiciales y de salud, y con semanas de atraso; la serie internacional
comparable para la Argentina es de 2023. Publica más rápido que nadie y en un
formato que ninguna máquina lee. Las dos cosas son ciertas y las dos se dicen.

POR QUÉ EL CATÁLOGO SÍ SE LEE AUNQUE EL DATO NO
------------------------------------------------
El observatorio corre sobre WordPress y expone su interfaz: se puede saber, sin
mirar una sola imagen, **qué se midió, de qué unidad, de qué mes, cuándo se
publicó y dónde está**. Son 351 informes desde 2020. El catálogo abierto y el
dato cerrado conviven, y el registro los declara por separado.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

COLECTOR = "subnacional"
CAPA = "publico"

# LAS JURISDICCIONES, UNA POR ENTRADA. Agregar una es agregar un diccionario:
# el recorrido, la lectura y la calificación no cambian.
#
# `codigo` es ISO 3166-2, que es el estándar que ya usan los institutos y evita
# inventar un padrón paralelo. `nombre_local` es como la llama su propio Estado
# y NO se traduce.
JURISDICCIONES = [
    {
        "codigo": "AR-S",
        "iso_pais": "ARG",
        "unidad": "Santa Fe",
        "nombre_local": "provincia",
        "orden": 1,
        "fuente": {
            "nombre": "Observatorio de Seguridad Pública de Santa Fe",
            "tipo": "oficial_propia",
            "url": "https://www.santafe.gob.ar/ms/osp/",
            "quien": "Ministerio Público de la Acusación y Ministerio de Justicia y "
                     "Seguridad de la Provincia de Santa Fe",
        },
        # La interfaz del gestor de contenidos: el catálogo se lee aunque el dato
        # viva adentro de una imagen.
        "api": "https://www.santafe.gob.ar/ms/osp/wp-json/wp/v2/informs",
        "grado_apertura": 2,
        "porque_ese_grado": "Publica infografías mensuales: la cifra existe y la lee una "
                            "persona, no un robot. El CATÁLOGO de informes sí es legible "
                            "por máquina, y por eso se puede decir qué mide y de cuándo.",
    },
]

# Los ámbitos que el observatorio distingue dentro de la jurisdicción. Se leen
# del título del informe porque es donde la fuente los declara.
AMBITO = re.compile(
    r"(Provincia de [A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ ]+?|Departamento [A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ ]+?)"
    r"\s*(?:\(|,|$)")
# La ciudad que a veces acompaña al departamento en el título. El ámbito es el
# departamento: la ciudad es detalle y va aparte.
CIUDAD_PEGADA = re.compile(r"\s+y\s+(?:la\s+)?ciudad(?:es)?\s+de\s+.*$", re.I)


def _clave_ambito(nombre: str) -> str:
    """La misma unidad, escrita de una sola manera.

    MEDIDO EN EL PROPIO CATALOGO DE SANTA FE: el Departamento General López
    aparece con cuatro grafías distintas —con tilde y sin tilde, «Ciudad» y
    «ciudad»— y Castellanos con tres. Contarlas como unidades separadas habría
    dicho que la provincia publica de trece ámbitos cuando publica de siete.
    Es exactamente por esto que una capa subnacional necesita un código
    homologado y no el nombre que cada quien escribe.
    """
    t = unicodedata.normalize("NFKD", CIUDAD_PEGADA.sub("", nombre or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()
# La materia, también del título: homicidios, femicidios, armas, cárceles.
MATERIAS = [
    ("homicidios", re.compile(r"homicid", re.I)),
    ("muertes_violentas_mujeres", re.compile(r"muertes violentas de mujeres|femicid", re.I)),
    ("armas_de_fuego", re.compile(r"armas de fuego", re.I)),
    ("personas_privadas_libertad", re.compile(r"privadas de libertad", re.I)),
    ("criminalidad_registrada", re.compile(r"criminalidad registrada", re.I)),
    ("censo_policial", re.compile(r"censo policial", re.I)),
    ("violencias_lesivas", re.compile(r"violencias altamente lesivas", re.I)),
]


def limpiar(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = (t.replace("&#8211;", "–").replace("&#8217;", "’").replace("&amp;", "&")
         .replace("&nbsp;", " ").replace("&#8220;", "«").replace("&#8221;", "»"))
    return re.sub(r"\s+", " ", t).strip()


def pedir(url: str):
    peticion = urllib.request.Request(
        url, headers={"User-Agent": comun.AGENTE, "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=comun.ESPERA * 2) as respuesta:
        return json.loads(respuesta.read().decode("utf-8", "replace")), dict(respuesta.headers)


def informes_de(j: dict) -> tuple:
    """Todo el catálogo de la jurisdicción, paginado. Devuelve (informes, total)."""
    informes, pagina, total = [], 1, None
    while pagina <= 12:                                  # tope de cortesía: 1.200 informes
        d, cab = pedir(f"{j['api']}?per_page=100&page={pagina}&orderby=date&order=desc")
        if total is None:
            total = int(cab.get("X-WP-Total") or 0)
        if not d:
            break
        for x in d:
            titulo = limpiar((x.get("title") or {}).get("rendered", ""))
            m = AMBITO.search(titulo)
            materia = next((c for c, pat in MATERIAS if pat.search(titulo)), None)
            informes.append({
                "titulo": titulo,
                "ambito": m.group(1).strip() if m else None,
                "materia": materia,
                "publicado": (x.get("date") or "")[:10],
                "enlace": x.get("link"),
            })
        if len(d) < 100:
            break
        pagina += 1
    return informes, (total or len(informes))


def construir() -> Path:
    registros, vacios = [], []
    for j in JURISDICCIONES:
        informes, total = informes_de(j)
        if not informes:
            raise RuntimeError(f"{j['codigo']}: la fuente no devolvió ningún informe")

        # Qué mide, con qué frescura y sobre qué ámbitos. Todo sale del catálogo:
        # ni una cifra se lee de una imagen.
        por_materia, por_ambito = {}, {}
        for i in informes:
            if i["materia"]:
                d = por_materia.setdefault(i["materia"], {"informes": 0, "ultimo": None})
                d["informes"] += 1
                if not d["ultimo"] or i["publicado"] > d["ultimo"]:
                    d["ultimo"] = i["publicado"]
            if i["ambito"]:
                k = _clave_ambito(i["ambito"])
                a = por_ambito.setdefault(k, {"nombre": CIUDAD_PEGADA.sub("", i["ambito"]).strip(),
                                              "informes": 0, "ultimo": None, "grafias": set()})
                a["informes"] += 1
                a["grafias"].add(i["ambito"])
                if not a["ultimo"] or i["publicado"] > a["ultimo"]:
                    a["ultimo"] = i["publicado"]

        fechas = sorted(i["publicado"] for i in informes if i["publicado"])
        ultimo = informes[0] if informes else None
        sin_materia = sum(1 for i in informes if not i["materia"])
        if sin_materia:
            vacios.append(
                f"{j['unidad']}: {sin_materia} de {len(informes)} informes no declaran su "
                "materia en el título y quedan sin clasificar. Se cuentan igual: esconderlos "
                "haría parecer que la jurisdicción publica menos de lo que publica.")

        registros.append({
            "codigo": j["codigo"],
            "iso_pais": j["iso_pais"],
            "unidad": j["unidad"],
            "nombre_local": j["nombre_local"],
            "orden": j["orden"],
            "fuente_propia": j["fuente"],
            "grado_apertura": j["grado_apertura"],
            "porque_ese_grado": j["porque_ese_grado"],
            "informes": total,
            "informes_leidos": len(informes),
            "desde": fechas[0] if fechas else None,
            "hasta": fechas[-1] if fechas else None,
            "dias_desde_el_ultimo": comun.dias_desde(fechas[-1]) if fechas else None,
            "materias": [{"clave": c, **v} for c, v in sorted(por_materia.items())],
            "ambitos": [{"nombre": v["nombre"], "informes": v["informes"],
                          "ultimo": v["ultimo"],
                          # Las grafías se declaran cuando hay más de una: es un
                          # hecho sobre cómo publica la jurisdicción.
                          "grafias_en_la_fuente": (sorted(v["grafias"])
                                                   if len(v["grafias"]) > 1 else None)}
                         for _, v in sorted(por_ambito.items(),
                                            key=lambda x: -x[1]["informes"])],
            "ultimo_informe": ultimo,
            # NINGUNA CIFRA. Lo que la jurisdicción mide está adentro de una
            # infografía y no se transcribe a ojo.
            "cifras_leibles": False,
        })

    vacios.append(
        "Este colector NO publica cifras de criminalidad de las jurisdicciones. Publica "
        "quién publica, con qué método y con qué frescura. Donde el dato vive adentro de "
        "una imagen se declara que existe y se enlaza: transcribir un número leyéndolo de "
        "un dibujo es lo que este registro no hace.")
    vacios.append(
        "Una sola jurisdicción censada. El censo se amplía agregando una entrada por "
        "provincia o estado: mientras tanto, la ausencia de las demás no significa que no "
        "publiquen, significa que todavía no se las miró.")

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Censo propio de fuentes subnacionales — Fundación Sherman Kent, sobre los "
               "catálogos que publica cada jurisdicción",
        url_fuente=JURISDICCIONES[0]["fuente"]["url"],
        calificacion=comun.calificar(
            "A", 2, False,
            "Cada renglón se comprueba repitiendo la consulta al catálogo de la propia "
            "jurisdicción. No hay segunda fuente porque no la puede haber: quién publica "
            "qué lo declara el que publica."),
        registros=registros,
        vacios=vacios,
        extra={"escala_de_apertura": {
            "5": "serie descargable y legible por una máquina",
            "4": "tabla en una página, sin archivo",
            "3": "informe en PDF con las cifras adentro",
            "2": "infografía: la cifra existe, la lee una persona y no un robot",
            "1": "solo comunicados o notas de prensa",
            "0": "no publica nada de sí misma",
        }},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
