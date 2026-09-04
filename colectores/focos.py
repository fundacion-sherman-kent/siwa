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

POR QUÉ SE REESCRIBIÓ, Y LA LECCIÓN ES LA DE SIEMPRE
-----------------------------------------------------
La primera versión pedía los focos **país por país**, contra una dirección que
no existe. El robot devolvía `HTTP 400 · Invalid API call.` y se detenía. Era
fácil culpar a la credencial recién cargada.

Se probó con una clave **deliberadamente falsa**: contra el recuadro geográfico
la fuente contestó *«Invalid MAP_KEY»* —ruta correcta, clave mala— y contra el
país, *«Invalid API call»* —la ruta no existe, con clave o sin ella—. La clave
estaba bien desde el principio. **El instrumento falló antes que la fuente.**

Esta fuente **no tiene consulta por país**: solo por recuadro. Así que se pide
una vez el recuadro entero de América Latina y el Caribe y se atribuye cada
detección a su Estado con `geo.pais_de`, que existe para exactamente esto. Sale
más barato —una consulta en lugar de treinta y tres— y usa lo que ya estaba.
"""

from __future__ import annotations

import csv
import io
import os
import sys
import time
import urllib.error
import urllib.request
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
DIAS = 3          # la ventana; la interfaz admite de uno a cinco días
# El recuadro de América Latina y el Caribe, en el orden que pide la fuente:
# oeste, sur, este, norte. Va holgado a propósito: recortar de menos deja focos
# afuera, y recortar de más solo cuesta unos puntos que caen fuera del padrón.
RECUADRO = "-118,-56,-34,33"
# Brasil tiene focos TODOS los dias del anio. Si el control da cero, el que
# fallo es el instrumento, no el mundo.
CONTROL = "BRA"
# Si la respuesta llega justo en el tope, es que se cortó: publicar la mitad de
# los focos como si fueran todos sería peor que no publicar ninguno.
TOPE_LECTURA = 80_000_000
# Un parpadeo de red del servidor que corre el robot no es una respuesta de la
# fuente: se reintenta. Si igual falla, se detiene la corrida; nunca se anota cero.
# Tres intentos en veinticuatro segundos NO alcanzaron: volvio a fallar dos veces
# despues de ponerlos. Se estira la espera, que es gratis en una tarea horaria.
INTENTOS = 4
ESPERA_ENTRE_INTENTOS = 10  # segundos, y crece con cada intento


def _pedir(clave: str, dias: int) -> list:
    """Una sola consulta: el recuadro entero. La fuente NO admite pedir por país.

    Se reintenta ante fallas de RED, no ante rechazos de la fuente. Un «Network is
    unreachable» del servidor que corre el robot es un parpadeo y se pasa solo; un
    HTTP 400 es una respuesta, y repetirla da lo mismo dos veces.

    El reintento NO afloja la regla: si los tres intentos fallan, la corrida se
    detiene igual. Lo que no se hace nunca es tapar la falla con un cero.
    """
    url = f"{BASE}/area/csv/{clave}/{SENSOR}/{RECUADRO}/{dias}"
    ultima = None
    for numero in range(INTENTOS):
        try:
            peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
            with urllib.request.urlopen(peticion, timeout=180) as respuesta:
                crudo = respuesta.read(TOPE_LECTURA)
            break
        except urllib.error.HTTPError as error:
            cuerpo = error.read(400).decode("utf-8", "replace").strip()
            raise RuntimeError(
                f"La fuente rechazó la consulta: HTTP {error.code} · {cuerpo}. "
                "NO se anota cero: no poder mirar no es haber mirado. Si dice «Invalid "
                "MAP_KEY» el problema es la credencial; si dice «Invalid API call», la "
                "dirección.") from error
        except Exception as error:  # noqa: BLE001 — falla de red: se reintenta
            ultima = error
            print(f"[focos] intento {numero + 1} de {INTENTOS}: {type(error).__name__}: "
                  f"{error}", file=sys.stderr)
            time.sleep(ESPERA_ENTRE_INTENTOS * (numero + 1))
    else:
        raise RuntimeError(
            f"No se pudo llegar a la fuente en {INTENTOS} intentos: "
            f"{type(ultima).__name__}: {ultima}. Es una falla de RED, no una respuesta "
            "de la fuente. NO se anota cero: no poder mirar no es haber mirado.")

    if len(crudo) >= TOPE_LECTURA:
        raise RuntimeError(
            f"La respuesta llegó al tope de lectura ({TOPE_LECTURA} bytes), así que "
            "está cortada. NO se publica una parte de los focos como si fueran todos.")

    texto = crudo.decode("utf-8", "replace").strip()
    if not texto or texto.lower().startswith("invalid"):
        raise RuntimeError(
            f"La fuente contestó «{texto[:120]}» en lugar de datos. NO se anota cero.")
    return list(csv.DictReader(io.StringIO(texto)))


def recolectar():
    clave = os.environ.get("NASA_FIRMS_MAP_KEY", "").strip()
    if not clave:
        print("[focos] sin clave: la variable NASA_FIRMS_MAP_KEY está vacía o no "
              "definida. El nombre tiene que coincidir exactamente.", file=sys.stderr)

    registros, conFoco, sinMirar = [], 0, 0
    instrumentoSano = None
    porIso: dict = {}
    fueraDelPadron = 0

    if clave:
        filas = _pedir(clave, DIAS)

        # Cada deteccion es un punto: se le pregunta al padron de que Estado es.
        for f in filas:
            try:
                lon, lat = float(f["longitude"]), float(f["latitude"])
            except (KeyError, TypeError, ValueError):
                continue
            pais = geo.pais_de(lon, lat)
            if not pais:
                fueraDelPadron += 1
                continue
            caja = porIso.setdefault(pais["iso"], {"total": 0, "alta": 0, "noche": 0})
            caja["total"] += 1
            confianza = str(f.get("confidence", "")).strip()
            if confianza.lower() in ("h", "high") or (
                    confianza.isdigit() and int(confianza) >= 80):
                caja["alta"] += 1
            if str(f.get("daynight", "")).upper() == "N":
                caja["noche"] += 1

        # SE PRUEBA EL INSTRUMENTO ANTES DE CREERLE UN CERO A NADIE. La brecha
        # publico cero en 33 Estados por un filtro mal escrito; aca no se repite.
        instrumentoSano = porIso.get(CONTROL, {}).get("total", 0) > 0
        if not instrumentoSano:
            raise RuntimeError(
                f"La prueba del instrumento falló: {CONTROL} —que tiene focos todos los "
                f"días del año— no quedó con ninguno tras atribuir {len(filas)} "
                f"detecciones del recuadro. Eso NO significa que no haya ardido nada: "
                "significa que la consulta, la clave o la atribución al padrón no "
                "sirven. NO se publica un cero que no se puede sostener.")

    for pais in geo.padron():
        caja = porIso.get(pais["iso"]) if clave else None
        if not clave:
            sinMirar += 1
            registros.append({
                "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
                "estado": "sin_clave", "focos": None,
            })
            continue
        # Con la consulta hecha y el instrumento probado, un Estado sin puntos SI
        # es un cero legitimo: se lo miro y no habia nada.
        caja = caja or {"total": 0, "alta": 0, "noche": 0}
        if caja["total"]:
            conFoco += 1
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": "con_focos" if caja["total"] else "sin_focos_en_la_ventana",
            "focos": caja["total"],
            "confianza_alta": caja["alta"],
            "nocturnos": caja["noche"],
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
        "LA FUENTE NO ADMITE CONSULTA POR PAIS: solo por recuadro geografico. Se pide "
        "una vez el recuadro de America Latina y el Caribe y se ATRIBUYE CADA DETECCION "
        "a su Estado por la coordenada. Un punto que cae en el mar, en un pais vecino "
        "fuera del padron o en aguas internacionales NO se cuenta, y se declara cuantos "
        "fueron.",
        "ANTES DE CREERLE UN CERO A NADIE SE PRUEBA EL INSTRUMENTO contra Brasil, que "
        "tiene focos todos los dias del anio. Si ESE da cero, la corrida se detiene "
        "entera en lugar de publicar treinta y tres ceros. La primera version de este "
        "colector pedia por pais contra una direccion QUE NO EXISTE, y era facil culpar "
        "a la credencial: se probo con una clave deliberadamente falsa y la fuente "
        "distinguio «clave invalida» de «direccion invalida». El instrumento habia "
        "fallado antes que la fuente.",
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
                "recuadro": RECUADRO,
                "ventana_dias": DIAS,
                "detecciones_fuera_del_padron": fueraDelPadron,
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
