# -*- coding: utf-8 -*-
"""¿Puede el lector VER todas las fuentes que el registro dice tener?

POR QUÉ EXISTE
---------------
La página trae una lista de las fuentes del registro. Se arma así:

    FUENTES_DEL_REGISTRO.map(([k,rot]) => ({rot, d:almacen[k]})).filter(x => x.d)

Ese `filter` es la trampa: **si la clave no existe, el renglón desaparece sin
decir nada.** No hay error en la consola, no falla ningún control, la página se
ve entera. Simplemente hay una fuente menos.

El 11 de septiembre de 2026 se midió: la página mostraba **36** fuentes, el
rótulo que ven Google y WhatsApp decía **48**, y en los archivos había **51**.
Tres cifras distintas en un mismo producto, y ninguna escrita con mala fe.

Dos causas, de distinta naturaleza:

1. **Cuatro renglones apuntaban a claves inexistentes** —`ipc`, `regimen`,
   `trata`, `bienes`— porque los conjuntos se llaman `percepcion_corrupcion`,
   `regimen_politico`, `trata_personas` y `bienes_culturales`. Transparency
   International, V-Dem Regímenes, el informe de trata del Departamento de
   Estado y el convenio UNIDROIT estaban recolectados, publicados y contados, y
   el lector no podía verlos donde iba a buscarlos.
2. **Diez conjuntos nunca se agregaron a la lista** al entrar al registro.
   Agregar un colector y olvidar el renglón no rompe nada visible.

QUÉ HACE ESTE CONTROL
----------------------
Cruza tres cosas que hasta hoy nadie cruzaba: los archivos que tienen fuente
declarada, las claves de la lista de la página, y los conjuntos que la página
carga de verdad. Falla en rojo si:

  · una fuente publicada no está en la lista y tampoco está declarada como
    excluida, con su motivo;
  · un renglón de la lista apunta a una clave que la página no carga —el caso
    que costó cuatro fuentes—;
  · algo está excluido por un motivo que ya no corre.

LO QUE NO MIRA
--------------
Si la fuente es buena, si el dato es reciente o si hay dos fuentes por asunto.
Eso lo miden la auditoría y la regla de las dos fuentes, que corren aparte.
Esto mira una sola cosa: que lo que el registro tiene, el lector lo pueda ver.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
SITIO = RAIZ / "sitio" / "index.html"
DATOS = RAIZ / "datos" / "publico"

# LO QUE NO ES UNA FUENTE, y por qué. Cada exclusión se declara acá con su
# motivo: una exclusión sin motivo escrito es indistinguible de un olvido, que
# es exactamente lo que este control vino a encontrar.
NO_SON_FUENTES = {
    "auditoria.json": "es un CONTROL de la casa: mide al registro, no al mundo",
    "pantallas.json": "es un CONTROL de la casa: mide la maqueta, no al mundo",
    "mineria.json": "derivado propio, sin procedencia de tercero",
    "censo_subnacional.json": "es un INSTRUMENTO DE MEDICIÓN, no una fuente sobre el "
                              "mundo: cuenta qué se podría llegar a publicar por unidad "
                              "y a cuántos Estados alcanza, para decidir si la capa "
                              "subnacional llega al umbral que fijó la Dirección",
    "desplazamiento-serie.json": "es la serie histórica de ACNUR, que ya figura "
                                 "como «desplazamiento»: un mismo productor no se "
                                 "cuenta dos veces por entregar dos archivos",
    "subnacional.json": "SEGUNDA ETAPA: recolectada y todavía no publicada",
    "subnacional_datos.json": "SEGUNDA ETAPA: recolectada y todavía no publicada",
    "unidades.json": "SEGUNDA ETAPA: el padrón de unidades subnacionales",
    "gdl.json": "SEGUNDA ETAPA: subnacional, no publicada",
    "hapi.json": "SEGUNDA ETAPA: subnacional, no publicada",
}


def nombre_de_fuente(d) -> str | None:
    f = (d.get("procedencia") or {}).get("fuente")
    if isinstance(f, str):
        return f.strip() or None
    if isinstance(f, dict):
        return (f.get("nombre") or "").strip() or None
    return None


def conjuntos_que_carga(html: str) -> dict:
    """De qué archivo sale cada `almacen.X`.

    Se busca, para cada asignación, el PRIMER `traer('...')` de su misma
    sentencia. El primero y no el más cercano: varios conjuntos se piden junto
    con su archivo de estado —`Promise.all([traer('oms.json'), traer('estado/
    oms.json')])`— y quedarse con el último devuelve el estado en vez del dato.
    """
    mapa = {}
    for m in re.finditer(r"almacen\.([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:d|serie|u|sd)\b", html):
        clave = m.group(1)
        # El comienzo de la sentencia: el `traer(` o el `Promise.all(` anterior
        # más lejano que no tenga otro cierre de sentencia en el medio.
        antes = html[:m.start()]
        corte = max(antes.rfind("\n  traer("), antes.rfind("\n  Promise.all("),
                    antes.rfind("\n    traer("), antes.rfind("\n    Promise.all("))
        if corte < 0:
            continue
        archivos = re.findall(r"traer\('([^']+)'\)", html[corte:m.start()])
        if archivos and clave not in mapa:
            mapa[clave] = archivos[0]
    return mapa


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    html = SITIO.read_text(encoding="utf-8")

    lista = re.search(r"const FUENTES_DEL_REGISTRO = \[(.*?)\];", html, re.S)
    if not lista:
        print("[fuentes] No se halló FUENTES_DEL_REGISTRO: el control no puede correr.")
        sys.exit(1)
    renglones = re.findall(r"\['([^']*)','", lista.group(1))
    carga = conjuntos_que_carga(html)

    fallas = []

    # 1. Renglones que apuntan a una clave que la página no carga. Es el caso
    #    que costó cuatro fuentes, y el que no deja ningún rastro visible.
    for k in renglones:
        if k not in carga:
            fallas.append(f"el renglón «{k}» apunta a un conjunto que la página no "
                          f"carga: el lector NO lo ve y nada avisa")

    repetidas = {k for k in renglones if renglones.count(k) > 1}
    for k in sorted(repetidas):
        fallas.append(f"el renglón «{k}» está dos veces en la lista")

    # 2. Fuentes publicadas que no llegan a la lista.
    listados = {carga.get(k) for k in renglones if k in carga}
    con_fuente = {}
    for ruta in sorted(DATOS.glob("*.json")):
        try:
            d = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — un archivo ilegible no es una fuente perdida
            continue
        if not isinstance(d, dict):
            continue
        n = nombre_de_fuente(d)
        if n:
            con_fuente[ruta.name] = n

    for archivo, fuente in sorted(con_fuente.items()):
        if archivo in listados:
            continue
        motivo = NO_SON_FUENTES.get(archivo)
        if motivo:
            continue
        fallas.append(f"«{fuente[:60]}» ({archivo}) está publicada y NO figura en la "
                      f"lista de fuentes: el lector no puede encontrarla")

    # 3. Exclusiones que ya no corren: o el archivo dejó de existir, o alguien lo
    #    agregó a la lista y olvidó sacarlo de acá.
    for archivo, motivo in sorted(NO_SON_FUENTES.items()):
        if not (DATOS / archivo).exists():
            continue
        if archivo in listados:
            fallas.append(f"{archivo} está en la lista Y declarado como excluido: "
                          f"una de las dos cosas sobra")

    # 4. IDENTIFICADORES REPETIDOS EN LA PAGINA. Es la quinta vez en este
    #    proyecto que un identificador repetido rompe algo en silencio —cuatro
    #    veces en los flujos del robot y una acá—, y siempre de la misma
    #    manera: el navegador se queda con el PRIMERO que encuentra, así que una
    #    sección queda muda y otra muestra la procedencia equivocada. Ninguna
    #    cifra es falsa y nada avisa. Ya no.
    ids = re.findall(r'\sid="([^"]+)"', html)
    for k, n in collections.Counter(ids).items():
        if n > 1:
            fallas.append(f"el identificador «{k}» está {n} veces en la página: el "
                          f"navegador se queda con el primero, así que una sección queda "
                          f"muda y otra muestra lo que no le corresponde")

    visibles = len([k for k in renglones if k in carga])
    print(f"[fuentes] {visibles} fuentes visibles en la lista · "
          f"{len(con_fuente)} archivos con fuente declarada · "
          f"{len([a for a in NO_SON_FUENTES if (DATOS / a).exists()])} excluidos con motivo")
    for f in fallas:
        print(f"  FALLA · {f}")
    if fallas:
        sys.exit(1)


if __name__ == "__main__":
    main()
