"""Desastres y emergencias — el registro operativo de la Cruz Roja (IFRC GO).

El registro no tenía **ninguna** capa de desastres, y en esta región eso es un
hueco grande: inundación, ciclón, sequía, terremoto, erupción y epidemia
condicionan la situación de un Estado tanto como la violencia o la economía.

Qué es esta fuente, exactamente
-------------------------------
**IFRC GO es el sistema operativo de la Federación Internacional de Sociedades
de la Cruz Roja y de la Media Luna Roja.** Registra las emergencias ante las que
la red responde o sobre las que informa. **No es un catálogo de todos los
desastres del mundo**, y la diferencia manda: un Estado con sociedad nacional
grande y activa reporta más que uno con sociedad chica. **Más asientos no
significan más desastres: pueden significar más capacidad de respuesta.** Va
declarado en cada ficha.

El filtro que no filtra
-----------------------
La interfaz acepta `countries__iso3` **y lo ignora en silencio**: pedirle los
eventos de Colombia devuelve los 6.065 del mundo, exactamente igual que pedirle
un parámetro inventado. Un colector que le creyera publicaría los desastres del
planeta entero como si fueran de un país. Por eso **se filtra por región —que sí
filtra, y se comprueba en cada corrida— y el país se cruza acá** contra el
padrón, con los códigos que la propia fuente trae en cada evento.
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

BASE = "https://goadmin.ifrc.org/api/v2/event/"
FUENTE = ("IFRC GO — Federación Internacional de Sociedades de la Cruz Roja y de la "
          "Media Luna Roja, registro de emergencias")
URL_FUENTE = "https://go.ifrc.org/emergencies"
NAVEGADOR = comun.AGENTE

REGION_AMERICAS = 1
REGION_IMPOSIBLE = 99      # no existe: tiene que devolver cero
ANIOS = 5
TAMANO = 200
TOPE_PAGINAS = 12
ESPERA = 90
INTENTOS = 3
DESCANSO = 8

MINIMO_ESTADOS = 12        # de 33; con la ventana de 5 años se verificaron mas
EVENTOS_POR_ESTADO = 6     # los mas recientes que se publican por ficha

GRAVEDAD = {
    "Red": {"clave": "roja", "rotulo": "Roja", "orden": 3},
    "Orange": {"clave": "naranja", "rotulo": "Naranja", "orden": 2},
    "Yellow": {"clave": "amarilla", "rotulo": "Amarilla", "orden": 1},
}

# Los rotulos de tipo vienen en ingles. Se traducen los que aparecen en la region
# y el resto se publica como llega: inventar una traduccion para un tipo que no
# se vio seria adivinar.
TIPOS = {
    "Flood": "Inundación", "Pluvial/Flash Flood": "Inundación repentina",
    "Cyclone": "Ciclón", "Storm Surge": "Marejada", "Drought": "Sequía",
    "Earthquake": "Terremoto", "Volcanic Eruption": "Erupción volcánica",
    "Landslide": "Deslizamiento", "Fire": "Incendio", "Forest Fire": "Incendio forestal",
    "Epidemic": "Epidemia", "Food Insecurity": "Inseguridad alimentaria",
    "Population Movement": "Movimiento de población", "Cold Wave": "Ola de frío",
    "Heat Wave": "Ola de calor", "Civil Unrest": "Disturbios civiles",
    "Complex Emergency": "Emergencia compleja", "Other": "Otro",
    "Biological Emergency": "Emergencia biológica", "Tsunami": "Tsunami",
    "Transport Accident": "Accidente de transporte",
    "Chemical Emergency": "Emergencia química",
}


def _pedir(consulta: str) -> dict:
    url = f"{BASE}?format=json&{consulta}"
    ultimo = ""
    for intento in range(INTENTOS):
        try:
            peticion = urllib.request.Request(url, headers={
                "User-Agent": NAVEGADOR, "Accept": "application/json"})
            with urllib.request.urlopen(peticion, timeout=ESPERA,
                                        context=ssl.create_default_context()) as r:
                return json.loads(r.read(20_000_000).decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"IFRC GO respondió HTTP {e.code} en «{consulta[:70]}»") from e
        except Exception as e:  # noqa: BLE001 — falla de red: se reintenta
            ultimo = f"{type(e).__name__}: {e}"
            print(f"[desastres] intento {intento + 1} de {INTENTOS}: {ultimo}",
                  file=sys.stderr)
            time.sleep(DESCANSO * (intento + 1))
    raise RuntimeError(f"No hubo respuesta en {INTENTOS} intentos: {ultimo}")


def _probar_el_filtro() -> tuple:
    """EL FILTRO TIENE QUE FILTRAR, y se comprueba en cada corrida.

    Esta fuente acepta parametros que no aplica y contesta 200 igual. Se le
    piden tres cosas cuyo resultado se conoce de antemano: el total, la region
    de las Americas —que tiene que ser MENOR que el total— y una region que no
    existe —que tiene que dar cero—. Si las tres no se cumplen, el filtro no
    esta filtrando y lo que se recolecte sera el mundo entero disfrazado de
    region.
    """
    total = _pedir("limit=1")["count"]
    americas = _pedir(f"limit=1&regions__in={REGION_AMERICAS}")["count"]
    imposible = _pedir(f"limit=1&regions__in={REGION_IMPOSIBLE}")["count"]
    if not (0 < americas < total) or imposible != 0:
        raise RuntimeError(
            f"El filtro por región NO está filtrando: total {total}, Américas "
            f"{americas}, región inexistente {imposible}. Se esperaba que las "
            "Américas fueran menos que el total y que la región inexistente diera "
            "cero. Sin esa garantía, lo que se recolecte serían los desastres del "
            "mundo entero publicados como si fueran de la región. No se publica.")
    return total, americas


def recolectar():
    total_mundo, total_americas = _probar_el_filtro()

    hoy = datetime.datetime.now(datetime.timezone.utc)
    desde = (hoy - datetime.timedelta(days=365 * ANIOS)).date().isoformat()
    consulta = (f"regions__in={REGION_AMERICAS}&disaster_start_date__gte={desde}"
                f"&ordering=-disaster_start_date&limit={TAMANO}")

    eventos, pagina, desplazamiento = [], 0, 0
    while pagina < TOPE_PAGINAS:
        cuerpo = _pedir(f"{consulta}&offset={desplazamiento}")
        lote = cuerpo.get("results") or []
        eventos.extend(lote)
        pagina += 1
        if not cuerpo.get("next") or not lote:
            break
        desplazamiento += TAMANO

    isos = {p["iso"] for p in geo.padron()}
    porIso: dict = {}
    fuera_del_padron = 0
    for evento in eventos:
        paises = [c.get("iso3") for c in (evento.get("countries") or []) if c.get("iso3")]
        propios = [i for i in paises if i in isos]
        if not propios:
            fuera_del_padron += 1
            continue
        crudo = (evento.get("dtype") or {}).get("name") or "Otro"
        gravedad = GRAVEDAD.get(evento.get("ifrc_severity_level_display") or "")
        ficha = {
            "id": evento.get("id"),
            "nombre": " ".join(str(evento.get("name") or "").split())[:180],
            "tipo": TIPOS.get(crudo, crudo),
            "tipo_en_la_fuente": crudo,
            "comienzo": (evento.get("disaster_start_date") or "")[:10],
            "gravedad": gravedad["rotulo"] if gravedad else None,
            "gravedad_orden": gravedad["orden"] if gravedad else 0,
            "afectados": evento.get("num_affected"),
            "enlace": f"https://go.ifrc.org/emergencies/{evento.get('id')}",
            # Un evento que toca a varios Estados cuenta para cada uno, y se dice
            # cuales son: sumar las fichas de los 33 daria mas que los eventos.
            "alcanza": propios,
        }
        for iso in propios:
            porIso.setdefault(iso, []).append(ficha)

    # PROBAR ANTES DE AFIRMAR: con una ventana de cinco años, que casi ningun
    # Estado de la region tenga una sola emergencia describe una lectura fallida,
    # no una region sin desastres.
    if len(porIso) < MINIMO_ESTADOS:
        raise RuntimeError(
            f"Sólo {len(porIso)} de los 33 Estados tienen alguna emergencia en "
            f"{ANIOS} años, y se esperaban al menos {MINIMO_ESTADOS}. Eso no "
            "describe a América Latina y el Caribe: describe una lectura fallida. "
            "No se publica.")

    registros = []
    for pais in geo.padron():
        fichas = sorted(porIso.get(pais["iso"], []),
                        key=lambda f: f["comienzo"], reverse=True)
        porTipo = collections.Counter(f["tipo"] for f in fichas)
        porGravedad = collections.Counter(f["gravedad"] for f in fichas if f["gravedad"])
        registros.append({
            "iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
            "emergencias": len(fichas),
            "tipos": [{"tipo": t, "cantidad": n} for t, n in porTipo.most_common()],
            "por_gravedad": dict(porGravedad),
            "ultima": fichas[0] if fichas else None,
            "recientes": fichas[:EVENTOS_POR_ESTADO],
        })
    registros.sort(key=lambda r: (-r["emergencias"], r["pais"]))

    tipos_region = collections.Counter()
    for r in registros:
        for t in r["tipos"]:
            tipos_region[t["tipo"]] += t["cantidad"]
    sin_registro = [r["pais"] for r in registros if not r["emergencias"]]

    vacios = [
        "**Esto registra las emergencias ante las que la red de la Cruz Roja responde o "
        "sobre las que informa, no todos los desastres que ocurren.** Un Estado con "
        "sociedad nacional grande y activa deja más asientos que uno con sociedad chica. "
        "**Más emergencias registradas puede significar más capacidad de respuesta, no "
        "más desastres.** Es la advertencia que manda en esta capa.",
        "**El nivel de gravedad —amarillo, naranja, rojo— es la escala operativa de la "
        "propia Federación**, pensada para decidir despliegues. No mide daño ni "
        "víctimas: mide qué respuesta amerita el hecho a juicio de la organización.",
        "**La cantidad de afectados falta en la mayoría de los asientos** y por eso no se "
        "usa para ordenar Estados. Cuando está, es la estimación operativa del momento, "
        "que suele corregirse después y que este registro no persigue.",
        "**Un evento que alcanza a varios Estados cuenta en la ficha de cada uno.** "
        "Sumar las fichas de los 33 da más que la cantidad de eventos: cada ficha "
        "publica qué Estados alcanza para que la cuenta se pueda rehacer.",
        f"La ventana es de {ANIOS} años. Lo anterior existe en la fuente y no se trae: "
        "esta capa sirve para ver el período reciente, no para una serie histórica.",
        "**El filtro por país de esta interfaz no funciona: se lo pide y contesta el "
        "mundo entero.** Se filtra por región —que sí filtra, y se comprueba en cada "
        "corrida con una región inexistente que debe dar cero— y el país se cruza acá "
        "con los códigos que la propia fuente trae en cada evento.",
    ]
    if sin_registro:
        vacios.append(
            f"**{len(sin_registro)} Estados no tienen ninguna emergencia registrada en la "
            f"ventana**: {', '.join(sin_registro)}. No significa que no hayan tenido "
            "desastres: significa que la red no registró operación ni informe.")
    if fuera_del_padron:
        vacios.append(
            f"{fuera_del_padron} emergencias de la región americana quedaron fuera por "
            "corresponder a Estados que no integran el padrón de los 33 —Estados Unidos, "
            "el Canadá y territorios—.")

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Registro operativo de la organización humanitaria que responde: fuente "
              "primaria sobre su propia actividad y sobre los hechos que la motivan. Lo "
              "que se consigna es que la emergencia fue registrada y con qué rótulo, no "
              "una medición independiente de su magnitud."),
    )

    return comun.escribir(
        colector="desastres",
        capa="publico",
        fuente=FUENTE,
        url_fuente=URL_FUENTE,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "ventana_anios": ANIOS,
                "desde": desde,
                "emergencias": sum(r["emergencias"] for r in registros),
                "estados_con_registro": sum(1 for r in registros if r["emergencias"]),
                "estados_del_padron": len(registros),
                "eventos_leidos": len(eventos),
                "por_tipo": dict(tipos_region.most_common()),
                "consultado": comun.ahora(),
            },
            "filtro_comprobado": {
                "total_mundial": total_mundo,
                "region_americas": total_americas,
                "region_inexistente": 0,
                "dice": ("El filtro por región se comprueba en cada corrida: las Américas "
                         "tienen que ser menos que el total mundial y una región "
                         "inexistente tiene que dar cero."),
            },
            "escala_de_gravedad": [
                {"rotulo": g["rotulo"], "orden": g["orden"]}
                for g in sorted(GRAVEDAD.values(), key=lambda x: -x["orden"])
            ],
        },
    )


if __name__ == "__main__":
    comun.correr("desastres", recolectar)
