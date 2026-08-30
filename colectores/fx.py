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
    "ARS": ("Argentina", ["ARG"]),
    "BOB": ("Bolivia", ["BOL"]),
    "BRL": ("Brasil", ["BRA"]),
    "BSD": ("Bahamas", ["BHS"]),
    "BBD": ("Barbados", ["BRB"]),
    "BZD": ("Belice", ["BLZ"]),
    "CLP": ("Chile", ["CHL"]),
    "COP": ("Colombia", ["COL"]),
    "CRC": ("Costa Rica", ["CRI"]),
    "CUP": ("Cuba", ["CUB"]),
    "DOP": ("República Dominicana", ["DOM"]),
    "GTQ": ("Guatemala", ["GTM"]),
    "GYD": ("Guyana", ["GUY"]),
    "HTG": ("Haití", ["HTI"]),
    "HNL": ("Honduras", ["HND"]),
    "JMD": ("Jamaica", ["JAM"]),
    "MXN": ("México", ["MEX"]),
    "NIO": ("Nicaragua", ["NIC"]),
    "PAB": ("Panamá", ["PAN"]),
    "PEN": ("Perú", ["PER"]),
    "PYG": ("Paraguay", ["PRY"]),
    "SRD": ("Surinam", ["SUR"]),
    "TTD": ("Trinidad y Tobago", ["TTO"]),
    "UYU": ("Uruguay", ["URY"]),
    "VES": ("Venezuela", ["VEN"]),
    # Unión monetaria del Caribe oriental: una moneda, seis Estados del padrón.
    "XCD": ("Caribe oriental", ["ATG", "DMA", "GRD", "KNA", "VCT", "LCA"]),
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
    for codigo, (ambito, isos) in sorted(MONEDAS_PADRON.items()):
        if codigo in tasas:
            registros.append(
                {
                    "moneda": codigo,
                    "nombre": catalogo.get(codigo),
                    "ambito": ambito,
                    "isos": isos,
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
