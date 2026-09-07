"""Violencia organizada — el Programa de Datos de Conflicto de Upsala (UCDP).

Cierra un vacío que el registro venía declarando desde el principio: las muertes
en conflicto entraban sólo por Our World in Data, con la serie detenida donde ese
intermediario la corta.

Por qué el archivo y no la interfaz con credencial
--------------------------------------------------
UCDP expone una interfaz que **exige credencial**, y la Fundación la gestionó y
la tiene. Pero **el mismo conjunto se descarga como archivo, sin credencial y sin
tope diario de consultas**, y esa puerta es mejor por tres razones: no depende de
un secreto, no gasta cuota, y **se puede probar antes de publicar**. La
credencial queda para lo que el archivo no da: consultas filtradas del conjunto
georreferenciado, evento por evento.

Qué se toma
-----------
El conjunto de **país-año sobre violencia organizada dentro de las fronteras**:
una fila por Estado y por año, desde 1989. De ahí salen dos cosas distintas que
no hay que confundir.

**Qué tipo de violencia hubo**, en las categorías que UCDP distingue y que no
significan lo mismo ni se suman:

* **estatal** — el Estado es una de las partes. Se subdivide en interna (contra
  un grupo armado dentro del país) e interestatal (contra otro Estado).
* **no estatal** — entre grupos armados, **sin el Estado como parte**. En esta
  región es, en buena medida, disputa entre organizaciones criminales.
* **unilateral** — violencia deliberada de un actor armado contra civiles que no
  se defienden.

**Y cuánta.** Las muertes que UCDP contabiliza, con su **estimación baja, mejor y
alta**: el proyecto no publica un número sino un rango, y quedarse con el del
medio escondería lo que el propio productor declara no saber.

El umbral, que cambia lo que significa un cero
----------------------------------------------
**UCDP exige 25 muertes en un año para registrar un conflicto.** Un Estado con
violencia real por debajo de ese umbral aparece en cero. **El cero no dice «no
hay violencia»: dice «no alcanzó el umbral de UCDP».** Buena parte de la
violencia de la región —homicidio común, extorsión, violencia intrafamiliar—
nunca entra acá porque no es conflicto armado organizado.
"""

from __future__ import annotations

import csv
import io
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile

import comun
import geo

URL = ("https://ucdp.uu.se/downloads/organizedviolencecy/"
       "organizedviolencecy-261-csv.zip")
VERSION = "26.1"
FUENTE = ("UCDP — Programa de Datos de Conflicto de Upsala, Universidad de Upsala. "
          "Conjunto de país-año sobre violencia organizada dentro de las fronteras")
URL_FUENTE = "https://ucdp.uu.se/downloads/"
NAVEGADOR = comun.AGENTE

VENTANA = 15             # años de serie que se publican por Estado
ESPERA = 180
INTENTOS = 3
DESCANSO = 8

# PROBAR ANTES DE AFIRMAR. Colombia tiene violencia estatal registrada por UCDP
# desde hace decadas: si la lectura no la encuentra, lo que fallo es la lectura
# —la tabla, el rotulo del pais o el campo— y no la historia de Colombia.
CONTROL = "Colombia"
MINIMO_ESTADOS = 25
MINIMO_FILAS = 5000      # el archivo verificado trae 7.132

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
    {"clave": "estatal", "rotulo": "Violencia estatal", "existe": "sb_exist",
     "mejor": "sb_total_deaths_best", "baja": "sb_total_deaths_low",
     "alta": "sb_total_deaths_high", "partes": "sb_dyad_names",
     "dice": "El Estado es una de las partes del conflicto armado."},
    {"clave": "estatal_interna", "rotulo": "Violencia estatal interna",
     "existe": "sb_intrastate_exist", "mejor": "sb_intrastate_deaths_best",
     "baja": "sb_intrastate_deaths_low", "alta": "sb_intrastate_deaths_high",
     "partes": "sb_intrastate_dyad_names",
     "dice": "El Estado enfrenta a un grupo armado dentro de sus fronteras."},
    {"clave": "estatal_interestatal", "rotulo": "Violencia estatal entre Estados",
     "existe": "sb_interstate_exist", "mejor": "sb_interstate_deaths_best",
     "baja": "sb_interstate_deaths_low", "alta": "sb_interstate_deaths_high",
     "partes": "sb_interstate_dyad_names",
     "dice": "El Estado enfrenta a otro Estado."},
    {"clave": "no_estatal", "rotulo": "Violencia no estatal", "existe": "ns_exist",
     "mejor": "ns_total_deaths_best", "baja": "ns_total_deaths_low",
     "alta": "ns_total_deaths_high", "partes": "ns_dyad_names",
     "dice": "Entre grupos armados, sin el Estado como parte. En esta región es, "
             "en buena medida, disputa entre organizaciones criminales."},
    {"clave": "unilateral", "rotulo": "Violencia unilateral", "existe": "os_exist",
     "mejor": "os_total_deaths_best", "baja": "os_total_deaths_low",
     "alta": "os_total_deaths_high", "partes": "os_dyad_names",
     "dice": "Violencia deliberada de un actor armado contra civiles que no se "
             "defienden."},
]
TOTAL_MEJOR = "cumulative_total_deaths_in_orgvio_best"
TOTAL_BAJA = "cumulative_total_deaths_in_orgvio_low"
TOTAL_ALTA = "cumulative_total_deaths_in_orgvio_high"
OBLIGATORIOS = ["country", "year"] + [t["existe"] for t in TIPOS] + [TOTAL_MEJOR]


