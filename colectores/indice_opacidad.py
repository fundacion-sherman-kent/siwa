"""Índice de Opacidad — edición uno: el puntaje de 0 a 100.

LA PROMESA QUE SE CUMPLE ACÁ
-----------------------------
La edición cero dejó escrito: «tampoco emite puntaje de 0 a 100… el puntaje es
la edición uno». Esto es la edición uno.

**0 es el Estado más transparente y 100 el más opaco.** La dirección importa y
va dicha: este índice mide la AUSENCIA, no la presencia. Un puntaje de apertura
no se puede refutar mostrando una dirección; una afirmación de ausencia sí, y
eso es lo que la vuelve seria.

POR QUÉ NO SE COPIA LA FÓRMULA DE TRANSPARENCIA INTERNACIONAL
--------------------------------------------------------------
La Dirección sugirió tomarla. Se miró y **se descartó, con motivo**: el índice
de percepción de corrupción es un **promedio de encuestas a expertos**. Mide lo
que un panel *cree* sobre un país. Es un instrumento respetable y contesta una
pregunta legítima, pero **no es la pregunta de esta casa**.

Este registro tiene una ventaja que no conviene tirar: **mide actos observables,
no opiniones**. Que un portal responda o no, que un sitio oficial esté en pie o
retirado, que un Estado haya declarado su comercio de armas a Naciones Unidas —
todo eso **cualquiera lo comprueba repitiendo la consulta**. Una encuesta a
expertos no se puede repetir; una consulta sí.

Por eso el índice se arma con **seis actos**, no con seis percepciones. Y por
eso **no debe compararse con el índice de percepción**: contestan preguntas
distintas y ordenarían distinto con toda razón.

LOS SEIS ACTOS, Y DE DÓNDE SALE CADA UNO
-----------------------------------------
Ninguno es una estimación: los seis los midió este mismo registro y cada uno
tiene su colector, su fecha y su rastro.

1. **Puerta a los datos** — ¿el portal oficial deja que una máquina lo lea?
2. **Sitio oficial en pie** — ¿su organismo sigue en línea o fue retirado?
3. **Compras públicas comparables** — ¿publica contrataciones en formato abierto?
4. **Declara su comercio de armas** — ¿informó el capítulo 93 a Naciones Unidas?
5. **Informa al tratado de especies** — ¿presentó su informe anual a CITES?
6. **Publica lo que importa** — de las seis materias del registro, ¿cuántas
   tienen conjuntos en su portal? Sólo puntúa donde hay portal, y existe porque
   sin él seis Estados empataban en cero.

LO QUE NO SE HACE, Y ES LO MÁS IMPORTANTE
------------------------------------------
**No se castiga lo que no se miró.** Si a un Estado le falta la evidencia de un
acto, ese acto **no puntúa**: no suma ni resta, y el índice se calcula sobre los
que sí tienen evidencia. Un Estado con menos de tres actos medidos queda **SIN
MEDIR**, que no es lo mismo que opaco.

Y hay un caso que parece opacidad y no lo es: cuando el archivo público de la
web no responde, **el que falló es el archivo, no el Estado**. Ese acto se
descarta en lugar de contarse en contra.

LOS PESOS SON IGUALES, Y ES UNA ELECCIÓN
-----------------------------------------
Los seis actos pesan lo mismo. Podría argumentarse que la puerta a los datos
vale más que el informe de especies —y sería razonable—, pero **cualquier
reparto de pesos es un juicio**, y un juicio metido adentro de una fórmula deja
de verse. Pesos iguales es la única elección que no esconde una preferencia. Se
declara acá y se dice en pantalla.
"""

from __future__ import annotations

import json
import sys

import comun
import geo

# El acto vale 0 cuando el Estado lo cumplió y 100 cuando no. Los valores
# intermedios existen donde la realidad es intermedia, y se justifican uno a uno.
MINIMO_ACTOS = 3          # con menos de tres, el Estado queda SIN MEDIR

