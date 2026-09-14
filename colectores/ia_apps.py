# -*- coding: utf-8 -*-
"""Asistentes de inteligencia artificial en la tienda de apps de cada país, por origen de la empresa.

POR QUÉ EXISTE
--------------
La dirección pidió saber qué IA se usan en cada país, de todo origen —de Estados
Unidos, de China, de Rusia, de Europa, de la región—, y no solo ChatGPT y Claude
(autorizado el 14/9/2026). Ninguna fuente abierta publica la cuota de uso de cada
IA por país. Lo más cercano que se puede medir, cada día y para 31 de los 33
Estados, es la tienda de apps de Apple: qué asistentes de IA están entre las más
descargadas y cuáles están disponibles.

QUÉ PUBLICA
-----------
  · Cuántos asistentes de IA hay entre las apps gratuitas más descargadas del
    país —las 100 del ranking general y las 100 de Productividad—, y de qué
    origen son sus empresas.
  · Cuántos asistentes del padrón están disponibles en la tienda del país.
  · En el archivo, el detalle por app: puesto, origen y fuente de ese origen.

LO QUE NO ES, Y SE DECLARA
--------------------------
**Un ranking de descargas no mide usuarios.** Premia lo que crece hace poco y lo
que invierte en publicidad. El iPhone es minoritario frente a Android en la
región. Los asistentes que viven dentro de otras apps —Meta AI en WhatsApp,
Gemini en Android, Copilot en Windows— no se ven acá. **Cuba y Haití no tienen
tienda de Apple.**
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "ia_apps"
CAPA = "publico"
PADRON = Path(__file__).resolve().parent / "fijas" / "ia-asistentes" / "padron.json"
GENERAL = "https://rss.applemarketingtools.com/api/v2/{cc}/apps/top-free/100/apps.json"
PRODUCTIVIDAD = "https://itunes.apple.com/{cc}/rss/topfreeapplications/limit=100/genre=6007/json"
LOOKUP = "https://itunes.apple.com/lookup?id={ids}&country={cc}"
SIN_TIENDA = {"CUB", "HTI"}   # support.apple.com/en-us/118205: no figuran
ESTADOS_UNIDOS, CHINA = "Estados Unidos", "China"


def pedir(url: str):
    for intento in range(3):
        try:
            peticion = urllib.request.Request(url, headers={"User-Agent": comun.AGENTE})
            with urllib.request.urlopen(peticion, timeout=40) as respuesta:
                return json.loads(respuesta.read())
        except urllib.error.HTTPError as error:
            if error.code in (400, 404):
                return None
        except Exception:  # noqa: BLE001 — se reintenta
            pass
        time.sleep(4 * (intento + 1))
    return None


def ranking_general(cc: str) -> dict | None:
    d = pedir(GENERAL.format(cc=cc))
    if not d:
        return None
    return {str(a["id"]): i for i, a in enumerate(d["feed"]["results"], 1)}


def ranking_productividad(cc: str) -> dict | None:
    d = pedir(PRODUCTIVIDAD.format(cc=cc))
    if not d:
        return None
    entradas = d.get("feed", {}).get("entry", [])
    entradas = entradas if isinstance(entradas, list) else [entradas]
    return {x["id"]["attributes"]["im:id"]: i for i, x in enumerate(entradas, 1)}


def disponibles(cc: str, ids: list) -> set | None:
    d = pedir(LOOKUP.format(ids=",".join(ids), cc=cc))
    if d is None:
        return None
    return {str(a.get("trackId")) for a in d.get("results") or []}


def construir() -> Path:
    padron = json.loads(PADRON.read_text(encoding="utf-8"))
    asistentes = {a["id"]: a for a in padron["asistentes"]}
    ids = list(asistentes)
    anio = datetime.now(timezone.utc).year
    registros, cobertura, caidas, leidos = [], {}, [], 0

    for p in geo.padron():
        iso = p["iso"]
        f = {"iso": iso, "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        if iso in SIN_TIENDA:
            f["sin_tienda"] = True
            registros.append(f)
            continue
        cc = comun.DOS_LETRAS[iso].lower()
        gen = ranking_general(cc); time.sleep(1)
        prod = ranking_productividad(cc); time.sleep(1)
        disp = disponibles(cc, ids); time.sleep(3)
        if gen is None and prod is None and disp is None:
            caidas.append(p["pais"])
            registros.append(f)
            continue
        leidos += 1
        en_ranking = []
        for i, a in asistentes.items():
            pg, pp = (gen or {}).get(i), (prod or {}).get(i)
            if pg or pp:
                en_ranking.append({"app": a["app"], "empresa": a["empresa"], "origen": a["origen"],
                                   "puesto_general": pg, "puesto_productividad": pp})
        en_ranking.sort(key=lambda x: (x["puesto_general"] or 999, x["puesto_productividad"] or 999))
        por_origen = {}
        for x in en_ranking:
            por_origen[x["origen"]] = por_origen.get(x["origen"], 0) + 1

        def ficha(valor, nota=None):
            d = {"valor": valor, "anio": anio, "anio_anterior": None, "valor_anterior": None,
                 "serie": [{"anio": anio, "valor": valor}]}
            if nota:
                d["nota"] = nota
            return d

        nombres = lambda filtro: ", ".join(x["app"] for x in en_ranking if filtro(x)) or None
        f["indicadores"]["ia_apps_ranking"] = ficha(len(en_ranking), nombres(lambda x: True))
        f["indicadores"]["ia_apps_ranking_eeuu"] = ficha(
            por_origen.get(ESTADOS_UNIDOS, 0), nombres(lambda x: x["origen"] == ESTADOS_UNIDOS))
        f["indicadores"]["ia_apps_ranking_china"] = ficha(
            por_origen.get(CHINA, 0), nombres(lambda x: x["origen"] == CHINA))
        otros = len(en_ranking) - por_origen.get(ESTADOS_UNIDOS, 0) - por_origen.get(CHINA, 0)
        f["indicadores"]["ia_apps_ranking_otros"] = ficha(
            otros, nombres(lambda x: x["origen"] not in (ESTADOS_UNIDOS, CHINA)))
        if disp is not None:
            faltan = [asistentes[i]["app"] for i in ids if i not in disp and asistentes[i]["origen"] != "no verificado"]
            f["indicadores"]["ia_apps_disponibles"] = ficha(
                len(disp & set(ids)),
                ("no están: " + ", ".join(faltan[:8]) + ("…" if len(faltan) > 8 else "")) if faltan else None)
        f["detalle_ia"] = {"en_ranking": en_ranking, "por_origen": por_origen,
                           "rankings_leidos": {"general": gen is not None, "productividad": prod is not None}}
        for c in f["indicadores"]:
            cobertura[c] = cobertura.get(c, 0) + 1
        registros.append(f)

    if leidos < 20:
        raise RuntimeError(f"La tienda de Apple respondió solo en {leidos} países: la lectura falló. NO se publica.")

    base = {"eje": "Desarrollo", "unidad": "asistentes de IA", "unidad_singular": "asistente de IA",
            "mas_es_peor": False, "sin_direccion": True,
            "origen": "Apple App Store — rankings de descargas y disponibilidad por país"}
    cautela = ("Cuenta los asistentes de IA de un padrón verificado que figuran entre las 100 apps "
               "gratuitas más descargadas del iPhone en el país, en el ranking general o en el de "
               "Productividad. UN RANKING DE DESCARGAS NO MIDE USUARIOS: premia lo que crece hace poco "
               "y lo que hace publicidad, y el iPhone es minoritario en la región. Los asistentes "
               "dentro de otras apps —Meta AI en WhatsApp, Gemini en Android— no se ven. Cuba y Haití "
               "no tienen tienda de Apple.")
    medidas = [
        dict(base, clave="ia_apps_ranking", rotulo="Asistentes de IA entre las apps más descargadas",
             cautela=cautela + " La ficha nombra cuáles son."),
        dict(base, clave="ia_apps_ranking_eeuu", rotulo="De ellos, de empresas de Estados Unidos",
             cautela="Asistentes de empresas con sede o matriz en Estados Unidos, verificada en la "
                     "ficha legal que publica Apple o en la política de la empresa. " + cautela),
        dict(base, clave="ia_apps_ranking_china", rotulo="De ellos, de empresas de China",
             cautela="Asistentes de empresas con sede o matriz verificada en China. Las empresas con sede "
                     "en Singapur cuya matriz china no está verificada —como Dola, vinculada por indicios "
                     "a ByteDance— NO se cuentan acá: van en «otros orígenes». " + cautela),
        dict(base, clave="ia_apps_ranking_otros", rotulo="De ellos, de otros orígenes",
             cautela="Singapur, Rusia (Alice de Yandex), Europa, Emiratos y la propia región (Zapia de "
                     "Uruguay, Maritaca de Brasil), además de los de origen no verificado. " + cautela),
        dict(base, clave="ia_apps_disponibles", rotulo="Asistentes de IA disponibles en la tienda del país",
             unidad="asistentes de un padrón de " + str(len(ids)),
             cautela="Cuántos asistentes del padrón se pueden descargar en la tienda del país. La tienda "
                     "no dice por qué falta uno: puede ser decisión de la empresa, de Apple o de una "
                     "norma. La ficha nombra los que faltan."),
    ]
    publicables = [m for m in medidas if cobertura.get(m["clave"])]
    origenes = sorted({a["origen"] for a in padron["asistentes"]})
    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Apple App Store — rankings de apps gratuitas y disponibilidad por país; padrón de "
               "asistentes de IA con origen verificado por la Fundación",
        url_fuente="https://rss.applemarketingtools.com/",
        calificacion=comun.calificar(
            "B", 3, False,
            "Datos que publica Apple sobre su propia tienda, sin método de ranking declarado; el "
            "origen de cada empresa lo verifica la Fundación en fuente primaria. Mide presencia en "
            "descargas, no uso: credibilidad 3."),
        registros=registros,
        vacios=[
            "NINGUNA FUENTE ABIERTA MIDE QUÉ PARTE DEL USO DE IA DE CADA PAÍS VA A CADA EMPRESA. Esto "
            "mide presencia entre las apps más descargadas y disponibilidad, que es lo más cercano "
            "que se puede observar cada día.",
            "UN RANKING DE DESCARGAS NO MIDE USUARIOS: Apple no publica su método, premia el "
            "crecimiento reciente y la publicidad, y el iPhone es minoritario frente a Android en la "
            "región. Google Play no publica rankings sin credencial.",
            "LOS ASISTENTES DENTRO DE OTRAS APPS NO SE VEN: Meta AI en WhatsApp, Gemini en Android, "
            "Copilot en Windows.",
            "CUBA Y HAITÍ NO TIENEN TIENDA DE APPLE (support.apple.com/en-us/118205): sin dato.",
            f"EL ORIGEN ES EL DE LA EMPRESA, verificado en fuente primaria (padrón revisado el "
            f"{padron['revisado']}). Orígenes del padrón: {', '.join(origenes)}. Las apps que imitan "
            "el nombre de ChatGPT se cuentan con su propio origen.",
            "EL RANKING DE PRODUCTIVIDAD SALE DE UN CANAL HEREDADO DE APPLE sin documentación vigente: "
            "si deja de responder, se declara y el conteo usa solo el ranking general.",
        ] + ([f"La tienda no respondió en esta corrida para: {', '.join(caidas)}."] if caidas else []),
        extra={"indicadores": publicables,
               "cobertura": {m["clave"]: cobertura.get(m["clave"], 0) for m in publicables},
               "padron_asistentes": padron["asistentes"],
               "resumen": {"paises_leidos": leidos, "padron_revisado": padron["revisado"],
                           "consultado": comun.ahora()}},
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
