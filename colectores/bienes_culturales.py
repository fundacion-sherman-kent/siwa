"""Bienes culturales — qué está tipificado en cada Estado, no cuánto se trafica.

**Y la diferencia importa.** Se rastreó en seis idiomas —español, inglés, francés,
alemán, italiano y portugués— UNESCO, UNODC (SHERLOC), UNIDROIT, ICOM, la
Organización Mundial de Aduanas, INTERPOL, los Carabinieri para la Tutela del
Patrimonio Culturale, Kulturgutschutz Deutschland, la base POP del Ministerio de
Cultura francés, el IBRAM, ARCA y Trafficking Culture. **No existe fuente libre
con volúmenes de tráfico de bienes culturales por país.** INTERPOL exige
convenio; la Aduana publica agregados regionales en PDF; SHERLOC da
jurisprudencia y legislación, no cantidades.

Lo que sí es comparable en los 33 Estados es **el estado de ratificación del
Convenio de UNIDROIT de 1995 sobre bienes culturales robados o exportados
ilícitamente**, que dice qué Estado se obligó a restituir y bajo qué reglas. No
mide tráfico: mide qué está tipificado y qué no, que es una pregunta distinta y
contestable.

Lo que falta, y por qué
----------------------
**El Convenio de la UNESCO de 1970 —el principal, y el que más Estados
ratificaron— no se pudo recolectar.** UNESCO interpone una verificación
anti-robot en todas las direcciones que se probaron: la página del convenio, la
vía antigua `eri/la/convention.asp`, el portal heredado y los subdominios de
datos. No es que el dato no exista ni que sea reservado: es que el sitio del
organismo rechaza a los programas. Queda declarado y se gestiona por vía oficial,
como corresponde (`doctrina/limites.md`).
"""

from __future__ import annotations

import html
import re
import ssl
import urllib.error
import urllib.request

import comun
import geo

FUENTE = "UNIDROIT — Convenio de 1995 sobre bienes culturales robados o exportados ilícitamente"
URL = "https://www.unidroit.org/instruments/cultural-property/1995-convention/status/"
NAVEGADOR = comun.AGENTE

# La tabla de Estados parte es la primera de la página, pero la página trae nueve
# tablas y varias son declaraciones territoriales de otros instrumentos. Si se
# tomara «la primera» sin mirar qué dice, un rediseño del sitio haría que este
# colector publicara la lista de provincias del Canadá como si fueran Estados
# soberanos. Por eso se exige que el encabezado sea el que se verificó.
ENCABEZADO = ("state", "signature")
MINIMO_ESTADOS = 50          # la tabla verificada trae 65; muy por debajo, algo se rompió
CONTROL = "Peru"             # parte desde 1998: si no aparece, el que falló es el lector

# UNESCO cierra la puerta a los programas. Se declara con la dirección exacta que
# se probó, para que cualquiera pueda repetir la prueba y contradecirnos.
UNESCO_1970 = {
    "convenio": "UNESCO 1970 — medidas contra la importación, la exportación y la "
                "transferencia de propiedad ilícitas de bienes culturales",
    "url": "https://www.unesco.org/en/legal-affairs/convention-means-prohibiting-and-"
           "preventing-illicit-import-export-and-transfer-ownership-cultural",
    "estado": "verificacion_anti_robot",
    "detalle": "Las cuatro direcciones probadas devuelven una página de verificación "
               "anti-robot en lugar de la tabla de Estados parte. No se esquiva la "
               "protección: se declara y se gestiona la vía oficial.",
}

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

VIAS = {"RT": "ratificación", "AS": "adhesión", "AC": "aceptación", "AP": "aprobación"}