def _plano(texto: str) -> str:
    """Nombre sin tildes ni mayúsculas, para que «Haiti» y «Haïti» se encuentren."""
    sin = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sin if not unicodedata.combining(c)).strip().lower()


def _entero(valor):
    try:
        return int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return None


def _si(valor) -> bool:
    return _entero(valor) == 1


def _bajar() -> bytes:
    ultimo = ""
    for intento in range(INTENTOS):
        try:
            peticion = urllib.request.Request(URL, headers={
                "User-Agent": NAVEGADOR, "Accept": "application/zip"})
            with urllib.request.urlopen(peticion, timeout=ESPERA,
                                        context=ssl.create_default_context()) as r:
                return r.read(60_000_000)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"UCDP respondió HTTP {e.code} al pedir el archivo") from e
        except Exception as e:  # noqa: BLE001 — falla de red: se reintenta
            ultimo = f"{type(e).__name__}: {e}"
            print(f"[ucdp] intento {intento + 1} de {INTENTOS}: {ultimo}", file=sys.stderr)
            time.sleep(DESCANSO * (intento + 1))
    raise RuntimeError(f"El archivo no llegó en {INTENTOS} intentos: {ultimo}")


def recolectar():
    z = zipfile.ZipFile(io.BytesIO(_bajar()))
    csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if not csvs:
        raise RuntimeError(f"El archivo no trae ningún CSV: {z.namelist()}")
    lector = csv.DictReader(io.StringIO(z.read(csvs[0]).decode("utf-8-sig", "replace")))
    filas = list(lector)

    if len(filas) < MINIMO_FILAS:
        raise RuntimeError(
            f"El conjunto trae {len(filas)} filas y se esperaban al menos "
            f"{MINIMO_FILAS}. Vino cortado o cambió de contenido: no se publica.")
    faltantes = [c for c in OBLIGATORIOS if c not in (lector.fieldnames or [])]
    if faltantes:
        raise RuntimeError(
            f"Al conjunto le faltan columnas documentadas: {faltantes}. Cambió de "
            "forma y no se publica una lectura armada con otras columnas.")

    porNombre = {_plano(n): iso for n, iso in NOMBRES.items()}
    porIso: dict = {}
    for fila in filas:
        iso = porNombre.get(_plano(str(fila.get("country") or "")))
        anio = _entero(fila.get("year"))
        if not iso or anio is None:
            continue
        porIso.setdefault(iso, {"nombre_en_la_fuente": str(fila["country"]).strip(),
                                "filas": {}})["filas"][anio] = fila

    # PROBAR ANTES DE AFIRMAR: sin el control, lo que falló es la lectura.
    controlado = porIso.get(NOMBRES[CONTROL])
    if not controlado or not any(_si(f.get("sb_exist"))
                                 for f in controlado["filas"].values()):
        raise RuntimeError(
            f"El control ({CONTROL}) no aparece con violencia estatal en ningún año de "
            f"la serie. Eso no describe a Colombia: describe una lectura fallida. Se "
            f"leyeron {len(filas)} filas y {len(porIso)} Estados del padrón. "
            "No se publica.")
    if len(porIso) < MINIMO_ESTADOS:
        raise RuntimeError(
            f"Sólo {len(porIso)} de los 33 Estados encontraron correspondencia de "
            f"nombre, y se esperaban al menos {MINIMO_ESTADOS}. Los rótulos de UCDP "
            "cambiaron y publicar así dejaría Estados en cero por un problema de "
            "nombres. No se publica.")

    ultimo = max(a for f in porIso.values() for a in f["filas"])

    registros = []
    for pais in geo.padron():
        ficha = porIso.get(pais["iso"])
        registro = {"iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
                    "en_la_fuente": bool(ficha)}
        if not ficha:
            registro["por_que_no"] = (
                "UCDP no incluye a este Estado en el conjunto: no dice nada sobre su "
                "situación.")
            registros.append(registro)
            continue

        fila = ficha["filas"].get(ultimo)
        registro["nombre_en_la_fuente"] = ficha["nombre_en_la_fuente"]
        registro["anio"] = ultimo
        registro["sin_fila_del_ultimo_anio"] = fila is None
        activos = []
        for tipo in TIPOS:
            hay = bool(fila) and _si(fila.get(tipo["existe"]))
            registro[tipo["clave"]] = hay
            if hay:
                # El separador es el PUNTO Y COMA. Partir por coma cortaria los
                # nombres que la llevan adentro y pegaria dos grupos en uno.
                partes = [p.strip() for p in
                          str(fila.get(tipo["partes"]) or "").split(";") if p.strip()]
                activos.append({
                    "clave": tipo["clave"], "rotulo": tipo["rotulo"],
                    "dice": tipo["dice"],
                    "muertes": _entero(fila.get(tipo["mejor"])),
                    "muertes_baja": _entero(fila.get(tipo["baja"])),
                    "muertes_alta": _entero(fila.get(tipo["alta"])),
                    "partes": partes[:6],
                    "partes_total": len(partes),
                })
        registro["tipos_activos"] = activos
        registro["muertes"] = _entero(fila.get(TOTAL_MEJOR)) if fila else None
        registro["muertes_baja"] = _entero(fila.get(TOTAL_BAJA)) if fila else None
        registro["muertes_alta"] = _entero(fila.get(TOTAL_ALTA)) if fila else None

        serie = []
        for anio in sorted(ficha["filas"])[-VENTANA:]:
            f = ficha["filas"][anio]
            serie.append({"anio": anio,
                          "muertes": _entero(f.get(TOTAL_MEJOR)),
                          **{t["clave"]: _si(f.get(t["existe"])) for t in TIPOS}})
        registro["serie"] = serie
        registros.append(registro)

    registros.sort(key=lambda r: (not r["en_la_fuente"], -(r.get("muertes") or 0),
                                  -len(r.get("tipos_activos") or []), r["pais"]))

    conteo = {t["rotulo"]: sum(1 for r in registros if r.get(t["clave"]))
              for t in TIPOS}
    con_muertes = [r for r in registros if (r.get("muertes") or 0) > 0]
    sin_correspondencia = [r["pais"] for r in registros if not r["en_la_fuente"]]

    vacios = [
        "**UCDP exige 25 muertes relacionadas en un año para registrar un conflicto.** "
        "Un Estado con violencia real por debajo de ese umbral aparece en cero. **El "
        "cero no dice «no hay violencia»: dice «no alcanzó el umbral de UCDP».** Buena "
        "parte de la violencia de la región —homicidio común, extorsión, violencia "
        "intrafamiliar— nunca entra acá porque no es conflicto armado organizado.",
        "**Los tres tipos no significan lo mismo y no se suman entre sí.** La violencia "
        "estatal tiene al Estado como parte; la no estatal ocurre entre grupos armados "
        "sin el Estado; la unilateral es contra civiles que no se defienden. Un Estado "
        "puede tener las tres, una o ninguna.",
        "**Las muertes son un rango, no un número.** UCDP publica una estimación baja, "
        "una mejor y una alta, y acá se publican las tres. Quedarse con la del medio "
        "escondería lo que el propio productor declara no saber: cuando la baja y la "
        "alta están lejos, la cifra del medio no sostiene una comparación fina.",
        f"El conjunto llega hasta {ultimo} y **el año más reciente no es el año en "
        "curso**: UCDP cierra el año calendario y publica meses después. Lo que pasó "
        "este año todavía no está.",
        "**Los nombres de las partes en conflicto son los que asigna UCDP**, no una "
        "caracterización de la Fundación. Que un grupo figure como parte de un "
        "conflicto armado no es un juicio sobre su naturaleza jurídica ni política.",
        "La correspondencia entre los rótulos de UCDP y el padrón se hace **por "
        "nombre**, porque el código numérico de UCDP es el de Gleditsch y Ward y no es "
        "el ISO. Cada ficha publica el nombre con el que figura en la fuente.",
        "**Se toma el archivo publicado y no la interfaz con credencial.** El mismo "
        "conjunto está en las dos puertas; la del archivo no depende de un secreto, no "
        "gasta cuota diaria y se puede verificar antes de publicar.",
    ]
    if sin_correspondencia:
        vacios.append(
            f"**{len(sin_correspondencia)} Estados no están en el conjunto**: "
            f"{', '.join(sin_correspondencia)}. No es que no tengan dato: es que UCDP "
            "no los incluye, y eso no dice nada sobre su situación.")

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Programa académico de la Universidad de Upsala, la referencia establecida "
              "en datos de conflicto armado, con libro de códigos publicado y "
              "versionado. Lo que se registra es lo que el proyecto codificó bajo su "
              "propio umbral de 25 muertes anuales, no toda la violencia que hubo."),
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
                "estados_con_muertes": len(con_muertes),
                "muertes_en_la_region": sum(r.get("muertes") or 0 for r in registros),
                "filas_leidas": len(filas),
                "por_tipo": conteo,
                "consultado": comun.ahora(),
            },
            "tipos": [{"clave": t["clave"], "rotulo": t["rotulo"], "dice": t["dice"]}
                      for t in TIPOS],
            "umbral": ("UCDP registra un conflicto a partir de 25 muertes relacionadas "
                       "en un año calendario. Por debajo de ese umbral, un Estado "
                       "aparece en cero aunque haya violencia."),
        },
    )


if __name__ == "__main__":
    comun.correr("ucdp", recolectar)
