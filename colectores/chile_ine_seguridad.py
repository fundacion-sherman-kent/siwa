# -*- coding: utf-8 -*-
"""Chile — víctimas de homicidio del INE (Estadísticas Policiales), fuente fresca.

POR QUÉ EXISTE
--------------
El dato de delitos más fino de Chile (CEAD, por comuna) bloquea el acceso desde
la nube, igual que NASA FIRMS: el robot no puede bajarlo. Pero el Instituto
Nacional de Estadísticas (INE) publica sus «Estadísticas Policiales» en un
archivo Excel estático que SÍ se alcanza desde la nube. Trae víctimas por región
y por materia, con la Clasificación Internacional de Delitos (ICCS), y llega al
año en curso. Es la ruta limpia que reemplaza a CEAD para el robot.

CÓMO ENCUENTRA EL ARCHIVO
-------------------------
El sitio del INE arma la lista de archivos con dos servicios del gestor de
contenidos (Sitefinity): `hijosCarpeta/` da las subcarpetas y `getArchivos/` da
los archivos, ambos por POST con el campo `idFolder`. Se baja por el árbol
Estadísticas Policiales → año más reciente → el cuadro «penal», sin URL fija:
así sigue andando cuando el INE publica un año nuevo.

QUÉ PUBLICA, Y QUÉ NO
---------------------
Víctimas de homicidio registradas por Carabineros de Chile, del cuadro 18 del
archivo penal (víctimas por región, según familia y materia). Se informan las
materias de homicidio de la ICCS por separado —homicidio, homicidio calificado,
homicidio en riña— y su suma, más el femicidio. NO es la tasa: sin población por
región no se calcula, y el año en curso es PROVISIONAL (acumula lo que va del
año). No se compara con otros países: cada Estado registra a su manera.
"""
from __future__ import annotations

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun  # noqa: E402
import estado_reciente as er  # noqa: E402

COLECTOR = "chile_ine_seguridad"
CAPA = "publico"

BASE = ("https://www.ine.gob.cl/estadisticas-por-tema/sociedad-y-condiciones-de-vida/"
        "estadisticas-policiales-y-judiciales")
HIJOS = f"{BASE}/hijosCarpeta/"
ARCHIVOS = f"{BASE}/getArchivos/"
# Identificador estable de la carpeta «Estadísticas Policiales» en el gestor de
# contenidos del INE. Se arranca de acá y no de la raíz, que no responde por API.
CARPETA_POLICIALES = "3922ae2f-ada4-4a9e-a34c-0cd0887ad2c8"
# Red de seguridad: último archivo conocido, por si el servicio de listado falla.
RESPALDO = ("https://www.ine.gob.cl/docs/default-source/estadisticas-policiales-y-judiciales/"
            "cuadro-estadístico/estadisticas-policiales/2025/"
            "estadísticas-policiales_penal_2025.xlsx")
RESPALDO_ANIO = 2025

# Materias de homicidio de la ICCS en el archivo del INE (columna «Código»).
HOMICIDIO = {"702": "Homicidio", "703": "Homicidio calificado", "705": "Homicidio en riña o pelea"}
FEMICIDIO = {"720": "Femicidio íntimo", "766": "Femicidio no íntimo"}


