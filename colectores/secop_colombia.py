# -*- coding: utf-8 -*-
"""SECOP Colombia: actividad de contratación pública por año, fuente VIVA.

POR QUÉ EXISTE
--------------
El colector regional de contrataciones abiertas (OCDS) cubre Colombia, pero su fuente
quedó MUERTA: el último proceso es de abril de 2022 (hace más de cuatro años). SECOP,
por su portal de datos abiertos (Socrata), sigue vivo. Este colector le pide a SECOP el
Plan Anual de Adquisiciones agregado por año —cuántos planes y cuánto presupuesto— para
tener el dato FRESCO de Colombia (mandato de dato más actual). Impacta la fila de
Colombia; no reemplaza al regional, lo refresca.

QUÉ MIDE, Y QUÉ NO
------------------
Mide el Plan Anual de Adquisiciones (lo que las entidades PLANEAN comprar), no los
contratos ejecutados: es un proxy de actividad y de transparencia de la planificación,
no del gasto real. El presupuesto va en pesos colombianos. Se agrega por año en el
propio servidor de Socrata (una sola consulta), así que ya viene como serie.
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import urllib.request

import comun

BASE = "https://www.datos.gov.co/resource/b6m4-qgqv.json"
CONSULTA = {
    "$select": "anno, count(1) as planes, sum(valor_presupuesto_general) as presupuesto",
    "$group": "anno",
    "$order": "anno DESC",
    "$limit": 30,
}


def recolectar():
    url = BASE + "?" + urllib.parse.urlencode(CONSULTA)
    pet = urllib.request.Request(url, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(pet, timeout=120) as r:
        filas = json.loads(r.read().decode("utf-8", "replace"))

    # El año en curso, medido igual que la auditoría (UTC), para que el límite entre
    # «medido» y «planificado» sea exactamente el mismo que el control usa.
    este_anio = dt.datetime.now(dt.timezone.utc).year

    serie = []
    for f in filas:
        try:
            anio = int(str(f.get("anno") or "").strip())
        except ValueError:
            continue
        if not (2000 <= anio <= 2100):
            continue
        planes = int(float(f.get("planes") or 0))
        presupuesto = int(float(f.get("presupuesto") or 0))
        punto = {"anio": anio, "planes": planes, "presupuesto_cop": presupuesto}
        # El Plan Anual de Adquisiciones mira a futuro: SECOP ya publica planes de
        # años que todavía no empezaron. No es una medición fechada en el futuro
        # —sería un error—; es un plan que existe hoy, y se marca como tal para que
        # el control lo distinga y las figuras no lo lean como un dato cerrado.
        if anio > este_anio:
            punto["planificado"] = True
        serie.append(punto)
    serie.sort(key=lambda x: x["anio"])

    recientes = [s for s in serie if s["anio"] >= 2023 and s["planes"] > 0]
    if not recientes:
        raise RuntimeError(
            "SECOP no devolvió ningún año reciente (>=2023) con planes. La consulta o el dataset "
            "cambiaron de forma. NO se publica.")

    # El encabezado toma el último año EN CURSO O PASADO: un plan a futuro (p. ej.
    # 2027, con pocas entidades cargadas todavía) no representa el estado y no debe
    # ser la cifra de tapa. Si sólo hubiera años planificados, cae al último.
    medidos = [s for s in serie if not s.get("planificado")]
    ultimo = medidos[-1] if medidos else serie[-1]
    registros = [{
        "iso": "COL", "pais": "Colombia", "bloque": "Andina",
        "anio": ultimo["anio"], "planes": ultimo["planes"],
        "presupuesto_cop": ultimo["presupuesto_cop"], "serie": serie,
    }]
    vacios = [
        "Es el Plan Anual de Adquisiciones (lo que las entidades PLANEAN comprar), no los "
        "contratos ejecutados: mide la planificación y su transparencia, no el gasto real.",
        "El presupuesto va en pesos colombianos, no en dólares, y no está deflactado.",
        "Refresca el dato de Colombia, que en la fuente regional (OCDS) quedó en abril de 2022. "
        "Es de un solo país: no ordena a los 33 ni entra al compuesto.",
    ]
    calificacion = comun.calificar(
        fiabilidad="A", credibilidad=2, corroborado=False,
        nota=("SECOP — datos abiertos de la Agencia Nacional de Contratación Pública de Colombia, "
              "vía Socrata. Fiabilidad A porque es el registro oficial del Estado colombiano. "
              "Credibilidad 2 porque es un recuento administrativo de planes, no de ejecución."),
    )
    return comun.escribir(
        colector="secop_colombia",
        capa="publico",
        fuente="SECOP — Plan Anual de Adquisiciones, Agencia Nacional de Contratación Pública (Colombia), datos abiertos",
        url_fuente=BASE,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={"resumen": {"anio": ultimo["anio"], "planes_ultimo": ultimo["planes"],
                           "anios_en_serie": len(serie), "consultado": comun.ahora()},
               "licencia": "Datos abiertos de Colombia; cita a SECOP. Este registro se considera de uso no comercial."},
    )


if __name__ == "__main__":
    comun.correr("secop_colombia", recolectar)
