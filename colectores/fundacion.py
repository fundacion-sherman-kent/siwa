"""Los informes de la propia Fundación.

Cierra el circuito: **SIWA entrega el dato en abierto; la Fundación publica el
análisis**. Este colector lee el canal de `fundacionkent.org` y trae los informes
más recientes, de modo que cuando la Fundación publica uno nuevo **aparece solo
en el registro**, sin que nadie tenga que cargarlo a mano.

La escalera de difusión, que el propio canal ya declara
-------------------------------------------------------
Las categorías del sitio distinguen **Informes Libres** de **Informes
Reservados**. El registro respeta esa distinción y la muestra: al libre se entra
directo; el reservado se anuncia y su acceso lo administra la Fundación.

Lo que este colector NO hace
----------------------------
**No copia el contenido de los informes.** Trae título, fecha, categoría y
dirección: lo justo para que el lector sepa que existe y pueda ir a leerlo en la
web de la Fundación. El análisis vive allá, con su firma y sus autoridades; acá
vive el dato.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import comun

CANAL = "https://fundacionkent.org/feed"
SITIO = "https://fundacionkent.org/"
NAVEGADOR = comun.AGENTE
TOPE = 12

# Secciones de la web institucional, verificadas el 31 de agosto de 2026.
SECCIONES = [
    {"rotulo": "Informes y artículos", "url": "https://fundacionkent.org/articulos/",
     "detalle": "Los productos de análisis de la Fundación: informes, artículos académicos y de opinión."},
    {"rotulo": "Cómo trabajamos", "url": "https://fundacionkent.org/nosotros/metodo-de-analisis/",
     "detalle": "El método de análisis de la casa, del que este registro es la capa de datos."},
    {"rotulo": "Formación", "url": "https://fundacionkent.org/formacion/",
     "detalle": "Cursos y maestrías en análisis de inteligencia estratégica."},
    {"rotulo": "Quiénes somos", "url": "https://fundacionkent.org/nosotros/",
     "detalle": "La Fundación, sus autoridades y su ámbito de trabajo."},
    {"rotulo": "Transparencia", "url": "https://fundacionkent.org/transparencia/",
     "detalle": "Cómo se financia y cómo rinde cuentas la Fundación."},
    {"rotulo": "Contacto", "url": "https://fundacionkent.org/contacto/",
     "detalle": "Para requerimientos, prensa y contrapartes institucionales."},
]


def _limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", texto or "")).strip()


def recolectar():
    TOPE_BYTES = 4_000_000
    try:
        peticion = urllib.request.Request(CANAL, headers={"User-Agent": NAVEGADOR})
        with urllib.request.urlopen(peticion, timeout=45) as r:
            crudo = r.read(TOPE_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"El canal de la Fundación respondio HTTP {e.code}") from e

    # Un XML CORTADO A LA MITAD nunca parsea, y el error que devuelve —«not
    # well-formed»— hace creer que el canal esta roto cuando lo unico que pasa es
    # que el tope de lectura quedo corto. Se distingue una cosa de la otra.
    if len(crudo) > TOPE_BYTES:
        raise RuntimeError(
            f"El canal de la Fundación supera los {TOPE_BYTES // 1_000_000} MB: no se lo "
            "leyo entero y por eso no parsea. Hay que subir el tope, no culpar al canal.")
    try:
        raiz = ET.fromstring(crudo)
    except ET.ParseError as e:
        # Pasa cuando el sitio devuelve una pagina de error o un desafio del
        # cortafuegos con codigo 200. Se dice QUE llego, no solo que no parseo.
        cabeza = " ".join(crudo[:120].decode("utf-8", "replace").split())
        raise RuntimeError(
            f"El canal de la Fundación respondio 200 pero no es XML valido ({e}). "
            f"Empieza con: {cabeza}") from e

    registros = []
    for item in raiz.findall(".//item")[:TOPE]:
        titulo = _limpiar(item.findtext("title"))
        enlace = (item.findtext("link") or "").strip()
        if not titulo or not enlace:
            continue
        categorias = [_limpiar(c.text) for c in item.findall("category") if c.text]
        fecha = item.findtext("pubDate") or ""
        try:
            momento = parsedate_to_datetime(fecha).astimezone(timezone.utc)
            iso = momento.isoformat(timespec="seconds")
        except Exception:  # noqa: BLE001 — una fecha ilegible no descarta el informe
            iso = None
        # La categoria del propio sitio decide el nivel de difusion: no se supone.
        reservado = any("reservad" in c.lower() for c in categorias)
        registros.append({
            "titulo": titulo,
            "enlace": enlace,
            "categorias": categorias,
            "difusion": "reservado" if reservado else "libre",
            "publicado": iso,
            "resumen": _limpiar(item.findtext("description"))[:260],
        })

    libres = sum(1 for r in registros if r["difusion"] == "libre")
    vacios = [
        "Este colector NO copia el contenido de los informes: trae titulo, fecha, "
        "categoría y dirección. El análisis vive en la web de la Fundación, con su firma "
        "y sus autoridades; acá vive el dato.",
        "La distinción entre informe LIBRE y RESERVADO la declara el propio sitio en la "
        "categoría de cada pieza. El registro la respeta y la muestra: NO decide por su "
        "cuenta que se publica en abierto.",
        f"Se traen los {TOPE} mas recientes del canal. Los anteriores están en la web de "
        "la Fundación y no se replican acá.",
        "Un informe de la Fundación es ANÁLISIS, no dato: lleva juicios con confianza y "
        "probabilidad declaradas. Este registro publica hechos calificados y no emite "
        "juicios. Son dos productos distintos y no deben leerse como uno solo.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=1,
        corroborado=True,
        nota=("Publicaciones de la propia Fundación, tomadas de su canal oficial. "
              "Credibilidad 1 porque lo que se registra es que la pieza existe y donde "
              "esta, hecho verificable en dos lugares —el canal y la pagina—, no el "
              "contenido de su análisis."),
    )

    return comun.escribir(
        colector="fundacion",
        capa="publico",
        fuente="Fundación Sherman Kent — canal institucional",
        url_fuente=SITIO,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "informes": len(registros),
                "libres": libres,
                "reservados": len(registros) - libres,
                "consultado": comun.ahora(),
            },
            "secciones": SECCIONES,
            "sitio": SITIO,
        },
    )


if __name__ == "__main__":
    comun.correr("fundacion", recolectar)
