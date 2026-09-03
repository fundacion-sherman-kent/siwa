"""Focos de calor: dónde está ardiendo algo, hoy.

POR QUÉ EXISTE, Y POR QUÉ ESTABA PROMETIDO
------------------------------------------
El README declaraba este colector **en servicio con calificación A-2** y no
existía: alguien lo planificó, cargó la credencial y anotó como hecho lo que
nunca se construyó. La clave llevaba días huérfana en el repositorio.

Se construye para que esa afirmación sea cierta, y de paso porque llena parte de
**economías ilícitas**: la quema es el rastro visible de la deforestación, de la
apertura de tierra y de la minería informal.

LO QUE DETECTA, Y ES MENOS DE LO QUE PARECE
-------------------------------------------
El satélite detecta **anomalías térmicas**, no incendios ni delitos. Un foco
puede ser una quema agrícola legal, un incendio forestal, una antorcha
industrial, un basural o una operación minera. **La imagen no distingue la causa,
y el registro tampoco va a inventarla.**

Por eso el foco entra como **señal fechada y ubicada**, nunca como indicador de
ilegalidad. Decir «tantos focos, tanta minería ilegal» sería exactamente la
clase de salto que este registro no da.

POR QUÉ NO ORDENA ESTADOS
-------------------------
El recuento depende del tamaño del país, de la estación del año, de la nubosidad
—una semana nublada esconde todo— y de cuántas veces pasó el satélite. Brasil
tendrá siempre más focos que Granada por superficie, no por conducta.

Se publica el recuento por Estado **como magnitud**, con la misma arquitectura
que Defensa y la medición de red: al lado del dato comparable, nunca adentro.
"""

from __future__ import annotations

import csv
import io
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import comun
import geo

BASE = "https://firms.modaps.eosdis.nasa.gov/api"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# El sensor de mayor resolución disponible sin costo.
SENSOR = "VIIRS_SNPP_NRT"
DIAS = 3          # la ventana; la interfaz admite hasta diez
# Brasil tiene focos TODOS los dias del anio. Si el control da cero, el que
# fallo es el instrumento, no el mundo.
CONTROL = "BRA"


