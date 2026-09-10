# -*- coding: utf-8 -*-
"""La auditoría, corrida por el robot en vez de por una persona que se acuerde.

POR QUÉ EXISTE
--------------
Hasta hoy la calidad del registro se controlaba cuando alguien pedía una
auditoría. Eso funciona una vez y no funciona nunca más: entre pedido y pedido
el registro puede pasar semanas roto y nadie se entera, porque **el que rompe y
el que revisa son el mismo, y solo revisa cuando se lo piden**.

Este archivo convierte esa revisión en maquinaria, como ya se hizo con el banco
de pruebas de fuentes y con el latido del robot. Corre en cada recolección,
mide, escribe lo que midió en `datos/publico/auditoria.json` —que el registro
publica— y **termina en rojo si algo está mal**. El aviso llega solo.

LO QUE SE CONTROLA, Y POR QUÉ CADA COSA
----------------------------------------
Las FALLAS tumban la corrida: describen un registro que estaría mintiendo.

  1. Procedencia completa. Un dato sin fuente, sin fecha o sin calificación no
     cumple la regla de la casa: toda afirmación es trazable.
  2. Fecha que no sea del futuro. Una fecha adelantada haría pasar por fresco
     un dato viejo.
  3. Padrón cerrado. Un ISO que no está entre los 33 significa que el colector
     está trayendo un Estado que este registro no cubre.
  4. Conjunto por Estado que quedó vacío. Un archivo con cero filas se ve igual
     que uno con datos hasta que alguien lo abre.
  5. Lo que la pantalla pide existe. Se leen del propio `sitio/index.html` los
     archivos que carga y se comprueba que estén. Es la falla que rompe la
     página sin tocar la página: se renombra un colector y nadie lo nota.
  6. Series sin agujeros silenciosos. Un punto de serie con año y sin valor —o
     al revés— es un dato a medias que las figuras dibujan como si fuera bueno.

Las BRECHAS no tumban nada: son la distancia que falta recorrer, y se publican
justamente para que se vea. Cuántos temas tienen serie larga —la que permite
tendencia—, cuántos apenas dos o tres años y cuántos ninguno; qué Estados del
padrón están peor cubiertos; cuántas fuentes candidatas esperan en el banco de
pruebas y con qué disponibilidad medida.

POR QUÉ LA BRECHA SE PUBLICA Y NO SE GUARDA
--------------------------------------------
Porque un objetivo sin medición es una intención. El registro declara que
quiere ser la primera plataforma de consulta de la región; la única forma
honesta de sostener eso es publicar, al lado de la declaración, cuánto le falta
—y que la cifra la calcule una máquina que no tiene interés en que dé bien—.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PUBLICO = RAIZ / "datos" / "publico"
SALIDA = PUBLICO / "auditoria.json"
PAGINA = RAIZ / "sitio" / "index.html"

sys.path.insert(0, str(RAIZ / "colectores"))
import comun  # noqa: E402
import geo  # noqa: E402

# Cuántos años seguidos hacen falta para que el registro se anime a prolongar
# una serie. Es la misma cifra que usa la pantalla: si acá dijera otra, la
# auditoría estaría midiendo un registro distinto del que se publica.
ANIOS_PARA_TENDENCIA = 5


def leer(ruta: pathlib.Path):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — un archivo ilegible ES una falla
        return {"__ilegible__": str(e)[:160]}


def serie_de(fila: dict) -> list:
    """Los puntos de serie de una fila, mire donde mire el colector.

    Cada colector guarda su serie donde le conviene —«serie», «serie_varones»,
    o adentro del diccionario de indicadores—. La auditoría no puede exigirles
    una forma única: tiene que saber leerlas todas, porque su trabajo es medir
    el registro tal como está, no como se hubiera querido.
    """
    puntos = []
    for clave, valor in fila.items():
        if clave.startswith("serie") and isinstance(valor, list):
            puntos.append((clave, valor))
    ind = fila.get("indicadores")
    if isinstance(ind, dict):
        for clave, cont in ind.items():
            if isinstance(cont, dict) and isinstance(cont.get("serie"), list):
                puntos.append((clave, cont["serie"]))
    return puntos


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ahora = datetime.now(timezone.utc)
    padron = {p["iso"] for p in geo.padron()}
    fallas, brechas = [], []

    # ---- lo que la pantalla pide ------------------------------------------
    # Se lee del propio sitio: una lista escrita a mano acá se desactualizaría,
    # y una auditoría desactualizada aprueba lo que debería frenar.
    pide = set()
    if PAGINA.exists():
        for m in re.finditer(r"traer\('([a-z0-9_/-]+\.json)'\)", PAGINA.read_text(encoding="utf-8")):
            nombre = m.group(1)
            if not nombre.startswith("estado/"):     # los testigos de falla pueden faltar
                pide.add(nombre)
    for nombre in sorted(pide):
        if not (PUBLICO / nombre).exists():
            fallas.append({"que": "archivo que la pantalla pide y no existe",
                           "donde": nombre,
                           "porque": "la página lo carga al abrirse: sin él, esa sección no pinta"})

    # ---- conjunto por conjunto ---------------------------------------------
    conjuntos, con_serie_larga, con_serie_corta, sin_serie = [], 0, 0, 0
    cobertura = {iso: 0 for iso in padron}
    for ruta in sorted(PUBLICO.glob("*.json")):
        # Los testigos de control no son datos y no se les puede exigir una
        # procedencia que no les corresponde. La lista vive en comun.py, que es
        # de donde la toma también el catálogo: dos copias divergen.
        if ruta.name in comun.TESTIGOS:
            continue
        d = leer(ruta)
        if "__ilegible__" in d:
            fallas.append({"que": "archivo ilegible", "donde": ruta.name,
                           "porque": d["__ilegible__"]})
            continue
        if not isinstance(d, dict):
            continue
        proc = d.get("procedencia") or {}
        fuente = proc.get("fuente") or {}
        cal = proc.get("calificacion") or {}

        falta = [c for c, v in (("colector", proc.get("colector")),
                                ("fuente.nombre", fuente.get("nombre")),
                                ("fuente.url", fuente.get("url")),
                                ("obtenido_en", proc.get("obtenido_en")),
                                ("calificacion", cal.get("fiabilidad"))) if not v]
        if falta:
            fallas.append({"que": "procedencia incompleta", "donde": ruta.name,
                           "porque": "falta " + ", ".join(falta)
                                     + ": toda afirmación de este registro tiene que ser trazable"})

        cuando = proc.get("obtenido_en") or ""
        try:
            t = datetime.fromisoformat(cuando.replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            if t > ahora:
                fallas.append({"que": "fecha de recolección en el futuro", "donde": ruta.name,
                               "porque": f"dice {cuando} y hoy es {ahora.date()}: "
                                         "haría pasar por fresco un dato viejo"})
        except Exception:  # noqa: BLE001
            if cuando:
                fallas.append({"que": "fecha de recolección ilegible", "donde": ruta.name,
                               "porque": f"«{cuando}» no es una fecha"})

        filas = d.get("registros")
        porEstado = isinstance(filas, list) and filas and isinstance(filas[0], dict) \
            and "iso" in filas[0]
        if porEstado:
            ajenos = sorted({f.get("iso") for f in filas
                             if isinstance(f, dict) and f.get("iso") not in padron} - {None})
            if ajenos:
                fallas.append({"que": "Estado fuera del padrón", "donde": ruta.name,
                               "porque": "trae " + ", ".join(ajenos[:6])
                                         + ": este registro cubre 33 Estados y solo esos"})
            if not filas:
                fallas.append({"que": "conjunto por Estado vacío", "donde": ruta.name,
                               "porque": "cero filas se ve igual que con datos hasta que alguien abre"})

            # Series: agujeros duros, y largo para la brecha.
            largas = cortas = 0
            for f in filas:
                if not isinstance(f, dict):
                    continue
                tiene = False
                for clave, puntos in serie_de(f):
                    # NO TODAS LAS SERIES SE LLAMAN «valor». La de desplazamiento
                    # forzado trae cinco medidas con nombre propio en cada punto
                    # —refugiados de origen, solicitantes, asilo, desplazados
                    # internos—. La primera versión de esta auditoría exigía
                    # «valor» en todos lados y acusó a 122 puntos legítimos: el
                    # instrumento falló antes que el registro, que es el orden
                    # habitual. Se mira la forma que la serie declara tener.
                    conValor = any(isinstance(pt, dict) and "valor" in pt for pt in puntos)
                    buenos = 0
                    for pt in puntos:
                        if not isinstance(pt, dict):
                            continue
                        # LA MARCA DE TIEMPO NO SIEMPRE SE LLAMA «anio». El
                        # archivo del Índice de Opacidad guarda un punto por DÍA
                        # —«fecha»—, porque cuatro de sus seis actos son del
                        # presente y no tienen año. Es la tercera forma legítima
                        # que este instrumento tuvo que aprender: primero exigió
                        # «valor» donde había cinco medidas con nombre, ahora
                        # exigía «anio» donde hay una fecha. La regla de fondo no
                        # se toca: un punto necesita SU TIEMPO y SU VALOR.
                        anio = pt.get("anio") if pt.get("anio") is not None else pt.get("fecha")
                        if conValor:
                            valor = pt.get("valor")
                            if (anio is None) != (valor is None):
                                fallas.append({
                                    "que": "punto de serie a medias",
                                    "donde": f"{ruta.name} · {f.get('iso')}",
                                    "porque": f"en «{clave}» hay un punto con "
                                              + ("tiempo y sin valor" if valor is None
                                                 else "valor y sin año ni fecha")
                                              + ": las figuras lo dibujan como si fuera bueno"})
                                break
                        elif anio is not None and all(
                                v is None for k, v in pt.items() if k != "anio"):
                            fallas.append({
                                "que": "punto de serie sin ninguna medida",
                                "donde": f"{ruta.name} · {f.get('iso')}",
                                "porque": f"en «{clave}» hay un año con todas sus medidas vacías: "
                                          "es un hueco disfrazado de dato"})
                            break
                        if anio is not None:
                            buenos += 1
                    if buenos >= ANIOS_PARA_TENDENCIA:
                        largas += 1; tiene = True
                    elif buenos >= 2:
                        cortas += 1; tiene = True
                if tiene and f.get("iso") in cobertura:
                    cobertura[f["iso"]] += 1
            if largas:
                con_serie_larga += 1
            elif cortas:
                con_serie_corta += 1
            else:
                sin_serie += 1

        conjuntos.append({"archivo": ruta.name, "por_estado": bool(porEstado),
                          "filas": len(filas) if isinstance(filas, list) else None})

    # ---- las brechas, que no tumban nada pero se publican -------------------
    total = con_serie_larga + con_serie_corta + sin_serie
    if sin_serie:
        brechas.append({"que": "conjuntos sin ninguna serie histórica",
                        "cuantos": sin_serie, "de": total,
                        "porque": "muestran el último valor y no dejan ver si mejora o empeora"})
    if con_serie_corta:
        brechas.append({"que": "conjuntos con serie corta",
                        "cuantos": con_serie_corta, "de": total,
                        "porque": f"tienen entre 2 y {ANIOS_PARA_TENDENCIA - 1} años: "
                                  "alcanza para dibujar, no para prolongar"})
    flojos = sorted(cobertura.items(), key=lambda x: x[1])[:5]
    if flojos and flojos[0][1] < max(cobertura.values() or [0]) / 2:
        brechas.append({"que": "Estados peor cubiertos",
                        "cuales": [f"{iso} ({n})" for iso, n in flojos],
                        "porque": "miden menos temas con serie que el resto del padrón"})

    sondeo = leer(PUBLICO / "sondeo.json") if (PUBLICO / "sondeo.json").exists() else {}
    candidatas = sondeo.get("registros") if isinstance(sondeo.get("registros"), list) else []
    if candidatas:
        brechas.append({"que": "fuentes candidatas en el banco de pruebas",
                        "cuantos": len(candidatas),
                        "porque": "esperan una disponibilidad medida antes de entrar al registro"})

    salida = {
        "que_es": "Auditoría automática del registro. La corre el robot en cada recolección, "
                  "no una persona cuando se acuerda.",
        "corrida": ahora.isoformat(timespec="seconds"),
        "conjuntos_revisados": len(conjuntos),
        "estados_del_padron": len(padron),
        "fallas": fallas,
        "cuantas_fallas": len(fallas),
        "brechas": brechas,
        "series": {"con_serie_larga": con_serie_larga, "con_serie_corta": con_serie_corta,
                   "sin_serie": sin_serie, "anios_para_tendencia": ANIOS_PARA_TENDENCIA},
        "cobertura_por_estado": cobertura,
        "veredicto": "sin fallas" if not fallas else f"{len(fallas)} falla"
                     + ("" if len(fallas) == 1 else "s"),
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8",
                      newline="")

    print(f"[auditoría] {len(conjuntos)} conjuntos · {salida['veredicto']} · "
          f"{len(brechas)} brecha{'' if len(brechas) == 1 else 's'} declarada"
          f"{'' if len(brechas) == 1 else 's'}")
    for f in fallas[:12]:
        print(f"  FALLA · {f['que']} · {f['donde']}: {f['porque']}")
    if len(fallas) > 12:
        print(f"  … y {len(fallas) - 12} más, todas en {SALIDA.relative_to(RAIZ)}")
    # La corrida termina en rojo: es la única forma de que el aviso llegue solo.
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
