"""Violencia organizada — el Programa de Datos de Conflicto de Upsala (UCDP).

Cierra un vacío que el registro venía declarando desde el principio: **la
interfaz de UCDP devuelve 401 sin credencial**, y hasta ahora las muertes en
conflicto entraban sólo por Our World in Data, con la serie detenida donde ese
intermediario la corta. Con credencial se va a la fuente.

Qué se toma, y por qué esa tabla
--------------------------------
De las siete tablas que la interfaz expone, se usa **`organizedviolencecy`** —el
conjunto de país-año sobre violencia organizada dentro de las fronteras de cada
Estado—. No es la más grande ni la más detallada: es la **comparable**. Una fila
por Estado y por año, con la presencia declarada de los tres tipos de violencia
que UCDP distingue y que no significan lo mismo:

* **estatal** — el Estado es una de las partes. Se subdivide en interna
  (contra un grupo armado dentro del país) e interestatal (contra otro Estado).
* **no estatal** — entre grupos armados, **sin el Estado como parte**. En esta
  región es, en buena medida, disputa entre organizaciones criminales.
* **unilateral** — violencia deliberada de un actor armado contra civiles que no
  se defienden.

El conjunto georreferenciado de eventos (`gedevents`) tiene 417.968 filas y
obliga a paginar. Traerlo entero para contar muertes por país gastaría cientos
de peticiones diarias por un resultado que esta tabla ya entrega agregado. Si
alguna vez hace falta el detalle de un evento, ahí está.

El umbral, que cambia lo que estos ceros significan
---------------------------------------------------
**UCDP exige 25 muertes en un año para registrar un conflicto.** Un Estado con
violencia real pero por debajo de ese umbral aparece en cero. **El cero no dice
«no hay violencia»: dice «no alcanzó el umbral de UCDP».** Es la advertencia más
importante de esta capa y viaja con cada ficha.

La credencial
-------------
El token se lee de la variable de entorno `UCDP_TOKEN` y **nunca se escribe en
el archivo de datos, ni en el registro de la corrida, ni en un mensaje de
error**. Si no está, el colector lo dice y no publica ceros: treinta y tres
Estados «sin mirar» no son treinta y tres Estados en paz.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.request

import comun
import geo

BASE = "https://ucdpapi.pcr.uu.se/api"
RECURSO = "organizedviolencecy"
VERSION = "26.1"
FUENTE = ("UCDP — Programa de Datos de Conflicto de Upsala, Universidad de Upsala. "
          "Conjunto de país-año sobre violencia organizada dentro de las fronteras")
URL_FUENTE = "https://ucdp.uu.se/apidocs/"
NAVEGADOR = comun.AGENTE

VENTANA = 15             # años de serie que se publican por Estado
TAMANO_PAGINA = 1000
TOPE_PAGINAS = 400       # techo de seguridad; si la tabla lo supera, se avisa
ESPERA = 90
INTENTOS = 3
DESCANSO = 8

# PROBAR ANTES DE AFIRMAR. Colombia tiene conflicto estatal registrado por UCDP
# desde hace decadas: si la lectura no lo encuentra, lo que fallo es la lectura
# —el nombre, la tabla o el filtro— y no la historia de Colombia.
CONTROL = "Colombia"
MINIMO_ESTADOS = 25

# Los nombres con que UCDP rotula a los Estados del padron. Se declaran acá para
# que un rótulo que cambie se vea como Estado sin correspondencia, y no como
# Estado en paz. La correspondencia se hace por nombre porque el codigo numerico
# de UCDP es el de Gleditsch y Ward, que NO es el ISO y no se adivina.
NOMBRES = {
    "Argentina": "ARG", "Bolivia": "BOL", "Brazil": "BRA", "Chile": "CHL",
    "Colombia": "COL", "Costa Rica": "CRI", "Cuba": "CUB",
    "Dominican Republic": "DOM", "Ecuador": "ECU", "El Salvador": "SLV",
    "Guatemala": "GTM", "Haiti": "HTI", "Honduras": "HND", "Mexico": "MEX",
    "Nicaragua": "NIC", "Panama": "PAN", "Paraguay": "PRY", "Peru": "PER",
    "Uruguay": "URY", "Venezuela": "VEN", "Belize": "BLZ", "Guyana": "GUY",
    "Suriname": "SUR", "Antigua and Barbuda": "ATG", "Bahamas": "BHS",
    "Barbados": "BRB", "Dominica": "DMA", "Grenada": "GRD", "Jamaica": "JAM",
    "Saint Kitts and Nevis": "KNA", "Saint Lucia": "LCA",
    "Saint Vincent and the Grenadines": "VCT", "Trinidad and Tobago": "TTO",
}

TIPOS = [
    {"campo": "sb_exist", "clave": "estatal", "rotulo": "Violencia estatal",
     "dice": "El Estado es una de las partes del conflicto armado."},
    {"campo": "sb_intrastate_exist", "clave": "estatal_interna",
     "rotulo": "Violencia estatal interna",
     "dice": "El Estado enfrenta a un grupo armado dentro de sus fronteras."},
    {"campo": "sb_interstate_exist", "clave": "estatal_interestatal",
     "rotulo": "Violencia estatal entre Estados",
     "dice": "El Estado enfrenta a otro Estado."},
    {"campo": "ns_exist", "clave": "no_estatal", "rotulo": "Violencia no estatal",
     "dice": "Entre grupos armados, sin el Estado como parte. En esta región es, "
             "en buena medida, disputa entre organizaciones criminales."},
    {"campo": "os_exist", "clave": "unilateral", "rotulo": "Violencia unilateral",
     "dice": "Violencia deliberada de un actor armado contra civiles que no se "
             "defienden."},
]
CAMPOS = [t["campo"] for t in TIPOS]


def _plano(texto: str) -> str:
    """Nombre sin tildes ni mayusculas, para que «Haiti» y «Haïti» se encuentren."""
    sin = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sin if not unicodedata.combining(c)).strip().lower()


def _pedir(token: str, pagina: int) -> dict:
    """Una página. El token va en la cabecera y NO en la dirección."""
    url = f"{BASE}/{RECURSO}/{VERSION}?pagesize={TAMANO_PAGINA}&page={pagina}"
    ultimo = ""
    for intento in range(INTENTOS):
        try:
            peticion = urllib.request.Request(url, headers={
                "User-Agent": NAVEGADOR,
                "Accept": "application/json",
                "x-ucdp-access-token": token})
            with urllib.request.urlopen(peticion, timeout=ESPERA,
                                        context=ssl.create_default_context()) as r:
                return json.loads(r.read(40_000_000).decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            # El 401 NO se reintenta: reintentar una credencial rechazada gasta
            # peticiones del tope diario sin ninguna posibilidad de éxito.
            if e.code == 401:
                raise RuntimeError(
                    "UCDP rechazó la credencial (401). El token es inválido, venció "
                    "o el secreto UCDP_TOKEN quedó mal cargado. NO se publica: "
                    "treinta y tres Estados en cero dirían que no hay violencia.") from e
            if e.code == 429:
                raise RuntimeError(
                    "UCDP contestó 429: se agotó el tope diario de peticiones. Se "
                    "vuelve a intentar en la próxima corrida; el dato anterior "
                    "queda intacto.") from e
            raise RuntimeError(f"UCDP respondió HTTP {e.code} en la página {pagina}") from e
        except Exception as e:  # noqa: BLE001 — falla de red: se reintenta
            ultimo = f"{type(e).__name__}: {e}"
            print(f"[ucdp] página {pagina}, intento {intento + 1} de {INTENTOS}: "
                  f"{ultimo}", file=sys.stderr)
            time.sleep(DESCANSO * (intento + 1))
    raise RuntimeError(f"La página {pagina} no llegó en {INTENTOS} intentos: {ultimo}")


def _bandera(fila: dict, campo: str) -> bool:
    valor = fila.get(campo)
    if valor in (None, "", "NA"):
        return False
    try:
        return int(valor) == 1
    except (TypeError, ValueError):
        return str(valor).strip().lower() in ("true", "yes", "1")


def recolectar():
    token = os.environ.get("UCDP_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Sin credencial: la variable UCDP_TOKEN está vacía o no definida. El "
            "nombre tiene que coincidir exactamente. NO se publica una tabla de "
            "ceros: treinta y tres Estados sin mirar no son treinta y tres Estados "
            "en paz.")

    filas, pagina = [], 1
    total_paginas = total_filas = None
    while pagina <= TOPE_PAGINAS:
        cuerpo = _pedir(token, pagina)
        if not isinstance(cuerpo, dict) or "Result" not in cuerpo:
            raise RuntimeError(
                "La respuesta no tiene la forma documentada —un objeto con «Result»—. "
                "La interfaz cambió y no se publica una lectura a ciegas.")
        if total_paginas is None:
            total_paginas = int(cuerpo.get("TotalPages") or 1)
            total_filas = cuerpo.get("TotalCount")
            # UNA LECTURA CORTADA SIN AVISO ES PEOR QUE UNA QUE FALLA. Si la tabla
            # tiene mas paginas que el tope, faltarian Estados enteros y nadie se
            # enteraria: los que caigan en las paginas no leidas apareceran en cero.
            if total_paginas > TOPE_PAGINAS:
                raise RuntimeError(
                    f"La tabla tiene {total_paginas} páginas y el tope de este colector "
                    f"es {TOPE_PAGINAS}: la lectura vendría cortada y los Estados de las "
                    "páginas no leídas aparecerían en cero sin que nadie lo note. Hay "
                    "que subir el tope, no publicar así.")
        filas.extend(cuerpo.get("Result") or [])
        if pagina >= total_paginas:
            break
        pagina += 1

    if not filas:
        raise RuntimeError("UCDP contestó sin filas. No se publica.")

    # SE LEYO TODO, O NO SE PUBLICA. La respuesta declara cuantas filas tiene la
    # tabla; si llegaron menos, la lectura vino cortada —el servidor puede
    # entregar menos por pagina de lo que se le pide, sin avisar— y los Estados
    # que caen en lo no leido apareceran en cero. Un cero por lectura corta es
    # indistinguible de un cero real, y por eso no se publica ninguno de los dos.
    if isinstance(total_filas, int) and len(filas) < total_filas:
        raise RuntimeError(
            f"Llegaron {len(filas)} filas y la fuente declara {total_filas} en "
            f"{total_paginas} páginas: la lectura vino CORTADA. El servidor entregó "
            f"menos de las {TAMANO_PAGINA} filas por página que se le pidieron. Los "
            "Estados de las filas no leídas aparecerían en cero, y un cero por lectura "
            "corta no se distingue de un cero real. No se publica.")
    faltantes = [c for c in CAMPOS + ["country", "year"] if c not in filas[0]]
    if faltantes:
        raise RuntimeError(
            f"A la tabla le faltan campos documentados: {faltantes}. Cambió de forma "
            "y no se publica una lectura armada con otros campos.")

    porNombre = {_plano(n): iso for n, iso in NOMBRES.items()}
    porIso: dict = {}
    vistos = set()
    for fila in filas:
        nombre = str(fila.get("country") or "")
        vistos.add(nombre)
        iso = porNombre.get(_plano(nombre))
        if not iso:
            continue
        try:
            anio = int(fila.get("year"))
        except (TypeError, ValueError):
            continue
        marca = {t["clave"]: _bandera(fila, t["campo"]) for t in TIPOS}
        ficha = porIso.setdefault(iso, {"nombre_en_la_fuente": nombre, "serie": []})
        ficha["serie"].append({"anio": anio, **marca})

    # PROBAR ANTES DE AFIRMAR: sin el control, lo que falló es la lectura.
    #
    # Y cuando falla, el colector CUENTA QUE VIO. La credencial vive en el
    # repositorio y no se puede consultar la fuente desde afuera para averiguarlo:
    # si el mensaje dijera solo «falló», no habría manera de arreglarlo. Así que
    # el diagnóstico viaja en el propio mensaje, que queda en el archivo de estado.
    control_iso = NOMBRES.get(CONTROL)
    controlado = porIso.get(control_iso)
    if not controlado or not any(a["estatal"] for a in controlado["serie"]):
        parecidos = sorted(n for n in vistos if "colomb" in _plano(n))
        muestra = sorted(vistos)[:14]
        campos = sorted(filas[0]) if filas else []
        detalle = ""
        if parecidos:
            filas_control = [f for f in filas if str(f.get("country")) in parecidos]
            anios_vistos = sorted({str(f.get("year")) for f in filas_control})[-6:]
            crudos = [{c: f.get(c) for c in CAMPOS + ["year"]}
                      for f in filas_control[:3]]
            detalle = (f" El nombre SÍ está en la tabla como {parecidos}, con "
                       f"{len(filas_control)} filas y años {anios_vistos}. Las banderas "
                       f"crudas de las primeras filas son {crudos}.")
        else:
            detalle = (" El nombre NO aparece en la tabla: ningún rótulo contiene "
                       "«colomb».")
        raise RuntimeError(
            f"El control ({CONTROL}) no aparece con violencia estatal en ningún año de "
            f"la serie. Eso no describe a Colombia: describe una lectura fallida. "
            f"DIAGNÓSTICO: se leyeron {len(filas)} filas en {pagina} de "
            f"{total_paginas} páginas (la fuente declara {total_filas} filas); "
            f"{len(vistos)} rótulos de país distintos; {len(porIso)} Estados del padrón "
            f"con correspondencia.{detalle} Los campos de la primera fila son {campos}. "
            f"Una muestra de rótulos: {muestra}. No se publica."
        )
    if len(porIso) < MINIMO_ESTADOS:
        raise RuntimeError(
            f"Sólo {len(porIso)} de los 33 Estados encontraron correspondencia de "
            f"nombre, y se esperaban al menos {MINIMO_ESTADOS}. Los rótulos de UCDP "
            "cambiaron y publicar así dejaría Estados en cero por un problema de "
            "nombres. No se publica.")

    anios = {a["anio"] for f in porIso.values() for a in f["serie"]}
    ultimo = max(anios)

    registros = []
    for pais in geo.padron():
        ficha = porIso.get(pais["iso"])
        registro = {"iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
                    "en_la_fuente": bool(ficha)}
        if ficha:
            serie = sorted(ficha["serie"], key=lambda a: a["anio"])
            delAnio = next((a for a in serie if a["anio"] == ultimo), None)
            registro.update({
                "nombre_en_la_fuente": ficha["nombre_en_la_fuente"],
                "anio": ultimo,
                "serie": serie[-VENTANA:],
                **({t["clave"]: delAnio[t["clave"]] for t in TIPOS} if delAnio
                   else {t["clave"]: False for t in TIPOS}),
                "sin_fila_del_ultimo_anio": delAnio is None,
                "tipos_activos": ([t["rotulo"] for t in TIPOS
                                   if delAnio and delAnio[t["clave"]]] if delAnio else []),
            })
        else:
            registro["por_que_no"] = (
                "Ningún rótulo de UCDP corresponde a este Estado en la tabla leída.")
        registros.append(registro)
    registros.sort(key=lambda r: (not r["en_la_fuente"],
                                  -len(r.get("tipos_activos") or []), r["pais"]))

    conteo = {}
    for t in TIPOS:
        conteo[t["rotulo"]] = sum(1 for r in registros if r.get(t["clave"]))
    sin_correspondencia = [r["pais"] for r in registros if not r["en_la_fuente"]]

    vacios = [
        "**UCDP exige 25 muertes en un año para registrar un conflicto.** Un Estado "
        "con violencia real por debajo de ese umbral aparece en cero. **El cero no "
        "dice «no hay violencia»: dice «no alcanzó el umbral de UCDP».** Es la "
        "advertencia más importante de esta capa: buena parte de la violencia de la "
        "región —homicidio común, extorsión, violencia intrafamiliar— nunca entra acá "
        "porque no es conflicto armado organizado.",
        "**Los tres tipos no significan lo mismo y no se suman.** La violencia estatal "
        "tiene al Estado como parte; la no estatal ocurre entre grupos armados sin el "
        "Estado; la unilateral es contra civiles que no se defienden. Un Estado puede "
        "tener las tres, una o ninguna, y contarlas juntas produce un número que no "
        "quiere decir nada.",
        "**Presencia, no intensidad.** Esta tabla dice si hubo, no cuánto. Dos Estados "
        "marcados con violencia no estatal pueden estar a un orden de magnitud de "
        "distancia. Para la intensidad hay que ir al conjunto georreferenciado de "
        "eventos, que este colector no trae.",
        f"El conjunto llega hasta {ultimo} y **el año más reciente no es el año en "
        "curso**: UCDP cierra el año calendario y publica meses después. Lo que pasó "
        "este año todavía no está.",
        "La correspondencia entre los rótulos de UCDP y el padrón se hace **por "
        "nombre**, porque el código numérico de UCDP es el de Gleditsch y Ward y no es "
        "el ISO. Cada ficha publica el nombre con el que figura en la fuente, y un "
        "Estado sin correspondencia aparece declarado como tal —no como Estado en paz—.",
    ]
    if sin_correspondencia:
        vacios.append(
            f"**{len(sin_correspondencia)} Estados no encontraron correspondencia de "
            f"nombre**: {', '.join(sin_correspondencia)}. No es que no tengan dato: es "
            "que el rótulo no coincide y hay que revisarlo.")

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Programa académico de la Universidad de Upsala, la referencia establecida "
              "en datos de conflicto armado, con codebook publicado y versionado. Lo que "
              "se registra es la presencia que el proyecto codificó bajo su propio "
              "umbral, no la violencia que hubo."),
    )

    return comun.escribir(
        colector="ucdp",
        capa="publico",
        fuente=FUENTE,
        url_fuente=URL_FUENTE,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "anio": ultimo,
                "version": VERSION,
                "estados_en_la_fuente": len(porIso),
                "estados_del_padron": len(registros),
                "filas_leidas": len(filas),
                "paginas": pagina,
                "por_tipo": conteo,
                "consultado": comun.ahora(),
            },
            "tipos": [{"clave": t["clave"], "rotulo": t["rotulo"], "dice": t["dice"]}
                      for t in TIPOS],
            "umbral": ("UCDP registra un conflicto a partir de 25 muertes relacionadas "
                       "en un año calendario."),
        },
    )


if __name__ == "__main__":
    comun.correr("ucdp", recolectar)
