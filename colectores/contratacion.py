"""Contratación pública: quién publica sus compras en formato abierto, y quién no.

POR QUÉ EXISTE
--------------
«Contratación pública» era una de las seis materias que el registro nombra y no
podía medir. Es donde el Estado gasta, y donde la corrupción deja rastro
documental: sin una serie, la materia era una promesa.

El registro de publicadores de contrataciones abiertas responde sin credencial y
dice, para cada publicador, dónde publica, hasta qué fecha llega su serie, con
qué frecuencia la actualiza y si dejó de moverse.

LO QUE MIDE, Y LO QUE NO
------------------------
Mide **la publicación**, no la contratación. Un Estado que compra mucho y publica
poco aparece con poca cobertura; uno que compra poco y publica todo, con mucha.
`ESTO NO ES UNA MEDIDA DE VOLUMEN DE COMPRA NI DE LIMPIEZA.`

Y **no distingue el publicador nacional del subnacional**. México tiene dieciocho
publicadores y la mayoría son de un estado o de un organismo: contarlos como
cobertura nacional sería falso. Se publica el recuento y se declara la mezcla,
porque clasificarlos por el título sería inventar una distinción que el registro
no trae.

LA AUSENCIA ES EL DATO
----------------------
Dieciocho de los treinta y tres Estados no tienen un solo publicador. Esa lista
no es un vacío nuestro: es una medición de opacidad en compras del Estado, y por
eso este colector la publica como resultado y no como faltante.

Se aplica la regla asimétrica de la casa: no figurar en este registro **no prueba
que el Estado no publique** —puede publicar fuera del estándar, o en un portal
que el registro no incorporó—. Prueba que no publica *en el formato que permite
compararlo*, que es una afirmación más chica y verdadera.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path

import comun
import geo

REGISTRO = "https://data.open-contracting.org/en/publications.json"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# El registro nombra a los Estados en inglés; el padrón de la casa, en castellano.
# La tabla es explícita a proposito: adivinar por parecido de cadena confunde
# «Dominica» con «Dominican Republic», que son dos Estados distintos del padrón.
EQUIVALE = {
    "Mexico": "MEX", "Brazil": "BRA", "Peru": "PER", "Panama": "PAN",
    "Dominican Republic": "DOM", "Dominica": "DMA", "Haiti": "HTI",
    "Argentina": "ARG", "Bolivia": "BOL", "Chile": "CHL", "Colombia": "COL",
    "Costa Rica": "CRI", "Ecuador": "ECU", "Guatemala": "GTM",
    "Honduras": "HND", "Paraguay": "PRY", "Uruguay": "URY",
    "El Salvador": "SLV", "Nicaragua": "NIC", "Venezuela": "VEN",
    "Cuba": "CUB", "Belize": "BLZ", "Guyana": "GUY", "Suriname": "SUR",
    "Jamaica": "JAM", "Trinidad and Tobago": "TTO", "Barbados": "BRB",
    "Bahamas": "BHS", "Antigua and Barbuda": "ATG", "Grenada": "GRD",
    "Saint Lucia": "LCA", "Saint Kitts and Nevis": "KNA",
    "Saint Vincent and the Grenadines": "VCT",
}

# Un publicador cuya serie no llega ni a este umbral describe otra epoca.
MESES_VIGENTE = 24


def _traer() -> list:
    peticion = urllib.request.Request(
        REGISTRO, headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=60) as respuesta:
        return json.loads(respuesta.read(4_000_000).decode("utf-8", "replace"))


def _dias(fecha: str | None) -> int | None:
    try:
        return (date.today() - date.fromisoformat(fecha[:10])).days
    except Exception:  # noqa: BLE001 — una fecha ilegible no descarta el publicador
        return None


def recolectar():
    crudo = _traer()

    porEstado: dict[str, list] = {}
    sin_equivalencia = set()
    for p in crudo:
        pais = (p.get("country") or "").strip()
        iso = EQUIVALE.get(pais)
        if not iso:
            if p.get("region") == "LAC":
                sin_equivalencia.add(pais)
            continue
        porEstado.setdefault(iso, []).append(p)

    if sin_equivalencia:
        print(f"[contratacion] AVISO: en ALC y sin equivalencia en el padrón -> "
              f"{', '.join(sorted(sin_equivalencia))}")

    registros, conPublicador, vigentes = [], 0, 0
    for pais in geo.padron():
        iso = pais["iso"]
        suyos = porEstado.get(iso, [])
        detalle = []
        for p in sorted(suyos, key=lambda x: (x.get("date_to") or ""), reverse=True):
            hasta = (p.get("date_to") or "")[:10]
            detalle.append({
                "titulo": (p.get("title") or "").strip(),
                "enlace": p.get("source_url") or "",
                "hasta": hasta,
                "dias_desde_el_final": _dias(hasta),
                "frecuencia": (p.get("update_frequency") or "sin declarar").lower(),
                "detenido": bool(p.get("frozen")),
                "ultima_lectura": (p.get("last_retrieved") or "")[:10],
            })

        if detalle:
            conPublicador += 1
            frescos = [d for d in detalle
                       if d["dias_desde_el_final"] is not None
                       and d["dias_desde_el_final"] <= MESES_VIGENTE * 30]
            estado = "vigente" if frescos else "publica_pero_atrasado"
            if frescos:
                vigentes += 1
        else:
            estado = "sin_publicador"

        registros.append({
            "iso": iso, "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": estado,
            "publicadores": len(detalle),
            "detenidos": sum(1 for d in detalle if d["detenido"]),
            "detalle": detalle[:6],
        })

    sinNinguno = [r["pais"] for r in registros if r["estado"] == "sin_publicador"]

    vacios = [
        "MIDE LA PUBLICACION, NO LA CONTRATACION. Un Estado que compra mucho y publica "
        "poco aparece con poca cobertura, y uno que compra poco y publica todo aparece "
        "con mucha. NO ES UNA MEDIDA DE VOLUMEN DE COMPRA NI DE LIMPIEZA.",
        "NO SE DISTINGUE EL PUBLICADOR NACIONAL DEL SUBNACIONAL, porque el registro no "
        "lo declara. Mexico tiene dieciocho publicadores y la mayoria son de un estado "
        "o de un organismo: leer ese numero como cobertura nacional seria falso. "
        "Clasificarlos por el titulo seria inventar una distincion que la fuente no trae.",
        f"NO FIGURAR ACA NO PRUEBA QUE EL ESTADO NO PUBLIQUE. Prueba que no publica EN EL "
        f"FORMATO QUE PERMITE COMPARARLO, que es una afirmacion mas chica y verdadera. "
        f"Los {len(sinNinguno)} Estados sin publicador son: {', '.join(sinNinguno)}.",
        "LA FECHA ES HASTA DONDE LLEGA LA SERIE PUBLICADA, no cuando se toco el archivo. "
        "Un publicador puede haberse leido ayer y contener contratos que terminan en "
        "2021; el registro declara las dos fechas por separado.",
        "EL RECUENTO DE PUBLICADORES NO SE SUMA ENTRE ESTADOS ni se promedia: dieciocho "
        "publicadores subnacionales no son mejores que uno nacional que cubra todo.",
    ]

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=2,
        corroborado=False,
        nota=("Registro de publicadores del estandar de contrataciones abiertas, "
              "mantenido por la organizacion que define ese estandar. Fiabilidad B "
              "porque es un tercero con criterio propio, no el organismo que contrata. "
              "Credibilidad 2 porque se verifico que el publicador figura y hasta "
              "cuando llega su serie, NO el contenido de los contratos."),
    )

    return comun.escribir(
        colector="contratacion",
        capa="publico",
        fuente="Registro de publicadores de contrataciones abiertas",
        url_fuente=REGISTRO,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados_con_publicador": conPublicador,
                "estados_con_serie_vigente": vigentes,
                "estados_sin_publicador": len(sinNinguno),
                "estados_del_padron": len(registros),
                "publicadores_en_la_region": sum(r["publicadores"] for r in registros),
                "meses_para_considerar_vigente": MESES_VIGENTE,
                "consultado": comun.ahora(),
            },
            "sin_publicador": sinNinguno,
        },
    )


if __name__ == "__main__":
    comun.correr("contratacion", recolectar)
