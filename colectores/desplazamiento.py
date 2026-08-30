"""Desplazamiento forzado — ACNUR, Refugee Data Finder.

Materia del eje de inteligencia estratégica. Sin clave y sin registro.

De cada Estado del padrón se registran dos caras que no deben confundirse:

- **Como país de origen**: personas nacidas allí que están refugiadas o
  solicitando asilo en otra parte. Mide expulsión.
- **Como país de asilo**: personas de otro origen alojadas allí, más los
  desplazados internos dentro de sus fronteras. Mide recepción y conflicto
  interno.

Un país puede ser alto en ambas. Presentarlas juntas como «migración» sería
fundir dos fenómenos distintos.

Escribe dos archivos, conforme a `doctrina/siwa.md` §2:
- `datos/publico/desplazamiento.json` — el año más reciente
- `datos/suscriptor/desplazamiento-serie.json` — la serie anual completa
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import comun
import geo

FUENTE = "ACNUR — Refugee Data Finder"
BASE = "https://api.unhcr.org/population/v1/population/"
URL_PUBLICA = "https://www.unhcr.org/refugee-statistics/"

DESDE = 2015
PAUSA = 0.25          # cortesía con una interfaz pública y gratuita


def _codigos_acnur() -> dict:
    """Traduce el código ISO 3166 del padrón al código propio de ACNUR.

    ACNUR **no usa ISO**: Honduras es `HON` y no `HND`, Guatemala `GUA`, El
    Salvador `SAL`, Haití `HAI`, Uruguay `URU`. Consultar con el código ISO
    devuelve cero filas sin error, lo que se leería como ausencia de datos
    cuando en realidad es una consulta mal formada. El mapa se toma de la
    propia fuente y no se escribe a mano.
    """
    crudo = comun.pedir("https://api.unhcr.org/population/v1/countries/?limit=400")
    return {
        fila["iso"]: fila["code"]
        for fila in crudo.get("items", [])
        if fila.get("iso") and fila.get("code")
    }


def _serie(parametro: str, codigo: str, hasta: int) -> dict:
    """Trae la serie anual de un país, como origen o como asilo."""
    url = f"{BASE}?yearFrom={DESDE}&yearTo={hasta}&{parametro}={codigo}&limit=200"
    crudo = comun.pedir(url)
    filas = {}
    for fila in crudo.get("items", []):
        filas[int(fila["year"])] = {
            "refugiados": int(fila.get("refugees") or 0),
            "solicitantes_asilo": int(fila.get("asylum_seekers") or 0),
            "desplazados_internos": int(fila.get("idps") or 0),
        }
    return filas


def recolectar():
    hasta = datetime.now(timezone.utc).year
    codigos = _codigos_acnur()
    registros, serie_completa = [], []
    sin_dato, sin_codigo = [], []

    for pais in geo.padron():
        codigo = codigos.get(pais["iso"])
        if not codigo:
            sin_codigo.append(pais["pais"])
            continue

        origen = _serie("coo", codigo, hasta)
        time.sleep(PAUSA)
        asilo = _serie("coa", codigo, hasta)
        time.sleep(PAUSA)

        anios = sorted(set(origen) | set(asilo))
        if not anios:
            sin_dato.append(pais["pais"])
            continue

        filas = []
        for anio in anios:
            o = origen.get(anio, {})
            a = asilo.get(anio, {})
            filas.append(
                {
                    "anio": anio,
                    "origen_refugiados": o.get("refugiados", 0),
                    "origen_solicitantes": o.get("solicitantes_asilo", 0),
                    "asilo_refugiados": a.get("refugiados", 0),
                    "asilo_solicitantes": a.get("solicitantes_asilo", 0),
                    "desplazados_internos": a.get("desplazados_internos", 0),
                }
            )

        serie_completa.append({**pais, "serie": filas})
        ultima = filas[-1]
        registros.append(
            {
                **pais,
                "anio": ultima["anio"],
                "expulsion": ultima["origen_refugiados"] + ultima["origen_solicitantes"],
                "recepcion": ultima["asilo_refugiados"] + ultima["asilo_solicitantes"],
                "desplazados_internos": ultima["desplazados_internos"],
                "detalle": ultima,
            }
        )

    registros.sort(key=lambda r: r["expulsion"], reverse=True)
    # El año que se declara es el del dato, no el que se pidió.
    anio_del_dato = max((r["anio"] for r in registros), default=None)

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=(
            "Registro estadístico del organismo multilateral con mandato sobre la "
            "materia. Fuente única: la segunda fuente independiente sería el registro "
            "migratorio de cada Estado, no incorporado. Declarado conforme a "
            "doctrina/fuentes.md §2 ter."
        ),
    )

    vacios = [
        "La cifra es ANUAL y de cierre de año. No es un dato en vivo: entre "
        "publicaciones, la situación puede haber cambiado por completo.",
        "ACNUR cuenta a quien está bajo su mandato o registrado ante autoridades. "
        "La migración irregular no registrada no aparece, y en varios corredores de "
        "la región es la mayoría del flujo.",
        "Sin desglose subnacional: la cifra es nacional y el mapa la muestra como tal.",
        "«Expulsión» y «recepción» son dos fenómenos distintos y no se suman: un "
        "mismo Estado puede ser alto en ambos.",
        "Los desplazados internos se consignan en el país que los aloja, que es "
        "también su país de origen.",
        (
            f"Serie desde {DESDE}. Sin registro en la fuente para {len(sin_dato)} "
            f"Estados del padrón: {', '.join(sin_dato)}."
        )
        if sin_dato
        else f"Serie desde {DESDE}. Los 33 Estados del padrón tienen registro.",
    ]
    if sin_codigo:
        vacios.append(
            f"{len(sin_codigo)} Estados del padrón no figuran en el nomenclador de "
            f"la fuente y no pudieron consultarse: {', '.join(sin_codigo)}."
        )

    comun.escribir(
        colector="desplazamiento-serie",
        capa="suscriptor",
        fuente=FUENTE,
        url_fuente=URL_PUBLICA,
        calificacion=calificacion,
        registros=serie_completa,
        vacios=vacios + [
            "Esta serie es la capa de suscriptor. No es material reservado: el "
            "repositorio es público (doctrina/siwa.md §2.2)."
        ],
    )

    return comun.escribir(
        colector="desplazamiento",
        capa="publico",
        fuente=FUENTE,
        url_fuente=URL_PUBLICA,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={"serie_disponible_desde": DESDE, "anio_de_la_cifra": anio_del_dato},
    )


if __name__ == "__main__":
    comun.correr("desplazamiento", recolectar)
