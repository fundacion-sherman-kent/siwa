"""Régimen político — la clasificación «Regímenes del Mundo» de V-Dem.

Cuatro categorías, no un puntaje. Es la pregunta previa a todas las demás del
eje de gobernanza: **qué clase de régimen es**, antes de medir cuánto publica o
cuánta corrupción se le atribuye.

* **Autocracia cerrada** — no hay elecciones multipartidistas para el ejecutivo
  o el legislativo.
* **Autocracia electoral** — hay elecciones multipartidistas, pero no reúnen las
  condiciones de libertad y limpieza que exige la democracia electoral.
* **Democracia electoral** — las elecciones son libres y limpias, y las
  libertades de expresión y de asociación se respetan.
* **Democracia liberal** — a lo anterior se suma el control efectivo del
  ejecutivo por la justicia y el legislativo, y la protección de las libertades
  individuales.

Por qué esta vía y no la del productor
--------------------------------------
V-Dem publica su base completa, pero **la descarga exige registro** y su libro
de códigos dice «todos los derechos reservados». **Our World in Data la
redistribuye con licencia abierta**, y es la misma vía por la que este registro
ya toma trece indicadores de V-Dem. Se sigue usando la puerta que está abierta,
y la responsabilidad por el dato queda donde corresponde: en el productor.
"""

from __future__ import annotations

import csv
import io
import urllib.error
import urllib.request

import comun
import geo

SLUG = "political-regime"
COLUMNA = "regime_row_owid"
FUENTE = ("V-Dem, Universidad de Gotemburgo — «Regímenes del Mundo», "
          "vía Our World in Data")
URL = f"https://ourworldindata.org/grapher/{SLUG}"
NAVEGADOR = comun.AGENTE

CATEGORIAS = {
    "0": {"clave": "autocracia_cerrada", "rotulo": "Autocracia cerrada", "orden": 0,
          "dice": "No hay elecciones multipartidistas para el ejecutivo o el "
                  "legislativo."},
    "1": {"clave": "autocracia_electoral", "rotulo": "Autocracia electoral", "orden": 1,
          "dice": "Hay elecciones multipartidistas, pero no reúnen las condiciones de "
                  "libertad y limpieza que exige la democracia electoral."},
    "2": {"clave": "democracia_electoral", "rotulo": "Democracia electoral", "orden": 2,
          "dice": "Las elecciones son libres y limpias, y se respetan las libertades "
                  "de expresión y de asociación."},
    "3": {"clave": "democracia_liberal", "rotulo": "Democracia liberal", "orden": 3,
          "dice": "A lo anterior se suman el control efectivo del ejecutivo por la "
                  "justicia y el legislativo, y la protección de las libertades "
                  "individuales."},
}

# V-Dem NO cubre a los Estados chicos del Caribe. Ocho del padrón quedan fuera, y
# eso es una brecha del proyecto, no una característica de esos Estados: no
# significa que no tengan régimen clasificable, significa que nadie los codificó.
CONTROL = "URY"          # clasificado desde hace décadas; si falta, falló la lectura
MINIMO_ESTADOS = 20      # se verificaron 25; muy por debajo, algo se rompió


