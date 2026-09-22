# -*- coding: utf-8 -*-
"""Terrorismo — Global Terrorism Index (GTI), Institute for Economics & Peace (IEP).

QUÉ AGREGA, Y POR QUÉ HACÍA FALTA
----------------------------------
La sección «Terrorismo» del registro se quedó sin fuente propia el 21/9/2026:
la Base Global de Terrorismo (START, vía Our World in Data) se retiró porque su
EULA prohíbe la redistribución (ver `colectores/owd.py` y
`SERIES_DETENIDAS` en `colectores/comun.py`). Lo que quedó en su lugar fue un
puntero a «Violencia organizada» (UCDP), que **mide otra cosa** —violencia
organizada con un umbral de 25 muertes anuales— y así se declaró, sin
presentarse como reemplazo.

Este colector cierra ese vacío con **fuente propia de terrorismo**: el GTI
publica, para cada país y año, un puntaje de impacto del terrorismo y el
recuento de atentados, muertes, heridos y rehenes que ese puntaje resume.

  · **gti_score** — Índice del Terrorismo Global. Compuesto ponderado de
    atentados, muertes, heridos y rehenes de los últimos cinco años (metodología
    del IEP); 0 es sin impacto registrado, y no tiene techo fijo.
  · **gti_incidentes**, **gti_muertes**, **gti_heridos**, **gti_rehenes** — los
    cuatro recuentos anuales que alimentan el puntaje, publicados aparte porque
    un score compuesto esconde si lo que subió fueron los atentados o las
    víctimas por atentado.

CÓMO — archivo file-drop, con licencia gestionada a mano, sin puerta en línea
--------------------------------------------------------------------------
El GTI **no tiene descarga pública directa**: el IEP lo entrega por licencia,
a pedido, mediante un formulario de solicitud de datos
(`economicsandpeace.org/consulting/data-licensing` — verificado en vivo el
21/9/2026 por `owd.py`, que dejó la gestión pendiente). La Dirección tramitó
esa licencia y bajó el archivo `GTI_PublicReleaseData_2026.xlsx` a mano. Este
colector **no intenta ninguna descarga en línea**: es el mismo patrón que
Latinobarómetro y que la copia del Servicio Geológico de los Estados Unidos
(`colectores/fijas/usgs-mcs2026/`) — una fuente gated, con su copia guardada
en el repositorio y su procedencia declarada en
`colectores/fijas/gti-iep-2026/LEEME.md`.

Lo que se guarda en el repositorio **no es el archivo del IEP entero**: son
solo las filas de los Estados de América Latina y el Caribe, en un CSV más
liviano y más fácil de auditar que el XLSX de 163 países. Ver el LEEME de esa
carpeta para la decisión completa.

LICENCIA — no comercial, y se declara pegada al dato
-------------------------------------------------------
El GTI se licencia **Creative Commons Atribución-NoComercial-CompartirIgual
4.0 (CC BY-NC-SA 4.0)**, con atribución obligatoria al IEP. Este archivo se
publica con `restriccion_de_uso="gti_iep_no_comercial"`: el dato vive en el
registro público y gratuito de SIWA, y no puede viajar a ningún producto que
la Fundación cobre sin gestionar antes una licencia distinta.

UNA SOLA FUENTE, Y SE DECLARA ASÍ
------------------------------------
El GTI es la única fuente de terrorismo que este registro tiene: UCDP mide
violencia organizada, que es otra cosa, y no corrobora al GTI. La
calificación de Almirantazgo de este conjunto queda con `corroborado=False`
y la regla de las dos fuentes (`herramientas/segunda-fuente.py`, asunto
«terrorismo») lo va a mostrar en la agenda de búsqueda de segunda fuente, no
como falla: es la realidad del asunto, no un error de este colector.

QUÉ NO TRAE, A PROPÓSITO
---------------------------
El archivo del IEP también trae un `rank` (posición mundial entre 163 países).
No se republica como indicador aparte: ordena exactamente igual que
`gti_score` y, mezclado en una lista de solo 23 Estados de la región,
un «puesto 100 de 163» sin los otros 140 países a la vista confunde más de lo
que aclara. Quien lo necesite lo tiene en el archivo fuente citado.
"""
from __future__ import annotations

import csv
from pathlib import Path

import comun
import geo

COLECTOR = "gti"
CAPA = "publico"

FUENTE = ("Institute for Economics & Peace (IEP) — Global Terrorism Index 2026: "
          "Measuring the Impact of Terrorism")
URL_FUENTE = "https://www.economicsandpeace.org/"

