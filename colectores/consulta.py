"""Consulta dirigida: la sintaxis de búsqueda aplicada a la fuente primaria.

POR QUÉ EXISTE
--------------
SIWA publica el dato pero no le entrega al lector **la manera de ir a buscar el
siguiente**. Quien lee que Colombia registró tal cifra de homicidios queda sin
puente hacia el documento original del Estado colombiano, y termina buscando en
un motor general, donde el primer resultado casi nunca es la fuente primaria.

Los operadores de búsqueda —`site:`, `filetype:`, `intitle:`, rango de años,
exclusión con signo menos— resuelven exactamente eso, y son gratuitos. Este
colector los combina con **los dominios oficiales que SIWA ya probó**, y arma
para cada Estado y cada materia la consulta exacta contra su fuente primaria.

DE DÓNDE SALEN LOS DOMINIOS, Y DE DÓNDE NO
------------------------------------------
De `oficiales.json` y de `opacidad.json`, que son padrones verificados a mano y
donde cada dirección respondió cuando se la pidió. **Ningún dominio se construye
por analogía.** Suponer que Nicaragua publica en `datos.gob.ni` porque Argentina
publica en `datos.gob.ar` es exactamente la clase de invención que la casa no
admite: se vería plausible y mandaría al lector a una dirección inexistente.

Por eso buena parte de los 33 Estados sale **sin acotar por dominio**, y el
producto lo dice en lugar de disimularlo. El recuento exacto no se escribe acá
—cambiaría en silencio cada vez que se verifica un portal nuevo— sino que se
calcula en cada corrida y viaja en el bloque `resumen`.

LO QUE NO HACE
--------------
No consulta ningún motor de búsqueda ni trae resultados. **Arma la consulta y la
entrega armada**: el lector la ejecuta y ve el resultado sin intermediación
nuestra. Un recuento de resultados de un motor no es un dato —varía por país,
por sesión y por idioma— y publicarlo como cifra sería falsearlo.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import comun
import geo

AQUI = Path(__file__).resolve().parent
OFICIALES = AQUI / "oficiales.json"
OPACIDAD = AQUI / "opacidad.json"

# El ruido que se resta. Son piezas administrativas del ORGANISMO, que se
# actualizan seguido y no dicen nada del fenomeno.
#
# Se restan solo palabras que NUNCA son el asunto buscado. «Licitacion» quedo
# afuera a proposito: es ruido cuando se buscan homicidios, pero es EXACTAMENTE
# el asunto cuando se busca contratacion publica, y restarla vaciaria la materia
# que vino a cubrirse.
RUIDO = {
    "es": ["nomina", "organigrama"],
    "pt": ["organograma", "\"folha de pagamento\""],
    "en": ["payroll", "vacancy"],
    "fr": ["organigramme", "recrutement"],
    "nl": ["organogram", "vacature"],
}

# EL ESTADO NO PUBLICA EN NUESTRO IDIOMA. Brasil rotula en portugues, Jamaica y
# Guyana en ingles, Haiti en frances, Surinam en neerlandes. Buscar «muertes
# violentas» en `dados.gov.br` no devuelve nada, y el vacio que produce no seria
# del Estado brasileno sino nuestro. El padron de los 33 tiene cinco lenguas.
LENGUA = {
    "BRA": "pt", "HTI": "fr", "SUR": "nl",
    "ATG": "en", "BHS": "en", "BRB": "en", "BLZ": "en", "DMA": "en",
    "GRD": "en", "GUY": "en", "JAM": "en", "KNA": "en", "LCA": "en",
    "VCT": "en", "TTO": "en",
}

# Y EL NOMBRE DEL PAIS TAMBIEN. Cuando no hay dominio probado la consulta se
# acota por el nombre del Estado, y ese nombre tiene que ir como se escribe ALLA:
# «Haití» con tilde no aparece en un documento frances, que dice Haïti; Surinam
# se escribe Suriname en neerlandes. Escribir el exonimo castellano vaciaria
# justamente las consultas que mas dependen de este recurso, porque casi ningun
# Estado del Caribe tiene dominio probado todavia.
NOMBRE_LOCAL = {
    "HTI": "Haïti", "SUR": "Suriname",
    "ATG": "Antigua and Barbuda", "BHS": "Bahamas", "BRB": "Barbados",
    "BLZ": "Belize", "DMA": "Dominica", "GRD": "Grenada", "GUY": "Guyana",
    "JAM": "Jamaica", "KNA": "Saint Kitts and Nevis", "LCA": "Saint Lucia",
    "VCT": "Saint Vincent and the Grenadines", "TTO": "Trinidad and Tobago",
}

# Cada materia con el termino que los Estados usan de verdad, y el tipo de
# documento donde suele estar el dato duro.
MATERIAS = [
    {"materia": "Violencia organizada", "eje": "Seguridad", "formato": "pdf", "terminos": {
        "es": ["homicidios", "\"muertes violentas\""],
        "pt": ["homicídios", "\"mortes violentas\""],
        "en": ["homicides", "\"violent deaths\""],
        "fr": ["homicides", "\"morts violentes\""],
        "nl": ["moorden", "geweldsmisdrijven"]}},
    {"materia": "Delito registrado", "eje": "Seguridad", "formato": "xlsx", "terminos": {
        "es": ["\"hechos delictivos\"", "denuncias"],
        "pt": ["\"ocorrências criminais\"", "denúncias"],
        "en": ["\"crime statistics\"", "\"recorded crime\""],
        "fr": ["\"statistiques criminelles\"", "délinquance"],
        "nl": ["criminaliteitsstatistieken", "aangiften"]}},
    {"materia": "Economías ilícitas", "eje": "Seguridad", "formato": "pdf", "terminos": {
        "es": ["\"lavado de activos\"", "incautaciones"],
        "pt": ["\"lavagem de dinheiro\"", "apreensões"],
        "en": ["\"money laundering\"", "seizures"],
        "fr": ["\"blanchiment d'argent\"", "saisies"],
        "nl": ["witwassen", "inbeslagnames"]}},
    {"materia": "Contrabando", "eje": "Seguridad", "formato": "pdf", "terminos": {
        "es": ["contrabando", "aduana decomiso"],
        "pt": ["contrabando", "aduana apreensão"],
        "en": ["smuggling", "customs seizure"],
        "fr": ["contrebande", "douane saisie"],
        "nl": ["smokkel", "douane inbeslagname"]}},
    {"materia": "Contratación pública", "eje": "Gobernanza", "formato": "csv", "terminos": {
        "es": ["contrataciones", "\"compras públicas\""],
        "pt": ["licitações", "\"compras públicas\""],
        "en": ["\"public procurement\"", "tenders"],
        "fr": ["\"marchés publics\"", "appels d'offres"],
        "nl": ["\"openbare aanbestedingen\"", "aanbestedingen"]}},
    {"materia": "Integridad", "eje": "Gobernanza", "formato": "pdf", "terminos": {
        "es": ["corrupción", "\"declaración jurada\""],
        "pt": ["corrupção", "\"declaração de bens\""],
        "en": ["corruption", "\"asset declaration\""],
        "fr": ["corruption", "\"déclaration de patrimoine\""],
        "nl": ["corruptie", "vermogensverklaring"]}},
    {"materia": "Acceso a la información", "eje": "Gobernanza", "formato": "pdf", "terminos": {
        "es": ["\"acceso a la información\" solicitudes"],
        "pt": ["\"acesso à informação\" pedidos"],
        "en": ["\"freedom of information\" requests"],
        "fr": ["\"accès à l'information\" demandes"],
        "nl": ["\"toegang tot informatie\" verzoeken"]}},
    {"materia": "Ciberseguridad", "eje": "Gobernanza", "formato": "pdf", "terminos": {
        "es": ["ciberseguridad incidentes", "CSIRT"],
        "pt": ["cibersegurança incidentes", "CSIRT"],
        "en": ["cybersecurity incidents", "CSIRT"],
        "fr": ["cybersécurité incidents", "CSIRT"],
        "nl": ["cyberveiligheid incidenten", "CSIRT"]}},
    {"materia": "Desinformación", "eje": "Gobernanza", "formato": "pdf", "terminos": {
        "es": ["desinformación", "\"alfabetización mediática\""],
        "pt": ["desinformação", "\"educação midiática\""],
        "en": ["disinformation", "\"media literacy\""],
        "fr": ["désinformation", "\"éducation aux médias\""],
        "nl": ["desinformatie", "mediawijsheid"]}},
]

# La ficha de operadores. Va al sitio porque el lector tiene que poder ARMAR la
# suya, no solo apretar la que le dimos.
OPERADORES = [
    {"operador": "site:", "hace": "encierra la búsqueda en un solo dominio",
     "ejemplo": "homicidios site:datos.gob.ar"},
    {"operador": "filetype:", "hace": "devuelve un solo tipo de archivo",
     "ejemplo": "homicidios filetype:pdf"},
    {"operador": "intitle:", "hace": "exige que la palabra esté en el título",
     "ejemplo": "intitle:homicidios"},
    {"operador": "comillas", "hace": "busca la frase exacta y en ese orden",
     "ejemplo": "\"muertes violentas\""},
    {"operador": "signo menos", "hace": "resta el ruido que ensucia el resultado",
     "ejemplo": "homicidios -nomina -licitacion"},
    {"operador": "AAAA..AAAA", "hace": "acota a un rango de años",
     "ejemplo": "homicidios 2024..2026"},
    {"operador": "OR", "hace": "acepta cualquiera de dos formas de nombrar lo mismo",
     "ejemplo": "homicidios OR feminicidios"},
]


def _dominio(url: str) -> str:
    return re.sub(r"^https?://", "", (url or "")).split("/")[0].strip().lower()


# El orden importa y no es alfabetico. Un portal general de datos abiertos sirve
# para cualquier materia; el Banco Central no publica homicidios. Elegir el
# primero por orden alfabetico llevaba a armar «homicidios site:api.bcra.gob.ar»,
# una consulta que se ve correcta y no puede devolver nada.
RANGO = {"general": 0, "transparencia": 1, "sectorial": 2}


def _dominiosProbados() -> dict:
    """Los dominios oficiales que ya respondieron, ordenados por utilidad."""
    porEstado: dict[str, dict] = {}

    def sumar(iso, url, clase):
        d = _dominio(url)
        if not iso or not d:
            return
        # Un host `api.` entrega JSON a un programa: NO es una pagina indexada, y
        # acotarle una busqueda con site: no devuelve nada. Sirve al colector,
        # no al lector.
        if d.startswith("api.") or d.startswith("servicodados."):
            return
        previo = porEstado.setdefault(iso, {}).get(d)
        if previo is None or RANGO[clase] < RANGO[previo]:
            porEstado[iso][d] = clase

    oficiales = json.loads(OFICIALES.read_text(encoding="utf-8"))
    for p in oficiales.get("portales", []):
        sumar(p.get("iso"), p.get("base"), "general")
    for s in oficiales.get("sectoriales_verificados", []):
        sumar(s.get("iso"), s.get("consulta"), "sectorial")
    # Un portal BLOQUEADO para el robot sigue siendo la fuente primaria para una
    # persona: que no admita consulta automatizada no lo saca del padron.
    for grupo in (oficiales.get("_bloqueados") or {}).values():
        if isinstance(grupo, list):
            for b in grupo:
                sumar(b.get("iso"), b.get("portal"), "general")

    opacidad = json.loads(OPACIDAD.read_text(encoding="utf-8"))
    for e in opacidad.get("estados", []):
        iso = e.get("iso")
        for valor in e.values():
            if isinstance(valor, str) and valor.startswith("http"):
                sumar(iso, valor, "transparencia")
            elif isinstance(valor, dict):
                for v in valor.values():
                    if isinstance(v, str) and v.startswith("http"):
                        sumar(iso, v, "transparencia")

    return {iso: [d for d, _ in sorted(ds.items(), key=lambda x: (RANGO[x[1]], x[0]))]
            for iso, ds in porEstado.items()}


def _armar(termino: str, formato: str, dominios: list, pais: str, lengua: str) -> str:
    """La consulta, con el dominio si lo hay y con el país si no lo hay."""
    partes = [termino]
    if dominios:
        # Un solo site: por consulta. Encadenar varios con OR los vuelve
        # fragiles y distintos motores los interpretan distinto.
        partes.append(f"site:{dominios[0]}")
    else:
        # Sin dominio probado, lo unico honesto es acotar por el nombre del
        # Estado y AVISAR que no esta acotado a la fuente oficial.
        partes.append(f'"{pais}"')
    if formato:
        partes.append(f"filetype:{formato}")
    partes.extend(f"-{r}" for r in RUIDO[lengua])
    return " ".join(partes)


def recolectar():
    dominios = _dominiosProbados()
    registros = []
    conDominio = 0

    for pais in geo.padron():
        iso, nombre = pais["iso"], pais["pais"]
        suyos = dominios.get(iso, [])
        if suyos:
            conDominio += 1
        lengua = LENGUA.get(iso, "es")
        consultas = []
        for m in MATERIAS:
            for t in m["terminos"][lengua]:
                consultas.append({
                    "materia": m["materia"],
                    "eje": m["eje"],
                    "consulta": _armar(t, m["formato"], suyos,
                                       NOMBRE_LOCAL.get(iso, nombre), lengua),
                    "acotada_a_fuente_oficial": bool(suyos),
                })
        registros.append({
            "iso": iso,
            "pais": nombre,
            "bloque": pais["bloque"],
            "lengua": lengua,
            "dominios_oficiales": suyos,
            "estado": "con_dominio_probado" if suyos else "sin_dominio_probado",
            "consultas": consultas,
        })

    vacios = [
        "ESTO NO ES UN DATO: ES UNA CONSULTA ARMADA. No se ejecuta ningun motor de "
        "busqueda ni se trae ningun resultado. El lector la ejecuta y ve lo que hay, "
        "sin intermediacion de la Oficina.",
        f"SOLO {conDominio} DE 33 ESTADOS tienen dominio oficial ya probado. Para los "
        f"{len(registros) - conDominio} restantes la consulta NO esta acotada a la fuente "
        "oficial: se acota por el nombre del Estado, y el producto lo declara en cada "
        "ficha. NINGUN DOMINIO SE CONSTRUYE POR ANALOGIA: suponer 'datos.gob.ni' porque "
        "existe 'datos.gob.ar' mandaria al lector a una direccion inexistente.",
        "UN RECUENTO DE RESULTADOS NO SE PUBLICA COMO CIFRA. Lo que un motor devuelve "
        "varia por pais, por sesion, por idioma y por historial: no es comparable entre "
        "Estados y no sostiene ningun juicio.",
        "LOS OPERADORES NO GARANTIZAN QUE LA FUENTE SEA FIABLE. Acotar por dominio "
        "oficial acota el ORIGEN, no la calidad: un documento oficial puede estar "
        "desactualizado, incompleto o ser el objeto mismo de la controversia.",
        "EL TERMINO ES EL QUE USA EL ESTADO, no el nuestro. Un conjunto rotulado con "
        "otro vocabulario no aparece en estas consultas, y esa es la limitacion "
        "principal: la busqueda alcanza hasta donde llega el vocabulario elegido.",
        "LA CONSULTA VA EN LA LENGUA DEL ESTADO —castellano, portugues, ingles, frances "
        "o neerlandes segun el caso—, porque ningun Estado rotula en la nuestra. Queda "
        "un vacio conocido: HAITI publica en frances pero buena parte de su vida "
        "administrativa transcurre en criollo haitiano, y SURINAM tiene el neerlandes "
        "como lengua oficial con el sranan tongo de uso corriente. En esos dos casos la "
        "consulta alcanza la lengua oficial y no necesariamente la de la fuente.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Los dominios provienen de los padrones verificados a mano de la Oficina "
              "—portales oficiales e Indice de Opacidad—, donde cada direccion "
              "respondio cuando se la pidio. Fiabilidad A por eso. Credibilidad 2 y no "
              "1 porque LA COMBINACION DE OPERADORES ES UNA CONSTRUCCION DE LA "
              "FUNDACION, no un dato de la fuente: dice donde buscar, no que se va a "
              "encontrar."),
    )

    return comun.escribir(
        colector="consulta",
        capa="publico",
        fuente="Fundación Sherman Kent — consulta dirigida a la fuente primaria",
        url_fuente="https://fundacion-sherman-kent.github.io/siwa/sitio/index.html#consulta",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "operadores": OPERADORES,
            "resumen": {
                "estados_con_dominio_probado": conDominio,
                "estados_sin_dominio_probado": len(registros) - conDominio,
                "estados_del_padron": len(registros),
                "materias_cubiertas": len(MATERIAS),
                "ruido_restado": RUIDO,
            },
        },
    )


if __name__ == "__main__":
    comun.correr("consulta", recolectar)
