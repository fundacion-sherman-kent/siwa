"""Sismicidad — el catálogo del Servicio Geológico de los Estados Unidos (USGS).

América Latina y el Caribe está sobre uno de los bordes de placa más activos del
planeta: la subducción de Nazca bajo Sudamérica, el arco centroamericano y el
arco de las Antillas Menores. El registro no tenía **ninguna** capa sísmica.

Dónde ocurren, que no es un detalle
-----------------------------------
**La mayoría de los sismos importantes de esta región ocurren en el mar**, en la
fosa donde una placa se hunde bajo la otra. Un colector que asignara cada sismo
a un Estado y descartara lo que cae fuera de tierra firme **borraría justamente
los más grandes**, que son los que generan tsunami. Por eso acá el mar es una
categoría declarada, no un descarte: cada sismo se asigna a un Estado si su
epicentro cae en tierra, y si no, se cuenta como **mar adentro** con su
distancia al Estado más cercano según lo que la propia fuente rotula.

Lo que esta capa NO es
----------------------
**No es una medida de riesgo ni de daño.** La magnitud dice cuánta energía
liberó el sismo, no cuánto destruyó: eso depende de la profundidad, del suelo, de
la hora y de cómo esté construida la ciudad. Un sismo de magnitud 6 a diez
kilómetros bajo una ciudad hace más daño que uno de 7 a doscientos kilómetros
mar adentro. **Contar sismos no ordena Estados por peligro.**
"""

from __future__ import annotations

import collections
import datetime
import json
import ssl
import sys
import time
import urllib.error
import urllib.request

import comun
import geo

BASE = "https://earthquake.usgs.gov/fdsnws/event/1"
FUENTE = ("Servicio Geológico de los Estados Unidos (USGS) — catálogo de sismos, "
          "servicio FDSN")
URL_FUENTE = "https://earthquake.usgs.gov/fdsnws/event/1/"
NAVEGADOR = comun.AGENTE

# El mismo recuadro que usa el colector de focos de calor: América Latina y el
# Caribe con el mar de los dos lados, porque la fosa esta mar adentro.
OESTE, SUR, ESTE, NORTE = -118.0, -56.0, -34.0, 33.0
MAGNITUD = 4.5           # por debajo, el catalogo se llena de eventos sin consecuencia
DIAS = 90
ESPERA = 90
INTENTOS = 3
DESCANSO = 8
TOPE = 20000             # el propio servicio no entrega mas por consulta


def _pedir(ruta: str, parametros: str) -> dict:
    url = f"{BASE}/{ruta}?format=geojson&{parametros}"
    ultimo = ""
    for intento in range(INTENTOS):
        try:
            peticion = urllib.request.Request(url, headers={
                "User-Agent": NAVEGADOR, "Accept": "application/json"})
            with urllib.request.urlopen(peticion, timeout=ESPERA,
                                        context=ssl.create_default_context()) as r:
                return json.loads(r.read(30_000_000).decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"USGS respondió HTTP {e.code} en «{ruta}»") from e
        except Exception as e:  # noqa: BLE001 — falla de red: se reintenta
            ultimo = f"{type(e).__name__}: {e}"
            print(f"[sismos] intento {intento + 1} de {INTENTOS}: {ultimo}",
                  file=sys.stderr)
            time.sleep(DESCANSO * (intento + 1))
    raise RuntimeError(f"No hubo respuesta en {INTENTOS} intentos: {ultimo}")


