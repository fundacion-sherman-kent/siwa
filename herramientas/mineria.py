# -*- coding: utf-8 -*-
"""El minero: busca en lo que el registro ya tiene lo que nadie fue a mirar.

POR QUÉ EXISTE
--------------
El registro publica más de cien temas sobre 33 Estados. Un lector puede cruzar
dos por vez, y esa es la única forma en que hoy aparece una relación: **porque a
alguien se le ocurrió buscarla**. Eso deja afuera todo lo que nadie sospechó.

Este minero cruza **todos los pares posibles** —más de cinco mil— y mide cuáles
se acompañan. No para concluir nada: para dejar **pistas** sobre la mesa del
analista, que es lo que la minería de datos hace bien y lo único que hace.

LA TRAMPA DE LAS COMPARACIONES MÚLTIPLES, Y CÓMO SE LA DESARMA
---------------------------------------------------------------
Acá está el peligro real de esta herramienta, y por eso se escribe antes que el
código. Con cinco mil pares y el umbral de siempre —«p menor que 0,05»—,
**doscientos cincuenta pares darían «significativo» por puro azar** aunque los
datos fueran ruido. Publicar esa lista sería fabricar hallazgos a escala
industrial, con la apariencia de rigor que da una cifra.

Se corrige con el procedimiento de Benjamini y Hochberg, que controla la
proporción esperada de falsos hallazgos entre los que se declaran. Y se declara
el número de pares probados **al lado de cada resultado**, porque sin ese número
un coeficiente no se puede interpretar.

Además se marcan dos parentescos que producen hallazgos triviales:

  · **Misma fuente**: dos indicadores del mismo archivo suelen venir del mismo
    cuestionario. Que se acompañen no dice nada del mundo.
  · **Misma categoría**: «democracia electoral» y «democracia liberal» miden
    casi lo mismo. Descubrir que se parecen no es descubrir.

QUÉ MÁS BUSCA
-------------
**Anomalías contra la propia historia de cada Estado.** No «este Estado está
alto» —eso lo dice el ranking—, sino **este Estado se salió de su propia
serie**: el último valor está a más de tres desvíos de lo que venía haciendo.
Es la pista que hace levantar el teléfono.

LO QUE ESTE ARCHIVO NO HACE, Y NO ES UNA FORMALIDAD
----------------------------------------------------
No emite juicios. No dice que una cosa cause la otra. No ordena Estados por
nada. Las relaciones que encuentra son **candidatas a ser miradas por una
persona**, y así se publican: con su coeficiente, su cantidad de casos, cuántos
pares se probaron para encontrarla y si las dos puntas vienen de la misma
fuente.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PUBLICO = RAIZ / "datos" / "publico"
SALIDA = PUBLICO / "mineria.json"

sys.path.insert(0, str(RAIZ / "colectores"))
import comun  # noqa: E402

MINIMO_CASOS = 15        # con menos Estados en común, un coeficiente no dice nada
FDR = 0.05               # proporción de falsos hallazgos que se acepta declarar
DESVIOS_ANOMALIA = 3.0   # cuánto se tiene que salir un Estado de su propia serie
MINIMO_SERIE = 5         # puntos mínimos para que «su propia serie» signifique algo
MAXIMA_REPETICION = 0.60  # si un valor domina más que esto, la medida no describe la región
CAMBIO_MINIMO = 0.10      # una anomalía tiene que moverse al menos un décimo, no solo desviarse
CASI_LA_MISMA = 0.999     # por encima de esto, son dos nombres de la misma medida


# ------------------------------------------------------------------ lectura
def series_del_registro() -> dict:
    """Cada medida del registro como {clave: {'valores': {iso: v}, 'de': archivo}}.

    Se lee de los archivos publicados y no de una lista escrita a mano: una
    lista se desactualiza y el minero terminaría buscando en un registro que ya
    no existe.
    """
    medidas = {}
    for ruta in sorted(PUBLICO.glob("*.json")):
        if ruta.name in comun.TESTIGOS or ruta.name in ("mineria.json",):
            continue
        try:
            d = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — un archivo ilegible no frena la mina
            continue
        if not isinstance(d, dict):
            continue
        filas = d.get("registros")
        if not isinstance(filas, list) or not filas:
            continue
        meta = {i.get("clave"): i for i in (d.get("indicadores") or []) if isinstance(i, dict)}
        for fila in filas:
            if not isinstance(fila, dict) or not fila.get("iso"):
                continue
            iso = fila["iso"]
            # a) el diccionario de indicadores, que es donde vive la mayoría
            ind = fila.get("indicadores")
            if isinstance(ind, dict):
                for clave, cont in ind.items():
                    if isinstance(cont, dict) and isinstance(cont.get("valor"), (int, float)):
                        m = medidas.setdefault(clave, {
                            "valores": {}, "de": ruta.stem,
                            "rotulo": (meta.get(clave) or {}).get("rotulo", clave),
                            "categoria": (meta.get(clave) or {}).get("categoria"),
                        })
                        m["valores"][iso] = float(cont["valor"])
            # b) los campos numéricos sueltos del propio colector
            for campo, valor in fila.items():
                if campo in ("iso", "orden", "puesto", "de", "anio", "año"):
                    continue
                if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                    continue
                clave = f"{ruta.stem}:{campo}"
                m = medidas.setdefault(clave, {"valores": {}, "de": ruta.stem,
                                               "rotulo": f"{ruta.stem} · {campo}",
                                               "categoria": None})
                m["valores"][iso] = float(valor)
    return {k: v for k, v in medidas.items() if _tiene_variacion(v["valores"])}


def _tiene_variacion(valores: dict) -> bool:
    """Si una medida tiene suficiente vida como para correlacionar con algo.

    ENCONTRADO EN LA PRIMERA CORRIDA, y es la clase de error que hace que una
    herramienta así no sirva: «exporta armas sin declarar destino» vale CERO en
    26 de 33 Estados. Dos medidas casi todas en cero, con las mismas dos
    excepciones, dan coeficiente 1,00 —y el minero las ofrecía como el hallazgo
    más fuerte del registro—. No es una relación: es que casi no hay datos.

    Se exige que el valor más repetido no domine, y que haya suficientes valores
    distintos. Una medida con 26 ceros no describe a la región: describe a dos
    Estados.
    """
    if len(valores) < MINIMO_CASOS:
        return False
    lista = list(valores.values())
    distintos = set(lista)
    if len(distintos) < max(5, len(lista) // 3):
        return False
    mas_comun = max(lista.count(x) for x in distintos)
    return mas_comun <= len(lista) * MAXIMA_REPETICION


def series_por_estado() -> list:
    """Las series de cada Estado, para buscar anomalías contra su propia historia."""
    salida = []
    for ruta in sorted(PUBLICO.glob("*.json")):
        if ruta.name in comun.TESTIGOS:
            continue
        try:
            d = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        meta = {i.get("clave"): i for i in (d.get("indicadores") or []) if isinstance(i, dict)}
        for fila in (d.get("registros") or []):
            if not isinstance(fila, dict) or not fila.get("iso"):
                continue
            ind = fila.get("indicadores")
            if not isinstance(ind, dict):
                continue
            for clave, cont in ind.items():
                s = (cont or {}).get("serie") if isinstance(cont, dict) else None
                if not isinstance(s, list) or len(s) < MINIMO_SERIE:
                    continue
                puntos = [(p.get("anio"), p.get("valor")) for p in s
                          if isinstance(p, dict) and isinstance(p.get("valor"), (int, float))]
                if len(puntos) < MINIMO_SERIE:
                    continue
                salida.append({"iso": fila["iso"], "pais": fila.get("pais"), "clave": clave,
                               "rotulo": (meta.get(clave) or {}).get("rotulo", clave),
                               "puntos": puntos, "de": ruta.stem})
    return salida


# ------------------------------------------------------------------ cuentas
def _rangos(xs: list) -> list:
    """Los valores cambiados por su puesto, con promedio en los empates."""
    orden = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and xs[orden[j + 1]] == xs[orden[i]]:
            j += 1
        medio = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[orden[k]] = medio
        i = j + 1
    return r


def correlacion(a: dict, b: dict):
    """Coeficiente de RANGOS —Spearman—, no de valores.

    POR QUE DE RANGOS, y esto se decidió mirando la segunda corrida. Casi todo
    lo que este registro cuenta está torcido hacia arriba: exportación de armas,
    listados de sanciones, víctimas de extorsión informática. En datos así el
    coeficiente de Pearson lo decide el país más grande —Brasil o México— y
    aparecían relaciones de 0,97 entre cosas sin parentesco, sostenidas por dos
    puntos. Cambiar los valores por sus puestos desarma eso: pregunta si los
    Estados se ordenan parecido, que es lo que una pista tiene que contestar.
    """
    comunes = [i for i in a if i in b]
    n = len(comunes)
    if n < MINIMO_CASOS:
        return None
    xs = _rangos([a[i] for i in comunes])
    ys = _rangos([b[i] for i in comunes])
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)
    return max(-1.0, min(1.0, r)), n


def p_de_r(r: float, n: int) -> float:
    """Probabilidad de ver un coeficiente así de grande si no hubiera relación.

    Aproximación de Fisher: el arcotangente hiperbólico de r se comporta como
    una normal. Alcanza y sobra para ordenar candidatas, que es lo único que se
    hace acá. NO se usa para afirmar nada.
    """
    if n <= 3 or abs(r) >= 1:
        return 0.0 if abs(r) >= 1 else 1.0
    z = 0.5 * math.log((1 + r) / (1 - r)) * math.sqrt(n - 3)
    return math.erfc(abs(z) / math.sqrt(2))


def benjamini_hochberg(pares: list, alfa: float) -> list:
    """Los que sobreviven a la corrección por comparaciones múltiples.

    Sin esto, con cinco mil pares y el umbral de siempre, doscientos cincuenta
    darían «significativo» aunque los datos fueran ruido puro.
    """
    ordenados = sorted(pares, key=lambda x: x["p"])
    m = len(ordenados)
    corte = 0
    for k, par in enumerate(ordenados, start=1):
        if par["p"] <= alfa * k / m:
            corte = k
    return ordenados[:corte]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    medidas = series_del_registro()
    claves = sorted(medidas)

    pares, probados = [], 0
    for i, a in enumerate(claves):
        for b in claves[i + 1:]:
            probados += 1
            r = correlacion(medidas[a]["valores"], medidas[b]["valores"])
            if not r:
                continue
            coef, n = r
            pares.append({
                "a": a, "b": b,
                "rotulo_a": medidas[a]["rotulo"], "rotulo_b": medidas[b]["rotulo"],
                "coeficiente": round(coef, 3), "estados": n, "tipo": "rangos (Spearman)",
                "p": p_de_r(coef, n),
                # DOS NOMBRES DE LA MISMA MEDIDA. «contratacion · publicadores» y
                # «contrataciones_abiertas · publicadores» dieron 1,00: son el
                # mismo recuento en dos archivos. No es un hallazgo, es un
                # duplicado, y se marca para que no ensucie las pistas.
                "casi_la_misma": abs(coef) >= CASI_LA_MISMA,
                "misma_fuente": medidas[a]["de"] == medidas[b]["de"],
                "misma_categoria": bool(medidas[a]["categoria"])
                                   and medidas[a]["categoria"] == medidas[b]["categoria"],
            })

    sobreviven = benjamini_hochberg(pares, FDR)
    # Las pistas que valen: sobreviven a la corrección Y no son parentescos.
    pistas = [x for x in sobreviven
              if not x["misma_fuente"] and not x["misma_categoria"] and not x["casi_la_misma"]]
    pistas.sort(key=lambda x: -abs(x["coeficiente"]))

    # ---- anomalías contra la propia historia -------------------------------
    anomalias = []
    for s in series_por_estado():
        vals = [v for _, v in s["puntos"]]
        previos, ultimo = vals[:-1], vals[-1]
        if len(previos) < MINIMO_SERIE - 1:
            continue
        # MEDIANA Y DESVIACION ABSOLUTA MEDIANA, no promedio y desvío. En la
        # primera corrida Colombia salió a 554 desvíos porque su serie de
        # efectivos militares casi no se mueve: con un desvío diminuto,
        # cualquier cambio real da una cifra absurda que no informa nada.
        #
        # Y SE EXIGE ADEMAS UN CAMBIO RELATIVO: una anomalía tiene que moverse,
        # no solo desviarse. Colombia bajó de 481.075 a 428.000 —un 11 %—, que
        # es una noticia; decir «554 desvíos» la convertía en un chiste.
        ordenados = sorted(previos)
        mitad = len(ordenados) // 2
        m = (ordenados[mitad] if len(ordenados) % 2 else
             (ordenados[mitad - 1] + ordenados[mitad]) / 2)
        desvios_abs = sorted(abs(v - m) for v in previos)
        k = len(desvios_abs) // 2
        mad = (desvios_abs[k] if len(desvios_abs) % 2 else
               (desvios_abs[k - 1] + desvios_abs[k]) / 2) * 1.4826
        if mad <= 0 or m == 0:
            continue
        # PISO A LA DESVIACION. Una serie casi plana daba desvíos de setecientos
        # ante un cambio del once por ciento, y esa cifra no informa: infla lo
        # que en realidad es una serie quieta. Con un piso del uno por ciento de
        # la mediana, el desvío queda acotado y sigue midiendo lo mismo.
        mad = max(mad, abs(m) * 0.01)
        z = (ultimo - m) / mad
        # EL CAMBIO PORCENTUAL NO SIRVE PARA TODO. Los índices centrados en cero
        # —«ausencia de autocensura», «estabilidad política»— cruzan el cero, y
        # un porcentaje contra una mediana cercana a cero explota: Nicaragua
        # salió a −4.384 %. Se calcula solo cuando la mediana está lejos del
        # cero en la escala de la propia serie; si no, se declara nulo y se
        # muestra el cambio en las unidades de la medida.
        tiene_cero_util = abs(m) > mad
        cambio = abs(ultimo - m) / abs(m) if tiene_cero_util else None
        if abs(z) >= DESVIOS_ANOMALIA and (cambio is None or cambio >= CAMBIO_MINIMO):
            anomalias.append({
                "iso": s["iso"], "pais": s["pais"], "clave": s["clave"], "rotulo": s["rotulo"],
                "anio": s["puntos"][-1][0], "valor": round(ultimo, 3),
                "mediana_previa": round(m, 3), "desvios": round(z, 2),
                "cambio_pct": (round(100 * (ultimo - m) / abs(m), 1)
                               if tiene_cero_util else None),
                "cambio_en_unidades": round(ultimo - m, 3),
                "puntos_previos": len(previos), "de": s["de"],
            })
    # Se ordenan por desvío, que es la única medida que sirve para las dos clases
    # de escala: la que tiene cero útil y la que está centrada en cero. Con el
    # piso puesto arriba, el desvío ya no se dispara por una serie quieta.
    anomalias.sort(key=lambda x: -abs(x["desvios"]))

    salida = {
        "que_es": "Minería sobre el propio registro: cruza todos los pares de medidas y busca "
                  "Estados que se salieron de su propia historia. Deja PISTAS para que las "
                  "mire una persona; no emite juicios ni afirma causas.",
        "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "medidas_con_suficientes_casos": len(claves),
        "pares_probados": probados,
        "correccion": {
            "metodo": "Benjamini-Hochberg",
            "alfa": FDR,
            "por_que": f"Con {probados} pares y el umbral de siempre, alrededor de "
                       f"{int(probados * 0.05)} darían «significativo» por puro azar aunque "
                       "los datos fueran ruido. Publicar esa lista sería fabricar hallazgos a "
                       "escala industrial.",
            "sobreviven": len(sobreviven),
            "de_ellos_son_parentescos": len(sobreviven) - len(pistas),
        },
        "minimos": {"casos_por_par": MINIMO_CASOS, "puntos_de_serie": MINIMO_SERIE,
                    "desvios_para_anomalia": DESVIOS_ANOMALIA,
                    "cambio_minimo_para_anomalia": CAMBIO_MINIMO,
                    "maxima_repeticion_de_un_valor": MAXIMA_REPETICION},
        # Se publican las más fuertes y se declara CUANTAS hay: mostrar sesenta
        # sin decir que son mil doscientas haría creer que el registro encontró
        # sesenta cosas.
        "pistas_totales": len(pistas),
        "anomalias_totales": len(anomalias),
        "pistas": pistas[:60],
        "anomalias": anomalias[:40],
        "lo_que_no_dice": "Que una cosa cause la otra. Dos medidas pueden acompañarse por un "
                          "tercer factor, por la forma en que se recolectan o por azar que "
                          "esta corrección reduce pero no elimina.",
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8",
                      newline="")
    print(f"[minería] {len(claves)} medidas · {probados} pares probados · "
          f"{len(sobreviven)} sobreviven a la corrección · {len(pistas)} pistas "
          f"(sin parentescos) · {len(anomalias)} anomalías")


if __name__ == "__main__":
    main()
