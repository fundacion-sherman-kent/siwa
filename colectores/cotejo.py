# -*- coding: utf-8 -*-
"""Cotejar el nombre de una unidad de una fuente con el padrón de este registro.

Vive aparte porque lo usan varios colectores, y porque dos copias de esta lógica
que se separaran una de otra publicarían dos mapas distintos del mismo país.

LO QUE RESUELVE, QUE NO ES OBVIO
---------------------------------
Las fuentes internacionales no siempre miden por unidad de primer orden. Unas
usan las provincias; otras, regiones de encuesta que agrupan varias —«Cuyo»,
«NOA»— y otras nombran el grupo enumerando sus miembros: «Región I (Peravia,
San Cristóbal, San José de Ocoa, Azua)». Y encima los nombres vienen mal
escritos de los dos lados: la fuente pone «Arbucania» por Araucanía, y el
padrón heredó de la CEPAL nombres rotos —«Camag» por Camagüey, «CA8AR» por
Cañar—.

`cubre()` separa las tres situaciones y **nunca toma por una unidad a un
renglón que enumera varios lugares**, que es el error que arruinaría el mapa
sin que se note: pintar un departamento con el promedio de cinco.
"""
from __future__ import annotations

import re
import unicodedata


# Palabras que sobran al comparar nombres: «Provincia de Santa Fe» y «Santa Fe»
# son la misma unidad escrita distinto. NO se sacan «región», «distrito» ni
# «territorio»: en Venezuela, «Región Capital» y «Distrito Capital» son cosas
# distintas —la primera incluye Miranda y Vargas— y borrar esa palabra las
# haría pasar por la misma. La regla es sacar lo que sobra, nunca lo que separa.
SOBRAN = re.compile(
    r"\b(provincias?|departamentos?|departments?|departements?|comarcas?|estados?|"
    r"prov|dept|de|del|la|el|los|las|des|du|le|les|and|y|e|incl|former)\b")

# Por dónde se parte un nombre que en realidad nombra varias unidades:
# «Corozal, Orange Walk» son dos, y «Región I (Peravia, San Cristóbal…)» las lista.
CORTES = re.compile(r"[,()]|\s+and\s+", re.IGNORECASE)


