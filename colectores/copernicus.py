"""Qué se puede mirar desde arriba, y de cuándo es lo último que hay.

POR QUÉ EXISTE
--------------
Minería ilegal, deforestación, puertos y pasos fronterizos son cuatro materias
donde ninguna fuente publica una serie comparable de la región. Lo que sí existe
es **imagen satelital libre y reciente**, y hasta hoy el registro no decía
siquiera si la había.

Este colector no mira la imagen: **dice que existe, de cuándo es y dónde está**.
Es la misma arquitectura que la publicación oficial reciente —se publica la
existencia, la fecha y el enlace, y el lector va al original—.

LO QUE SE PUEDE COMPARAR Y LO QUE NO
------------------------------------
**El recuento de escenas NO se compara entre Estados.** Depende del tamaño del
territorio, de la latitud y de por dónde pasa el satélite: Brasil tiene más
escenas que Granada por geometría, no por nada que se pueda decir de ninguno de
los dos. Ordenar Estados por esa cifra sería ordenarlos por superficie.

**Lo que sí es comparable es la frescura**: cuántos días hace de la última
escena. Ahí un Estado grande y uno chico están en igualdad, porque el satélite
pasa por todos con cadencia parecida.

LO QUE NO DICE, Y CONVIENE TENERLO PRESENTE
-------------------------------------------
- **Una imagen no acredita un hecho.** Prueba que había algo el día que pasó el
  satélite; no prueba qué era ni de quién. Entra como material de recolección,
  jamás como cifra.
- **La nube manda en el trópico.** Este colector cuenta escenas *disponibles*,
  no escenas *utilizables*: buena parte de América Central y de la Amazonia está
  cubierta buena parte del año.
- **Se consulta por un rectángulo, no por la forma del país.** El rectángulo de
  Chile abarca medio océano Pacífico y parte de la Argentina.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import comun
import geo

CATALOGO = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
MIRADOR = "https://browser.dataspace.copernicus.eu/"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DIAS = 15          # la ventana de observación
COLECCION = "SENTINEL-2"


def _rectangulos() -> dict:
    """El rectángulo de cada Estado, del mismo padrón que dibuja el mapa."""
    d = json.loads(Path(geo.PADRON_GEO).read_text(encoding="utf-8"))
    salida = {}
    for f in d.get("features", []):
        iso = (f.get("properties") or {}).get("iso")
        caja = f.get("bbox")
        if iso and caja and len(caja) == 4:
            salida[iso] = caja
    return salida


def _consultar(par: tuple) -> tuple:
    iso, caja, desde = par
    o, s, e, n = caja
    poligono = f"POLYGON(({o} {s},{e} {s},{e} {n},{o} {n},{o} {s}))"
    filtro = (f"Collection/Name eq '{COLECCION}' and "
              f"OData.CSC.Intersects(area=geography'SRID=4326;{poligono}') and "
              f"ContentDate/Start gt {desde}T00:00:00.000Z")
    url = CATALOGO + "?" + urllib.parse.urlencode({
        "$filter": filtro, "$top": "1", "$count": "true",
        "$orderby": "ContentDate/Start desc",
    })
    try:
        peticion = urllib.request.Request(
            url, headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
        with urllib.request.urlopen(peticion, timeout=120) as respuesta:
            d = json.loads(respuesta.read(400_000).decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 — la falla de un Estado no tumba la corrida
        return iso, None

    primera = (d.get("value") or [None])[0]
    return iso, {
        "escenas": d.get("@odata.count"),
        "mas_reciente": ((primera or {}).get("ContentDate") or {}).get("Start", "")[:10] or None,
        "nombre": (primera or {}).get("Name"),
    }


def _dias(fecha: str | None) -> int | None:
    try:
        return (date.today() - date.fromisoformat(fecha)).days
    except Exception:  # noqa: BLE001
        return None


def recolectar():
    cajas = _rectangulos()
    fin = datetime.now(timezone.utc).date()
    desde = (fin - timedelta(days=DIAS)).isoformat()

    tareas = [(p["iso"], cajas[p["iso"]], desde) for p in geo.padron() if p["iso"] in cajas]
    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        hallado = dict(ejecutor.map(_consultar, tareas))

    registros, conImagen, sinRectangulo, sinRespuesta = [], 0, 0, 0
    frescos = []
    for pais in geo.padron():
        iso = pais["iso"]
        if iso not in cajas:
            sinRectangulo += 1
            registros.append({
                "iso": iso, "pais": pais["pais"], "bloque": pais["bloque"],
                "estado": "sin_rectangulo_en_el_padron",
            })
            continue

        d = hallado.get(iso)
        if d is None:
            sinRespuesta += 1
            estado = "el_catalogo_no_respondio"
            escenas = dias = mas = None
        else:
            escenas = d["escenas"] or 0
            mas = d["mas_reciente"]
            dias = _dias(mas)
            if escenas:
                conImagen += 1
                if dias is not None:
                    frescos.append(dias)
            estado = "con_imagen" if escenas else "sin_imagen_en_la_ventana"

        o, s, e, n = cajas[iso]
        registros.append({
            "iso": iso, "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": estado,
            "escenas": escenas,
            "mas_reciente": mas,
            "dias_desde_la_ultima": dias,
            "mirador": (MIRADOR + "?zoom=6"
                        + f"&lat={round((s + n) / 2, 4)}&lng={round((o + e) / 2, 4)}"
                        + "&cloudCoverage=30&dateMode=SINGLE"),
        })

    vacios = [
        "EL RECUENTO DE ESCENAS NO SE COMPARA ENTRE ESTADOS. Depende del tamanio del "
        "territorio, de la latitud y de por donde pasa el satelite: Brasil tiene mas "
        "escenas que Granada por geometria, no por nada que se pueda decir de ninguno "
        "de los dos. Ordenar Estados por esa cifra seria ordenarlos por superficie. LO "
        "QUE SI ES COMPARABLE ES LA FRESCURA: cuantos dias hace de la ultima escena.",
        "UNA IMAGEN NO ACREDITA UN HECHO. Prueba que habia algo el dia que paso el "
        "satelite; NO prueba que era ni de quien. Entra como material de recoleccion, "
        "jamas como cifra, y ningun juicio del registro se apoya en ella.",
        "SE CUENTAN ESCENAS DISPONIBLES, NO UTILIZABLES. La nube manda en el tropico: "
        "buena parte de America Central y de la Amazonia esta cubierta buena parte del "
        "anio. Una escena existente puede no dejar ver nada.",
        "SE CONSULTA POR UN RECTANGULO, NO POR LA FORMA DEL PAIS. El rectangulo de "
        "Chile abarca medio oceano Pacifico y parte de la Argentina, de modo que "
        "escenas contadas para un Estado pueden caer fuera de el.",
        "NO SE DESCARGA NI SE SIRVE NINGUNA IMAGEN: se publica que existe, de cuando es "
        "y el enlace al mirador oficial, que es donde vive. Descargarla exige registro "
        "gratuito, y ese tramite no lo hace el robot.",
        f"LA VENTANA ES DE {DIAS} DIAS y se mueve con cada corrida: sirve para ver que "
        "hay ahora, NO para comparar contra el mes pasado.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Catalogo del programa de observacion de la Tierra de la Union Europea, "
              "consultado por su interfaz publica y sin credencial. Fiabilidad A porque "
              "publica el organismo que opera los satelites. Credibilidad 2 porque se "
              "verifico QUE LA ESCENA EXISTE y de cuando es, NO su contenido: nadie "
              "miro la imagen."),
    )

    frescos.sort()
    return comun.escribir(
        colector="copernicus",
        capa="publico",
        fuente="Copernicus — catálogo de observación de la Tierra de la Unión Europea",
        url_fuente=CATALOGO,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "ventana_dias": DIAS,
                "desde": desde,
                "coleccion": COLECCION,
                "estados_con_imagen": conImagen,
                "estados_sin_imagen": len(registros) - conImagen - sinRespuesta - sinRectangulo,
                "el_catalogo_no_respondio": sinRespuesta,
                "estados_del_padron": len(registros),
                "escenas_en_la_region": sum(r.get("escenas") or 0 for r in registros),
                "dias_mediana_desde_la_ultima": (frescos[len(frescos) // 2] if frescos else None),
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("copernicus", recolectar)
