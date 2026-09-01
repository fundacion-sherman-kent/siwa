"""Contrabando y subfacturación por estadística espejo.

El método, que es viejo y sólido
--------------------------------
Cuando el país A declara que exportó cien al país B, y B declara que importó
sesenta de A, **esos cuarenta se fueron por algún lado**. La diferencia entre lo
que un Estado declara enviar y lo que el otro declara recibir se llama *brecha
espejo*, y es el indicio estándar de contrabando, subfacturación y triangulación.

Fuente: **Comtrade de Naciones Unidas**, vista pública sin credencial.

La cautela que ordena todo lo demás
-----------------------------------
> **Una brecha de pocos puntos NO es contrabando: es contabilidad.**

El exportador declara en valor FOB —la mercadería puesta en el barco— y el
importador en valor CIF, que además incluye **flete y seguro**. Solo por eso el
importador registra de rutina entre 3 % y 10 % más. A eso se suman los envíos que
cruzan el año calendario y las diferencias de clasificación aduanera.

**Lo que sí llama la atención es la brecha grande, persistente y asimétrica**, y
sobre todo la brecha **negativa**: que el importador declare MENOS de lo que el
exportador dice haberle mandado no tiene explicación contable inocente, porque el
CIF debería empujar en el sentido contrario.

Un error que costó encontrar y queda escrito
--------------------------------------------
La respuesta trae **una fila por modo de transporte** además de la fila total.
Sumarlas todas —que es lo primero que uno hace— **duplica el comercio**: en la
primera prueba Argentina–Brasil dio una brecha de **+109 %**, que es absurda. Con
la fila total sola, la brecha real es **+4,7 %**, perfectamente explicable por el
FOB contra CIF. Por eso el colector filtra explícitamente `motCode = 0`,
`customsCode = C00` y `partner2Code = 0`, y descarta el resto.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import comun
import geo

BASE = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
ANIO = 2023           # último año con cobertura amplia en la vista pública
NAVEGADOR = comun.AGENTE
ESPERA = 2.5          # cortesía con el servidor público
POR_CORRIDA = 5       # la vista pública admite pocas consultas por ventana
ARCHIVO = comun.DATOS / "publico" / "comercio.json"

# Código numérico de Naciones Unidas para cada Estado del padrón.
M49 = {
    "ARG": 32, "BOL": 68, "BRA": 76, "CHL": 152, "COL": 170, "CRI": 188,
    "CUB": 192, "DOM": 214, "ECU": 218, "SLV": 222, "GTM": 320, "HND": 340,
    "MEX": 484, "NIC": 558, "PAN": 591, "PRY": 600, "PER": 604, "URY": 858,
    "VEN": 862, "HTI": 332, "JAM": 388, "TTO": 780, "GUY": 328, "SUR": 740,
    "BLZ": 84, "BHS": 44, "BRB": 52, "ATG": 28, "DMA": 212, "GRD": 308,
    "KNA": 659, "LCA": 662, "VCT": 670,
}

# Pares donde la brecha importa de verdad: los que comparten frontera, mas los
# corredores regionales de mayor volumen. No se barren los 1.056 pares posibles:
# la mayoria no tiene comercio significativo y solo agregaria ruido.
PARES = [
    ("ARG", "BRA"), ("ARG", "PRY"), ("ARG", "BOL"), ("ARG", "CHL"), ("ARG", "URY"),
    ("BRA", "PRY"), ("BRA", "BOL"), ("BRA", "URY"), ("BRA", "PER"), ("BRA", "COL"),
    ("BRA", "VEN"), ("BRA", "GUY"), ("BRA", "SUR"),
    ("COL", "VEN"), ("COL", "ECU"), ("COL", "PER"), ("COL", "PAN"), ("COL", "BRA"),
    ("PER", "ECU"), ("PER", "BOL"), ("PER", "CHL"),
    ("BOL", "CHL"), ("BOL", "PRY"),
    ("MEX", "GTM"), ("MEX", "BLZ"),
    ("GTM", "HND"), ("GTM", "SLV"), ("GTM", "BLZ"),
    ("HND", "SLV"), ("HND", "NIC"), ("NIC", "CRI"), ("CRI", "PAN"),
    ("DOM", "HTI"),
    ("VEN", "GUY"), ("GUY", "SUR"),
    ("CHL", "PRY"), ("URY", "PRY"),
]


def _pedir(consulta: dict):
    url = BASE + "?" + urllib.parse.urlencode(consulta)
    pet = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
    with urllib.request.urlopen(pet, timeout=90) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _valor(reporter: int, partner: int, flujo: str):
    """Valor total declarado. Devuelve (valor, filas_descartadas, falla)."""
    try:
        d = _pedir({"reporterCode": reporter, "partnerCode": partner,
                    "flowCode": flujo, "period": ANIO, "cmdCode": "TOTAL"})
    except urllib.error.HTTPError as e:
        return None, 0, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001 — la falla se declara, no se oculta
        return None, 0, type(e).__name__
    filas = d.get("data") or []
    # LA LINEA QUE IMPORTA: solo la fila total. Las demas son el mismo comercio
    # abierto por modo de transporte, y sumarlas lo duplica.
    buenas = [f for f in filas
              if f.get("motCode") in (0, "0")
              and f.get("customsCode") in (None, "C00")
              and f.get("partner2Code") in (0, "0", None)]
    if not buenas:
        return None, len(filas), "sin fila total"
    return (sum(float(f.get("primaryValue") or 0) for f in buenas),
            len(filas) - len(buenas), None)


def _par(p: tuple):
    a, b = p
    time.sleep(ESPERA)
    exporta, desc1, f1 = _valor(M49[a], M49[b], "X")   # A dice exportar a B
    time.sleep(ESPERA)
    importa, desc2, f2 = _valor(M49[b], M49[a], "M")   # B dice importar de A
    return {"origen": a, "destino": b,
            "declarado_por_el_exportador": exporta,
            "declarado_por_el_importador": importa,
            "filas_descartadas": desc1 + desc2,
            "falla": f1 or f2}


def recolectar():
    padron = geo.padron()
    nombres = {p["iso"]: p["pais"] for p in padron}
    bloques = {p["iso"]: p["bloque"] for p in padron}

    # --- Lo ya medido en corridas anteriores no se vuelve a pedir enseguida ---
    previos = {}
    if ARCHIVO.exists():
        try:
            viejo = json.loads(ARCHIVO.read_text(encoding="utf-8"))
            for c in (viejo.get("corredores") or []):
                previos[(c["origen"], c["destino"])] = c
        except Exception:  # noqa: BLE001 — un archivo ilegible no detiene la corrida
            previos = {}

    # La vista publica admite pocas consultas por ventana y devuelve 429 al resto.
    # No se la fuerza: cada corrida mide unos pocos corredores, empezando por los
    # que nunca se midieron y siguiendo por los mas viejos. En dos semanas de
    # corridas diarias el mapa queda completo, y cada corredor declara CUANDO se
    # midio. Es preferible un dato fechado que un barrido que el servidor rechaza.
    def antiguedad(par):
        c = previos.get(par)
        return "" if not c else (c.get("medido_en") or "")
    pendientes = sorted(PARES, key=antiguedad)[:POR_CORRIDA]

    crudo = [_par(par) for par in pendientes]

    caidos = [f"{c['origen']}-{c['destino']}: {c['falla']}" for c in crudo if c["falla"]]
    descartadas = sum(c["filas_descartadas"] for c in crudo)

    corredores, por_iso = [], {}
    # Primero entran los corredores ya medidos que no se volvieron a pedir.
    medidos_ahora = {(c["origen"], c["destino"]) for c in crudo}
    for par, viejo in previos.items():
        if par not in medidos_ahora:
            corredores.append(viejo)

    for c in crudo:
        x, m = c["declarado_por_el_exportador"], c["declarado_por_el_importador"]
        if not x or not m or x <= 0:
            continue
        brecha = m - x
        pct = brecha / x * 100
        fila = {
            "origen": c["origen"], "pais_origen": nombres[c["origen"]],
            "destino": c["destino"], "pais_destino": nombres[c["destino"]],
            "exportador_declara": round(x),
            "importador_declara": round(m),
            "brecha": round(brecha),
            "brecha_pct": round(pct, 1),
            # El signo es lo que se lee, no la magnitud.
            "sentido": "el importador declara menos" if pct < 0 else "el importador declara más",
            "llama_la_atencion": pct < -5 or pct > 25,
            "medido_en": comun.ahora(),
        }
        corredores.append(fila)
        for iso in (c["origen"], c["destino"]):
            por_iso.setdefault(iso, []).append(fila)

    for f in corredores:
        for iso in (f["origen"], f["destino"]):
            if f not in por_iso.setdefault(iso, []):
                por_iso[iso].append(f)
    corredores.sort(key=lambda f: f["brecha_pct"])

    registros = []
    for p in padron:
        filas = por_iso.get(p["iso"])
        if not filas:
            continue
        negativas = [f for f in filas if f["brecha_pct"] < -5]
        registros.append({
            "iso": p["iso"], "pais": p["pais"], "bloque": p["bloque"],
            "corredores": len(filas),
            "corredores_que_llaman_la_atencion": sum(1 for f in filas if f["llama_la_atencion"]),
            "peor_brecha_pct": min(f["brecha_pct"] for f in filas),
            "brecha_negativa_en": [f"{f['pais_origen']} → {f['pais_destino']}"
                                   for f in negativas][:4],
        })
    registros.sort(key=lambda r: r["peor_brecha_pct"])

    llamativos = [c for c in corredores if c["llama_la_atencion"]]
    vacios = [
        "UNA BRECHA DE POCOS PUNTOS NO ES CONTRABANDO: ES CONTABILIDAD. El exportador "
        "declara en valor FOB —la mercaderia puesta en el barco— y el importador en CIF, "
        "que ademas incluye FLETE Y SEGURO. Solo por eso el importador registra de rutina "
        "entre 3 % y 10 % mas. A eso se suman los envios que cruzan el anio calendario y "
        "las diferencias de clasificacion aduanera.",
        "LO QUE SI LLAMA LA ATENCION ES LA BRECHA NEGATIVA: que el importador declare "
        "MENOS de lo que el exportador dice haberle mandado no tiene explicacion contable "
        "inocente, porque el flete y el seguro empujan en el sentido contrario. Aun asi "
        "es un INDICIO que abre una linea de averiguacion, NO una prueba de delito.",
        f"Se comparan {len(PARES)} corredores —los que comparten frontera y los de mayor "
        "volumen regional—, no los 1.056 pares posibles: la mayoria no tiene comercio "
        "significativo y solo agregaria ruido. Un corredor ausente no esta limpio: no "
        "esta mirado.",
        f"LA MEDICION ES ACUMULATIVA. La vista publica de Comtrade admite pocas consultas "
        f"por ventana y rechaza el resto: en la primera prueba devolvio HTTP 429 en 34 de "
        f"37 pedidos. No se la fuerza. Cada corrida mide {POR_CORRIDA} corredores, "
        "empezando por los que nunca se midieron, y CADA CORREDOR DECLARA CUANDO SE "
        f"MIDIO. Van {len(corredores)} de {len(PARES)} medidos al menos una vez. Es "
        "preferible un dato fechado que un barrido que el servidor rechaza.",
        f"El anio es {ANIO}, el ultimo con cobertura amplia en la vista publica. NO es el "
        "anio corriente y no se estima ninguno posterior.",
        "Se compara el TOTAL de comercio, no producto por producto. La subfacturacion "
        "suele concentrarse en unas pocas partidas y se diluye en el total: este registro "
        "sirve para senalar el corredor, no la mercaderia.",
        "Un Estado que no reporta a Comtrade no genera brecha con nadie, y por lo tanto "
        "NO APARECE. La ausencia mide la calidad de su estadistica aduanera, no su "
        "honestidad comercial.",
    ]
    if descartadas:
        vacios.append(
            f"Se descartaron {descartadas} filas de apertura por modo de transporte. "
            "Sumarlas al total duplica el comercio: en la primera prueba la brecha "
            "Argentina-Brasil dio +109 %, que es absurdo; con la fila total sola da "
            "+4,7 %. Queda anotado porque es un error facil de cometer.")
    if caidos:
        vacios.append("Consultas que fallaron: " + "; ".join(caidos))

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Declaraciones aduaneras oficiales de cada Estado, compiladas por Naciones "
              "Unidas. La fuente es de primer orden; lo que NO es de primer orden es la "
              "interpretacion: la brecha es un indicio, no una medicion de contrabando."),
    )

    return comun.escribir(
        colector="comercio",
        capa="publico",
        fuente="Comtrade de Naciones Unidas — vista pública",
        url_fuente="https://comtradeapi.un.org/public/v1/preview/C/A/HS",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "corredores_comparados": len(corredores),
                "corredores_pedidos": len(PARES),
                "corredores_que_llaman_la_atencion": len(llamativos),
                "estados_con_dato": len(registros),
                "estados_del_padron": len(padron),
                "anio": ANIO,
                "filas_descartadas_por_transporte": descartadas,
            },
            "corredores": corredores,
            "metodo": (
                "Para cada corredor se pide lo que el origen declara EXPORTAR al destino "
                "y lo que el destino declara IMPORTAR del origen, en el mismo anio y "
                "sobre el total de mercaderias. Se toma UNICAMENTE la fila total "
                "—motCode 0, customsCode C00, partner2Code 0— y se descartan las "
                "aperturas por modo de transporte, que repiten el mismo comercio."
            ),
        },
    )


if __name__ == "__main__":
    comun.correr("comercio", recolectar)