# EL RECORTE FILE-DROP. No hay puerta en línea: ver el docstring y el LEEME de
# la carpeta. Si el archivo no está, el colector falla y lo declara — nunca
# escribe un valor de ejemplo (doctrina/siwa.md §8.1).
COPIA_GTI = Path(__file__).resolve().parent / "fijas" / "gti-iep-2026" / "GTI_ALC_2011-2025.csv"

# Los diez Estados del padrón que el GTI no incluye en esta edición. Se declara
# a mano y no se infiere de la ausencia en el archivo, porque una ausencia por
# fuente caída y una ausencia real del productor se ven igual si no se avisa.
FUERA_DEL_GTI = {"ATG", "BHS", "BLZ", "BRB", "DMA", "GRD", "KNA", "LCA", "VCT", "SUR"}

MEDIDAS = [
    {"clave": "gti_score", "columna": "score", "rotulo": "Índice del Terrorismo Global (GTI)",
     "unidad": "índice GTI (0 = sin impacto registrado, sin techo fijo)",
     "cautela": "Es un compuesto ponderado de atentados, muertes, heridos y rehenes de los "
                "últimos cinco años, no la cuenta de un solo año. Un score alto dice que el "
                "impacto del terrorismo fue alto en la ventana que pondera el índice, no "
                "necesariamente en el último año publicado."},
    {"clave": "gti_incidentes", "columna": "incidents", "rotulo": "Atentados terroristas registrados (GTI)",
     "unidad": "hechos por año",
     "cautela": "Cuenta hechos que el IEP codificó como terrorismo bajo su propia definición, "
                "que es una definición disputada: varios Estados de la región han calificado "
                "de terrorista a la protesta social, y ese uso político del término no es el "
                "que codifica este conjunto."},
    {"clave": "gti_muertes", "columna": "fatalities", "rotulo": "Muertes por atentados terroristas (GTI)",
     "unidad": "personas por año",
     "cautela": "Muertes atribuidas a los atentados que el IEP codificó en el año. No se "
                "suma con «Violencia organizada» (UCDP): miden universos distintos y sumarlos "
                "contaría hechos de una sola vez si se solaparan, o ninguno si no."},
    {"clave": "gti_heridos", "columna": "injuries", "rotulo": "Heridos en atentados terroristas (GTI)",
     "unidad": "personas por año",
     "cautela": "Heridos en los mismos hechos que las dos medidas anteriores. Un país con "
                "muchos heridos y pocas muertes no tuvo menos atentados: tuvo atentados menos "
                "letales, lo que no es lo mismo que menos graves."},
    {"clave": "gti_rehenes", "columna": "hostages", "rotulo": "Rehenes tomados en atentados terroristas (GTI)",
     "unidad": "personas por año",
     "cautela": "Personas tomadas como rehenes en los hechos que el IEP codificó como "
                "terrorismo. En la mayoría de los Estados y años de la región vale cero."},
]


def _numero(v):
    try:
        v = str(v).strip()
        return None if v in ("", "None") else float(v)
    except (TypeError, ValueError):
        return None


