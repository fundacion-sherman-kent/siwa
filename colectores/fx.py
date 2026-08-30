"""Tipos de cambio contra el dólar — Banco Central Europeo, vía Frankfurter.

Fuente: api.frankfurter.app, que redistribuye las referencias diarias del BCE.

Este colector existe además como demostración de la regla de vacíos: el BCE
publica muy pocas monedas de la región, y el archivo resultante declara
explícitamente cuáles del padrón no están cubiertas en vez de omitirlas
(`doctrina/tabularium.md` §1, regla 7 de la casa).
"""

from __future__ import annotations

import comun

FUENTE = "Banco Central Europeo — referencias diarias, vía Frankfurter"
URL_MONEDAS = "https://api.frankfurter.app/currencies"
URL_ULTIMO = "https://api.frankfurter.app/latest?from=USD"

# Monedas de curso legal en los 33 Estados del padrón (fuentes/paises.md).
MONEDAS_PADRON = {
    "ARS": "Argentina",
    "BOB": "Bolivia",
    "BRL": "Brasil",
    "BSD": "Bahamas",
    "BBD": "Barbados",
    "BZD": "Belice",
    "CLP": "Chile",
    "COP": "Colombia",
    "CRC": "Costa Rica",
    "CUP": "Cuba",
    "DOP": "República Dominicana",
    "GTQ": "Guatemala",
    "GYD": "Guyana",
    "HTG": "Haití",
    "HNL": "Honduras",
    "JMD": "Jamaica",
    "MXN": "México",
    "NIO": "Nicaragua",
    "PAB": "Panamá",
    "PEN": "Perú",
    "PYG": "Paraguay",
    "SRD": "Surinam",
    "TTD": "Trinidad y Tobago",
    "UYU": "Uruguay",
    "VES": "Venezuela",
    "XCD": "Caribe oriental (unión monetaria)",
}


def recolectar():
    catalogo = comun.pedir(URL_MONEDAS)
    ultimo = comun.pedir(URL_ULTIMO)

    if ultimo.get("base") != "USD":
        raise RuntimeError(
            f"La fuente devolvió base {ultimo.get('base')!r} en lugar de 'USD'. "
            "No se escribe nada hasta revisar el pedido."
        )

    tasas = ultimo.get("rates", {})
    fecha_referencia = ultimo.get("date")

    registros = []
    for codigo, pais in sorted(MONEDAS_PADRON.items()):
        if codigo in tasas:
            registros.append(
                {
                    "moneda": codigo,
                    "nombre": catalogo.get(codigo),
                    "ambito": pais,
                    "unidades_por_dolar": tasas[codigo],
                    "fecha_referencia": fecha_referencia,
                }
            )

    faltantes = sorted(set(MONEDAS_PADRON) - set(tasas))

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=(
            "Referencia oficial de banco central. Fuente única: la segunda fuente "
            "exigiría el banco central de cada país, todavía no incorporado. "
            "Declarado conforme a doctrina/fuentes.md §2 ter."
        ),
    )

    vacios = [
        "El BCE publica referencias solo de un subconjunto de monedas del mundo.",
        (
            f"Sin cobertura para {len(faltantes)} de las {len(MONEDAS_PADRON)} monedas "
            f"del padrón: {', '.join(faltantes)}."
        ),
        "La referencia del BCE no refleja mercados paralelos ni tipos de cambio "
        "múltiples, que en varios Estados del padrón son el precio efectivo.",
    ]

    return comun.escribir(
        colector="fx",
        capa="publico",
        fuente=FUENTE,
        url_fuente=URL_ULTIMO,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
    )


if __name__ == "__main__":
    comun.correr("fx", recolectar)
