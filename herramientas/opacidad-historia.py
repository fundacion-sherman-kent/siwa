# -*- coding: utf-8 -*-
"""La historia del Índice de Opacidad: sin serie no hay evolución, y no se inventa.

EL PROBLEMA. El índice ya da un puntaje de 0 a 100 y un puesto para los 33
Estados, pero solo del día en que se corrió. Sin historia no se puede contestar
la única pregunta que le importa a quien vigila la transparencia: **¿está
mejorando o empeorando?**

POR QUÉ LA SERIE EMPIEZA HOY Y NO ANTES
----------------------------------------
Se evaluó reconstruirla hacia atrás y **se descartó, con motivo**. El índice se
arma con seis actos. Dos de ellos —declarar el comercio de armas a Naciones
Unidas, informar al tratado de especies— tienen año y se podrían reconstruir.
Los otros cuatro son actos del presente: si el portal responde hoy, si el sitio
oficial está en pie hoy. **Nadie puede saber si el portal de Guyana respondía en
marzo.**

Un índice de seis actos reconstruido con dos sería otro índice, y ponerlo en la
misma línea que el de seis fabricaría una evolución que no ocurrió. Así que la
serie arranca el día en que se empieza a archivar, y **el archivo dice desde
cuándo**. Una serie corta y verdadera vale más que una larga y falsa.

QUÉ GUARDA, Y QUÉ NO
--------------------
Un punto por Estado y por día, con el puntaje y cuántos actos lo sostienen. No
guarda el detalle de los seis actos: eso ya vive en `indice_opacidad.json`, que
se reescribe entero en cada corrida. Acá va lo mínimo para dibujar una línea y
para poder decir «este Estado mejoró seis puntos desde tal fecha».

Y NO GUARDA DOS VECES EL MISMO DÍA. El robot corre cada hora; archivar cada
corrida daría veinticuatro puntos diarios idénticos que solo engordan el
archivo. Se guarda el último de cada día.
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PUBLICO = RAIZ / "datos" / "publico"
FUENTE = PUBLICO / "indice_opacidad.json"
SALIDA = PUBLICO / "opacidad_historia.json"

sys.path.insert(0, str(RAIZ / "colectores"))
import comun  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not FUENTE.exists():
        print("[opacidad-historia] todavía no hay índice: no se archiva nada", file=sys.stderr)
        return
    d = json.loads(FUENTE.read_text(encoding="utf-8"))
    hoy = datetime.now(timezone.utc).date().isoformat()

    # LA FECHA DEL PUNTO ES LA DEL ÍNDICE, NO LA DE HOY. Esto archivaba con la fecha
    # de la corrida: si el índice no se recalculaba durante tres días —porque el
    # colector falló—, la historia igual anotaba tres puntos, uno por día, todos con
    # el mismo valor viejo. Eso es inventar tres mediciones que nadie hizo. Se usa el
    # día en que el índice se calculó de verdad, y si ese día ya está archivado no se
    # vuelve a escribir: no hubo medición nueva que guardar.
    medido = ((d.get("procedencia") or {}).get("obtenido_en") or "")[:10]
    if not medido:
        print("[opacidad-historia] el índice no dice cuándo se calculó: no se archiva",
              file=sys.stderr)
        sys.exit(1)
    if medido > hoy:
        print(f"[opacidad-historia] el índice dice haberse calculado el {medido}, que todavía "
              f"no llegó: no se archiva", file=sys.stderr)
        sys.exit(1)

    historia = {}
    if SALIDA.exists():
        try:
            historia = json.loads(SALIDA.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — un archivo roto no borra la historia: se avisa
            print("[opacidad-historia] el archivo anterior no se pudo leer; no se pisa",
                  file=sys.stderr)
            sys.exit(1)

    por_iso = {r["iso"]: r for r in historia.get("registros", [])}
    # SE LIMPIA LO QUE YA ESTABA. La versión anterior fechaba con el día de la corrida
    # y podía dejar dos puntos del mismo día en la misma serie. Al cargar se colapsa
    # por fecha —gana el último escrito— y se ordena, así el archivo se sana solo sin
    # que haya que tocarlo a mano.
    for fila in por_iso.values():
        unico = {}
        for q in fila.get("serie") or []:
            unico[q.get("fecha")] = q
        fila["serie"] = [unico[f] for f in sorted(unico)]
    nuevos = cambiados = 0
    for r in d.get("registros", []):
        if r.get("estado") != "medido" or r.get("opacidad") is None:
            continue
        fila = por_iso.setdefault(r["iso"], {"iso": r["iso"], "pais": r.get("pais"),
                                             "bloque": r.get("bloque"), "serie": []})
        fila["pais"] = r.get("pais") or fila.get("pais")
        fila["bloque"] = r.get("bloque") or fila.get("bloque")
        punto = {"fecha": medido, "valor": round(float(r["opacidad"]), 1),
                 "actos": r.get("actos_medidos")}
        # SE BUSCA POR FECHA, NO SE MIRA SOLO EL ÚLTIMO. Mirando el último, un punto
        # con fecha anterior —que pasa cuando el índice se recalcula tarde— se agregaba
        # al final y la serie quedaba desordenada y con el día repetido. Se indexa por
        # fecha, se reemplaza el del día y se ordena al guardar.
        serie = fila["serie"]
        porFecha = {q["fecha"]: i for i, q in enumerate(serie)}
        if punto["fecha"] in porFecha:
            i = porFecha[punto["fecha"]]
            if serie[i] != punto:
                serie[i] = punto
                cambiados += 1
        else:
            serie.append(punto)
            nuevos += 1
        serie.sort(key=lambda q: q["fecha"])

    registros = sorted(por_iso.values(), key=lambda x: x["iso"])
    desde = min((f["serie"][0]["fecha"] for f in registros if f["serie"]), default=medido)
    dias = len({p["fecha"] for f in registros for p in f["serie"]})

    salida = {
        "procedencia": {
            "colector": "opacidad-historia",
            "fuente": {"nombre": "Fundación Sherman Kent — archivo del Índice de Opacidad",
                       "url": f"{comun.BASE}/datos/publico/indice_opacidad.json"},
            "obtenido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            # SE CALIFICA CON LA FUNCIÓN DE LA CASA, NO A MANO. Escrita a mano, esta
            # ficha declaraba credibilidad «1» —la máxima— sin corroboración, que es
            # justo lo que `comun.calificar` prohíbe, y además como texto en vez de
            # número, así que ningún control podía ordenarla. Es archivo propio de un
            # índice propio: fiable como acto —lo escribió esta casa y quedó fechado—
            # y credibilidad 2, porque nadie fuera de la casa lo comprueba.
            "calificacion": comun.calificar(
                "A", 2, False,
                "Archivo propio: esta casa guarda cada día el Índice de Opacidad que ella misma "
                "calcula. La fecha y el acto de archivar son ciertos; el índice archivado vale lo "
                "que valga el índice, y no lo corrobora nadie de afuera."),
            "vacios_declarados": [
                "La serie empieza el " + desde + ", que es cuando esta casa empezó a "
                "archivarla. NO se reconstruyó hacia atrás: cuatro de los seis actos del "
                "índice son del presente —si el portal responde hoy, si el sitio está en "
                "pie hoy— y nadie puede saber si respondían en marzo. Un índice de seis "
                "actos reconstruido con dos sería otro índice.",
            ],
            "restriccion_de_uso": None,
        },
        "resumen": {"desde": desde, "dias_archivados": dias,
                    "estados": len(registros),
                    "escala": "0 el más transparente · 100 el más opaco"},
        "registros": registros,
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8",
                      newline="")
    print(f"[opacidad-historia] {len(registros)} Estados · {dias} día"
          f"{'' if dias == 1 else 's'} archivado{'' if dias == 1 else 's'} desde {desde}"
          f" · {nuevos} punto{'' if nuevos == 1 else 's'} nuevo{'' if nuevos == 1 else 's'}"
          + (f", {cambiados} corregido{'' if cambiados == 1 else 's'}" if cambiados else ""))


if __name__ == "__main__":
    main()
