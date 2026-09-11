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
# DOS CANDIDATAS SALIERON DE ESTA LISTA PORQUE SE RESOLVIERON, el 7 de septiembre
# de 2026, y conviene recordar como:
#
# UCDP pedia un testigo. Se gestiono y se obtuvo, pero resulto que EL MISMO
# CONJUNTO se descarga como archivo sin credencial: la puerta con llave no era la
# unica. Antes de gestionar un permiso conviene mirar si hay otra puerta.
#
# CEPALSTAT figuraba como «nunca respondio» por un 500. La interfaz estaba SANA:
# lo que estaba roto era EL INDICADOR CON EL QUE SE LA PROBABA. Probar una fuente
# con un solo indicador y concluir que la fuente esta muerta es el mismo error que
# probar un pais y concluir que no publica.
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
        "clave": "reliefweb",
        "rotulo": "ReliefWeb — desastres y crisis",
        "url": "https://api.reliefweb.int/v2/disasters?appname=fusk-siwa&limit=1",
        "porque": "Capa de hoy: desastres y crisis con fecha y país.",
        "traba": "403 · exige un nombre de aplicación autorizado, que hay que pedir.",
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

    # ── Portales oficiales que existen y le cierran la puerta a las maquinas ──
    # Hallados en la auditoria del 6 de septiembre de 2026: los cinco publican
    # para personas y devuelven 403, 500 o nada a un programa. NO son fuentes
    # descartadas: son fuentes CERRADAS HOY. El banco las prueba todos los dias
    # para que el registro se entere EL MISMO DIA en que abran, sin que nadie
    # tenga que acordarse de volver a mirar.
    {
        "clave": "datos_ecuador",
        "rotulo": "Ecuador — portal de datos abiertos",
        "url": "https://www.datosabiertos.gob.ec/api/3/action/package_search?rows=1",
        "porque": "Ecuador tiene dominio oficial probado y catálogo publicado: sumarlo "
                  "cerraría uno de los huecos de datos de gobierno.",
        "traba": "403 · bloquea incluso identificándose como navegador.",
    },
    {
        "clave": "datos_guatemala",
        "rotulo": "Guatemala — portal de datos abiertos",
        "url": "https://www.datos.gob.gt/api/3/action/package_search?rows=1",
        "porque": "Mismo caso que Ecuador: el portal existe y responde a personas.",
        "traba": "403 · bloquea incluso identificándose como navegador.",
    },
    {
        "clave": "datos_bolivia",
        "rotulo": "Bolivia — portal de datos abiertos",
        "url": "https://datos.gob.bo/api/3/action/package_search?rows=1",
        "porque": "Mismo caso: dominio oficial probado, catálogo cerrado a los programas.",
        "traba": "403 · bloquea incluso identificándose como navegador.",
    },
    {
        "clave": "estadistica_costarica",
        "rotulo": "Costa Rica — instituto de estadística",
        "url": "https://www.inec.cr/",
        "porque": "Costa Rica es un Estado de alta transparencia y sin embargo NO tiene "
                  "ninguna fuente oficial en el registro: su instituto bloquea y su "
                  "portal de datos no responde. El hueco es técnico, no político.",
        "traba": "403 en el instituto; el portal de datos no resuelve.",
    },
    {
        "clave": "estadistica_cuba",
        "rotulo": "Cuba — oficina nacional de estadística",
        "url": "https://onei.gob.cu/",
        "porque": "Es la única vía oficial de cifras cubanas. Sin ella, Cuba queda "
                  "descrita sólo por fuentes de terceros. Su sitio YA RESPONDE y está "
                  "en el padrón de oficinas de estadística; lo que falta es que "
                  "publique algo consultable por máquina.",
        "traba": "Responde como sitio para personas: no expone catálogo ni interfaz.",
    },
    # ---- Halladas en la busqueda del 8 de septiembre de 2026 ----------------
    {
        "clave": "global_forest_watch",
        "rotulo": "Global Forest Watch — pérdida de bosque por Estado",
        "url": "https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss",
        "porque": "Daría hectáreas donde hoy solo hay una evaluación de especialistas de 1 a "
                  "10: «delitos contra la flora» es una de las medidas del Índice Global de "
                  "Crimen Organizado y no tiene ninguna cifra física detrás.",
        "traba": "El catálogo responde sin credencial, pero la consulta de datos devuelve 403: "
                 "exige una clave que hay que pedir. Probado el 9 de septiembre de 2026.",
    },
    {
        "clave": "hdx_hapi",
        "rotulo": "HDX HAPI (OCHA) — interfaz humanitaria",
        "url": "https://hapi.humdata.org/docs",
        "porque": "La alternativa real a ReliefWeb: desastres, crisis, desplazados internos y "
                  "seguridad alimentaria por país, con licencia CC BY 4.0. No pide "
                  "autorización: pide un identificador de aplicación que se genera con un "
                  "nombre y un correo institucional. Es una decisión de la Dirección, no "
                  "una carta.",
        "traba": "Sin identificador de aplicación las consultas devuelven 403; la "
                 "documentación responde.",
    },
    {
        "clave": "itu_gci",
        "rotulo": "UIT — Índice Global de Ciberseguridad",
        "url": "https://datahub.itu.int/api/v1/data?indicator=90014",
        "porque": "La única medida comparable de ciberseguridad para los 33 Estados: cinco "
                  "pilares, puntaje de 0 a 100, edición 2024.",
        "traba": "La interfaz contesta 202 sin cuerpo a un programa, y la reproducción de "
                 "datos de la UIT exige permiso escrito (jur@itu.int). Es una carta.",
    },
    {
        "clave": "ncsi",
        "rotulo": "NCSI — Índice Nacional de Ciberseguridad (e-Governance Academy)",
        "url": "https://ncsi.ega.ee/country/ar/",
        "porque": "Índice vivo de preparación en ciberseguridad, 160 países, con evidencia "
                  "pública por país; cubre 15 de los 33 Estados con puntaje.",
        "traba": "Sus condiciones prohíben reproducir sin acuerdo con el aviso de derechos. "
                 "Es una carta (ncsi@ega.ee). La página responde.",
    },
    {
        "clave": "inegi_mexico",
        "rotulo": "INEGI — instituto de estadística de México",
        "url": "https://www.inegi.org.mx/servicios/api_indicadores.html",
        "porque": "México es el Estado del padrón con más unidades de primer orden (32) y "
                  "su instituto publica interfaz propia. Es la clase de fuente que la "
                  "doctrina subnacional pide: la jurisdicción consultada a sí misma.",
        "traba": "Su interfaz exige una credencial que se pide en el sitio. Falta pedirla "
                 "y decidir qué indicadores entran.",
    },
    {
        "clave": "observatorios_nacionales",
        "rotulo": "Observatorios nacionales de violencia — CERAC, Ideas para la Paz, IUDPAS",
        "url": "https://iudpas.unah.edu.hn/",
        "porque": "Los observatorios de la propia región miden con más detalle que "
                  "cualquier organismo mundial, y son la fuente que la doctrina subnacional "
                  "pide para contrastar lo que dice el Estado sobre sí mismo.",
        "traba": "NINGUNO PUBLICA PARA MÁQUINAS. CERAC rechaza al programa con un 406, "
                 "Ideas para la Paz no responde, el de Guatemala tampoco, y el de Honduras "
                 "entrega páginas web. Publican informes en PDF para personas. Que un "
                 "observatorio de transparencia no sea legible por máquina ES EN SÍ MISMO "
                 "UN DATO sobre el acceso a la información en la región.",
    },
    {
        "clave": "ilostat",
        "rotulo": "OIT — ILOSTAT, estadísticas del trabajo",
        "url": "https://rplumber.ilo.org/data/indicator/?id=SDG_0831_SEX_ECO_RT_A&ref_area=ARG&format=.json",
        "porque": "SEGUNDA FUENTE del bloque laboral, que hoy sostiene solo el Banco "
                  "Mundial: empleo informal en 27 de los 33 Estados y desempleo juvenil "
                  "en 29, medido y comprobado. Además trae desempleo total en los 33 con "
                  "serie desde 1969.",
        "traba": "Ninguna medida: contesta JSON sin credencial. Falta escribir el colector "
                 "y filtrar las dimensiones de sexo y edad, que vienen desagregadas.",
    },
    {
        "clave": "oms_gho",
        "rotulo": "OMS — Observatorio Mundial de la Salud",
        "url": "https://ghoapi.azureedge.net/api/Indicator?$top=3",
        "porque": "Segunda fuente para violencia letal y puerta a materias que el registro "
                  "no mide: mortalidad por causa, suicidio, muertes de tránsito. El "
                  "registro ya usa una cifra suya de homicidios por otra vía; esta es la "
                  "interfaz completa.",
        "traba": "Ninguna medida: contesta JSON sin credencial. Falta elegir indicadores.",
    },
    {
        "clave": "bid_datos",
        "rotulo": "BID — Números para el Desarrollo",
        "url": "https://data.iadb.org/api/3/action/package_search?rows=1",
        "porque": "Banco regional con datos propios de América Latina y el Caribe. Su "
                  "catálogo abierto tiene 1.591 conjuntos y responde sin credencial.",
        "traba": "La dirección anterior estaba mal y por eso daba 404: la buena es "
                 "data.iadb.org, no mydata. Lo que publica son en su mayoría MICRODATOS "
                 "DE INVESTIGACIÓN —encuestas asociadas a papers— y no series de "
                 "indicadores comparables entre países, que es lo que este registro usa. "
                 "Sirve para bajar a un tema puntual, no como segunda fuente de una "
                 "materia.",
    },
    {
        "clave": "lapop",
        "rotulo": "LAPOP — Barómetro de las Américas",
        "url": "https://www.vanderbilt.edu/lapop/",
        "porque": "Segunda fuente de lo que la gente DECLARA —victimización, confianza en "
                  "la policía, percepción de corrupción—, que hoy mide solo la comisión "
                  "regional. Es la encuesta de referencia del hemisferio.",
        "traba": "Publica en informes y en archivos de encuesta, no en una interfaz de "
                 "datos. Hay que ver si existe una ruta legible por máquina.",
    },
    {
        "clave": "uis_unesco",
        "rotulo": "UNESCO — Instituto de Estadística (interfaz abierta)",
        "url": "https://api.uis.unesco.org/api/public/data/indicators?indicator=CR.1&geoUnit=ARG",
        "porque": "Educación y ciencia para los 33, con licencia CC BY-SA 3.0 IGO. No es la "
                  "ruta del convenio de 1970 que se le pide a UNESCO por carta: es otra "
                  "puerta, abierta, para el eje de Desarrollo.",
        "traba": "Ninguna medida: contesta JSON. Falta decidir qué indicadores entran.",
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
        "Esto no mide la calidad de una fuente: mide si contesta. Una fuente que contesta "
        "siempre y publica basura sigue siendo basura; una que contesta la mitad de las "
        "veces puede ser excelente y estar sobrecargada.",
        "Responder no es servir. Un 200 con cero bytes no sirve para nada, de modo que un "
        "intento cuenta como bueno solo si además devolvió contenido.",
        "La medición es desde una sola maquina y una sola red. Una fuente puede estar viva "
        "para el mundo y caída para el robot: la cifra dice cuánto pudo usarla este "
        "registro, que es justamente lo que hay que saber antes de construir encima.",
        f"SE CONSERVAN LOS ULTIMOS {MEMORIA} INTENTOS por candidata. Mas atras no se "
        "guarda, de modo que la disponibilidad describe el periodo reciente y no toda la "
        "historia.",
        "Una candidata que no figura acá no fue descartada: es que nadie la puso en la "
        "lista. El banco prueba lo que se le declara, no todo lo que existe.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=1,
        corroborado=True,
        nota=("Medicion propia del robot sobre su propia capacidad de alcanzar cada "
              "fuente. Fiabilidad a y credibilidad 1 porque el hecho medido es la "
              "respuesta que el registro recibio: no hay intermediario entre la "
              "observacion y quien la publica, y cada intento queda con su fecha."),
    )

    sirven = [r for r in registros if r["veredicto"] == "sirve_siempre"]
    return comun.escribir(
        colector="sondeo",
        capa="publico",
        fuente="Fundación Sherman Kent — banco de pruebas de fuentes candidatas",
        url_fuente=f"{comun.BASE}/sitio/index.html#sondeo",
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
