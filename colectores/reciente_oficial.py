"""Lo más reciente que cada Estado publica de su propia criminalidad.

POR QUÉ EXISTE
--------------
La serie comparable de homicidios es de la UNODC y llega con **tres a cuatro
años de retraso**, porque la UNODC recibe de los Estados, valida y recién
entonces publica. No hay forma de acelerarla, y publicar una cifra «al día» que
la fuente no publicó sería inventarla.

Pero **los Estados sí publican lo suyo, y rápido**: la Policía Nacional de
Colombia actualiza a diario, el SNIC argentino y el Secretariado mexicano
mensualmente. Este colector no reemplaza la serie comparable: **la acompaña**,
diciendo qué publicó cada Estado de sí mismo y cuándo.

LA REGLA QUE LO ORDENA, Y NO ES NEGOCIABLE
------------------------------------------
`ESTO NO ES COMPARABLE ENTRE PAÍSES Y NO SE SUMA.` Cada Estado define el delito
a su manera, lo cuenta con su método y lo publica con su cadencia. Una serie
regional armada sumando estas cifras sería **una serie falsa**. Por eso este
colector publica **la existencia, la fecha y la dirección** —no una cifra
regional—: manda al lector al original, donde la definición está escrita.

Es la misma arquitectura que la señal de prensa: va **al lado** del indicador,
nunca adentro, y dice explícitamente que no actualiza la cifra comparable.

LO QUE NO HACE
--------------
No descarga las cifras ni las normaliza. Siete portales tienen siete esquemas
distintos, y homologarlos a mano seria inventar una comparabilidad que los
propios Estados no ofrecen.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

import comun
import geo

PORTALES = Path(__file__).resolve().parent / "oficiales.json"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Se busca con el vocabulario que los Estados usan de verdad, no con el nuestro.
TERMINOS = [
    "homicidios", "delitos", "criminalidad",
    "seguridad ciudadana", "hechos delictivos",
]

# Un conjunto entra solo si su titulo habla del hecho delictivo. Sin esto entran
# nominas de empleados y ejecuciones presupuestarias de organismos de seguridad,
# que se actualizan seguido y no dicen nada del delito.
PERTINENTE = re.compile(
    r"delito|delictiv|homicid|criminal|hurto|robo|lesion|secuestro|extorsi|"
    r"violencia|femicid|feminicid|denuncia|imputaci|victim", re.I)

# Y se descarta lo que es del ORGANISMO y no del fenomeno.
ADMINISTRATIVO = re.compile(
    r"n[oó]mina|presupuest|balance general|directorio|sueldo|planilla|"
    r"viatico|licitaci|contrato", re.I)

MESES_UTILES = 18   # más viejo que esto ya no es «lo más reciente»


def _consultar(portal: dict, termino: str) -> list:
    base = portal["base"].rstrip("/")
    q = urllib.parse.quote(termino)
    if portal["tipo"] == "CKAN":
        url = f"{base}/api/3/action/package_search?q={q}&rows=12"
    else:
        url = f"{base}/api/catalog/v1?q={q}&limit=12"
    try:
        peticion = urllib.request.Request(
            url, headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
        with urllib.request.urlopen(peticion, timeout=35) as respuesta:
            crudo = json.loads(respuesta.read(900_000).decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 — la falla del portal se declara arriba
        return []

    salida = []
    if portal["tipo"] == "CKAN":
        for c in crudo.get("result", {}).get("results", []):
            salida.append({
                "titulo": (c.get("title") or "").strip(),
                "organismo": ((c.get("organization") or {}).get("title") or "").strip(),
                "actualizado": (c.get("metadata_modified") or "")[:10],
                "enlace": f"{base}/dataset/{c.get('name','')}",
                "formatos": sorted({(r.get("format") or "").upper()
                                    for r in (c.get("resources") or []) if r.get("format")}),
            })
    else:
        for c in crudo.get("results", []):
            rec = c.get("resource", {})
            salida.append({
                "titulo": (rec.get("name") or "").strip(),
                "organismo": ((c.get("owner") or {}).get("display_name") or "").strip(),
                "actualizado": (rec.get("updatedAt") or "")[:10],
                "enlace": c.get("permalink", base),
                "formatos": [],
            })
    return salida


def _delEstado(portal: dict) -> tuple:
    vistos = {}
    for termino in TERMINOS:
        for c in _consultar(portal, termino):
            if not c["titulo"] or not c["actualizado"]:
                continue
            if not PERTINENTE.search(c["titulo"]) or ADMINISTRATIVO.search(c["titulo"]):
                continue
            previo = vistos.get(c["enlace"])
            if not previo or c["actualizado"] > previo["actualizado"]:
                vistos[c["enlace"]] = c
    lista = sorted(vistos.values(), key=lambda c: c["actualizado"], reverse=True)
    return portal["iso"], lista[:6]


def _dias(fecha: str) -> int | None:
    try:
        return (date.today() - date.fromisoformat(fecha)).days
    except Exception:  # noqa: BLE001 — una fecha ilegible no descarta el conjunto
        return None


def recolectar():
    portales = json.loads(PORTALES.read_text(encoding="utf-8"))["portales"]
    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        hallado = dict(ejecutor.map(_delEstado, portales))

    registros, frescos = [], 0
    for pais in geo.padron():
        iso = pais["iso"]
        conjuntos = hallado.get(iso)
        if conjuntos is None:
            estado, detalle = "sin_portal", []
        elif not conjuntos:
            estado, detalle = "sin_conjunto", []
        else:
            detalle = []
            for c in conjuntos:
                d = _dias(c["actualizado"])
                detalle.append({**c, "dias": d})
            mas_nuevo = detalle[0]["dias"]
            estado = ("al_dia" if mas_nuevo is not None and mas_nuevo <= MESES_UTILES * 30
                      else "atrasado")
            if estado == "al_dia":
                frescos += 1
        registros.append({
            "iso": iso, "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": estado, "conjuntos": detalle,
        })

    vacios = [
        "ESTO NO ES COMPARABLE ENTRE PAISES Y NO SE SUMA. Cada Estado define el delito a "
        "su manera, lo cuenta con su metodo y lo publica con su cadencia. Una serie "
        "regional armada sumando estas cifras seria UNA SERIE FALSA. Va AL LADO de la "
        "serie comparable de la UNODC, nunca adentro, y NO la actualiza.",
        "NO SE DESCARGAN LAS CIFRAS: se publica que el conjunto existe, de cuando es y "
        "donde esta. Siete portales tienen siete esquemas distintos, y homologarlos a mano "
        "seria inventar una comparabilidad que los propios Estados no ofrecen.",
        "LA FECHA ES LA DE ACTUALIZACION DEL CATALOGO, no la del hecho. Un conjunto puede "
        "actualizarse hoy y contener datos del anio pasado: dice cuando el Estado toco el "
        "archivo, no hasta cuando llega la serie.",
        "Solo alcanza a los Estados con portal de datos abiertos consultable. Los demas "
        "quedan como SIN PORTAL, que no prueba que no publiquen: puede exigir registro, "
        "interponer un obstaculo automatico o publicar sin interfaz.",
        "Un conjunto entra si su titulo habla del hecho delictivo. Uno rotulado con otro "
        "vocabulario no aparece; y se descartan las piezas administrativas del organismo "
        "—nominas, presupuestos, directorios— que se actualizan seguido y no dicen nada "
        "del delito.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Catalogos oficiales de los propios Estados, consultados por su interfaz "
              "publica. Fiabilidad A porque publica el organismo responsable. Credibilidad "
              "2 y no 1 porque NO se verifico el contenido de cada conjunto: se verifico "
              "que existe, de cuando es y donde esta."),
    )

    return comun.escribir(
        colector="reciente_oficial",
        capa="publico",
        fuente="Catalogos oficiales de los Estados — lo mas reciente publicado",
        url_fuente="https://fundacion-sherman-kent.github.io/siwa/sitio/index.html",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados_con_portal": len(portales),
                "estados_con_publicacion_reciente": frescos,
                "estados_del_padron": len(registros),
                "meses_para_considerar_reciente": MESES_UTILES,
                "consultado": comun.ahora(),
            },
            "terminos_de_busqueda": TERMINOS,
        },
    )


if __name__ == "__main__":
    comun.correr("reciente_oficial", recolectar)