def recolectar():
    url = (f"https://ourworldindata.org/grapher/{SLUG}.csv"
           f"?csvType=full&useColumnShortNames=true")
    try:
        peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
        with urllib.request.urlopen(peticion, timeout=180) as respuesta:
            texto = respuesta.read(30_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Our World in Data respondió HTTP {e.code}") from e

    filas = list(csv.DictReader(io.StringIO(texto)))
    if not filas or COLUMNA not in filas[0]:
        raise RuntimeError(
            f"La planilla no trae la columna «{COLUMNA}». Cambió de forma: NO se "
            "publica una clasificación leída de otra columna.")

    isos = {p["iso"] for p in geo.padron()}
    ultimo = {}
    for fila in filas:
        iso, anio, valor = fila.get("code"), fila.get("year"), fila.get(COLUMNA)
        if iso not in isos or not anio or valor in (None, ""):
            continue
        if iso not in ultimo or int(anio) > int(ultimo[iso]["anio"]):
            ultimo[iso] = {"anio": anio, "valor": valor.strip()}

    # PROBAR ANTES DE AFIRMAR: sin el control, lo que falló es la lectura.
    if CONTROL not in ultimo or len(ultimo) < MINIMO_ESTADOS:
        raise RuntimeError(
            f"Se leyeron {len(ultimo)} Estados y el control ({CONTROL}) "
            f"{'está' if CONTROL in ultimo else 'NO está'}. Con menos de "
            f"{MINIMO_ESTADOS} o sin el control, la lectura falló y no se publica: "
            "un mapa vacío diría que la región dejó de estar clasificada.")

    desconocidos = sorted({d["valor"] for d in ultimo.values()} - set(CATEGORIAS))
    if desconocidos:
        raise RuntimeError(
            f"La planilla trae valores fuera de la escala de cuatro categorías: "
            f"{desconocidos}. La escala cambió y no se publica una categoría inventada.")

    registros, anios = [], set()
    for pais in geo.padron():
        dato = ultimo.get(pais["iso"])
        registro = {"iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
                    "clasificado": bool(dato)}
        if dato:
            categoria = CATEGORIAS[dato["valor"]]
            registro.update({"categoria": categoria["clave"], "rotulo": categoria["rotulo"],
                             "orden": categoria["orden"], "dice": categoria["dice"],
                             "anio": int(dato["anio"])})
            anios.add(int(dato["anio"]))
        else:
            registro["por_que_no"] = ("V-Dem no codifica a este Estado: la brecha es del "
                                      "proyecto, no del Estado.")
        registros.append(registro)
    registros.sort(key=lambda r: (not r["clasificado"], r.get("orden", 9), r["pais"]))

    conteo = {}
    for r in registros:
        if r["clasificado"]:
            conteo[r["rotulo"]] = conteo.get(r["rotulo"], 0) + 1
    sin_clasificar = [r["pais"] for r in registros if not r["clasificado"]]

    vacios = [
        "**Es una clasificación, no un puntaje, y no ordena Estados dentro de una misma "
        "categoría.** Dos democracias electorales no están empatadas: están en la misma "
        "casilla. Para el matiz están los índices continuos que el registro ya publica.",
        "**Es evaluación de especialistas, no un recuento de hechos.** V-Dem construye la "
        "categoría a partir de índices que promedian el juicio de varios codificadores "
        "por país, con intervalo de incertidumbre. Un cambio de casilla es una decisión "
        "de método tanto como un cambio del mundo.",
        f"**V-Dem no codifica a {len(sin_clasificar)} Estados del padrón**"
        + (f": {', '.join(sin_clasificar)}. " if sin_clasificar else ". ")
        + "Son los Estados chicos del Caribe, que quedan fuera del proyecto. **La brecha "
          "es del proyecto, no de esos Estados**: no significa que no tengan régimen "
          "clasificable, significa que nadie los codificó.",
        "**La categoría es del año que declara cada ficha, no de hoy.** La serie es anual "
        "y se publica meses después del cierre: un cambio ocurrido este año todavía no "
        "está acá.",
        "Se consulta por medio de Our World in Data porque **la base del productor exige "
        "registro** y su libro de códigos reserva los derechos. Our World in Data "
        "redistribuye con licencia abierta. La responsabilidad por el dato es de V-Dem.",
    ]

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=2,
        corroborado=False,
        nota=("Proyecto académico con método publicado y revisión por pares, consultado "
              "por medio de Our World in Data, que redistribuye con licencia abierta. "
              "Lo que se registra es la categoría que el proyecto asignó, no que la "
              "categoría sea la correcta: es evaluación experta, no hecho observado."),
    )

    return comun.escribir(
        colector="regimen_politico",
        capa="publico",
        fuente=FUENTE,
        url_fuente=URL,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados_clasificados": len(ultimo),
                "estados_del_padron": len(registros),
                "anio": max(anios) if anios else None,
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
    comun.correr("regimen_politico", recolectar)