def _probar_el_recuadro(desde: str) -> tuple:
    """EL RECUADRO TIENE QUE RECORTAR, y se comprueba en cada corrida.

    Se cuentan los sismos del mundo y los del recuadro con la misma ventana y la
    misma magnitud. Si el recuadro no recorta —si diera lo mismo—, lo que se
    publicaria seria la sismicidad del planeta repartida entre 33 Estados.
    """
    comun_ = f"starttime={desde}&minmagnitude={MAGNITUD}"
    mundo = _pedir("count", comun_)
    region = _pedir("count", f"{comun_}&minlatitude={SUR}&maxlatitude={NORTE}"
                             f"&minlongitude={OESTE}&maxlongitude={ESTE}")
    n_mundo = mundo.get("count") if isinstance(mundo, dict) else None
    n_region = region.get("count") if isinstance(region, dict) else None
    if not isinstance(n_mundo, int) or not isinstance(n_region, int):
        raise RuntimeError("El servicio de recuento no devolvió un número. No se publica.")
    if not (0 < n_region < n_mundo):
        raise RuntimeError(
            f"El recuadro NO está recortando: el mundo tiene {n_mundo} sismos y el "
            f"recuadro {n_region}. Se esperaba que el recuadro fuera menos que el "
            "mundo y mayor que cero. Publicar así repartiría la sismicidad del "
            "planeta entre los 33 Estados. No se publica.")
    if n_region >= TOPE:
        raise RuntimeError(
            f"El recuadro devuelve {n_region} sismos y el servicio entrega como "
            f"máximo {TOPE} por consulta: el resultado vendría cortado sin avisar. "
            "Hay que partir la consulta antes de publicar.")
    return n_mundo, n_region


