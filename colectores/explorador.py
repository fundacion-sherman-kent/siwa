"""El explorador: busca puertas de datos oficiales, todas las noches, solo.

QUÉ ES, Y QUÉ NO ES
-------------------
La Dirección pidió «una IA que siga buscando fuentes, sin costo». Esto no usa
ningún modelo, no necesita credencial y no gasta un peso. Hace lo que en esta
casa dio resultado: **probar de forma sistemática**.

Los hallazgos de estos días no vinieron de adivinar. El índice de crimen
organizado apareció abriendo el sitio y mirando qué consulta hace él; el
comercio de armas, notando que un código de Igarapé era arancelario; los doce
Estados del Caribe, probando sesenta organismos uno por uno. **Lo difícil nunca
fue proponer: fue verificar.**

LA REGLA QUE LO GOBIERNA
------------------------
**Propone, no publica.** El explorador no agrega nada al registro. Toca puertas,
anota cuál abrió, con qué forma y desde cuándo, y **deja el hallazgo declarado
para que una persona decida**. Un colector que se autoalimentara con lo que
encuentra rompería la única regla que hace confiable a este registro: que todo
lo que se afirma, se probó.

QUÉ PRUEBA
----------
Los portales de datos abiertos del mundo hablan un puñado de dialectos, y cada
uno tiene una dirección conocida donde se anuncia. Se prueban esos caminos
contra el dominio oficial de cada Estado:

  · CKAN            el más extendido en la región
  · Socrata         el de Colombia
  · OpenDataSoft    frecuente en el Caribe
  · DCAT            el estándar abierto: `/data.json`
  · ArcGIS Hub      cuando el portal es de mapas

Y distingue tres cosas que NO son lo mismo, porque confundirlas fue lo que dejó
a seis Estados mal descritos:

  · **abre**      responde y entrega catálogo
  · **cierra**    responde a personas y rechaza programas (403, 401)
  · **no está**   no hay nada en esa dirección (404, sin resolver)

«Cierra» no es «no está», y ninguno de los dos es «no publica».
"""

from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import comun
import geo

NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# Algunos organismos oficiales tienen el certificado vencido o mal encadenado.
# Eso NO es motivo para no mirar: se anota y se sigue.
LAXO = ssl.create_default_context()
LAXO.check_hostname = False
LAXO.verify_mode = ssl.CERT_NONE

# Los dialectos que hablan los portales, con la dirección donde se anuncian.
DIALECTOS = [
    ("CKAN", "/api/3/action/package_search?rows=1"),
    ("CKAN", "/api/3/action/package_list"),
    ("DCAT", "/data.json"),
    ("Socrata", "/api/views.json?limit=1"),
    ("OpenDataSoft", "/api/datasets/1.0/search/?rows=1"),
    ("DKAN", "/api/1/metastore/schemas/dataset/items?limit=1"),
    ("ArcGIS Hub", "/api/feed/dcat-us/1.1.json"),
]

# Dominios oficiales PROBADOS en la auditoría del 6 de septiembre de 2026: los
# 47 organismos que respondieron, de los 60 que se consultaron. No son
# suposiciones ni analogías —«si Perú usa datos.gob.pe, Bolivia usará
# datos.gob.bo»—, que es exactamente como se llega a una dirección inexistente.
PUERTAS = {
    "ARG": ["datos.gob.ar", "www.indec.gob.ar"],
    "BOL": ["datos.gob.bo", "www.ine.gob.bo"],
    "BRA": ["dados.gov.br", "servicodados.ibge.gov.br"],
    "CHL": ["datos.gob.cl", "www.ine.gob.cl"],
    "COL": ["www.datos.gov.co", "www.dane.gov.co"],
    "CRI": ["www.inec.cr"],
    "CUB": ["www.onei.gob.cu"],
    "DOM": ["datos.gob.do", "www.one.gob.do"],
    "ECU": ["www.datosabiertos.gob.ec", "www.ecuadorencifras.gob.ec"],
    "SLV": ["www.transparencia.gob.sv", "www.iaip.gob.sv"],
    "GTM": ["www.datos.gob.gt", "www.ine.gob.gt"],
    "HTI": ["www.ihsi.ht"],
    "HND": ["portalunico.iaip.gob.hn", "www.ine.gob.hn"],
    "MEX": ["datos.gob.mx", "www.inegi.org.mx"],
    "NIC": ["www.inide.gob.ni"],
    "PAN": ["www.datosabiertos.gob.pa", "www.inec.gob.pa"],
    "PRY": ["www.datos.gov.py", "www.ine.gov.py"],
    "PER": ["www.datosabiertos.gob.pe", "www.inei.gob.pe"],
    "URY": ["catalogodatos.gub.uy", "www.ine.gub.uy"],
    "VEN": ["www.ine.gob.ve"],
    "BLZ": ["sib.org.bz"],
    "GUY": ["statisticsguyana.gov.gy"],
    "SUR": ["statistics-suriname.org"],
    "ATG": ["statistics.gov.ag"],
    "BHS": ["www.bahamas.gov.bs"],
    "BRB": ["stats.gov.bb"],
    "DMA": ["stats.gov.dm"],
    "GRD": ["stats.gov.gd"],
    "JAM": ["data.gov.jm", "statinja.gov.jm"],
    "KNA": ["www.stats.gov.kn"],
    "LCA": ["www.stats.gov.lc"],
    "VCT": ["stats.gov.vc"],
    "TTO": ["cso.gov.tt"],
}