def _post_json(url: str, id_folder: str) -> dict:
    import json
    import urllib.parse
    import urllib.request
    datos = urllib.parse.urlencode({"idFolder": id_folder}).encode()
    cab = dict(comun.CABECERAS)
    cab["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    cab["X-Requested-With"] = "XMLHttpRequest"
    pet = urllib.request.Request(url, data=datos, headers=cab)
    with urllib.request.urlopen(pet, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _hallar_archivo_penal() -> tuple[str, int]:
    """Devuelve (url del xlsx penal del año más reciente, año).

    Arranca del GUID estable de «Estadísticas Policiales» y baja al año más nuevo.
    Si el servicio de listado no responde, cae al último archivo conocido.
    """
    def anio_de(f):
        t = (f.get("Titulo") or "").strip()
        return int(t) if t.isdigit() else -1
    try:
        anios = _post_json(HIJOS, CARPETA_POLICIALES).get("folder") or []
        anios = sorted((f for f in anios if anio_de(f) > 0), key=anio_de, reverse=True)
        for f in anios:
            docs = _post_json(ARCHIVOS, f["Id"]).get("documento") or []
            penal = next((d for d in docs if "penal" in (d.get("Titulo") or "").lower()
                          and (d.get("Tipo") or "").lower() == ".xlsx"), None)
            if penal:
                return (penal["Url"] or "").replace("http:", "https:"), anio_de(f)
    except Exception:  # noqa: BLE001 — el listado es frágil; se cae al respaldo
        pass
    return RESPALDO, RESPALDO_ANIO


def _num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _victimas_por_materia(xlsx: bytes) -> dict:
    """{codigo: total_nacional} desde el cuadro 18 (columna C = Total)."""
    filas = er._planilla(xlsx, "18")
    out = {}
    for num in sorted(filas):
        cod = filas[num].get("A")
        if isinstance(cod, str) and cod.strip() in (HOMICIDIO | FEMICIDIO):
            out[cod.strip()] = _num(filas[num].get("C"))
    return out


def construir() -> Path:
    import urllib.parse
    url, anio = _hallar_archivo_penal()
    # La URL trae acentos literales (…policiales_penal…); se codifican para descargar.
    xlsx = comun.traer_crudo(urllib.parse.quote(url, safe=":/?=&"))
    materias = _victimas_por_materia(xlsx)

    homi = {c: materias.get(c) for c in HOMICIDIO if materias.get(c) is not None}
    femi = {c: materias.get(c) for c in FEMICIDIO if materias.get(c) is not None}
    total_homi = sum(homi.values()) if homi else None

    registros = [{
        "iso": "CHL", "pais": "Chile", "bloque": "Cono Sur",
        "indicadores": {
            "homicidio_ine_chile": {
                "valor": total_homi, "anio": anio, "provisional": True,
                "componentes": {HOMICIDIO[c]: v for c, v in homi.items()},
                "femicidio": {FEMICIDIO[c]: v for c, v in femi.items()},
                "detalle": (f"{total_homi} víctimas de homicidio (ICCS 702+703+705) "
                            f"registradas por Carabineros, {anio} provisional"),
            }
        },
    }]

    medida = {
        "clave": "homicidio_ine_chile", "eje": "Seguridad",
        "rotulo": "Víctimas de homicidio (INE Chile, ICCS)",
        "unidad": "víctimas registradas", "unidad_singular": "víctima",
        "mas_es_peor": True,
        "origen": "Instituto Nacional de Estadísticas de Chile — Estadísticas Policiales",
        "cautela": ("Son VÍCTIMAS registradas por Carabineros de Chile, sumando las materias de "
                    "homicidio de la ICCS (702 homicidio, 703 calificado, 705 en riña). El año en "
                    "curso es PROVISIONAL: acumula lo que va del año, no un año cerrado. No es tasa "
                    "—falta población por región— y no se compara con otros países."),
    }
    return comun.escribir(
        colector=COLECTOR, capa=CAPA,
        fuente="Instituto Nacional de Estadísticas de Chile (INE) — Estadísticas Policiales, cuadro de víctimas",
        url_fuente=BASE,
        calificacion=comun.calificar(
            "A", 2, False,
            "Instituto oficial de estadística. Credibilidad 2: es registro administrativo de las "
            "policías, sujeto a subregistro y a revisión, y el año en curso es provisional."),
        registros=registros,
        vacios=[
            "ES RECUENTO DE VÍCTIMAS, NO TASA: sin población por región no se calcula tasa.",
            "EL AÑO EN CURSO ES PROVISIONAL: acumula lo que va del año, no un año cerrado.",
            "Solo Carabineros de Chile (cuadro 18). La Policía de Investigaciones publica su propio "
            "cuadro; no se suma acá para no duplicar víctimas.",
            "NO SE COMPARA ENTRE PAÍSES: cada Estado define y registra el homicidio a su manera.",
        ],
        extra={"indicadores": [medida],
               "resumen": {"anio": anio, "archivo": url,
                           "total_homicidio": total_homi,
                           "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