def recolectar():
    hoy = datetime.datetime.now(datetime.timezone.utc)
    desde = (hoy - datetime.timedelta(days=DIAS)).date().isoformat()
    n_mundo, n_region = _probar_el_recuadro(desde)

    cuerpo = _pedir("query", f"starttime={desde}&minmagnitude={MAGNITUD}"
                             f"&minlatitude={SUR}&maxlatitude={NORTE}"
                             f"&minlongitude={OESTE}&maxlongitude={ESTE}"
                             f"&orderby=time&limit={TOPE}")
    rasgos = cuerpo.get("features") or []
    if len(rasgos) != n_region:
        print(f"[sismos] el recuento dijo {n_region} y llegaron {len(rasgos)}: "
              "se publica lo que llegó y se declara la diferencia.", file=sys.stderr)

    porIso: dict = {}
    mar, sinCoordenada = [], 0
    for rasgo in rasgos:
        propiedades = rasgo.get("properties") or {}
        geometria = (rasgo.get("geometry") or {}).get("coordinates") or []
        if len(geometria) < 2:
            sinCoordenada += 1
            continue
        lon, lat = float(geometria[0]), float(geometria[1])
        profundidad = float(geometria[2]) if len(geometria) > 2 else None
        marca = propiedades.get("time")
        cuando = (datetime.datetime.fromtimestamp(marca / 1000, datetime.timezone.utc)
                  .isoformat(timespec="seconds") if marca else None)
        ficha = {
            "magnitud": propiedades.get("mag"),
            "lugar": propiedades.get("place"),
            "cuando": cuando,
            "profundidad_km": profundidad,
            "enlace": propiedades.get("url"),
            "tsunami": bool(propiedades.get("tsunami")),
        }
        pais = geo.pais_de(lon, lat)
        if pais:
            porIso.setdefault(pais["iso"], []).append(ficha)
        else:
            # El mar NO se descarta: es donde ocurren los mas grandes de la region.
            mar.append(ficha)

    if not rasgos:
        raise RuntimeError(
            f"El recuadro no devolvió ningún sismo de magnitud {MAGNITUD} o mayor en "
            f"{DIAS} días. En esta región eso no describe al mundo: describe una "
            "consulta fallida. No se publica.")

    registros = []
    for pais in geo.padron():
        fichas = sorted(porIso.get(pais["iso"], []),
                        key=lambda f: f["cuando"] or "", reverse=True)
        mayor = max((f for f in fichas if f["magnitud"] is not None),
                    key=lambda f: f["magnitud"], default=None)
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "sismos": len(fichas),
            "mayor_magnitud": mayor["magnitud"] if mayor else None,
            "mayor": mayor,
            "ultimo": fichas[0] if fichas else None,
            "recientes": fichas[:5],
        })
    registros.sort(key=lambda r: (-(r["mayor_magnitud"] or 0), -r["sismos"], r["pais"]))

    mar.sort(key=lambda f: f["magnitud"] or 0, reverse=True)
    magnitudes = [f["magnitud"] for f in
                  [x for v in porIso.values() for x in v] + mar
                  if f["magnitud"] is not None]
    reparto = collections.Counter(
        "6 o mayor" if m >= 6 else "5 a 5,9" if m >= 5 else "4,5 a 4,9"
        for m in magnitudes)

    vacios = [
        "**Esto no mide riesgo ni daño: mide energía liberada.** Un sismo de magnitud 6 "
        "a diez kilómetros bajo una ciudad hace más daño que uno de 7 a doscientos "
        "kilómetros mar adentro. **Contar sismos no ordena Estados por peligro**, y "
        "esta capa no entra a ningún índice compuesto.",
        f"**{len(mar)} de los {len(magnitudes)} sismos de la ventana ocurrieron en el "
        "mar** y no se asignan a ningún Estado. No se descartan: en esta región la fosa "
        "está mar adentro y **ahí ocurren los más grandes**, que son además los que "
        "pueden generar tsunami. Descartarlos habría borrado lo más importante.",
        f"La ventana es de {DIAS} días y el umbral, magnitud {MAGNITUD}. Por debajo de "
        "ese umbral hay muchísimos más sismos, casi todos sin consecuencia; por encima, "
        "el catálogo es prácticamente completo. **Cambiar el umbral cambia todos los "
        "recuentos**, de modo que no se los compare con los de otra fuente sin "
        "verificar qué umbral usa.",
        "**La asignación a un Estado es por el epicentro**, no por dónde se sintió. Un "
        "sismo con epicentro en un país se siente en los vecinos y aparece sólo en la "
        "ficha del primero.",
        "**El catálogo se revisa.** Las magnitudes de las primeras horas se corrigen "
        "después: lo que se publica es la lectura del momento de la consulta, con su "
        "fecha, y no la versión definitiva del catálogo.",
        "La marca de tsunami del catálogo indica que el evento **cumplió los criterios "
        "para evaluar** una alerta, no que haya habido tsunami ni daño.",
    ]
    if sinCoordenada:
        vacios.append(f"{sinCoordenada} eventos llegaron sin coordenada utilizable y "
                      "quedaron fuera del reparto por Estado.")

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=1,
        corroborado=True,
        nota=("Servicio geológico estatal con red instrumental propia y catálogo "
              "público revisado. Credibilidad 1 con corroboración porque el sismo es un "
              "hecho físico medido por múltiples estaciones independientes y publicado "
              "en paralelo por otros servicios sismológicos nacionales."),
    )

    return comun.escribir(
        colector="sismos",
        capa="publico",
        fuente=FUENTE,
        url_fuente=URL_FUENTE,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "ventana_dias": DIAS,
                "desde": desde,
                "magnitud_minima": MAGNITUD,
                "sismos": len(magnitudes),
                "en_tierra": len(magnitudes) - len(mar),
                "mar_adentro": len(mar),
                "estados_con_sismo": sum(1 for r in registros if r["sismos"]),
                "estados_del_padron": len(registros),
                "por_magnitud": dict(reparto),
                "consultado": comun.ahora(),
            },
            "mar": {
                "cantidad": len(mar),
                "mayores": mar[:8],
                "dice": ("Sismos cuyo epicentro cae fuera de tierra firme. No se "
                         "descartan: en esta región la fosa está mar adentro y ahí "
                         "ocurren los más grandes."),
            },
            "recuadro_comprobado": {
                "mundo": n_mundo,
                "recuadro": n_region,
                "dice": ("El recuadro se comprueba en cada corrida contra el recuento "
                         "mundial: tiene que recortar y tiene que dar más que cero."),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("sismos", recolectar)