ACTOS = [
    {"clave": "puerta_datos", "rotulo": "Puerta a los datos",
     "pregunta": "¿El portal oficial deja que una máquina lo lea?",
     "colector": "explorador"},
    {"clave": "sitio_en_pie", "rotulo": "Sitio oficial en pie",
     "pregunta": "¿Su organismo sigue en línea, o fue retirado?",
     "colector": "archivo"},
    {"clave": "compras_comparables", "rotulo": "Compras públicas comparables",
     "pregunta": "¿Publica sus contrataciones en formato abierto y comparable?",
     "colector": "contratacion"},
    {"clave": "declara_armas", "rotulo": "Declara su comercio de armas",
     "pregunta": "¿Informó el capítulo de armas y municiones a Naciones Unidas?",
     "colector": "armas"},
    {"clave": "informa_especies", "rotulo": "Informa al tratado de especies",
     "pregunta": "¿Presentó su informe anual al tratado de especies protegidas?",
     "colector": "cites"},
    # EL ACTO QUE DA RESOLUCION ARRIBA. Sin el, seis Estados empataban en 0,0: el
    # indice sabia decir «cumple los otros cinco» y no sabia distinguir entre los
    # que cumplen. Este solo existe donde hay portal —nueve Estados—, que es
    # justamente donde hacia falta separar, y en los demas NO PUNTUA.
    {"clave": "publica_lo_que_importa", "rotulo": "Publica lo que importa",
     "pregunta": "De las seis materias del registro, ¿cuántas tienen conjuntos en su portal?",
     "colector": "oficiales"},
]

# Uruguay abre su portal, tiene el sitio en pie, publica compras, declara armas,
# informa especies y publica las seis materias: tiene que puntuar bajo. Si sale alto, el que fallo es el
# calculo, no el Estado.
CONTROL = "URY"
TOPE_CONTROL = 35


def _leer(nombre: str) -> dict:
    ruta = comun.DATOS / "publico" / f"{nombre}.json"
    if not ruta.exists():
        return {}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — un archivo ilegible es un acto sin evidencia
        return {}


def _porIso(d: dict) -> dict:
    return {r["iso"]: r for r in d.get("registros", []) if isinstance(r, dict) and r.get("iso")}


def _puertaDatos(r: dict):
    """abre 0 · cierra 60 · sin puerta 100.

    «Cierra» vale 60 y no 100 a propósito: el portal EXISTE y responde a una
    persona. Publica; lo que no hace es dejarse recolectar. Es peor que abrir y
    mejor que no tener puerta, y la cifra tiene que decir eso.
    """
    e = r.get("estado")
    return {"abre": 0, "cierra": 60, "sin_puerta_hallada": 100}.get(e)


def _sitioEnPie(r: dict):
    """vivo 0 · no responde hoy 60 · retirado 100. Si falló el archivo, NO puntúa."""
    sitios = r.get("sitios") or []
    if not sitios:
        return None
    estados = [s.get("estado") for s in sitios]
    # El archivo publico es un tercero: si NO respondio, el que fallo es el
    # archivo y no el Estado. Ese acto se descarta, no se cuenta en contra.
    utiles = [e for e in estados if e != "archivo_no_respondio"]
    if not utiles:
        return None
    if "vivo" in utiles:
        return 0
    if "no_responde_hoy" in utiles:
        return 60
    if "retirado" in utiles:
        return 100
    return None


def _comprasComparables(r: dict):
    """Con publicador 0 · sin publicador 100."""
    n = r.get("publicadores")
    if n is None:
        return None
    return 0 if n > 0 else 100


def _declaraArmas(r: dict):
    """Declarado 0 · sin declarar 100."""
    e = r.get("estado")
    if e == "declarado":
        return 0
    if e == "sin_declarar":
        return 100
    return None


def _informaEspecies(r: dict, ultimoCompleto: int):
    """Al día 0 · un año atrás 50 · más atrás 100."""
    a = r.get("ultimo_anio_con_asiento")
    if not a or not ultimoCompleto:
        return None
    atraso = ultimoCompleto - a
    if atraso <= 0:
        return 0
    return 50 if atraso == 1 else 100


def _publicaLoQueImporta(r: dict):
    """De las seis materias, cuántas tienen conjuntos. Seis de seis 0 · ninguna 100.

    Solo puntúa donde hay portal. En los Estados sin portal NO se anota 100: la
    ausencia de portal ya la mide el primer acto, y contarla dos veces seria
    castigar el mismo hecho dos veces.
    """
    materias = r.get("materias")
    if not materias:
        return None
    con = sum(1 for m in materias if (m.get("cantidad") or 0) > 0)
    return round(100 - (con * 100 / len(materias)), 1)


