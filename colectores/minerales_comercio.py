"""Minerales: comercio bilateral de oro, estaño y coltán, declarado en la aduana.

POR QUÉ EXISTE
--------------
El mapa de corredores necesita el par origen→destino de los minerales sensibles.
El oro ilegal, el estaño y el coltán se lavan mezclándose con producción formal y
salen por la aduana declarados como legales; el flujo declarado, cruzado con las
asimetrías espejo y con los nodos de producción, es lo que se puede sostener. Este
colector le pregunta a Comtrade lo mismo que el de armas, con los códigos del metal.

GEMELO DEL COLECTOR DE ARMAS
-----------------------------
Usa el MISMO endpoint, el MISMO filtro de filas (una fila por modo de transporte y
régimen aduanero; sólo se conserva la total) y la MISMA prueba del lector. Cambian
los códigos arancelarios y los rótulos. Ver colectores/armas.py para el detalle del
error que la casa ya pagó una vez (sumar las filas de transporte multiplica).

LO QUE MIDE, Y LO QUE NO
------------------------
Es comercio LEGAL declarado en la aduana, valores en dólares, no cantidades. El
tráfico ilícito no pasa por una aduana y no está acá. Sirve para ver el flujo y,
cruzado con la brecha espejo, señalar dónde no cierra. La ilegalidad no se afirma:
se enlaza con GI-TOC, con las asimetrías y con los nodos de producción, y se declara.

CÓDIGOS
-------
7108 oro (no monetario) · 7112 desechos con metales preciosos · 2616 minerales de
metales preciosos · 8001 estaño en bruto · 2609 minerales de estaño · 2615 minerales
de niobio, tantalio y vanadio (coltán) · 8103 tantalio. Verificados contra la
nomenclatura HS; si Comtrade rechaza alguno, la corrida lo declara y sigue.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import comun
import geo

BASE = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
SOCIOS = "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"
NAVEGADOR = comun.AGENTE
CODIGOS = "7108,7112,2616,8001,2609,2615,8103"  # oro, desechos, minerales de metal precioso, estaño, coltán
ANIO = 2023           # último año con cobertura amplia en la vista pública
ANIOS_SERIE = "2019,2020,2021,2022,2023"  # ventana para la historia (mandato de tiempo real)
ESPERA = 2.5          # cortesía con un servidor público y gratuito
CUANTOS_SOCIOS = 6    # los mayores que se publican por Estado y sentido
SIN_DECLARAR = {"Areas, nes", "Other Asia, nes", "Bunkers", "Free Zones",
                "Special Categories", "Other Africa, nes", "Other Europe, nes",
                "Neutral Zone", "Br. Antr. Terr."}

# Misma tabla M49 que el colector de armas y el de la brecha espejo.
M49 = {
    "ARG": 32, "BOL": 68, "BRA": 76, "CHL": 152, "COL": 170, "CRI": 188,
    "CUB": 192, "DOM": 214, "ECU": 218, "SLV": 222, "GTM": 320, "HND": 340,
    "MEX": 484, "NIC": 558, "PAN": 591, "PRY": 600, "PER": 604, "URY": 858,
    "VEN": 862, "HTI": 332, "JAM": 388, "TTO": 780, "GUY": 328, "SUR": 740,
    "BLZ": 84, "BHS": 44, "BRB": 52, "ATG": 28, "DMA": 212, "GRD": 308,
    "KNA": 659, "LCA": 662, "VCT": 670,
}

# Perú y Colombia son exportadores de oro conocidos y declaran todos los años. Si
# el control sale vacío, el que falló es el lector, no el mundo.
CONTROL = "PER"


def _pedir(url: str, tope: int = 12_000_000):
    peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
    with urllib.request.urlopen(peticion, timeout=120) as respuesta:
        return json.loads(respuesta.read(tope).decode("utf-8", "replace"))


def _nombresDeSocio() -> dict:
    """La tabla oficial de socios. Se la pide a la fuente; no se la inventa."""
    d = _pedir(SOCIOS)
    filas = d.get("results") if isinstance(d, dict) else d
    return {int(f["PartnerCode"]): f["PartnerDesc"] for f in filas
            if str(f.get("PartnerCode", "")).lstrip("-").isdigit()}


def _flujo(codigo: int, sentido: str) -> tuple:
    """Un sentido del comercio de minerales de un Estado, sumando los códigos por
    socio. Devuelve (socios, descartadas)."""
    url = BASE + "?" + urllib.parse.urlencode(
        {"reporterCode": codigo, "flowCode": sentido, "period": ANIO, "cmdCode": CODIGOS})
    d = _pedir(url)
    filas = d.get("data") or []
    # LA LINEA QUE IMPORTA (igual que en armas): sólo la fila total por socio, no la
    # abierta por modo de transporte y régimen aduanero, que sumada multiplica.
    buenas = [f for f in filas
              if f.get("motCode") in (0, "0")
              and f.get("customsCode") in (None, "C00")
              and f.get("partner2Code") in (0, "0", None)]
    por_socio: dict = {}
    for f in buenas:
        socio = int(f.get("partnerCode") or 0)
        if socio in (0,):
            continue
        por_socio[socio] = por_socio.get(socio, 0.0) + float(f.get("primaryValue") or 0)
    socios = [{"codigo": s, "valor_usd": v} for s, v in por_socio.items()]
    return socios, len(filas) - len(buenas)


def _serie(codigo: int) -> dict:
    """Historia del comercio total (con el Mundo) por año, importar y exportar. Mandato de serie."""
    out = {"importa": {}, "exporta": {}}
    for sentido, clave in (("M", "importa"), ("X", "exporta")):
        url = BASE + "?" + urllib.parse.urlencode(
            {"reporterCode": codigo, "flowCode": sentido, "period": ANIOS_SERIE,
             "cmdCode": CODIGOS, "partnerCode": 0})
        d = _pedir(url)
        por_anio: dict = {}
        for f in d.get("data") or []:
            if (f.get("motCode") in (0, "0") and f.get("customsCode") in (None, "C00")
                    and f.get("partner2Code") in (0, "0", None)):
                anio = int(f.get("period") or f.get("refYear") or f.get("refPeriodId", 0) // 100 or 0)
                if 1990 <= anio <= 2100:
                    por_anio[anio] = por_anio.get(anio, 0.0) + float(f.get("primaryValue") or 0)
        out[clave] = por_anio
    return {k: [{"anio": a, "valor_usd": round(v)} for a, v in sorted(d.items())] for k, d in out.items()}


def recolectar():
    nombres = _nombresDeSocio()
    if len(nombres) < 100:
        raise RuntimeError(
            f"La tabla de socios devolvió {len(nombres)} entradas y deberían ser cientos. "
            "NO se publica con los socios sin nombre.")

    registros, conDato, descartadas, sinConsultar = [], 0, 0, []
    for pais in geo.padron():
        codigo = M49.get(pais["iso"])
        if not codigo:
            registros.append({"iso": pais["iso"], "pais": pais["pais"],
                              "bloque": pais["bloque"], "estado": "sin_codigo"})
            continue
        try:
            compra, d1 = _flujo(codigo, "M")
            time.sleep(ESPERA)
            vende, d2 = _flujo(codigo, "X")
            time.sleep(ESPERA)
            descartadas += d1 + d2
            try:
                serie = _serie(codigo)
                time.sleep(ESPERA)
            except Exception:  # noqa: BLE001 — la serie es extra; si falla, queda el año suelto
                serie = {"importa": [], "exporta": []}
        except urllib.error.HTTPError as error:
            sinConsultar = [p["pais"] for p in geo.padron()
                            if p["iso"] not in {r["iso"] for r in registros}]
            print(f"[minerales] la fuente cortó en {pais['iso']}: HTTP {error.code}. "
                  f"Quedan {len(sinConsultar)} Estados sin consultar.", file=sys.stderr)
            break
        except Exception as error:  # noqa: BLE001 — la falla de un Estado se declara
            registros.append({"iso": pais["iso"], "pais": pais["pais"],
                              "bloque": pais["bloque"], "estado": "no_se_pudo_leer",
                              "porque": f"{type(error).__name__}"})
            continue

        def mayores(lista):
            orden = sorted(lista, key=lambda x: -x["valor_usd"])[:CUANTOS_SOCIOS]
            return [{"socio": nombres.get(x["codigo"], f"código {x['codigo']}"),
                     "valor_usd": round(x["valor_usd"])} for x in orden]

        totalCompra = sum(x["valor_usd"] for x in compra)
        totalVende = sum(x["valor_usd"] for x in vende)
        opaco = lambda lista: sum(  # noqa: E731
            x["valor_usd"] for x in lista
            if nombres.get(x["codigo"], "") in SIN_DECLARAR)
        opacaCompra, opacaVenta = opaco(compra), opaco(vende)
        if compra or vende:
            conDato += 1
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": "declarado" if (compra or vende) else "sin_declarar",
            "importa_usd": round(totalCompra),
            "exporta_usd": round(totalVende),
            "socios_de_compra": len(compra),
            "socios_de_venta": len(vende),
            "mayores_proveedores": mayores(compra),
            "mayores_clientes": mayores(vende),
            "serie": serie,
            "importa_sin_declarar_origen_usd": round(opacaCompra),
            "exporta_sin_declarar_destino_usd": round(opacaVenta),
            "pct_compra_sin_origen": round(opacaCompra * 100 / totalCompra, 1) if totalCompra else None,
            "pct_venta_sin_destino": round(opacaVenta * 100 / totalVende, 1) if totalVende else None,
        })

    for pais in geo.padron():
        if pais["iso"] not in {r["iso"] for r in registros}:
            registros.append({"iso": pais["iso"], "pais": pais["pais"],
                              "bloque": pais["bloque"], "estado": "no_consultado"})

    control = next((r for r in registros if r["iso"] == CONTROL), {})
    if control.get("estado") == "declarado" and not control.get("exporta_usd"):
        raise RuntimeError(
            f"La prueba del lector falló: {CONTROL} —exportador de oro conocido— quedó con "
            "exportación cero. El filtro de filas o la consulta cambiaron. No se publica a ciegas.")

    vacios = [
        "Es comercio de metales DECLARADO EN LA ADUANA, no tráfico ilícito. El oro, el estaño "
        "y el coltán ilegales se mezclan con producción formal y salen declarados como legales; "
        "el tráfico en sí no pasa por una aduana y no está acá. Sirve para ver el flujo y, "
        "cruzado con la brecha espejo, señalar dónde no cierra.",
        "Son valores de aduana en dólares, no cantidades. No dice cuántos kilos de oro: dice "
        "cuánto dinero.",
        "La ilegalidad no se afirma en el dato: se enlaza con el Índice de GI-TOC, con las "
        "asimetrías entre lo que el exportador y el importador declaran, y con los nodos de "
        "producción de oro. Cada uno es un indicio, no una prueba.",
        "El coltán ilegal de Sudamérica (Venezuela, Colombia) es de bajo volumen y poco visible "
        "en el comercio declarado: su ausencia en estas cifras no significa que no exista.",
        f"LA FILA TOTAL ES LA ÚNICA QUE SE SUMA. Como en armas, la respuesta trae una fila por "
        f"modo de transporte y régimen aduanero además de la total; sumarlas multiplica el "
        f"comercio. En esta corrida se descartaron {descartadas} filas por ese motivo.",
        f"EL AÑO ES {ANIO}, el último con cobertura amplia en la vista pública y gratuita de la "
        "fuente. No es el último año calendario, y se dice.",
    ]
    if sinConsultar:
        vacios.append(
            f"LA FUENTE CORTÓ LA TANDA y quedaron {len(sinConsultar)} Estados SIN CONSULTAR: "
            f"{', '.join(sinConsultar)}. No figuran en cero: figuran como no consultados.")

    # GUARDA: si NINGÚN Estado declaró, la fuente falló (límite/caída de Comtrade). No se
    # publica un archivo en cero —pisaría el último dato bueno y vaciaría los corredores—.
    if conDato == 0:
        raise RuntimeError(
            f"Comtrade no devolvió ningún Estado con declaración (sin consultar: {len(sinConsultar)}). "
            "Probable límite o corte de la fuente. NO se publica para no pisar el último dato bueno.")

    calificacion = comun.calificar(
        fiabilidad="A", credibilidad=2, corroborado=False,
        nota=("Base de comercio de Naciones Unidas, alimentada por las aduanas de cada Estado. "
              "Fiabilidad A porque el productor compila declaraciones oficiales con método "
              "publicado. Credibilidad 2 porque se verifica la declaración aduanera —que "
              "consta— y no que refleje todo el comercio: lo que un Estado declara vender no "
              "coincide con lo que el otro declara comprar, y el tráfico ilegal no aparece."),
    )

    return comun.escribir(
        colector="minerales_comercio",
        capa="publico",
        fuente="Comtrade de Naciones Unidas — oro, estaño y coltán (HS 7108, 7112, 2616, 8001, 2609, 2615, 8103)",
        url_fuente=BASE,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "anio": ANIO,
                "codigos": CODIGOS,
                "estados_con_declaracion": conDato,
                "estados_del_padron": len(registros),
                "estados_sin_consultar": len(sinConsultar),
                "importado_por_la_region_usd": sum(r.get("importa_usd") or 0 for r in registros),
                "exportado_por_la_region_usd": sum(r.get("exporta_usd") or 0 for r in registros),
                "filas_descartadas_por_transporte": descartadas,
                "lector_probado": True,
                "consultado": comun.ahora(),
            },
            "licencia": ("Datos «transformados» de UN Comtrade (agregación y reordenamiento). "
                         "SIWA se considera uso no comercial. Confirmar suscripción premium activa."),
        },
    )


if __name__ == "__main__":
    comun.correr("minerales_comercio", recolectar)
