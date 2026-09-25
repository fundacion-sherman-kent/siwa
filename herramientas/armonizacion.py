# -*- coding: utf-8 -*-
"""Motor de armonización: vuelve comparables dos fuentes que miden lo mismo distinto.

POR QUÉ EXISTE
--------------
La dirección fijó (25/9/2026): «debemos poder comparar todo». No se declara «no
comparable»: se ARMONIZA y se declara el método y la incertidumbre. La estadística
oficial lo hace con enlace, benchmarking, normalización y concordancia (Manual
OCDE/JRC de indicadores compuestos; armonización ex-post de UNECE/Eurostat; SDMX;
benchmarking Denton/Chow-Lin del FMI). Este motor implementa el caso base —el
ENLACE por offset sobre el solapamiento— y deja la estructura para los otros.

QUÉ HACE, Y QUÉ NO
------------------
Lee `fuentes/armonizaciones.json` (los pares declarados: una fuente FRESCA y una
COMPARABLE, con el método). Por cada país que tiene las dos series, calcula la
relación (offset, coeficiente, incertidumbre) y emite una FICHA. Escribe
`datos/publico/armonizacion.json`, que el sitio lee para rotular la tarjeta.

CALCULA (proceso), NO DECIDE (juicio): propone el nivel y los números; el nivel, el
supuesto y si el offset es lo bastante estable para enlazar los confirma una
persona (`confirmado_por_humano` en la declaración). No incorpora fuentes, no toca
dato publicado, no consulta internet: todo lo que usa ya está en el repositorio.
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
DECL = RAIZ / "fuentes" / "armonizaciones.json"
SALIDA = PUBLICO / "armonizacion.json"


def _cargar(ruta: Path, defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — sin el archivo, se degrada y se declara
        return defecto


def _series_por_iso(archivo: str, clave: str) -> dict:
    """{iso: {anio: valor}} para una clave, leyendo la estructura estándar de la
    casa (`registros[].iso`, `registros[].indicadores[clave].serie`)."""
    d = _cargar(PUBLICO / archivo, None)
    if not isinstance(d, dict):
        return {}
    salida = {}
    for reg in d.get("registros", []) or []:
        iso = reg.get("iso")
        ind = (reg.get("indicadores") or {}).get(clave)
        if not iso or not isinstance(ind, dict):
            continue
        serie = {}
        for punto in ind.get("serie", []) or []:
            a, v = punto.get("anio"), punto.get("valor")
            if isinstance(a, int) and isinstance(v, (int, float)):
                serie[a] = float(v)
        # el último valor a veces vive fuera de la serie
        if isinstance(ind.get("anio"), int) and isinstance(ind.get("valor"), (int, float)):
            serie.setdefault(ind["anio"], float(ind["valor"]))
        if serie:
            salida[iso] = serie
    return salida


def _redondear(x, dec):
    return round(x, dec) if isinstance(x, (int, float)) else x


def enlazar(par: dict) -> list:
    """Calcula la ficha de enlace por país para un par declarado."""
    dec = int(par.get("decimales", 1))
    desde = int(par.get("desde_anio", 2000))
    fr = _series_por_iso(par["fresca"]["archivo"], par["fresca"]["clave"])
    co = _series_por_iso(par["comparable"]["archivo"], par["comparable"]["clave"])
    fichas = []
    for iso in sorted(set(fr) & set(co)):
        sf, sc = fr[iso], co[iso]
        comun = sorted(a for a in (set(sf) & set(sc)) if a >= desde)
        if len(comun) < 3:
            continue  # sin solapamiento suficiente, no se enlaza
        difs = [sf[a] - sc[a] for a in comun]
        offset = statistics.mean(difs)
        incert = statistics.pstdev(difs) if len(difs) > 1 else 0.0
        anio_fresca = max(sf)
        anio_comparable = max(sc)
        val_fresca = sf[anio_fresca]
        # la fresca llevada a la base COMPARABLE (para rankear contra los que sólo
        # tienen la comparable): valor_fresca − offset(fresca−comparable)
        base_comparable = val_fresca - offset
        fichas.append({
            "iso": iso,
            "clave": par["fresca"]["clave"],
            "indicador": par["indicador"],
            "unidad": par.get("unidad", ""),
            "nivel": par.get("nivel_propuesto", "C"),
            "metodo": par["metodo"],
            "fresca": {"fuente": par["fresca"]["fuente"], "anio": anio_fresca,
                       "valor": _redondear(val_fresca, dec)},
            "comparable": {"fuente": par["comparable"]["fuente"], "anio": anio_comparable,
                           "valor": _redondear(sc[anio_comparable], dec)},
            "solapamiento": {"desde": comun[0], "hasta": comun[-1], "anios": len(comun)},
            "offset_fresca_menos_comparable": _redondear(offset, 3),
            "incertidumbre": _redondear(incert, 3),
            "valor_en_base_comparable": _redondear(base_comparable, dec),
            "confirmado_por_humano": bool(par.get("confirmado_por_humano", False)),
            "nota": (f"Dato fresco {_redondear(val_fresca, dec)} ({anio_fresca}, "
                     f"{par['fresca']['fuente']}); en base {par['comparable']['fuente']} "
                     f"≈ {_redondear(base_comparable, dec)} ± {_redondear(incert, 1)}. "
                     f"Enlace sobre {comun[0]}–{comun[-1]} ({len(comun)} años)."),
        })
    return fichas


def construir() -> dict:
    decl = _cargar(DECL, None)
    if not isinstance(decl, dict):
        return {"que_es": "Motor de armonización — no encontró fuentes/armonizaciones.json.",
                "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "fichas": [], "vacios_declarados": ["Falta la declaración."]}
    fichas = []
    vacios = []
    for par in decl.get("armonizaciones", []) or []:
        metodo = par.get("metodo")
        if metodo == "enlace":
            f = enlazar(par)
            fichas.extend(f)
            if not f:
                vacios.append(f"«{par.get('indicador')}»: sin países con solapamiento suficiente "
                              "(las dos series recolectadas y con años en común).")
        else:
            # benchmarking / normalizacion / concordancia: declarados, aún no
            # implementados en el motor — se calculan al incorporar cada fuente.
            vacios.append(f"«{par.get('indicador')}»: método «{metodo}» declarado, todavía no "
                          "implementado en el motor (se agrega al traer esa fuente).")
    por_indicador = {}
    for x in fichas:
        por_indicador.setdefault(x["indicador"], 0)
        por_indicador[x["indicador"]] += 1
    return {
        "que_es": "Fichas de armonización: por cada par declarado (fuente fresca vs comparable) y "
                  "país, cómo se enlazan, con qué offset e incertidumbre, y el valor fresco llevado "
                  "a la base comparable. El sitio lo lee para rotular. CALCULA, no decide: el nivel y "
                  "el supuesto los confirma una persona.",
        "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "resumen": {"fichas": len(fichas), "por_indicador": por_indicador},
        "fichas": fichas,
        "vacios_declarados": vacios or ["Sin vacíos en esta corrida."],
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    salida = construir()
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8", newline="")
    r = salida.get("resumen", {})
    print(f"[armonizacion] {r.get('fichas', 0)} fichas · {r.get('por_indicador', {})}")
    for f in salida["fichas"][:6]:
        print(f"   {f['iso']} · {f['indicador']} · offset {f['offset_fresca_menos_comparable']:+} "
              f"± {f['incertidumbre']} · base comparable {f['valor_en_base_comparable']}")


if __name__ == "__main__":
    main()