def recolectar():
    fuentes = {a["colector"]: _leer(a["colector"]) for a in ACTOS}
    faltan = [c for c, d in fuentes.items() if not d]
    if faltan:
        raise RuntimeError(
            f"Faltan los archivos de {', '.join(faltan)}. El índice se DERIVA de otros "
            "colectores y no puede calcularse sin ellos: se detiene en lugar de publicar "
            "un puntaje armado con la mitad de los actos.")

    porColector = {c: _porIso(d) for c, d in fuentes.items()}
    ultimoCites = (fuentes["cites"].get("resumen") or {}).get("ventana_hasta")

    calculo = {
        "puerta_datos": lambda i: _puertaDatos(porColector["explorador"].get(i, {})),
        "sitio_en_pie": lambda i: _sitioEnPie(porColector["archivo"].get(i, {})),
        "compras_comparables": lambda i: _comprasComparables(porColector["contratacion"].get(i, {})),
        "declara_armas": lambda i: _declaraArmas(porColector["armas"].get(i, {})),
        "informa_especies": lambda i: _informaEspecies(porColector["cites"].get(i, {}), ultimoCites),
        "publica_lo_que_importa": lambda i: _publicaLoQueImporta(porColector["oficiales"].get(i, {})),
    }

    registros, medidos = [], 0
    for pais in geo.padron():
        iso = pais["iso"]
        detalle, valores = [], []
        for acto in ACTOS:
            v = calculo[acto["clave"]](iso)
            detalle.append({"clave": acto["clave"], "rotulo": acto["rotulo"],
                            "puntaje": v, "medido": v is not None})
            if v is not None:
                valores.append(v)
        if len(valores) < MINIMO_ACTOS:
            registros.append({
                "iso": iso, "pais": pais["pais"], "bloque": pais["bloque"],
                "estado": "sin_medir", "actos_medidos": len(valores),
                "porque": (f"Sólo {len(valores)} de {len(ACTOS)} actos tienen evidencia, y "
                           f"hacen falta {MINIMO_ACTOS}. NO significa que sea opaco: "
                           "significa que no se lo pudo medir."),
                "actos": detalle,
            })
            continue
        medidos += 1
        registros.append({
            "iso": iso, "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": "medido",
            "opacidad": round(sum(valores) / len(valores), 1),
            "actos_medidos": len(valores),
            "actos": detalle,
        })

    # SE PRUEBA EL CALCULO ANTES DE CREERLE UN PUNTAJE A NADIE.
    control = next((r for r in registros if r["iso"] == CONTROL), {})
    if control.get("estado") != "medido" or control.get("opacidad", 100) > TOPE_CONTROL:
        raise RuntimeError(
            f"La prueba del cálculo falló: {CONTROL} —que abre su portal, tiene el sitio "
            f"en pie, publica compras, declara armas e informa especies— dio "
            f"{control.get('opacidad', 'sin medir')} y debería estar por debajo de "
            f"{TOPE_CONTROL}. Alguna señal se está leyendo al revés. NO se publica un "
            "orden que no se puede sostener.")

    conPuntaje = [r for r in registros if r["estado"] == "medido"]
    orden = sorted(conPuntaje, key=lambda r: -r["opacidad"])
    for puesto, r in enumerate(orden, 1):
        r["puesto"] = puesto
        r["de"] = len(orden)

    vacios = [
        "Cero es el más transparente y cien el más opaco. La dirección importa: este "
        "índice mide la ausencia, no la presencia. Un puntaje de apertura no se puede "
        "refutar mostrando una dirección; una afirmación de ausencia si, y eso es lo que "
        "la vuelve seria.",
        "No se copia la fórmula de transparencia internacional, y no por descuido. Su "
        "índice de percepción de corrupción es un promedio de encuestas a expertos: mide "
        "lo que un panel cree sobre un país. Este mide actos observables que cualquiera "
        "comprueba repitiendo la consulta. Contestan preguntas distintas y no deben "
        "compararse: ordenarian distinto con toda razón.",
        f"NO SE CASTIGA LO QUE NO SE MIRO. Si a un Estado le falta la evidencia de un "
        f"acto, ese acto NO PUNTUA: no suma ni resta, y el indice se calcula sobre los "
        f"que si tienen evidencia. Con menos de {MINIMO_ACTOS} actos medidos el Estado "
        "queda sin medir, que no es lo mismo que opaco.",
        "Cuando el archivo público de la web no responde, el que fallo es el archivo y no "
        "el Estado. Ese acto se descarta en lugar de contarse en contra. Es la clase de "
        "confusión que convierte una falla propia en una acusación ajena.",
        "Los seis actos pesan lo mismo, y es una elección. Podría argumentarse que la "
        "puerta a los datos vale más que el informe de especies —y sería razonable—, pero "
        "cualquier reparto de pesos es un juicio, y un juicio metido adentro de una "
        "fórmula deja de verse. Pesos iguales es la única elección que no esconde una "
        "preferencia.",
        "«cierra» vale 60 Y no 100 A propósito. El portal existe y responde a una persona: "
        "Publica, y lo que no hace es dejarse recolectar. Es peor que abrir y mejor que no "
        "tener puerta, y la cifra tiene que decir eso.",
        "El sexto acto solo puntua donde hay portal, y es a propósito. Sin el, seis "
        "Estados empataban en cero: el índice sabia decir «cumple todo» y no sabia "
        "distinguir entre los que cumplen. En los Estados sin portal no se anota cien: la "
        "ausencia de portal ya la mide el primer acto, y contarla dos veces sería castigar "
        "el mismo hecho dos veces.",
        "Es un índice derivado, no una medición nueva. Los seis actos los midieron otros "
        "colectores de esta misma casa, cada uno con su fecha y su rastro. Si uno de ellos "
        "falla, este índice no se publica en lugar de calcularse con la mitad.",
        f"ANTES DE CREERLE UN PUNTAJE A NADIE SE PRUEBA EL CALCULO contra {CONTROL}, que "
        f"cumple los actos medibles: si diera mas de {TOPE_CONTROL}, alguna senial se estaria "
        "leyendo al revés y la corrida se detiene entera.",
        "No mide corrupción ni calidad de gobierno. Mide si el Estado deja ver lo que "
        "hace. Un Estado puede ser transparente y estar mal gobernado, y al revés.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=1,
        corroborado=True,
        nota=("Indice propio de la Oficina, derivado de cinco mediciones de esta misma "
              "casa. Fiabilidad a porque el productor es la Fundación y el método esta "
              "escrito entero. Credibilidad 1 porque cada acto es un hecho verificable "
              "por repetición —cualquiera pega la dirección y obtiene lo mismo—: la "
              "corroboracion es la reproducibilidad, y la formula esta publicada."),
    )

    return comun.escribir(
        colector="indice_opacidad",
        capa="publico",
        fuente="Fundación Sherman Kent — Índice de Opacidad, edición uno",
        url_fuente=comun.SITIO_URL + "#opacidad-seccion",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "edicion": 1,
                "escala": "0 el más transparente · 100 el más opaco",
                "estados_medidos": medidos,
                "estados_sin_medir": len(registros) - medidos,
                "estados_del_padron": len(registros),
                "actos_del_indice": len(ACTOS),
                "minimo_de_actos": MINIMO_ACTOS,
                "pesos": "iguales, por elección declarada",
                "calculo_probado": True,
                "consultado": comun.ahora(),
            },
            "formula": {
                "definicion": ("Promedio simple de los actos con evidencia. Cada acto vale "
                               "0 si el Estado lo cumplió y 100 si no; los valores "
                               "intermedios se justifican uno a uno."),
                "actos": [{**a, "escala": {
                    "puerta_datos": "abre 0 · cierra 60 · sin puerta 100",
                    "sitio_en_pie": "vivo 0 · no responde hoy 60 · retirado 100",
                    "compras_comparables": "con publicador 0 · sin publicador 100",
                    "declara_armas": "declarado 0 · sin declarar 100",
                    "informa_especies": "al día 0 · un año atrás 50 · más atrás 100",
                    "publica_lo_que_importa": "seis materias de seis 0 · ninguna 100 · proporcional",
                }[a["clave"]]} for a in ACTOS],
            },
        },
    )


if __name__ == "__main__":
    comun.correr("indice_opacidad", recolectar)