def _pedir(clave: str, iso: str, dias: int) -> list | None:
    url = f"{BASE}/country/csv/{clave}/{SENSOR}/{iso}/{dias}"
    try:
        peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
        with urllib.request.urlopen(peticion, timeout=90) as respuesta:
            crudo = respuesta.read(20_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        cuerpo = error.read(400).decode("utf-8", "replace").strip()
        raise RuntimeError(
            f"La fuente rechazó la consulta de {iso}: HTTP {error.code} · {cuerpo}. "
            "NO se anota cero: no poder mirar no es haber mirado.") from error
    except Exception:  # noqa: BLE001 — la falla de un Estado no tumba la corrida
        return None

    texto = crudo.strip()
    if not texto or texto.lower().startswith("invalid"):
        return None
    filas = list(csv.DictReader(io.StringIO(texto)))
    return filas


def _delEstado(par: tuple) -> tuple:
    clave, iso = par
    try:
        filas = _pedir(clave, iso, DIAS)
    except RuntimeError:
        return iso, None
    return iso, filas


def recolectar():
    clave = os.environ.get("NASA_FIRMS_MAP_KEY", "").strip()
    if not clave:
        print("[focos] sin clave: la variable NASA_FIRMS_MAP_KEY está vacía o no "
              "definida. El nombre tiene que coincidir exactamente.", file=sys.stderr)

    registros, conFoco, sinMirar = [], 0, 0
    instrumentoSano = None

    if clave:
        # SE PRUEBA EL INSTRUMENTO ANTES DE CREERLE UN CERO A NADIE. La brecha
        # publico cero en 33 Estados por un filtro mal escrito; acá no se repite.
        control = _pedir(clave, CONTROL, DIAS)
        instrumentoSano = bool(control)
        if not instrumentoSano:
            raise RuntimeError(
                f"La prueba del instrumento falló: la consulta de control sobre {CONTROL} "
                f"—que tiene focos todos los días del año— no devolvió ninguno en "
                f"{DIAS} días. Eso NO significa que no haya ardido nada: significa que la "
                "consulta o la clave no sirven. NO se publica un cero que no se puede "
                "sostener.")

        pares = [(clave, p["iso"]) for p in geo.padron()]
        with ThreadPoolExecutor(max_workers=4) as ejecutor:
            hallado = dict(ejecutor.map(_delEstado, pares))
    else:
        hallado = {}

    for pais in geo.padron():
        filas = hallado.get(pais["iso"]) if clave else None
        if filas is None:
            sinMirar += 1
            registros.append({
                "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
                "estado": "sin_clave" if not clave else "no_se_pudo_mirar",
                "focos": None,
            })
            continue

        # La confianza la declara el propio sensor. Se cuenta aparte la alta,
        # porque un foco de confianza baja no sostiene ninguna afirmacion.
        alta = sum(1 for f in filas
                   if str(f.get("confidence", "")).lower() in ("h", "high")
                   or (str(f.get("confidence", "")).isdigit()
                       and int(f["confidence"]) >= 80))
        nocturnos = sum(1 for f in filas if str(f.get("daynight", "")).upper() == "N")
        if filas:
            conFoco += 1
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": "con_focos" if filas else "sin_focos_en_la_ventana",
            "focos": len(filas),
            "confianza_alta": alta,
            "nocturnos": nocturnos,
        })

    vacios = [
        "EL SATELITE DETECTA ANOMALIAS TERMICAS, NO INCENDIOS NI DELITOS. Un foco puede "
        "ser una quema agricola legal, un incendio forestal, una antorcha industrial, un "
        "basural o una operacion minera. LA IMAGEN NO DISTINGUE LA CAUSA, y el registro "
        "no la inventa: decir «tantos focos, tanta mineria ilegal» seria un salto que "
        "esta casa no da.",
        "NO ORDENA ESTADOS. El recuento depende del tamanio del pais, de la estacion, de "
        "la nubosidad —una semana nublada esconde todo— y de cuantas veces paso el "
        "satelite. Brasil tendra siempre mas focos que Granada por superficie, no por "
        "conducta. Se publica como MAGNITUD, al lado del dato comparable y nunca adentro.",
        f"LA VENTANA ES DE {DIAS} DIAS y se mueve con cada corrida: sirve para ver que "
        "esta ardiendo ahora, NO para comparar contra el mes pasado.",
        "LA CONFIANZA LA DECLARA EL SENSOR y se cuenta aparte: un foco de confianza baja "
        "no sostiene ninguna afirmacion. El recuento total incluye todos; el de confianza "
        "alta es el unico que se puede citar.",
        "ANTES DE CREERLE UN CERO A NADIE SE PRUEBA EL INSTRUMENTO contra Brasil, que "
        "tiene focos todos los dias del anio. Si ESE da cero, la corrida se detiene "
        "entera en lugar de publicar treinta y tres ceros.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Sistema de deteccion de la agencia espacial estadounidense, con sensor y "
              "metodo publicados. Fiabilidad A porque el productor opera el satelite. "
              "Credibilidad 2 porque se verifica LA DETECCION —hubo una anomalia termica "
              "en esa coordenada— y NO su causa, que el sensor no puede establecer."),
    )

    return comun.escribir(
        colector="focos",
        capa="publico",
        fuente="NASA FIRMS — focos de calor detectados por satélite",
        url_fuente="https://firms.modaps.eosdis.nasa.gov/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "con_clave": bool(clave),
                "instrumento_probado": instrumentoSano,
                "sensor": SENSOR,
                "ventana_dias": DIAS,
                "estados_con_focos": conFoco,
                "estados_sin_mirar": sinMirar,
                "estados_del_padron": len(registros),
                "focos_en_la_region": sum(r["focos"] or 0 for r in registros),
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("focos", recolectar)
