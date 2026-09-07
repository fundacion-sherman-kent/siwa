"""Designados por el Consejo de Seguridad: quiénes están sancionados y de dónde.

POR QUÉ EXISTE
--------------
La Dirección pidió datos sobre organizaciones terroristas y criminales. Ésta es
**la única lista oficial, mundial y de acceso libre** que nombra organizaciones
y personas sujetas a sanciones obligatorias para todos los Estados: la lista
consolidada del Consejo de Seguridad de las Naciones Unidas.

LO QUE ENCONTRÓ, Y ES LO CONTRARIO DE LO QUE SE ESPERA
-------------------------------------------------------
De **275 entidades y 736 personas** designadas en el mundo, apenas **quince**
tienen vínculo con los 33 Estados del padrón. Y la mayoría son de Haití.

**Eso NO significa que la región no tenga crimen organizado ni terrorismo.**
Significa otra cosa, y es la que este colector existe para decir: **los regímenes
de sanciones del Consejo son geográficos y políticos**, no un termómetro de
amenaza. Los que existen apuntan a Al-Qaida, Corea del Norte, Irán, Irak, Libia,
Somalia, Yemen, la República Democrática del Congo, la República Centroafricana,
los talibanes y —desde 2022— Haití. **No hay régimen para América Latina**, y por
eso la región casi no figura.

Leer esta lista como un ranking de peligrosidad sería exactamente al revés.

LO QUE PUBLICA, Y LO QUE NO
---------------------------
Publica **los nombres de las ENTIDADES** —son organizaciones, la lista es
oficial y su publicación es su propósito— con el régimen que las alcanza y la
fecha en que fueron listadas.

De las **PERSONAS publica el recuento, no los nombres.** El registro ya toma esa
decisión con las víctimas de extorsión informática, y acá vale igual: la lista
del Consejo es pública y cualquiera puede consultarla en la fuente, pero **este
registro no es un buscador de personas** y republicar nóminas de individuos no
aporta nada que la cifra no diga.
"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

import comun
import geo

FUENTE = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
NAVEGADOR = comun.AGENTE
INTENTOS = 3
ESPERA = 5

# La lista escribe los nombres de país en inglés y con la forma larga de la ONU.
# La equivalencia va explícita: adivinarla es como se rompen los colectores.
COMO_LOS_NOMBRA = {
    "Argentina": "ARG", "Bolivia": "BOL", "Bolivia (Plurinational State of)": "BOL",
    "Brazil": "BRA", "Chile": "CHL", "Colombia": "COL", "Costa Rica": "CRI",
    "Cuba": "CUB", "Dominican Republic": "DOM", "Ecuador": "ECU",
    "El Salvador": "SLV", "Guatemala": "GTM", "Haiti": "HTI", "Honduras": "HND",
    "Mexico": "MEX", "Nicaragua": "NIC", "Panama": "PAN", "Paraguay": "PRY",
    "Peru": "PER", "Uruguay": "URY", "Venezuela": "VEN",
    "Venezuela (Bolivarian Republic of)": "VEN", "Belize": "BLZ", "Guyana": "GUY",
    "Suriname": "SUR", "Antigua and Barbuda": "ATG", "Bahamas": "BHS",
    "Barbados": "BRB", "Dominica": "DMA", "Grenada": "GRD", "Jamaica": "JAM",
    "Saint Kitts and Nevis": "KNA", "Saint Lucia": "LCA",
    "Saint Vincent and the Grenadines": "VCT", "Trinidad and Tobago": "TTO",
}

# Al-Qaida es el regimen con mas designados del mundo. Si la lectura no lo
# encuentra, el que fallo es el lector: la lista no se vacia de un dia para otro.
CONTROL = "Al-Qaida"
MINIMO_CONTROL = 40


def _traer() -> bytes:
    ultimo = None
    for numero in range(INTENTOS):
        try:
            peticion = urllib.request.Request(FUENTE, headers={"User-Agent": NAVEGADOR})
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                return respuesta.read(40_000_000)
        except urllib.error.HTTPError as error:
            raise RuntimeError(
                f"La fuente rechazó la consulta: HTTP {error.code}. NO se anota cero."
            ) from error
        except Exception as error:  # noqa: BLE001 — falla de red: se reintenta
            ultimo = error
            print(f"[designados] intento {numero + 1} de {INTENTOS}: "
                  f"{type(error).__name__}: {error}", file=sys.stderr)
            time.sleep(ESPERA * (numero + 1))
    raise RuntimeError(
        f"No se pudo leer la lista en {INTENTOS} intentos: {type(ultimo).__name__}: "
        f"{ultimo}. Es falla de RED. NO se anota cero: no poder mirar no es haber mirado.")


def _paisesDe(nodo) -> set:
    """De dónde es: domicilio, nacionalidad o lugar de nacimiento. Los tres cuentan."""
    fuera = set()
    for etiqueta in ("ENTITY_ADDRESS", "INDIVIDUAL_ADDRESS", "INDIVIDUAL_PLACE_OF_BIRTH"):
        for a in nodo.findall(etiqueta):
            pais = (a.findtext("COUNTRY") or "").strip()
            if pais:
                fuera.add(pais)
    for n in nodo.findall("NATIONALITY/VALUE"):
        if n.text and n.text.strip():
            fuera.add(n.text.strip())
    return fuera


def _nombre(nodo) -> str:
    partes = [(nodo.findtext(c) or "").strip()
              for c in ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME")]
    return " ".join(p for p in partes if p)


def recolectar():
    raiz = ET.fromstring(_traer())
    entidades = raiz.findall(".//ENTITY")
    personas = raiz.findall(".//INDIVIDUAL")

    # SE PRUEBA EL LECTOR ANTES DE CREERLE UN CERO A NADIE.
    deControl = sum(1 for x in entidades + personas
                    if (x.findtext("UN_LIST_TYPE") or "") == CONTROL)
    if deControl < MINIMO_CONTROL:
        raise RuntimeError(
            f"La prueba del lector falló: el régimen «{CONTROL}» —el más numeroso del "
            f"mundo— devolvió {deControl} designados, y no puede ser. La lista cambió de "
            "forma o no se leyó entera. NO se publica una lectura a ciegas.")

    porIso: dict = {}
    regimenes: set = set()
    for tipo, nodos in (("entidad", entidades), ("persona", personas)):
        for x in nodos:
            regimen = (x.findtext("UN_LIST_TYPE") or "sin régimen declarado").strip()
            for nombrePais in _paisesDe(x):
                iso = COMO_LOS_NOMBRA.get(nombrePais)
                if not iso:
                    continue
                regimenes.add(regimen)
                caja = porIso.setdefault(iso, {"entidades": [], "personas": 0,
                                               "regimenes": set()})
                caja["regimenes"].add(regimen)
                if tipo == "entidad":
                    caja["entidades"].append({
                        "nombre": _nombre(x),
                        "regimen": regimen,
                        "referencia": (x.findtext("REFERENCE_NUMBER") or "").strip(),
                        "listada_el": (x.findtext("LISTED_ON") or "").strip(),
                    })
                else:
                    caja["personas"] += 1

    registros, conVinculo = [], 0
    for pais in geo.padron():
        caja = porIso.get(pais["iso"])
        if not caja:
            registros.append({
                "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
                "estado": "sin_designados",
                "entidades": [], "personas": 0, "regimenes": [],
            })
            continue
        conVinculo += 1
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": "con_designados",
            "entidades": sorted(caja["entidades"], key=lambda e: e["listada_el"]),
            "personas": caja["personas"],
            "regimenes": sorted(caja["regimenes"]),
        })

    vacios = [
        "Que un Estado no tenga designados no significa que no tenga crimen organizado ni "
        "terrorismo. Los regimenes de sanciones del Consejo son geograficos y politicos, "
        "no un termometro de amenaza: existen para Al-Qaida, Corea del Norte, Iran, Irak, "
        "libia, Somalia, Yemen, la República Democrática del Congo, la República "
        "centroafricana, los talibanes y —desde 2022— Haití. No hay régimen para América "
        "latina, y por eso la región casi no figura. Leer esta lista como un ranking de "
        "peligrosidad sería exactamente al revés.",
        "De las personas se publica el recuento, no los nombres. La lista es pública y "
        "cualquiera puede consultarla en la fuente, pero este registro no es un buscador "
        "de personas: republicar nominas de individuos no agrega nada que la cifra no "
        "diga. De las entidades si se publica el nombre: son organizaciones y la "
        "publicación es el propósito de la lista.",
        "El vínculo con un Estado puede ser domicilio, nacionalidad o lugar de nacimiento, "
        "Y no todos significan lo mismo. Que una persona designada haya nacido en un país "
        "no dice que opere ahi. El registro cuenta el vínculo declarado por la fuente y no "
        "interpreta cual es.",
        "Una designación es una decisión política con efectos juridicos, no una condena. "
        "El Consejo la adopta por consenso de sus miembros y existe un procedimiento de "
        "exclusión. El registro publica que está designado y desde cuando; no afirma que "
        "sea culpable de nada.",
        "La lista cambia sin aviso: se agregan y se quitan nombres a lo largo del año. "
        "Lo que se publica es la foto del día de la consulta, con su fecha.",
        f"ANTES DE CREERLE UN CERO A NADIE SE PRUEBA EL LECTOR contra el regimen «{CONTROL}», "
        f"el mas numeroso del mundo: si devuelve menos de {MINIMO_CONTROL} designados, la "
        "corrida se detiene entera en lugar de publicar treinta y tres ceros que en "
        "realidad significan «no supimos leer».",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Lista consolidada del Consejo de Seguridad de las Naciones Unidas, "
              "Publicada por su Secretaria. Fiabilidad a porque el productor es el organo "
              "que adopta la designación: no informa sobre un hecho ajeno, informa sobre "
              "su propia decisión. Credibilidad 2 porque lo que se verifica es la "
              "designación —que consta— y no los hechos que la motivaron, que el registro "
              "no puede comprobar."),
    )

    return comun.escribir(
        colector="designados",
        capa="publico",
        fuente="Consejo de Seguridad de las Naciones Unidas — lista consolidada de sanciones",
        url_fuente="https://www.un.org/securitycouncil/content/un-sc-consolidated-list",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "entidades_en_el_mundo": len(entidades),
                "personas_en_el_mundo": len(personas),
                "estados_con_vinculo": conVinculo,
                "estados_del_padron": len(registros),
                "entidades_en_la_region": sum(len(r["entidades"]) for r in registros),
                "personas_en_la_region": sum(r["personas"] for r in registros),
                "regimenes_que_alcanzan_la_region": sorted(regimenes),
                "lector_probado": True,
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("designados", recolectar)
