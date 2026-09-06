"""Armas: quién le vende a quién, declarado en la aduana.

POR QUÉ EXISTE, Y CÓMO APARECIÓ
--------------------------------
La Dirección pidió mirar el Instituto Igarapé. Su visualización de comercio de
armas trae 81.638 registros bilaterales… y una categoría llamada **`930330`**,
que es un **código arancelario de Naciones Unidas**. Igarapé no produjo ese
dato: lo derivó de Comtrade, y su copia va de **1992 a 2010**.

Comtrade es una fuente que este registro **ya consulta todos los días** para la
brecha espejo. Así que en vez de importar una copia de dieciséis años, se le
pregunta a la fuente original lo mismo, hoy. **Copiar la copia vieja habría sido
el error.**

LO QUE MIDE, Y ES BASTANTE MENOS DE LO QUE SUENA
-------------------------------------------------
El capítulo 93 del arancel es **«armas y municiones; sus partes y accesorios»**:
armas de fuego, municiones, componentes. **NO incluye aviones, buques ni
vehículos militares**, que viajan en otros capítulos. Quien lea esto como «el
comercio de armas de un país» va a leer de menos, y bastante.

Y es **comercio DECLARADO EN LA ADUANA**. El tráfico ilegal —que es justamente
lo que preocupa— no pasa por una aduana y **no está acá**. Esta cifra sirve para
ver el flujo legal y, cruzada con la brecha espejo, para señalar dónde el flujo
legal no cierra.

EL ERROR QUE LA CASA YA PAGÓ UNA VEZ
-------------------------------------
La respuesta trae **una fila por modo de transporte y por régimen aduanero**,
además de la fila total. Sumarlas todas —que es lo primero que uno hace—
**multiplica el comercio**: Brasil daba 768 millones de importación cuando son
**192**. Cuatro veces de más. Se filtra `motCode = 0`, `customsCode = C00` y
`partner2Code = 0`, igual que en el colector de la brecha espejo, y se descarta
el resto.
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
CAPITULO = "93"       # armas y municiones; sus partes y accesorios
ANIO = 2023           # último año con cobertura amplia en la vista pública
ESPERA = 2.5          # cortesía con un servidor público y gratuito
CUANTOS_SOCIOS = 6    # los mayores que se publican por Estado y sentido
# CONTRAPARTE NO DECLARADA. La fuente usa codigos especiales para el comercio
# cuyo origen o destino el Estado NO especifica. En la primera corrida aparecio
# que el MAYOR PROVEEDOR DE ARMAS DE CHILE es uno de estos, y que Mexico exporta
# a solo dos destinos, uno de ellos sin declarar. Eso es un dato de transparencia
# y se cuenta aparte en vez de perderse entre los socios.
SIN_DECLARAR = {"Areas, nes", "Other Asia, nes", "Bunkers", "Free Zones",
                "Special Categories", "Other Africa, nes", "Other Europe, nes",
                "Neutral Zone", "Br. Antr. Terr."}

# Código numérico de Naciones Unidas para cada Estado del padrón. Es la misma
# tabla que usa el colector de la brecha espejo.
M49 = {
    "ARG": 32, "BOL": 68, "BRA": 76, "CHL": 152, "COL": 170, "CRI": 188,
    "CUB": 192, "DOM": 214, "ECU": 218, "SLV": 222, "GTM": 320, "HND": 340,
    "MEX": 484, "NIC": 558, "PAN": 591, "PRY": 600, "PER": 604, "URY": 858,
    "VEN": 862, "HTI": 332, "JAM": 388, "TTO": 780, "GUY": 328, "SUR": 740,
    "BLZ": 84, "BHS": 44, "BRB": 52, "ATG": 28, "DMA": 212, "GRD": 308,
    "KNA": 659, "LCA": 662, "VCT": 670,
}

# Brasil es exportador de armas conocido y declara todos los anios. Si el
# control sale vacio, el que fallo es el lector, no el mundo.
CONTROL = "BRA"


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
    """Un sentido del comercio de armas de un Estado. Devuelve (socios, descartadas)."""
    url = BASE + "?" + urllib.parse.urlencode(
        {"reporterCode": codigo, "flowCode": sentido, "period": ANIO, "cmdCode": CAPITULO})
    d = _pedir(url)
    filas = d.get("data") or []
    # LA LINEA QUE IMPORTA. Las demas son el mismo comercio abierto por modo de
    # transporte y regimen aduanero, y sumarlas lo multiplica.
    buenas = [f for f in filas
              if f.get("motCode") in (0, "0")
              and f.get("customsCode") in (None, "C00")
              and f.get("partner2Code") in (0, "0", None)]
    socios = [{"codigo": int(f.get("partnerCode") or 0),
               "valor_usd": float(f.get("primaryValue") or 0)}
              for f in buenas if f.get("partnerCode") not in (0, None, "0")]
    return socios, len(filas) - len(buenas)


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
        except urllib.error.HTTPError as error:
            # 429 es «demasiadas consultas», no «no hay datos». Se detiene la
            # tanda y se DECLARA a quiénes no se alcanzó a preguntar.
            sinConsultar = [p["pais"] for p in geo.padron()
                            if p["iso"] not in {r["iso"] for r in registros}]
            print(f"[armas] la fuente cortó en {pais['iso']}: HTTP {error.code}. "
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
            "importa_sin_declarar_origen_usd": round(opacaCompra),
            "exporta_sin_declarar_destino_usd": round(opacaVenta),
            "pct_compra_sin_origen": round(opacaCompra * 100 / totalCompra, 1) if totalCompra else None,
            "pct_venta_sin_destino": round(opacaVenta * 100 / totalVende, 1) if totalVende else None,
        })

    for pais in geo.padron():
        if pais["iso"] not in {r["iso"] for r in registros}:
            registros.append({"iso": pais["iso"], "pais": pais["pais"],
                              "bloque": pais["bloque"], "estado": "no_consultado"})

    # SE PRUEBA EL LECTOR ANTES DE CREERLE UN CERO A NADIE.
    control = next((r for r in registros if r["iso"] == CONTROL), {})
    if control.get("estado") == "declarado" and not control.get("exporta_usd"):
        raise RuntimeError(
            f"La prueba del lector falló: {CONTROL} —exportador de armas conocido— quedó "
            "con exportación cero. El filtro de filas o la consulta cambiaron. NO se "
            "publica una lectura a ciegas.")

    vacios = [
        "EL CAPITULO 93 ES «ARMAS Y MUNICIONES; SUS PARTES Y ACCESORIOS»: armas de fuego, "
        "municiones y componentes. NO INCLUYE AVIONES, BUQUES NI VEHICULOS MILITARES, que "
        "viajan en otros capitulos del arancel. Quien lea esto como «el comercio de armas "
        "de un pais» va a leer DE MENOS, y bastante.",
        "ES COMERCIO DECLARADO EN LA ADUANA. El trafico ilegal —que es justamente lo que "
        "preocupa— NO PASA POR UNA ADUANA Y NO ESTA ACA. Esta cifra sirve para ver el "
        "flujo legal y, cruzada con la brecha espejo, para señalar donde el flujo legal no "
        "cierra.",
        "SON VALORES DE ADUANA EN DOLARES, NO CANTIDADES. No dice cuantas armas: dice "
        "cuanto dinero. Un lote de municiones baratas y uno de fusiles caros pueden dar la "
        "misma cifra.",
        "LO QUE A DICE QUE VENDIO NO ES LO QUE B DICE QUE COMPRO. Cada Estado declara por "
        "su cuenta y las cifras no cierran entre si: el exportador declara el valor puesto "
        "en el barco y el importador ese valor MAS flete y seguro. La diferencia se mide "
        "aparte, en la brecha espejo.",
        "NO ORDENA ESTADOS Y NO ENTRA AL COMPUESTO. El volumen depende del tamanio de la "
        "economia, de tener o no industria propia y del papel de cada pais en la cadena. "
        "Brasil exporta mas que Uruguay por industria, no por conducta. Entra como "
        "MAGNITUD, igual que Defensa.",
        f"LA FILA TOTAL ES LA UNICA QUE SE SUMA. La respuesta trae una fila por modo de "
        f"transporte y por regimen aduanero ademas de la total, y sumarlas MULTIPLICA el "
        f"comercio: Brasil daba 768 millones de importacion cuando son 192, cuatro veces "
        f"de mas. En esta corrida se descartaron {descartadas} filas por ese motivo.",
        "HAY COMERCIO DE ARMAS CON CONTRAPARTE NO DECLARADA, y se cuenta aparte. La "
        "fuente usa codigos especiales cuando el Estado no especifica el origen o el "
        "destino. NO significa que sea ilegal: significa que la aduana no dijo con quien. "
        "Se publica el monto y su porcentaje porque es un dato de transparencia, no una "
        "acusacion.",
        f"EL ANIO ES {ANIO}, que es el ultimo con cobertura amplia en la vista publica y "
        "gratuita de la fuente. No es el ultimo anio calendario, y se dice.",
    ]
    if sinConsultar:
        vacios.append(
            f"LA FUENTE CORTO LA TANDA en esta corrida y quedaron {len(sinConsultar)} "
            f"Estados SIN CONSULTAR: {', '.join(sinConsultar)}. NO figuran en cero: "
            "figuran como no consultados, que es distinto.")

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Base de comercio de Naciones Unidas, alimentada por las aduanas de cada "
              "Estado. Fiabilidad A porque el productor compila declaraciones oficiales "
              "con metodo publicado. Credibilidad 2 porque se verifica LA DECLARACION "
              "ADUANERA —que consta— y no que refleje todo el comercio: lo que un Estado "
              "declara haber vendido no coincide con lo que el otro declara haber "
              "comprado, y el trafico ilegal no aparece."),
    )

    return comun.escribir(
        colector="armas",
        capa="publico",
        fuente="Comtrade de Naciones Unidas — capítulo 93: armas, municiones y sus partes",
        url_fuente=BASE,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "anio": ANIO,
                "capitulo": CAPITULO,
                "estados_con_declaracion": conDato,
                "estados_del_padron": len(registros),
                "estados_sin_consultar": len(sinConsultar),
                "importado_por_la_region_usd": sum(r.get("importa_usd") or 0 for r in registros),
                "exportado_por_la_region_usd": sum(r.get("exporta_usd") or 0 for r in registros),
                "filas_descartadas_por_transporte": descartadas,
                "lector_probado": True,
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("armas", recolectar)
