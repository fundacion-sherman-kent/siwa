"""Migrantes: venezolanos por país de destino, de la plataforma R4V.

POR QUÉ EXISTE
--------------
El mapa de corredores necesita un flujo de migración origen→destino, y el DTM no
sirve: su API sólo da desplazados INTERNOS (dentro de un país), no movimiento entre
Estados. La plataforma interagencial **R4V** (ACNUR–OIM) sí publica el corredor: los
refugiados y migrantes venezolanos que cada gobierno de destino reporta. Un solo
origen —Venezuela— hacia destinos regionales y de fuera de la región (EE.UU., España,
Italia, Portugal, Canadá), que es justo lo que el mapa quiere marcar.

QUÉ LEE, Y CÓMO
---------------
La página https://www.r4v.info/en/refugeeandmigrants trae la tabla como JSON embebido
en el bloque `drupalSettings` (clave `tables['r4v-table'].data`), un registro por país
con población, fuente y fecha. Ese JSON está en el HTML servido, así que se lee sin
navegador. Verificado en vivo el 29/9/2026: Colombia 2.844.498, Perú 1.632.322, etc.

QUÉ MIDE, Y QUÉ NO
------------------
Es el STOCK de venezolanos en cada destino que reporta el gobierno anfitrión —no el
flujo del año—, y R4V avisa que puede incluir estimación y subcontar a quienes están
en situación irregular. Las fuentes son mixtas (censos, migraciones, y estimaciones de
UNDESA), por eso la fiabilidad es B. Los renglones agregados («Others (Europe)», etc.)
y microterritorios sin coordenada del padrón no se dibujan: se declaran.
"""
from __future__ import annotations

import json
import re
import urllib.request

import comun

URL = "https://www.r4v.info/en/refugeeandmigrants"
CONTROL = "Colombia"  # el mayor destino; si no aparece, la página cambió de forma


def _bajar() -> str:
    peticion = urllib.request.Request(URL, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=120) as respuesta:
        return respuesta.read(4_000_000).decode("utf-8", "replace")


def _tabla(html: str) -> list:
    """La tabla r4v del bloque drupalSettings embebido en el HTML."""
    m = re.search(r'data-drupal-selector="drupal-settings-json"[^>]*>(.*?)</script>',
                  html, re.S)
    if not m:
        raise RuntimeError("No se encontró el bloque drupalSettings en la página de R4V. "
                           "La página cambió de forma. NO se publica.")
    ds = json.loads(m.group(1))
    tabla = (ds.get("tables") or {}).get("r4v-table") or {}
    data = tabla.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError("El bloque drupalSettings de R4V no trae tables['r4v-table'].data. "
                           "La página cambió de forma. NO se publica.")
    return data


def recolectar():
    data = _tabla(_bajar())
    registros = []
    for fila in data:
        destino = fila.get("country") or fila.get("pais")
        pobl = fila.get("poblacion")
        if not destino or not isinstance(pobl, (int, float)):
            continue
        registros.append({
            "destino": destino,
            "poblacion": int(pobl),
            "fuente": (fila.get("source") or fila.get("fuente") or "").strip(),
            "fecha": fila.get("Date") or fila.get("fecha"),
            "publicacion_r4v": fila.get("R4V Published") or fila.get("Publicacion R4V"),
        })

    # SE PRUEBA EL LECTOR ANTES DE CREERLE UN VACÍO A NADIE.
    control = next((r for r in registros if r["destino"] == CONTROL), None)
    if not control or control["poblacion"] < 1_000_000:
        raise RuntimeError(
            f"La prueba del lector falló: {CONTROL} —el mayor destino— no apareció con más de "
            "un millón. La tabla de R4V cambió de forma. NO se publica.")

    total_reportado = sum(r["poblacion"] for r in registros)
    vacios = [
        "Es el STOCK de venezolanos en cada destino que reporta el gobierno anfitrión, no el "
        "flujo del año. R4V avisa que puede incluir estimación y que probablemente subcuenta a "
        "quienes están en situación irregular.",
        "Las fuentes son mixtas: censos y registros de migración de cada país, y estimaciones de "
        "UNDESA donde el gobierno no publica un dato propio. Por eso la fiabilidad es B y cada "
        "renglón lleva su fuente y su fecha.",
        "Los renglones agregados de R4V («Others (Europe)», «Others (America)», etc.) y los "
        "microterritorios sin coordenada del padrón no se dibujan en el mapa: se cuentan acá pero "
        "no forman corredor.",
        "El origen es uno solo —Venezuela— porque R4V mide el éxodo venezolano. No es «toda la "
        "migración de la región»: es esta diáspora, que es la mayor y la mejor contada.",
    ]

    calificacion = comun.calificar(
        fiabilidad="B", credibilidad=2, corroborado=False,
        nota=("Plataforma interagencial de coordinación R4V (ACNUR–OIM), que compila las cifras "
              "oficiales de cada gobierno de destino. Fiabilidad B porque el dato lo produce cada "
              "Estado con método propio y algunos renglones son estimación de UNDESA. Credibilidad "
              "2 porque es un recuento administrativo coherente, no verificable de forma "
              "independiente y con subconteo declarado de la situación irregular."),
    )

    return comun.escribir(
        colector="migrantes_r4v",
        capa="publico",
        fuente="R4V — Plataforma de Coordinación Interagencial para Refugiados y Migrantes de Venezuela (ACNUR–OIM)",
        url_fuente=URL,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "origen": "Venezuela",
                "destinos": len(registros),
                "total_reportado": total_reportado,
                "consultado": comun.ahora(),
            },
            "licencia": ("Cifras oficiales compiladas por R4V; cita obligatoria a R4V y a la fuente "
                         "de cada renglón. SIWA se considera uso no comercial."),
        },
    )


if __name__ == "__main__":
    comun.correr("migrantes_r4v", recolectar)