def sello(t) -> str:
    t = unicodedata.normalize("NFKD", str(t or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"\bst\b", "saint", t)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", SOBRAN.sub(" ", t))).strip()


def _una(clave: str, propio: dict) -> str | None:
    """La unidad del padrón que le corresponde a este pedazo de nombre, si hay una sola.

    Primero prueba la igualdad. Si no la hay, admite dos parecidos, y SOLO SI EL
    RESULTADO ES ÚNICO —si dos unidades del país responden al mismo pedazo, no se
    elige ninguna—:

      · que el nombre del padrón esté **cortado a mitad de palabra** dentro del de
        la fuente. Esto existe porque **la CEPAL entrega nombres rotos** —«Camag»
        por Camagüey, «Guant» por Guantánamo, «CA8AR» por Cañar— y el padrón los
        heredó. El corte tiene que caer a mitad de palabra: si cayera en un
        espacio, «Durazno and Tacuarembo» pasaría por Durazno a secas, que es
        precisamente el error que este colector vino a evitar.
      · que el nombre de la fuente sea el comienzo o esté contenido en el del
        padrón: «Valle» por Valle del Cauca, «San Andrés» por el archipiélago.
    """
    if not clave or len(clave) < 5:
        return propio.get(clave) if clave else None
    if clave in propio:
        return propio[clave]
    cerca = []
    for k, v in propio.items():
        if len(k) < 5:
            continue
        # el padrón cortado a mitad de palabra dentro del nombre de la fuente
        corta = clave.startswith(k) and not clave[len(k):].startswith(" ")
        # el nombre de la fuente, más corto, dentro del del padrón
        dentro = k.startswith(clave) or f" {clave} " in f" {k} "
        if corta or dentro:
            cerca.append(v)
    if len(set(cerca)) == 1:
        return cerca[0]
    if cerca:
        return None
    # Última tolerancia: UNA letra de diferencia, y una sola, con resultado único.
    # La fuente trae erratas propias —«Bahoruco» por Baoruco, «Canideyu» por
    # Canindeyú, «Conception» por Concepción— y descartar esas unidades declararía
    # un vacío que no existe. Dos letras ya no se admiten: a esa distancia empiezan
    # a confundirse nombres que son de veras distintos.
    a_una = [v for k, v in propio.items() if len(k) >= 5 and _a_una_letra(clave, k)]
    return a_una[0] if len(set(a_una)) == 1 else None


def _a_una_letra(a: str, b: str) -> bool:
    """Si de «a» a «b» hay a lo sumo una letra cambiada, agregada o sacada."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    if i == len(a):
        return True
    if len(a) == len(b):
        return a[i + 1:] == b[i + 1:]
    return a[i:] == b[i + 1:]


# El encabezado «Región de …» con que algunos Estados nombran sus unidades.
ENCABEZADO = re.compile(r"^\s*regi[oó]n(\s+de\s+la|\s+de|\s+del)?\s+", re.IGNORECASE)

# Un nombre que enumera lugares: «Corozal, Orange Walk», «Arica and Parinacota».
ENUMERA = re.compile(r",|\sand\s", re.IGNORECASE)


def _resolver(texto: str, propio: dict) -> tuple:
    """Unidades del padrón nombradas en este texto, y cuántos nombres enumera."""
    if not (texto or "").strip():
        return [], 0
    partes = [p for p in CORTES.split(texto) if sello(p)]
    entero = _una(sello(texto), propio)
    if entero and len(partes) <= 1:
        return [entero], 1
    hallados = [u for u in (_una(sello(p), propio) for p in partes) if u]
    if not hallados and entero:
        return [entero], max(len(partes), 1)
    return hallados, max(len(partes), 1)


def cubre(nombre: str, propio: dict) -> tuple:
    """Qué unidades del padrón cubre este renglón, de qué clase es y si está entero.

    Tres clases, y la diferencia entre ellas decide qué se puede pintar:

      · **unidad** — el renglón nombra una sola unidad de primer orden. Se pinta.
      · **agrupamiento** — el renglón mide varias unidades juntas y las nombra:
        «Región I (Peravia, San Cristóbal, San José de Ocoa, Azua)». Se pinta a
        todas con el mismo valor, que es el del grupo y no el de cada una, **y
        solo si se identificaron todas las que enumera**: si el renglón lista
        cinco y este registro reconoce dos, no se sabe sobre qué territorio se
        calculó el número y no se pinta nada.
      · **región propia** — «Cuyo», «NOA», «Sierra». No corresponde a ninguna
        unidad; se publica con su nombre y no se pinta.

    LA REGLA QUE EVITA EL ERROR GRAVE: un renglón que enumera más de un lugar
    **nunca** se toma por una unidad, aunque solo se haya podido identificar una.
    Sin esto, «Centro (Durazno and Tacuarembó)» pintaría a Durazno con el promedio
    de dos departamentos, y «Central (Huancavelica, Huánuco, Junín, Pasco)»
    pintaría a Huancavelica con el de cuatro.
    """
    if not nombre:
        return [], "region_propia", 0, False
    # Un nombre que coincide entero con una unidad del padrón es esa unidad, aunque
    # lleve un «and» adentro: «Magallanes and La Antartica Chilena» es una sola.
    igual = propio.get(sello(nombre))
    if igual:
        return [igual], "unidad", 1, True

    # «Región de Antofagasta» es Antofagasta: en Chile el nombre oficial de la
    # unidad empieza así. Pero el encabezado se saca SOLO si lo que queda es
    # exactamente una unidad del padrón, nunca por parecido. La razón es
    # Venezuela: «Región Capital» no es el Distrito Capital —incluye a Miranda y
    # a Vargas— y aflojar acá la haría pasar por él.
    sin_encabezado = ENCABEZADO.sub("", nombre, count=1)
    if sin_encabezado != nombre:
        igual = propio.get(sello(sin_encabezado))
        if igual:
            return [igual], "unidad", 1, True

    base, entre = nombre, ""
    if "(" in nombre:
        base = nombre[:nombre.index("(")]
        entre = nombre[nombre.index("(") + 1:].rstrip(")")

    u_base, n_base = _resolver(base, propio)
    u_par, n_par = _resolver(entre, propio)
    vistos, cubiertas = set(), []
    for u in u_base + u_par:
        if u not in vistos:
            vistos.add(u)
            cubiertas.append(u)

    enumera = (max(n_base, n_par)
               if (ENUMERA.search(base) or ENUMERA.search(entre)) else 1)
    if not cubiertas:
        clase = "region_propia"
    elif len(cubiertas) == 1 and enumera == 1:
        clase = "unidad"
    else:
        clase = "agrupamiento"
    return cubiertas, clase, enumera, len(cubiertas) >= enumera