# Argentina abre y responde CKAN. Si el explorador no lo encuentra, el que fallo
# es el explorador, no el mundo.
CONTROL = "ARG"


def _probar(faena: tuple) -> dict:
    iso, dominio, dialecto, ruta = faena
    url = f"https://{dominio}{ruta}"
    try:
        peticion = urllib.request.Request(
            url, headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
        with urllib.request.urlopen(peticion, timeout=25, context=LAXO) as respuesta:
            # Perú anuncia su catálogo con la lista COMPLETA de nombres —miles—, y con
            # un tope chico la respuesta llegaba cortada, no parseaba y el recuento
            # salía vacío. El tope se mide por lo que la fuente manda, no por lo que
            # uno espera que mande.
            crudo = respuesta.read(4_000_000).decode("utf-8", "replace").lstrip()
        if not crudo.startswith(("{", "[")):
            return {"iso": iso, "dominio": dominio, "dialecto": dialecto,
                    "resultado": "no_es_catalogo", "detalle": "responde, pero en HTML"}
        try:
            d = json.loads(crudo)
        except Exception:  # noqa: BLE001 — respuesta cortada por el tope de lectura
            d = None
        cuantos = None
        if isinstance(d, dict):
            r = d.get("result")
            if isinstance(r, dict) and "count" in r:
                cuantos = r["count"]
            elif isinstance(r, list):
                cuantos = len(r)
            elif isinstance(d.get("dataset"), list):
                cuantos = len(d["dataset"])
            elif isinstance(d.get("nhits"), int):
                cuantos = d["nhits"]
        return {"iso": iso, "dominio": dominio, "dialecto": dialecto,
                "resultado": "abre", "conjuntos": cuantos, "url": url}
    except urllib.error.HTTPError as error:
        # 403 y 401 NO son «no existe»: son «existe y no te deja».
        cual = "cierra" if error.code in (401, 403, 429) else "no_esta"
        return {"iso": iso, "dominio": dominio, "dialecto": dialecto,
                "resultado": cual, "detalle": f"HTTP {error.code}"}
    except Exception as error:  # noqa: BLE001
        return {"iso": iso, "dominio": dominio, "dialecto": dialecto,
                "resultado": "no_esta", "detalle": type(error).__name__}


def recolectar():
    faenas = [(iso, dom, dia, ruta)
              for iso, doms in PUERTAS.items()
              for dom in doms
              for dia, ruta in DIALECTOS]
    with ThreadPoolExecutor(max_workers=12) as ejecutor:
        toques = list(ejecutor.map(_probar, faenas))

    # SE PRUEBA EL EXPLORADOR ANTES DE CREERLE UN VACIO A NADIE.
    abreControl = any(t["resultado"] == "abre" for t in toques if t["iso"] == CONTROL)
    if not abreControl:
        raise RuntimeError(
            f"La prueba del explorador falló: {CONTROL} —que publica un catálogo abierto y "
            "responde— no abrió en ninguna de las puertas probadas. El que falló es el "
            "explorador, no el mundo. NO se publica un mapa de puertas cerradas que en "
            "realidad son un error propio.")

    porIso: dict = {}
    for t in toques:
        porIso.setdefault(t["iso"], []).append(t)

    registros, abren, cierran, sinNada = [], 0, 0, 0
    for pais in geo.padron():
        suyos = porIso.get(pais["iso"], [])
        buenas = [t for t in suyos if t["resultado"] == "abre"]
        cerradas = [t for t in suyos if t["resultado"] == "cierra"]
        if buenas:
            estado, abren = "abre", abren + 1
        elif cerradas:
            estado, cierran = "cierra", cierran + 1
        else:
            estado, sinNada = "sin_puerta_hallada", sinNada + 1
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": estado,
            # Una misma puerta puede abrir por dos caminos del mismo dialecto
            # —CKAN anuncia catalogo en dos direcciones—. Se queda UNA por
            # dominio y dialecto, la que ademas trae el recuento.
            "puertas_abiertas": list({
                (t["dominio"], t["dialecto"]): {
                    "dominio": t["dominio"], "dialecto": t["dialecto"],
                    "conjuntos": t.get("conjuntos"), "url": t["url"]}
                # En un diccionario gana la ULTIMA, asi que las que traen
                # recuento van al final a proposito.
                for t in sorted(buenas, key=lambda x: x.get("conjuntos") is not None)
            }.values()),
            "puertas_cerradas": sorted({
                f'{t["dominio"]} · {t["detalle"]}' for t in cerradas}),
            "dominios_probados": sorted({t["dominio"] for t in suyos}),
        })

    vacios = [
        "ESTE COLECTOR PROPONE, NO PUBLICA. No agrega nada al registro: toca puertas, "
        "anota cual abrio y con que forma, y DEJA EL HALLAZGO DECLARADO para que una "
        "persona decida. Un colector que se autoalimentara con lo que encuentra romperia "
        "la unica regla que hace confiable a este registro: que todo lo que se afirma, se "
        "probo.",
        "«CIERRA» NO ES «NO ESTA», Y NINGUNO DE LOS DOS ES «NO PUBLICA». Un 403 o un 401 "
        "significan que el portal EXISTE y rechaza a los programas —publica para personas "
        "y no para maquinas—. Un 404 significa que no hay nada en esa direccion, que "
        "puede ser porque el portal esta en otra. Confundirlos fue lo que dejo a seis "
        "Estados mal descritos.",
        "SOLO SE PRUEBAN DOMINIOS OFICIALES YA VERIFICADOS, nunca direcciones deducidas "
        "por analogia. Suponer que «si Peru usa datos.gob.pe entonces Bolivia usara "
        "datos.gob.bo» es exactamente como se llega a una direccion inexistente y se la "
        "anota como Estado opaco.",
        "QUE UN ESTADO NO ABRA NINGUNA PUERTA NO SIGNIFICA QUE NO PUBLIQUE DATOS. "
        "Significa que no se hallo un catalogo legible por maquina en los dominios "
        "probados y en los dialectos conocidos. Puede publicar en PDF, en otra direccion "
        "o con un dialecto que este colector todavia no conoce.",
        f"ANTES DE CREER UN VACIO SE PRUEBA EL EXPLORADOR contra {CONTROL}, que publica "
        "catalogo abierto. Si ESE no abre, la corrida se detiene entera en lugar de "
        "publicar un mapa de puertas cerradas que en realidad son un error propio.",
        "LA CANTIDAD DE CONJUNTOS ES LA QUE DECLARA EL PORTAL, no un recuento propio, y "
        "no dice nada sobre su calidad ni su actualidad: un portal con diez mil conjuntos "
        "viejos no publica mas que uno con cien al dia.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=1,
        corroborado=True,
        nota=("Medicion propia de la Oficina: se consulta cada dominio oficial y se "
              "registra lo que contesta. Fiabilidad A porque el productor es esta casa y "
              "el metodo esta escrito. Credibilidad 1 porque el hecho registrado —que una "
              "direccion respondio de tal modo en tal momento— se verifica por si mismo y "
              "cualquiera puede repetir la consulta: la corroboracion es la reproducibilidad."),
    )

    return comun.escribir(
        colector="explorador",
        capa="publico",
        fuente="Fundación Sherman Kent — exploración de puertas de datos oficiales",
        url_fuente=comun.SITIO_URL + "#explorador",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados_que_abren": abren,
                "estados_que_cierran": cierran,
                "estados_sin_puerta_hallada": sinNada,
                "estados_del_padron": len(registros),
                "dominios_probados": len({d for l in PUERTAS.values() for d in l}),
                "dialectos_probados": len({d for d, _ in DIALECTOS}),
                "toques_realizados": len(toques),
                "explorador_probado": True,
                "consultado": comun.ahora(),
            },
            "dialectos": sorted({d for d, _ in DIALECTOS}),
        },
    )


if __name__ == "__main__":
    comun.correr("explorador", recolectar)
