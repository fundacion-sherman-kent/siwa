"""Conflictos territoriales y minería ilegal.

Fuente
------
**Instituto de Estudios Interculturales de la Pontificia Universidad Javeriana
Cali.** Publica un visor de conflictos de América Latina cuyas capas se sirven
abiertas, sin credencial: 443 conflictos territoriales georreferenciados —con
país, departamento, municipio, año de inicio, tipo de conflicto, actores y
resumen del caso— y polígonos de minería ilegal en cuatro Estados.

Por qué acá NO se republica el dato crudo
-----------------------------------------
**Las capas no declaran licencia.** Están abiertas al público y no llevan texto
de derechos ni condiciones de uso. Que un dato sea accesible no significa que sea
redistribuible, y esta Fundación **vende informes**: la misma cautela que se
aplicó en su momento a otras fuentes de uso no comercial se aplica acá.

En consecuencia este colector **publica recuentos y agregados** —cuántos
conflictos por Estado, de qué tipo, entre qué actores, desde qué año— y **no
vuelca los registros individuales ni las geometrías**. Es trabajo derivado, no
redifusión. Cada pantalla remite al visor original, y **la atribución va al
Instituto**, que es quien levantó el dato.

> **Pendiente y declarado:** solicitar autorización escrita al Instituto antes de
> usar estos datos en productos pagos de la Fundación, y para poder mostrar el
> detalle por caso. Es una institución par y el pedido corresponde hacerlo.

Qué mide y qué no
-----------------
**No es un censo de conflictos.** Es el corpus que un equipo académico levantó y
verificó caso por caso, con el alcance y el recorte de ese proyecto. Un Estado
con pocos casos puede tener pocos conflictos **o poca cobertura del proyecto**, y
las dos cosas no se distinguen desde afuera. La fecha de inicio es la del
conflicto, no la de su registro: **muchos siguen abiertos**.
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import comun
import geo

BASE = "https://services9.arcgis.com/pZylgd2zhNey2qXF/arcgis/rest/services"
VISOR = "https://experience.arcgis.com/experience/069a53907015424e88d95b04ae2430fb"
NAVEGADOR = comun.AGENTE
ANIO_RELLENO = 1905   # valor de relleno del origen, ver el vacio declarado

CONFLICTOS = [
    ("territorial", f"{BASE}/ConflictosLA/FeatureServer/0"),
    ("sociopolitico", f"{BASE}/ConflictosLA/FeatureServer/1"),
]
MINERIA = [
    ("VEN", f"{BASE}/Mineria_ilegal_Venezuela/FeatureServer/34"),
    ("PER", f"{BASE}/Mineria_ilegal_Peru/FeatureServer/26"),
    ("BRA", f"{BASE}/Mineria_ilegal_2018_Brasil/FeatureServer/29"),
    ("BOL", f"{BASE}/Mineria_ilegal_2017_Bolivia/FeatureServer/19"),
]


def _sin_marcas(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto or "")
                   if unicodedata.category(c) != "Mn").lower().strip()


def _pedir(url: str, timeout: int = 120):
    pet = urllib.request.Request(urllib.parse.quote(url, safe=":/?&=%,"),
                                 headers={"User-Agent": NAVEGADOR})
    with urllib.request.urlopen(pet, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _traer_conflictos(tarea: tuple) -> tuple:
    """Trae los atributos SIN geometria: no se republica la capa, se la resume."""
    tipo, url = tarea
    try:
        d = _pedir(f"{url}/query?where=1%3D1&outFields=*&returnGeometry=false"
                   f"&resultRecordCount=2000&f=json")
    except urllib.error.HTTPError as e:
        return tipo, [], f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001 — la falla se declara, no se oculta
        return tipo, [], type(e).__name__
    return tipo, [f.get("attributes", {}) for f in (d.get("features") or [])], None


def _contar_mineria(tarea: tuple) -> tuple:
    """Solo el recuento y el reparto por método: ninguna geometria sale de acá."""
    iso, url = tarea
    try:
        cnt = _pedir(f"{url}/query?where=1%3D1&returnCountOnly=true&f=json")
        muestra = _pedir(f"{url}/query?where=1%3D1&outFields=metodoexpl,substancia,"
                         f"situación&returnGeometry=false&resultRecordCount=2000&f=json")
    except urllib.error.HTTPError as e:
        return iso, None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return iso, None, type(e).__name__
    filas = [f.get("attributes", {}) for f in (muestra.get("features") or [])]
    def reparto(campo):
        c = Counter((f.get(campo) or "").strip() for f in filas if (f.get(campo) or "").strip())
        return [{"valor": k, "poligonos": n} for k, n in c.most_common(8)]
    return iso, {
        "poligonos": cnt.get("count", 0),
        "metodos": reparto("metodoexpl"),
        "sustancias": reparto("substancia"),
        "situacion": reparto("situación"),
    }, None


def recolectar():
    padron = geo.padron()
    por_nombre = {_sin_marcas(p["pais"]): p["iso"] for p in padron}
    # El proyecto nombra los Estados en español y a veces con variantes.
    por_nombre.update({"brasil": "BRA", "brazil": "BRA", "peru": "PER",
                       "mexico": "MEX", "republica dominicana": "DOM",
                       "el salvador": "SLV", "costa rica": "CRI",
                       "guatemala": "GTM", "honduras": "HND", "panama": "PAN"})
    nombres = {p["iso"]: p["pais"] for p in padron}
    bloques = {p["iso"]: p["bloque"] for p in padron}

    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        crudo = list(ejecutor.map(_traer_conflictos, CONFLICTOS))
        mineria = list(ejecutor.map(_contar_mineria, MINERIA))

    caidos = [f"conflictos {t}: {f}" for t, _, f in crudo if f]
    caidos += [f"mineria {i}: {f}" for i, _, f in mineria if f]

    por_iso, sin_atribuir, ejemplos = {}, [], {}
    for tipo, filas, falla in crudo:
        if falla:
            continue
        for a in filas:
            pais = _sin_marcas(a.get("Nivel_1__País_") or "")
            iso = por_nombre.get(pais)
            if not iso:
                if pais:
                    sin_atribuir.append(pais)
                continue
            reg = por_iso.setdefault(iso, {
                "total": 0, "por_tipo": Counter(), "categorias": Counter(),
                "actores": Counter(), "desde": [], "subnacional": set(),
            })
            reg["total"] += 1
            reg["por_tipo"][tipo] += 1
            cat = (a.get("Categoría_de_conflicto") or "").strip()
            if cat:
                reg["categorias"][cat] += 1
            act = (a.get("Tipo_de_conflicto_por_actor") or "").strip()
            if act:
                reg["actores"][act] += 1
            anio = re.search(r"(19|20)\d{2}", str(a.get("Fecha_de_inicio__año_") or ""))
            # 1905 aparece 70 veces en un corpus de 443, y ningun otro anio anterior
            # a 1950 salvo uno: es un valor de relleno del origen, no una fecha.
            # Publicarlo como «el conflicto mas antiguo» seria inventar un hecho.
            if anio and int(anio.group(0)) != ANIO_RELLENO:
                reg["desde"].append(int(anio.group(0)))
            for nivel in ("Nivel_2___Departamento_Estado__", "Nivel_3__Municipios_Provincias_"):
                for parte in re.split(r"[\n,;]+", str(a.get(nivel) or "")):
                    if parte.strip():
                        reg["subnacional"].add(parte.strip())
            if iso not in ejemplos and (a.get("Nombre") or "").strip():
                ejemplos[iso] = {
                    "nombre": a["Nombre"].strip()[:120],
                    "anio": anio.group(0) if anio else None,
                    "actores": act or None,
                }

    min_por_iso = {i: d for i, d, f in mineria if d and not f}

    registros = []
    for p in padron:
        iso = p["iso"]
        r = por_iso.get(iso)
        m = min_por_iso.get(iso)
        if not r and not m:
            continue
        fila = {"iso": iso, "pais": nombres[iso], "bloque": bloques[iso]}
        if r:
            fila["conflictos"] = {
                "total": r["total"],
                "territoriales": r["por_tipo"].get("territorial", 0),
                "sociopoliticos": r["por_tipo"].get("sociopolitico", 0),
                "mas_antiguo": min(r["desde"]) if r["desde"] else None,
                "mas_reciente": max(r["desde"]) if r["desde"] else None,
                "unidades_subnacionales": len(r["subnacional"]),
                "categorias": [{"categoria": k, "casos": n}
                               for k, n in r["categorias"].most_common(6)],
                "entre_actores": [{"actores": k, "casos": n}
                                  for k, n in r["actores"].most_common(6)],
                "ejemplo": ejemplos.get(iso),
            }
        if m:
            fila["mineria_ilegal"] = m
        registros.append(fila)
    registros.sort(key=lambda x: -(x.get("conflictos", {}).get("total", 0)))

    total_conf = sum(x.get("conflictos", {}).get("total", 0) for x in registros)
    total_min = sum(x.get("mineria_ilegal", {}).get("poligonos", 0) for x in registros)
    sin_conflicto = sorted(nombres[p["iso"]] for p in padron
                           if p["iso"] not in por_iso)

    vacios = [
        "LICENCIA NO DECLARADA. Las capas están abiertas al publico y no llevan texto "
        "de derechos ni condiciones de uso. Que un dato sea accesible no significa que "
        "sea redistribuible. Este registro es de ACCESO LIBRE Y GRATUITO y la Fundación "
        "no comercializa datos, de modo que el uso aquí es el que la licencia no "
        "comercial admite. Aun así se publican RECUENTOS Y AGREGADOS y no los registros "
        "individuales ni las geometrias, y PENDIENTE queda pedir autorización escrita al "
        "Instituto: no por licencia sino por cortesia entre instituciones, y porque con "
        "permiso podría publicarse el detalle caso por caso. Un dato de licencia no "
        "comercial NO puede entrar a un informe pago de la Fundación aunque sea gratuito "
        "en este registro: la licencia mira el uso, no el sitio.",
        "NO ES UN CENSO DE CONFLICTOS. Es el corpus que un equipo academico levanto y "
        "verifico caso por caso, con el alcance y el recorte de ese proyecto. Un Estado "
        "con pocos casos puede tener pocos conflictos O poca cobertura del proyecto, y "
        "las dos cosas NO se distinguen desde afuera.",
        "Sin ningún conflicto registrado por el proyecto: "
        + (", ".join(sin_conflicto) if sin_conflicto else "ninguno")
        + ". Ausencia en el corpus no es ausencia de conflicto.",
        "La minería ilegal esta mapeada en solo cuatro Estados y con años distintos "
        "—Bolivia y Venezuela 2017, Brasil 2018, Peru sin año declarado—: NO son "
        "comparables entre si ni con la situación actual. Y el número de poligonos no "
        "es una medida de magnitud: depende de como se dibujo cada capa. Venezuela "
        "figura con 1.317 poligonos y Peru con 3, y eso NO significa que en Peru casi "
        "no haya minería ilegal.",
        "La fecha registrada es la de INICIO del conflicto, no la de su registro. "
        "Muchos casos siguen abiertos y el corpus no declara cuales se cerraron.",
        f"EL AÑO {ANIO_RELLENO} SE DESCARTA: aparece 70 veces en un corpus de 443 y no "
        "hay ningún otro año anterior a 1950 salvo uno. Es un valor de relleno del "
        "origen, no una fecha. Publicarlo como «el conflicto mas antiguo» de seis "
        "Estados habria sido inventar un hecho. Esos 70 casos entran al recuento pero "
        "no al rango de años. Otros 21 registros no traen año legible.",
    ]
    if sin_atribuir:
        vacios.append("Nombres de país que no se pudieron atribuir al padron: "
                      + ", ".join(sorted(set(sin_atribuir))[:12]))
    if caidos:
        vacios.append("Capas que fallaron en esta corrida: " + "; ".join(caidos))

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=3,
        corroborado=False,
        nota=("Corpus academico verificado caso por caso por el Instituto de Estudios "
              "Interculturales de la Pontificia Universidad Javeriana Cali. Credibilidad "
              "3 y no mayor porque el alcance del proyecto no es exhaustivo y no puede "
              "corroborarse contra un censo independiente: no existe."),
    )

    return comun.escribir(
        colector="conflictos",
        capa="publico",
        fuente=("Instituto de Estudios Interculturales, Pontificia Universidad "
                "Javeriana Cali — visor de conflictos de America Latina"),
        url_fuente=VISOR,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados_con_conflictos": len(por_iso),
                "estados_del_padron": len(padron),
                "conflictos_registrados": total_conf,
                "poligonos_mineria_ilegal": total_min,
                "estados_con_mineria_mapeada": len(min_por_iso),
            },
            "atribución": ("Instituto de Estudios Interculturales, Pontificia "
                           "Universidad Javeriana Cali. Visor original: " + VISOR),
            "método": ("Se consultan las capas publicas SIN pedir geometria y se "
                       "publican únicamente recuentos y repartos por Estado, tipo, "
                       "categoría y actores. Los registros individuales no se "
                       "republican."),
        },
    )


if __name__ == "__main__":
    comun.correr("conflictos", recolectar)
