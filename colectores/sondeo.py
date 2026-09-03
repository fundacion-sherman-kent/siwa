"""El banco de pruebas: las fuentes que todavía no entraron, medidas solas.

POR QUÉ EXISTE
--------------
El catálogo tiene una lista de fuentes **trabadas**: la que devolvió 500, la que
pide una credencial, la que no respondió el día que se la probó. Hasta hoy esa
lista dependía de que alguien se acordara de reintentar, y **nadie se acuerda**.

Peor todavía: una fuente puede haber vuelto hace tres semanas y nosotros
seguiríamos escribiendo en el catálogo que no responde.

Este colector las prueba en cada corrida y **guarda el resultado de cada
intento**. Con eso se contesta lo único que importa antes de construir encima de
una fuente: **¿de cada cien veces, cuántas responde?**

LA REGLA DE LA CASA, CONVERTIDA EN MAQUINARIA
----------------------------------------------
«Probar antes de afirmar» era una disciplina personal. Acá pasa a ser
infraestructura: ninguna fuente candidata entra al registro sin una cifra de
disponibilidad medida por el mismo robot que después la va a usar.

Y una precisión que evita el error de siempre: **esto NO mide la calidad de la
fuente.** Mide si contesta. Una fuente que contesta siempre y publica basura
sigue siendo basura; una que contesta la mitad de las veces puede ser
excelente y estar sobrecargada.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import comun

RAIZ = Path(__file__).resolve().parent.parent
BITACORA = RAIZ / "datos" / "sondeo.json"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# Cuántos intentos se conservan por candidata. Alcanza para una cifra estable y
# no deja crecer el archivo sin freno.
MEMORIA = 200

# Cada candidata declara QUE se le pide y QUE cuenta como respuesta buena. El
# «porque» dice para qué la queremos, de modo que quien lea esto dentro de seis
# meses no tenga que reconstruirlo.
CANDIDATAS = [
    {
        "clave": "gdelt",
        "rotulo": "GDELT — noticias del día, multilingües",
        "url": ("https://api.gdeltproject.org/api/v2/doc/doc"
                "?query=homicidio&mode=artlist&format=json&maxrecords=1"),
        "porque": "Sería la mejor pieza de la capa de hoy: noticias del día, en varias "
                  "lenguas, acotables por país y sin credencial.",
        "traba": "Respondió 2 de unas 20 consultas el 3 de septiembre de 2026.",
    },
    {
        "clave": "cepalstat",
        "rotulo": "CEPALSTAT — serie de un indicador",
        "url": "https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/2246/data?lang=es&format=json",
        "porque": "Es la única fuente estadística probada que es NATIVA de la región. "
                  "Su árbol temático responde; la descarga del dato, no.",
        "traba": "500 · Internal Server Error.",
    },
    {
        "clave": "reliefweb",
        "rotulo": "ReliefWeb — desastres y crisis",
        "url": "https://api.reliefweb.int/v2/disasters?appname=fusk-siwa&limit=1",
        "porque": "Capa de hoy: desastres y crisis con fecha y país.",
        "traba": "403 · exige un nombre de aplicación autorizado, que hay que pedir.",
    },
    {
        "clave": "ucdp",
        "rotulo": "UCDP — conflicto armado",
        "url": "https://ucdpapi.pcr.uu.se/api/gedevents/24_1?pagesize=1",
        "porque": "Reemplazo posible de las dos series de terrorismo detenidas en 2021, y "
                  "con licencia de atribución que SÍ permite redistribuir.",
        "traba": "401 · pide un testigo. Falta averiguar si es gratuito.",
    },
    {
        "clave": "ops",
        "rotulo": "OPS — datos abiertos de salud",
        "url": "https://opendata.paho.org/api/3/action/package_search?q=mortality&rows=1",
        "porque": "Mortalidad por causa, incluida la violenta, con cobertura regional.",
        "traba": "404 en la ruta publicada.",
    },
    {
        "clave": "iom_dtm",
        "rotulo": "OIM DTM — desplazamiento en curso",
        "url": "https://dtmapi.iom.int/api/common/GetAllCountryList",
        "porque": "Flujos de desplazamiento casi en vivo, que la serie anual de ACNUR no da.",
        "traba": "404 en tres rutas distintas.",
    },
]


def _probar(c: dict) -> dict:
    inicio = datetime.now(timezone.utc)
    try:
        peticion = urllib.request.Request(
            c["url"], headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
        with urllib.request.urlopen(peticion, timeout=35) as respuesta:
            cuerpo = respuesta.read(120_000)
            estado, detalle = respuesta.status, ""
    except urllib.error.HTTPError as error:
        estado, cuerpo, detalle = error.code, b"", "rechazo del servidor"
    except Exception as error:  # noqa: BLE001
        estado, cuerpo, detalle = 0, b"", type(error).__name__

    # Responder no es servir: un 200 con cero bytes no sirve para nada.
    sirve = estado == 200 and len(cuerpo) > 40
    return {
        "estado": estado,
        "bytes": len(cuerpo),
        "sirve": sirve,
        "detalle": detalle,
        "cuando": inicio.isoformat(timespec="seconds"),
    }


def _cargar() -> dict:
    if BITACORA.exists():
        try:
            return json.loads(BITACORA.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"intentos": {}}


def recolectar():
    bit = _cargar()
    registros = []

    for c in CANDIDATAS:
        r = _probar(c)
        previos = bit["intentos"].get(c["clave"], [])
        previos.append(r)
        bit["intentos"][c["clave"]] = previos[-MEMORIA:]

        serie = bit["intentos"][c["clave"]]
        buenos = sum(1 for x in serie if x.get("sirve"))
        # El último día que sirvió: es la pregunta que se le hace a una fuente
        # trabada —«¿volvió?»— y no se puede contestar sin memoria.
        ultimoBueno = next((x["cuando"][:10] for x in reversed(serie) if x.get("sirve")), None)

        registros.append({
            "clave": c["clave"], "rotulo": c["rotulo"],
            "porque": c["porque"], "traba_declarada": c["traba"],
            "intentos": len(serie),
            "respondio_bien": buenos,
            "disponibilidad_pct": round(buenos / len(serie) * 100, 1) if serie else None,
            "ultimo_intento": r,
            "ultimo_dia_que_sirvio": ultimoBueno,
            "veredicto": ("sirve_siempre" if buenos == len(serie) and len(serie) >= 5 else
                          "intermitente" if 0 < buenos < len(serie) else
                          "nunca_respondio" if buenos == 0 else "pocos_intentos"),
        })

    BITACORA.write_text(json.dumps(bit, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    vacios = [
        "ESTO NO MIDE LA CALIDAD DE UNA FUENTE: MIDE SI CONTESTA. Una fuente que contesta "
        "siempre y publica basura sigue siendo basura; una que contesta la mitad de las "
        "veces puede ser excelente y estar sobrecargada.",
        "RESPONDER NO ES SERVIR. Un 200 con cero bytes no sirve para nada, de modo que un "
        "intento cuenta como bueno solo si ademas devolvio contenido.",
        "LA MEDICION ES DESDE UNA SOLA MAQUINA Y UNA SOLA RED. Una fuente puede estar viva "
        "para el mundo y caida para el robot: la cifra dice cuanto pudo usarla ESTE "
        "registro, que es justamente lo que hay que saber antes de construir encima.",
        f"SE CONSERVAN LOS ULTIMOS {MEMORIA} INTENTOS por candidata. Mas atras no se "
        "guarda, de modo que la disponibilidad describe el periodo reciente y no toda la "
        "historia.",
        "UNA CANDIDATA QUE NO FIGURA ACA NO FUE DESCARTADA: es que nadie la puso en la "
        "lista. El banco prueba lo que se le declara, no todo lo que existe.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=1,
        corroborado=True,
        nota=("Medicion propia del robot sobre su propia capacidad de alcanzar cada "
              "fuente. Fiabilidad A y credibilidad 1 porque el hecho medido es la "
              "respuesta que el registro recibio: no hay intermediario entre la "
              "observacion y quien la publica, y cada intento queda con su fecha."),
    )

    sirven = [r for r in registros if r["veredicto"] == "sirve_siempre"]
    return comun.escribir(
        colector="sondeo",
        capa="publico",
        fuente="Fundación Sherman Kent — banco de pruebas de fuentes candidatas",
        url_fuente="https://fundacion-sherman-kent.github.io/siwa/sitio/index.html#sondeo",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "candidatas": len(registros),
                "listas_para_construir": len(sirven),
                "intermitentes": sum(1 for r in registros if r["veredicto"] == "intermitente"),
                "sin_responder": sum(1 for r in registros if r["veredicto"] == "nunca_respondio"),
                "intentos_guardados": sum(r["intentos"] for r in registros),
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("sondeo", recolectar)
