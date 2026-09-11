# -*- coding: utf-8 -*-
"""Cloudflare Radar: qué pasa en la red de cada Estado, medido en el tráfico real.

QUÉ APORTA AL HUECO DIGITAL. El registro ya mide anomalías de red, cortes de
conectividad y equipos de respuesta a incidentes, y **ninguna de las tres ordena
Estados**: la muestra de anomalías la hacen voluntarios, un corte no distingue la
causa, y contar equipos premia al Estado grande. Esta fuente mide **proporciones
del tráfico**, que no dependen del tamaño del país ni de cuánta gente mida: son
comparables entre los 33.

SOBRE LA LLAVE. Es una llave de lectura, gratuita, que se pide en el panel de
Cloudflare con permiso de sólo lectura sobre Radar. Se lee del entorno y no se
escribe acá. Sin ella la fuente contesta «faltan las cabeceras de autorización»
y este colector se detiene declarándolo, en vez de publicar un archivo vacío.

POR QUÉ ESTE COLECTOR SE DEFIENDE MÁS QUE LOS OTROS
-----------------------------------------------------
Se escribió **sin poder probarlo**: la llave vive en el robot y no en la máquina
donde se programó. Por eso no da nada por sentado sobre la forma de la respuesta:
lee lo que encuentra, y **lo que no entiende lo declara en vez de inventarlo**.
La primera corrida del robot es su verdadera prueba, y si algo no cuadra lo va a
decir en los vacíos del conjunto y no en silencio.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "radar"
CAPA = "publico"

BASE = "https://api.cloudflare.com/client/v4/radar"
SECRETO = "CLOUDFLARE_RADAR"
VENTANA = "28d"

ORIGEN = "Cloudflare Radar — mediciones sobre tráfico real de internet"

# Cada medida nombra un recorrido de «resumen» y la porción que se publica. Los
# resúmenes de esta fuente devuelven un reparto porcentual entre dos o tres
# categorías; se publica una y se dice cuál, porque publicar las dos sería
# publicar dos veces el mismo dato.
MEDIDAS = [
    {"clave": "trafico_automatizado", "ruta": "http/summary/bot_class", "porcion": "bot",
     "rotulo": "Tráfico de internet automatizado", "eje": "Seguridad",
     "unidad": "% del tráfico web", "mas_es_peor": True,
     "cautela": "Qué parte del tráfico web del país NO la genera una persona sino un "
                "programa. Incluye lo legítimo —buscadores, monitoreo— y lo hostil, y la "
                "fuente NO los separa: un valor alto no prueba ataque. Es proporción, así "
                "que no depende del tamaño del país."},
    {"clave": "internet_moderno", "ruta": "http/summary/ip_version", "porcion": "IPv6",
     "rotulo": "Tráfico por la internet moderna (IPv6)", "eje": "Desarrollo",
     "unidad": "% del tráfico web", "mas_es_peor": False,
     "cautela": "Qué parte del tráfico usa el protocolo nuevo. Mide modernización de la "
                "red, no seguridad ni velocidad. Un valor bajo suele indicar operadores "
                "que no actualizaron su infraestructura."},
]


def llave() -> str:
    v = (os.environ.get(SECRETO) or "").strip()
    if not v:
        raise RuntimeError(
            f"falta la variable {SECRETO}. Es una llave de lectura, gratuita, que se crea "
            "en el panel de Cloudflare con permiso de sólo lectura sobre Radar, y se carga "
            "como secreto del repositorio. Sin ella la fuente rechaza toda consulta.")
    return v


def pedir(ruta: str, lugar: str, token: str) -> dict:
    consulta = urllib.parse.urlencode({"location": lugar, "dateRange": VENTANA,
                                       "format": "json"})
    peticion = urllib.request.Request(
        f"{BASE}/{ruta}?{consulta}",
        headers={"User-Agent": comun.AGENTE, "Accept": "application/json",
                 "Authorization": f"Bearer {token}"})
    for intento in range(4):
        try:
            with urllib.request.urlopen(peticion, timeout=90) as respuesta:
                return json.loads(respuesta.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            # 429 es «más despacio», no una falla: se espera y se vuelve.
            if e.code != 429 or intento == 3:
                raise
            time.sleep(3 * (intento + 1))
    return {}


def porcion(respuesta: dict, cual: str):
    """El número que se busca, sin dar por sentada la forma de la respuesta.

    Se escribió sin poder probar contra la fuente, así que en vez de asumir el
    camino exacto se busca la porción por su nombre, sin distinguir mayúsculas,
    y se acepta tanto un número como un texto que contenga un número. Si no
    aparece, se devuelve None y el Estado queda declarado sin dato: **es
    preferible una ausencia declarada a un valor inventado**.
    """
    resumen = ((respuesta or {}).get("result") or {}).get("summary_0")
    if not isinstance(resumen, dict):
        return None
    for k, v in resumen.items():
        if str(k).lower() != cual.lower():
            continue
        try:
            return round(float(v), 2)
        except (TypeError, ValueError):
            return None
    return None


def construir() -> Path:
    token = llave()
    padron = geo.padron()
    dos = comun.DOS_LETRAS

    valores, caidos = {m["clave"]: {} for m in MEDIDAS}, []
    for p in padron:
        lugar = dos.get(p["iso"])
        if not lugar:
            continue
        for m in MEDIDAS:
            try:
                v = porcion(pedir(m["ruta"], lugar, token), m["porcion"])
            except Exception as error:  # noqa: BLE001 — el Estado caído se declara
                caidos.append(f"{p['pais']} · {m['rotulo']}: {type(error).__name__}")
                continue
            if v is not None:
                valores[m["clave"]][p["iso"]] = v
        time.sleep(0.4)   # cortesía con un servicio que contesta gratis

    if not any(valores.values()):
        raise RuntimeError(
            "la fuente no devolvió un solo valor utilizable. No se escribe nada: un "
            "archivo vacío se vería igual que un país sin tráfico, y no es lo mismo.")

    # La fecha de la medición es la ventana, no un año: se guarda el año en curso
    # para que el registro pueda ordenarla junto al resto, y la ventana se declara.
    # `comun.ahora()` devuelve una CADENA en ISO, no una fecha: pedirle `.year`
    # reventaba el colector entero. Fue el precio de escribirlo sin poder
    # correrlo —la credencial vive en el robot—, y el robot lo declaró en su
    # primera corrida real en vez de publicar algo a medias.
    anio = datetime.now(timezone.utc).year

    registros, cobertura = [], {}
    for p in padron:
        f = {"iso": p["iso"], "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        for m in MEDIDAS:
            v = valores[m["clave"]].get(p["iso"])
            if v is None:
                continue
            f["indicadores"][m["clave"]] = {
                "valor": v, "anio": anio,
                "anio_anterior": None, "valor_anterior": None, "variacion_pct": None,
                "anio_inicial": anio, "valor_inicial": v,
                "tendencia_ventana_pct": None,
                "serie": [{"anio": anio, "valor": v}],
            }
            cobertura[m["clave"]] = cobertura.get(m["clave"], 0) + 1
        if f["indicadores"]:
            registros.append(f)

    publicables = [m for m in MEDIDAS if cobertura.get(m["clave"], 0)]
    fuera = {m["clave"] for m in MEDIDAS} - {m["clave"] for m in publicables}
    for f in registros:
        for c in fuera:
            f["indicadores"].pop(c, None)
    registros = [r for r in registros if r["indicadores"]]
    registros.sort(key=lambda r: r["pais"])
    sin_dato = sorted(p["pais"] for p in padron
                      if p["iso"] not in {r["iso"] for r in registros})

    vacios = [
        f"ES UNA FOTO DE LOS ÚLTIMOS {VENTANA.rstrip('d')} DÍAS, no una serie histórica. "
        "Cada corrida reemplaza la anterior: acá no se puede ver si un país mejora o "
        "empeora con el tiempo, solo cómo está ahora respecto de los demás.",
        "El tráfico automatizado INCLUYE LO LEGÍTIMO Y LO HOSTIL en el mismo número "
        "—buscadores y monitoreo conviven con ataques— y la fuente no los separa. Un "
        "valor alto NO prueba que ese Estado esté bajo ataque.",
        "Lo que mide esta fuente es el tráfico QUE PASA POR SU PROPIA RED, que es grande "
        "pero no es toda internet. Un Estado cuyo tráfico circule mayormente por otras "
        "redes queda descrito por una muestra parcial, y eso no se puede corregir desde "
        "afuera.",
        "Este colector se escribió SIN PODER PROBARLO: la llave vive en el robot y no en "
        "la máquina donde se programó. Por eso, cuando no entiende una respuesta, deja al "
        "Estado sin dato y lo declara, en vez de publicar un número inventado.",
    ]
    if sin_dato:
        vacios.append(f"{len(sin_dato)} Estados sin ninguna medida: " + ", ".join(sin_dato) + ".")
    if caidos:
        vacios.append(f"{len(caidos)} consultas fallaron: " + "; ".join(caidos[:6])
                      + ("…" if len(caidos) > 6 else ""))

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente=ORIGEN,
        url_fuente="https://radar.cloudflare.com/",
        calificacion=comun.calificar(
            "B", 2, False,
            "Empresa privada que mide sobre su propia red, que es grande pero no es toda "
            "internet. Publica su método y no tiene interés en el resultado de ningún "
            "Estado del padrón; no es un organismo público ni un productor independiente, "
            "y por eso no sube de B."),
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": [{"clave": m["clave"], "rotulo": m["rotulo"], "eje": m["eje"],
                             "unidad": m["unidad"], "mas_es_peor": m["mas_es_peor"],
                             "origen": ORIGEN, "cautela": m["cautela"]}
                            for m in publicables],
            "cobertura": cobertura,
            "ventana": VENTANA,
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