def _limpiar(fragmento: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", "", fragmento))).strip()


def _bajar() -> str:
    contexto = ssl.create_default_context()
    peticion = urllib.request.Request(URL, headers={
        "User-Agent": NAVEGADOR,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en,es;q=0.8"})
    try:
        with urllib.request.urlopen(peticion, timeout=90, context=contexto) as respuesta:
            return respuesta.read(6_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"UNIDROIT respondió HTTP {e.code}") from e


def _tabla(pagina: str) -> list:
    """La tabla de Estados parte, reconocida por su encabezado y no por su lugar."""
    for cruda in re.findall(r"(?is)<table.*?</table>", pagina):
        filas = re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", cruda)
        if not filas:
            continue
        cabeza = [_limpiar(x).lower() for x in
                  re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", filas[0])]
        if len(cabeza) >= 2 and cabeza[0].startswith(ENCABEZADO[0]) and ENCABEZADO[1] in cabeza[1]:
            return filas
    raise RuntimeError(
        "No se halló en la página la tabla de Estados parte con el encabezado "
        "verificado. La página cambió de forma: NO se publica una lista armada con "
        "otra tabla, que es como se termina publicando provincias del Canadá como "
        "Estados soberanos.")


def recolectar():
    pagina = _bajar()
    filas = _tabla(pagina)

    partes = {}
    for fila in filas[1:]:
        celdas = [_limpiar(x) for x in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", fila)]
        if len(celdas) < 5 or not celdas[0]:
            continue
        partes[celdas[0]] = {
            "via": VIAS.get(celdas[2].strip().upper(), celdas[2].strip()),
            "fecha_del_acto": celdas[3],
            "en_vigor_desde": celdas[4],
        }

    # PROBAR ANTES DE AFIRMAR. Una lista corta o sin el control no significa que los
    # Estados no hayan ratificado: significa que no se leyó bien la tabla. Y decir
    # «no ratificó» de un Estado que sí ratificó es peor que no decir nada.
    if len(partes) < MINIMO_ESTADOS or CONTROL not in partes:
        raise RuntimeError(
            f"Se leyeron {len(partes)} Estados y el control ({CONTROL}) "
            f"{'está' if CONTROL in partes else 'NO está'} en la lista. Con menos de "
            f"{MINIMO_ESTADOS} o sin el control, lo que falló es la lectura de la tabla "
            "y no la ratificación de nadie. No se publica.")

    registros = []
    for pais in geo.padron():
        nombre = next((n for n, i in NOMBRES.items() if i == pais["iso"]), None)
        dato = partes.get(nombre) if nombre else None
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "nombre_en_la_fuente": nombre,
            "unidroit_1995": bool(dato),
            **({"via": dato["via"], "fecha_del_acto": dato["fecha_del_acto"],
                "en_vigor_desde": dato["en_vigor_desde"]} if dato else {}),
        })
    registros.sort(key=lambda r: (not r["unidroit_1995"], r["pais"]))
    obligados = sum(1 for r in registros if r["unidroit_1995"])

    vacios = [
        "**Esto no mide tráfico de bienes culturales: mide qué está tipificado.** Un "
        "Estado parte se obligó a restituir el bien robado y a admitir la acción de "
        "devolución; uno que no lo es puede tener igualmente ley interna. Que un "
        "Estado no figure NO dice que trafique más ni que proteja menos.",
        "**No existe fuente libre con volúmenes de tráfico por país**, y se buscó en "
        "seis idiomas en UNESCO, UNODC, UNIDROIT, ICOM, la Organización Mundial de "
        "Aduanas, INTERPOL, los Carabinieri, Kulturgutschutz, la base POP francesa, el "
        "IBRAM, ARCA y Trafficking Culture. INTERPOL exige convenio; la Aduana publica "
        "agregados regionales en PDF; SHERLOC da jurisprudencia y legislación, no "
        "cantidades. El vacío es del mundo, no de este registro.",
        "**Falta el convenio principal.** El de la UNESCO de 1970 lo ratificaron muchos "
        "más Estados, y no se pudo recolectar: UNESCO devuelve una verificación "
        "anti-robot en las cuatro direcciones probadas. El dato es público; el sitio "
        "del organismo rechaza a los programas. Se declara y se gestiona por vía "
        "oficial.",
        "La fecha del acto y la de entrada en vigor son distintas, y el convenio rige "
        "desde la segunda. Leerlas como una sola adelanta la obligación de un Estado "
        "entre seis meses y un año.",
        "El nombre de cada Estado se toma como lo escribe el depositario, en inglés, y "
        "se lo hace corresponder con el padrón. Un Estado que el depositario rotulara "
        "de otro modo quedaría fuera sin que nadie lo note: por eso se publica también "
        "el nombre con el que figura en la fuente.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("El depositario del convenio, que es quien lleva el registro de los actos "
              "de ratificación y adhesión: fuente primaria y única por naturaleza. Lo "
              "que se consigna es el acto y su fecha, no su cumplimiento."),
    )

    return comun.escribir(
        colector="bienes_culturales",
        capa="publico",
        fuente=FUENTE,
        url_fuente=URL,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados_obligados": obligados,
                "estados_del_padron": len(registros),
                "estados_en_la_fuente": len(partes),
                "consultado": comun.ahora(),
            },
            "convenio_faltante": UNESCO_1970,
        },
    )


if __name__ == "__main__":
    comun.correr("bienes_culturales", recolectar)
