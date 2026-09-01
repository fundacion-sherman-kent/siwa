"""Índice de Opacidad — edición cero, materia M6.

**Mide la AUSENCIA, no la presencia.** Es transparencia leída del otro lado, y
esa inversión no es retórica: un puntaje de apertura no se puede refutar
mostrando una dirección, y una afirmación de ausencia sí. Eso es lo que la
vuelve seria.

Lo que se busca, dicho con precisión
------------------------------------
**Un conjunto NACIONAL CONSOLIDADO** de solicitudes de acceso a la información
pública —recibidas, respondidas y denegadas con motivo—. Que cada organismo
publique el suyo **no satisface la exigencia**: sin consolidado no hay cifra del
Estado. La precisión importa: sin ella el caso dominicano no tiene respuesta
correcta.

La regla de asimetría, que es el corazón del método
---------------------------------------------------
**La presencia se prueba con una fuente; la ausencia exige las cuatro.**
Encontrar el dato en un solo lugar alcanza para decir que se publica. Para decir
que **no** se publica hay que haber revisado los cuatro pasos del procedimiento.
Mientras falte uno, el Estado queda **SIN VERIFICAR**, que no es lo mismo que
opaco y **no puntúa**.

Dos capas que no se confunden
-----------------------------
1. **Medición automática**, la que produce este archivo: la dirección de cada
   consulta, su código de respuesta, los términos y la fecha. **Cualquiera la
   repite pegando la dirección**, y por eso no se discute.
2. **Verificación humana**, que vive en `opacidad.json` y la mantiene el equipo
   analítico: si alguno de los candidatos ES el dato exigido. Eso es juicio, va
   marcado como tal y se refuta.

Lo que este colector NO puede hacer
-----------------------------------
Solo el **paso 2** —portal de datos abiertos— tiene interfaz de consulta. Los
pasos 1, 3 y 4 son páginas para navegar, no interfaces: se comprobó que los
portales de las autoridades de transparencia responden pero no exponen sus
estadísticas de forma automatizable. **El índice es irreduciblemente manual más
allá del paso 2**, y conviene que quede escrito acá y no en una nota al pie.

Tampoco emite puntaje de 0 a 100. Las siete dimensiones exigen abrir cada
conjunto y mirar sus columnas. **La edición cero publica el estado de
publicación con su rastro; el puntaje es la edición uno.**
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import comun
import geo

PADRON = Path(__file__).resolve().parent / "opacidad.json"
PORTALES = Path(__file__).resolve().parent / "oficiales.json"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Una ausencia hallada con UNA sola palabra mide nuestro vocabulario, no el del
# Estado. Se busca con varios términos, y los tres se publican en el rastro.
TERMINOS = [
    "solicitudes de acceso a la informacion",
    "acceso a la informacion publica estadisticas",
    "solicitudes de informacion publica",
]

# Descarta el ruido: en estos portales «acceso» aparece en escuelas de difícil
# acceso y en accesos viales. Un candidato tiene que hablar de una SOLICITUD.
PERTINENTE = re.compile(r"solicitud|pedido|requerimiento", re.I)

# El conteo que devuelve el portal NO es una medida: Colombia lo topa en 10.000 y
# los demás cuentan coincidencias de palabra. Se registra como rastro, nunca
# como cifra publicable.
TOPE_CANDIDATOS = 12


def _consultar(portal: dict, termino: str) -> dict:
    """Una consulta, con todo lo necesario para que un tercero la repita."""
    base = portal["base"].rstrip("/")
    q = urllib.parse.quote(termino)
    if portal["tipo"] == "CKAN":
        url = f"{base}/api/3/action/package_search?q={q}&rows={TOPE_CANDIDATOS}"
    else:
        url = f"{base}/api/catalog/v1?q={q}&limit={TOPE_CANDIDATOS}"

    registro = {"termino": termino, "consulta": url, "http": None,
                "devueltos": 0, "pertinentes": 0, "falla": None}
    try:
        peticion = urllib.request.Request(
            url, headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
        with urllib.request.urlopen(peticion, timeout=35) as respuesta:
            registro["http"] = respuesta.status
            crudo = json.loads(respuesta.read(900_000).decode("utf-8", "replace"))
    except Exception as error:  # noqa: BLE001 — la falla se declara, no se oculta
        registro["falla"] = type(error).__name__
        return registro

    if portal["tipo"] == "CKAN":
        crudos = crudo.get("result", {}).get("results", [])
        titulos = [(c.get("title") or "").strip() for c in crudos]
    else:
        crudos = crudo.get("results", [])
        titulos = [(c.get("resource", {}).get("name") or "").strip() for c in crudos]

    registro["devueltos"] = len(titulos)
    registro["pertinentes"] = sum(1 for t in titulos if PERTINENTE.search(t))
    return registro


def _rastro(portal: dict) -> list:
    with ThreadPoolExecutor(max_workers=3) as ejecutor:
        return list(ejecutor.map(lambda t: _consultar(portal, t), TERMINOS))


def recolectar():
    padron = json.loads(PADRON.read_text(encoding="utf-8"))
    portales = json.loads(PORTALES.read_text(encoding="utf-8"))["portales"]
    verificado = {e["iso"]: e for e in padron["estados"]}
    sin_hallar = padron.get("_no_verificados_con_portal", {})

    # La medición automática se corre de nuevo en cada pasada: si un portal deja
    # de responder o un conjunto desaparece, se ve acá y no seis meses después.
    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        rastros = dict(zip((p["iso"] for p in portales),
                           ejecutor.map(_rastro, portales)))

    caidas = [f"{iso}: {r['falla']}" for iso, rs in rastros.items()
              for r in rs if r["falla"]]

    registros = []
    for pais in geo.padron():
        iso = pais["iso"]
        ficha = verificado.get(iso)
        rastro = rastros.get(iso, [])
        if ficha:
            estado = ficha["estado"]
            detalle = {k: ficha[k] for k in
                       ("organismo", "conjunto", "enlace", "formatos",
                        "ultima_actualizacion", "pasos_revisados", "verificado", "nota")
                       if k in ficha}
        else:
            estado = "sin_verificar"
            detalle = {"nota": sin_hallar.get(
                iso,
                "Todavia no se verifico. NO cuenta como opaco: significa que la "
                "Oficina aun no reviso los cuatro pasos en este Estado.")}
        registros.append({
            "iso": iso, "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": estado,
            **detalle,
            "rastro": rastro,
        })

    cuenta = {}
    for r in registros:
        cuenta[r["estado"]] = cuenta.get(r["estado"], 0) + 1

    vacios = [
        "LA PRESENCIA SE PRUEBA CON UNA FUENTE; LA AUSENCIA EXIGE LAS CUATRO. Por eso "
        "ningun Estado figura como «no publica»: para afirmarlo hay que haber revisado "
        "organismo productor, portal de datos abiertos, portal de transparencia activa y "
        "memoria institucional. Mientras falte uno, dice SIN VERIFICAR.",
        "SIN VERIFICAR NO ES OPACO. Es la Oficina diciendo que todavia no miro. Contarlo "
        "como opacidad seria cometer, en el propio indice, el error que el indice existe "
        "para señalar.",
        f"Solo el paso 2 —portal de datos abiertos— tiene interfaz de consulta, y solo "
        f"{len(portales)} de los 33 Estados tienen portal verificado. Los pasos 1, 3 y 4 son "
        "paginas para navegar: se comprobo que las autoridades de transparencia responden "
        "pero no exponen sus estadisticas de forma automatizable. El indice es "
        "irreduciblemente manual mas alla del paso 2.",
        "EL CONTEO DEL PORTAL NO ES UNA MEDIDA y no se publica como cifra. Colombia lo topa "
        "en 10.000 y los demas cuentan coincidencias de palabra: se hallaron escuelas de "
        "«dificil acceso» entre los resultados de «acceso a la informacion». Va en el rastro "
        "para que la consulta se pueda repetir, nada mas.",
        "NO SE PUBLICA PUNTAJE DE 0 A 100. Las siete dimensiones del metodo —accesibilidad, "
        "actualidad, periodicidad, desagregacion, formato y continuidad— exigen abrir cada "
        "conjunto y mirar sus columnas. Esta edicion publica el ESTADO DE PUBLICACION con su "
        "rastro; el puntaje es la edicion siguiente.",
        "NO SE VERIFICO, Estado por Estado, que la ley nacional de acceso este vigente y "
        "exija publicar estas estadisticas. La exigencia se apoya en el ODS 16.10.2, que es "
        "universal; la obligacion legal concreta de cada Estado esta pendiente de comprobar.",
        "De los conjuntos hallados NO se verifico el contenido de las columnas: que se "
        "publique «solicitudes de acceso» no prueba que desagregue las denegadas ni su "
        "motivo. Es la verificacion de la edicion siguiente.",
        "TODA CELDA ES REFUTABLE. Si el dato existe y la Oficina no lo encontro, la "
        "correccion se recibe, se verifica, se publica con fecha y se acredita a quien la "
        "aporto. El registro de correcciones es publico y permanente.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=3,
        corroborado=False,
        nota=("Produccion propia con metodo declarado y rastro publicado: la consulta "
              "automatica la puede repetir cualquiera pegando la direccion. Credibilidad 3 "
              "y no 2 porque hasta ahora cada Estado se verifico por UNA sola via —el portal "
              "de datos abiertos—. Una ausencia hallada por un solo camino es un indicio, no "
              "un hecho: con dos vias independientes que coincidan sube a 2."),
    )

    return comun.escribir(
        colector="opacidad",
        capa="publico",
        fuente="Fundacion Sherman Kent — Indice de Opacidad, edicion cero",
        url_fuente="https://fundacion-sherman-kent.github.io/siwa/sitio/index.html#opacidad",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "materia": padron["_lo_que_se_busca"],
            "pasos": padron["_pasos"],
            "regla_de_asimetria": padron["_regla_de_asimetria"],
            "terminos_de_busqueda": TERMINOS,
            "resumen": {
                "publican_consolidado": cuenta.get("publicado", 0),
                "publican_parcial": cuenta.get("parcial", 0),
                "sin_verificar": cuenta.get("sin_verificar", 0),
                "estados_del_padron": len(registros),
                "estados_con_portal_consultable": len(portales),
                "consultado": comun.ahora(),
            },
            "caidas": caidas,
        },
    )


if __name__ == "__main__":
    comun.correr("opacidad", recolectar)
