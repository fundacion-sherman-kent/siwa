# -*- coding: utf-8 -*-
"""El termómetro de frescura: ¿de qué año es cada indicador que SIWA publica?

POR QUÉ EXISTE
---------------
El reloj de actualidad (`reloj-actualidad.py`) contesta una pregunta puntual:
¿SIWA tiene el último dato que SU FUENTE publica hoy? Necesita salir a la red y
sólo mira un puñado de fuentes (Banco Mundial, OMS, tres ediciones anuales).

Esta herramienta contesta una pregunta distinta y más simple: **de los más de
doscientos indicadores que SIWA YA TIENE publicados, ¿de qué año es cada uno?**
No sale a ningún lado: lee lo que el propio registro escribió. Con eso arma un
ranking — el termómetro — de qué está fresco y qué quedó viejo, sin necesitar
preguntarle nada a nadie.

**No mide si el dato es correcto.** Mide su edad. Un indicador de 2020 puede ser
lo más nuevo que existe (ver `comun.SERIES_DETENIDAS`) o puede ser un colector
que se quedó atrás: esta herramienta no distingue las dos cosas — para eso está
`propuestas-frescura.py`, que sí cruza esta lista contra lo que se sabe de cada
caso.

DE DÓNDE SALE CADA NÚMERO
--------------------------
De `registros[].indicadores[clave].anio` en cada archivo de
`datos/publico/*.json`. Es la MISMA fuente de verdad que ya usa
`comun.escribir()` para calcular `hasta_anio` y `rezago_anios` por archivo en
el momento de guardar: acá se vuelve a calcular, archivo por archivo, para
poder construir el panorama del REGISTRO ENTERO — el ranking y la mediana — que
hasta hoy no existía en ningún lado.

LO QUE NO HACE
---------------
No cambia ningún dato, no decide qué está mal y no falla la corrida por tener
indicadores viejos: eso sería castigar al robot por decir la verdad. Sólo falla
si de verdad no pudo escribir su resultado.
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
PUBLICO = RAIZ / "datos" / "publico"
SALIDA = PUBLICO / "frescura.json"

# Archivos que el propio termómetro escribe o que no describen indicadores por
# año (son mediciones del robot sobre sí mismo, catálogos o bitácoras). Se
# excluyen para no medir la frescura de la frescura.
PROPIOS = {"frescura.json", "propuestas-frescura.json", "indice.json",
           "auditoria.json", "segunda_fuente.json", "sondeo.json",
           "reloj-actualidad.json", "indice_opacidad.json", "opacidad_historia.json"}

# Tres cortes del termómetro. No son un juicio de qué es aceptable en cada
# materia —eso lo declara cada colector con su `hasta_anio`—: son sólo los tres
# baldes en que se agrupa el ranking para poder leerlo de un vistazo.
CORTE_FRESCO = 1
CORTE_TIBIO = 3


def _anio_hoy() -> int:
    return datetime.now(timezone.utc).year


def _cargar(ruta: Path):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — un archivo roto se declara y no tumba el resto
        return None


def _meta_por_clave(d: dict) -> dict:
    """{clave: {rotulo, eje, origen, seccion, serie_detenida}} del bloque
    `indicadores` que `comun.escribir()` ya deja en cada archivo."""
    salida = {}
    for i in d.get("indicadores") or []:
        clave = i.get("clave")
        if not clave:
            continue
        # Un mismo archivo puede declarar una clave compuesta, del tipo
        # "gdl (2 indicadores)": no corresponde a UNA columna de `registros` y
        # se salta, para no fabricar un año que no está.
        for una in [c.strip() for c in clave.split(",")]:
            salida[una] = {
                "rotulo": i.get("rotulo") or una,
                "eje": i.get("eje") or "Sin clasificar",
                "origen": i.get("origen"),
                "seccion": i.get("seccion"),
                "unidad": i.get("unidad"),
                "serie_detenida": i.get("serie_detenida"),
                "mas_es_peor": i.get("mas_es_peor"),
            }
    return salida


def medir() -> dict:
    hoy = _anio_hoy()
    por_indicador: dict[str, dict] = {}
    archivos_leidos, archivos_rotos, sin_indicadores = 0, [], []

    for ruta in sorted(PUBLICO.glob("*.json")):
        if ruta.name in PROPIOS or ruta.parent.name == "estado":
            continue
        d = _cargar(ruta)
        if d is None:
            archivos_rotos.append(ruta.name)
            continue
        if not isinstance(d, dict) or not isinstance(d.get("registros"), list):
            continue

        procedencia = d.get("procedencia") or {}
        fuente_archivo = procedencia.get("fuente")
        fuente_archivo = fuente_archivo.get("nombre") if isinstance(fuente_archivo, dict) else fuente_archivo
        colector = procedencia.get("colector") or ruta.stem
        meta = _meta_por_clave(d)

        # Un recorrido por fila: cada fila puede traer varias claves (un
        # archivo con seis indicadores tiene seis por Estado).
        por_clave: dict[str, list] = {}
        filas_con_iso = 0
        for fila in d["registros"]:
            if not isinstance(fila, dict):
                continue
            if fila.get("iso"):
                filas_con_iso += 1
            for clave, val in (fila.get("indicadores") or {}).items():
                if not isinstance(val, dict) or not val.get("anio"):
                    continue
                try:
                    anio = int(str(val["anio"])[:4])
                except (TypeError, ValueError):
                    continue
                por_clave.setdefault(clave, []).append(anio)

        if not por_clave:
            sin_indicadores.append(ruta.name)
        archivos_leidos += 1

        for clave, anios in por_clave.items():
            if clave in por_indicador:
                # Una clave no debería repetirse en dos archivos: si pasa, se
                # declara en vez de pisar en silencio el primero.
                por_indicador[clave].setdefault("_colision", []).append(ruta.name)
                continue
            m = meta.get(clave, {})
            anio_mas_reciente = max(anios)
            por_indicador[clave] = {
                "clave": clave,
                "rotulo": m.get("rotulo", clave),
                "eje": m.get("eje", "Sin clasificar"),
                "seccion": m.get("seccion"),
                "fuente": m.get("origen") or fuente_archivo or "sin declarar",
                "unidad": m.get("unidad"),
                "colector": colector,
                "archivo": ruta.name,
                "anio_mas_reciente": anio_mas_reciente,
                "antiguedad_anios": max(hoy - anio_mas_reciente, 0),
                "cobertura": {
                    "con_dato_en_el_anio_mas_reciente": sum(1 for a in anios if a == anio_mas_reciente),
                    "de_filas_con_iso": filas_con_iso or len(anios),
                },
                "serie_detenida": bool(m.get("serie_detenida")),
            }

    indicadores = [v for v in por_indicador.values()]
    colisiones = {k: v["_colision"] for k, v in por_indicador.items() if v.get("_colision")}
    for v in indicadores:
        v.pop("_colision", None)
    indicadores.sort(key=lambda x: (-x["antiguedad_anios"], x["clave"]))

    edades = [x["antiguedad_anios"] for x in indicadores]
    resumen = {
        "indicadores_medidos": len(indicadores),
        "mediana_antiguedad_anios": round(statistics.median(edades), 1) if edades else None,
        "al_dia_1_anio_o_menos": sum(1 for e in edades if e <= CORTE_FRESCO),
        "tibio_2_a_3_anios": sum(1 for e in edades if CORTE_FRESCO < e <= CORTE_TIBIO),
        "atrasado_4_anios_o_mas": sum(1 for e in edades if e > CORTE_TIBIO),
        "series_detenidas_declaradas": sum(1 for x in indicadores if x["serie_detenida"]),
        "archivos_leidos": archivos_leidos,
        "archivos_sin_json_valido": archivos_rotos,
        "archivos_sin_indicadores_por_anio": sin_indicadores,
    }

    salida = {
        "que_es": "Termómetro de frescura de SIWA: el año más reciente que tiene cada "
                  "indicador publicado, calculado de lo que el propio registro ya "
                  "escribió (sin salir a ninguna fuente). No mide si el dato es "
                  "correcto ni si está atrasado respecto de su fuente: eso lo hacen "
                  "`reloj-actualidad.py` (en vivo) y `propuestas-frescura.py` (con "
                  "esta misma medición).",
        "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cortes_del_termometro": {"al_dia": f"≤{CORTE_FRESCO} año", "tibio": f"2 a {CORTE_TIBIO} años",
                                  "atrasado": f"{CORTE_TIBIO + 1} años o más"},
        "resumen": resumen,
        "ranking_mas_atrasados": indicadores[:30],
        "indicadores": indicadores,
        "colisiones_de_clave": colisiones,
        "vacios_declarados": [
            "La 'cobertura' cuenta filas con dato en el año más reciente de ESE "
            "indicador, no contra el padrón de 33 Estados: un indicador regional "
            "(no por Estado) declara su propio total de filas.",
            "Un indicador con `serie_detenida` en verdadero no es un colector roto: "
            "se le preguntó a la fuente y no tiene nada más nuevo "
            "(`colectores/comun.SERIES_DETENIDAS`). Igual entra al ranking, porque "
            "la región sigue sin medida vigente de esa materia y eso hay que verlo.",
            "Esta medición es tan buena como lo que cada colector declaró en su "
            "bloque `indicadores`: un indicador sin ese bloque (o con la clave mal "
            "escrita) no entra al ranking aunque tenga datos. Ver "
            "`archivos_sin_indicadores_por_anio`.",
        ],
    }
    return salida


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    salida = medir()
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8", newline="")
    r = salida["resumen"]
    print(f"[frescura] {r['indicadores_medidos']} indicadores · mediana "
          f"{r['mediana_antiguedad_anios']} años · {r['al_dia_1_anio_o_menos']} al día · "
          f"{r['tibio_2_a_3_anios']} tibios · {r['atrasado_4_anios_o_mas']} atrasados")
    for x in salida["ranking_mas_atrasados"][:10]:
        print(f"   {x['antiguedad_anios']:>3} años · {x['rotulo']} ({x['clave']}) · "
              f"hasta {x['anio_mas_reciente']} · {x['fuente']}")
    if salida["colisiones_de_clave"]:
        print(f"[frescura] AVISO: {len(salida['colisiones_de_clave'])} clave(s) repetida(s) "
              f"en más de un archivo: {salida['colisiones_de_clave']}")
    if r["archivos_sin_json_valido"]:
        print(f"[frescura] AVISO: no se pudo leer {r['archivos_sin_json_valido']}")


if __name__ == "__main__":
    main()