def _leer_copia() -> list:
    if not COPIA_GTI.exists():
        raise RuntimeError(
            f"No está la copia del GTI ({COPIA_GTI.relative_to(comun.RAIZ)}). Es una fuente "
            "file-drop sin puerta en línea: sin el archivo, este colector no tiene de dónde "
            "leer y no escribe ningún dato de reemplazo.")
    with COPIA_GTI.open(encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        raise RuntimeError("La copia del GTI está vacía: no se publica un registro sin filas.")
    return filas


def construir():
    padron = geo.padron()
    filas = _leer_copia()

    por_iso: dict = {}
    for fila in filas:
        iso = (fila.get("iso3c") or "").strip()
        anio = _numero(fila.get("year"))
        if not iso or anio is None:
            continue
        por_iso.setdefault(iso, {})[int(anio)] = fila

    registros = []
    cobertura = {m["clave"]: 0 for m in MEDIDAS}
    for p in padron:
        iso = p["iso"]
        serie_por_anio = por_iso.get(iso)
        registro = {"iso": iso, "pais": p["pais"], "bloque": p.get("bloque")}
        if not serie_por_anio:
            registro["estado"] = "sin_dato_gti"
            registro["indicadores"] = {}
            if iso in FUERA_DEL_GTI:
                registro["por_que_no"] = (
                    "El Global Terrorism Index no incluye a este Estado en esta edición: no "
                    "dice nada sobre su situación de terrorismo, dice que el IEP no lo codifica.")
            registros.append(registro)
            continue

        anios = sorted(serie_por_anio)
        ultimo = anios[-1]
        indicadores = {}
        for m in MEDIDAS:
            serie = [{"anio": a, "valor": _numero(serie_por_anio[a].get(m["columna"]))}
                     for a in anios if _numero(serie_por_anio[a].get(m["columna"])) is not None]
            if not serie:
                continue
            valor_ultimo = serie[-1]["valor"]
            indicadores[m["clave"]] = {
                "rotulo": m["rotulo"],
                "valor": valor_ultimo,
                "anio": serie[-1]["anio"],
                "unidad": m["unidad"],
                "no_comparable_entre_paises": False,
                "serie": serie,
            }
            cobertura[m["clave"]] += 1
        registro["estado"] = "con_dato" if indicadores else "sin_dato_gti"
        registro["indicadores"] = indicadores
        registro["anio"] = ultimo
        registros.append(registro)

    con_dato = [r for r in registros if r["indicadores"]]
    sin_dato = [r["pais"] for r in registros if not r["indicadores"] and r["iso"] not in FUERA_DEL_GTI]
    ultimo_global = max((r["anio"] for r in con_dato if "anio" in r), default=None)

    vacios = [
        "**Fuente única de esta materia.** El Global Terrorism Index es la sola fuente de "
        "terrorismo del registro: «Violencia organizada» (UCDP) mide otra cosa y no lo "
        "corrobora. La calificación de este conjunto queda sin corroborar, y así se declara "
        "en vez de mezclarlo con UCDP para simular una segunda fuente que no existe.",
        f"**{len(FUERA_DEL_GTI)} Estados del padrón no están en el GTI**: Antigua y Barbuda, "
        "Bahamas, Belice, Barbados, Dominica, Granada, San Cristóbal y Nieves, Santa Lucía, "
        "San Vicente y las Granadinas y Surinam. No es que el IEP no les mida terrorismo: es "
        "que esta edición no los codifica. No aparecer no es lo mismo que tener cero.",
        "**Es file-drop, no una fuente en línea.** El IEP no tiene descarga pública directa: "
        "entrega el archivo por licencia, a pedido. Este colector lee la copia que la "
        "Dirección gestionó y bajó a mano (`colectores/fijas/gti-iep-2026/`), y no reintenta "
        "ninguna descarga: si esa copia falta, el colector falla y lo declara.",
        "**Licencia no comercial (CC BY-NC-SA 4.0), con atribución al IEP.** Este dato no "
        "puede viajar a ningún producto que la Fundación cobre; ver «restriccion_de_uso».",
        "**El «score» es un compuesto de cinco años, no la foto de uno.** Un país puede tener "
        "score alto con cero atentados en el último año publicado, si tuvo atentados graves "
        "en los cuatro anteriores. Los cuatro recuentos anuales —atentados, muertes, heridos, "
        "rehenes— se publican aparte para que esa diferencia no quede escondida.",
        "**«Terrorismo» es, de por sí, una definición disputada.** Varios Estados de la "
        "región han calificado de terrorista a la protesta social; la definición que aplica "
        "acá es la que codifica el IEP, no una de la Fundación.",
        "**El world rank del archivo original no se republica.** Ordena igual que "
        "«gti_score» y, sin los otros 140 países del mundo a la vista, confunde más de lo "
        "que aclara en una lista de solo 23 Estados. Quien lo necesite lo tiene en la fuente.",
    ]
    if sin_dato:
        vacios.append(
            f"{len(sin_dato)} Estados del padrón SÍ están en el GTI pero sin fila legible en "
            f"la copia guardada: {', '.join(sin_dato)}. Revisar el recorte.")

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=3,
        corroborado=False,
        nota=("Índice de un centro de estudios (IEP) con método publicado y actualización "
              "anual, ampliamente citado por organismos internacionales. Credibilidad 3 "
              "porque el score es un compuesto ponderado —no un acto administrativo único— y "
              "porque este registro no tiene una segunda fuente que mida terrorismo en el "
              "mismo sentido: UCDP mide violencia organizada, que es otra cosa."),
    )

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente=FUENTE,
        url_fuente=URL_FUENTE,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        restriccion="gti_iep_no_comercial",
        extra={
            "indicadores": [
                {"clave": m["clave"], "rotulo": m["rotulo"], "eje": "Seguridad",
                 "unidad": m["unidad"], "mas_es_peor": True, "sin_direccion": False,
                 "origen": "Institute for Economics & Peace — Global Terrorism Index 2026",
                 "cautela": m["cautela"]}
                for m in MEDIDAS
            ],
            "resumen": {
                "anio": ultimo_global,
                "estados_con_dato": len(con_dato),
                "estados_del_padron": len(registros),
                "estados_fuera_del_gti": len(FUERA_DEL_GTI),
                "cobertura": cobertura,
                "archivo": COPIA_GTI.name,
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
