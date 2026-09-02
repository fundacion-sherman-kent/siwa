"""Incorpora las Islas Malvinas a la geometría de la Argentina.

POR QUÉ ESTÁ ESTA HERRAMIENTA Y NO EL RESULTADO A MANO
------------------------------------------------------
El contorno **no se dibuja**: se toma de Natural Earth, que es la misma fuente
de la que salen los otros 33 contornos del mapa y es de dominio público.
Dibujar un archipiélago a mano sería fabricar geometría, y este registro no
fabrica nada.

LA POSICIÓN, DECLARADA
----------------------
La Fundación Sherman Kent tiene sede en la Argentina y **sigue la posición
argentina**: las Islas Malvinas son territorio argentino. La misma Natural Earth
clasifica el archipiélago como `TYPE: "Disputed"`, con soberanía atribuida al
Reino Unido, que lo administra; las Naciones Unidas lo tienen inscripto como
territorio no autónomo con una disputa de soberanía pendiente de negociación
entre ambos Estados.

**Ningún mapa es neutral en un territorio en disputa: o lo dibuja de un lado, o
del otro, o lo omite —que también es una posición—.** Lo que corresponde a un
registro serio no es fingir neutralidad, sino **decir qué posición toma**. Por
eso el mapa lleva la aclaración al pie, y por eso esta herramienta existe: para
que la decisión sea visible, reproducible y reversible.

    python herramientas/malvinas.py

Se corre a mano, una sola vez, y no forma parte del robot.
"""

from __future__ import annotations

import json
import pathlib
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
MAPA = RAIZ / "sitio" / "geo" / "paises-alc.geojson"
FUENTE = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
          "master/geojson/ne_50m_admin_0_countries.geojson")
NAVEGADOR = ("Mozilla/5.0 (compatible; SIWA/0.1; Fundacion Sherman Kent; "
             "direjecutiva@fundacionkent.org)")


def _partes(geometria: dict) -> list:
    """Devuelve las partes de un polígono simple o múltiple, siempre como lista."""
    if geometria["type"] == "Polygon":
        return [geometria["coordinates"]]
    if geometria["type"] == "MultiPolygon":
        return list(geometria["coordinates"])
    raise RuntimeError(f"Geometria inesperada: {geometria['type']}")


def incorporar() -> None:
    mapa = json.loads(MAPA.read_text(encoding="utf-8"))
    argentina = next(f for f in mapa["features"] if f["properties"]["iso"] == "ARG")

    # Idempotente: si ya se incorporó, no se duplica el archipiélago.
    if argentina["properties"].get("incluye_malvinas"):
        print("Ya estaban incorporadas. No se hace nada.")
        return

    peticion = urllib.request.Request(FUENTE, headers={"User-Agent": NAVEGADOR})
    with urllib.request.urlopen(peticion, timeout=180) as respuesta:
        mundo = json.loads(respuesta.read(60_000_000))

    isla = next(
        (f for f in mundo["features"]
         if str(f["properties"].get("ISO_A3", "")).upper() == "FLK"
         or "falkland" in str(f["properties"].get("ADMIN", "")).lower()),
        None)
    if isla is None:
        raise RuntimeError(
            "No se hallo el archipielago en Natural Earth. NO se inventa el "
            "contorno: se corrige la busqueda o no se incorpora.")

    print("hallado en la fuente:",
          {k: isla["properties"].get(k) for k in ("NAME", "NAME_ES", "TYPE", "SOVEREIGNT")})

    antes = _partes(argentina["geometry"])
    argentina["geometry"] = {
        "type": "MultiPolygon",
        "coordinates": antes + _partes(isla["geometry"]),
    }
    argentina["properties"]["incluye_malvinas"] = True

    MAPA.write_text(json.dumps(mapa, ensure_ascii=False), encoding="utf-8")
    print(f"Argentina: {len(antes)} partes -> {len(_partes(argentina['geometry']))}")
    print(f"{MAPA.name}: {MAPA.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    incorporar()
