"""Extorsión informática: víctimas publicadas por los propios atacantes.

Qué se cuenta, y de dónde sale
------------------------------
Los grupos de extorsión informática mantienen **sitios donde publican a sus
víctimas** para presionarlas a pagar. `ransomware.live` recopila esos sitios y
expone lo recopilado en una interfaz abierta. De ahí salen estas cifras: víctima,
sector, grupo atacante, país y fecha.

**Es la única medida de ciberseguridad por HECHOS —no por infraestructura— que se
encontró gratuita y con atribución por país** para los 33 Estados del padrón. El
registro ya publica servidores cifrados y usuarios de internet, que miden
superficie y exposición; esto mide **ataques con víctima declarada**.

El sesgo, que es grande y estructural
-------------------------------------
> **Acá solo aparece quien NO pagó rápido.**

El atacante publica a la víctima **para presionarla**. La empresa que paga
enseguida y en silencio **nunca aparece en ninguna lista**. Es decir: esta cifra
**subestima el fenómeno de manera sistemática, y por una magnitud que nadie puede
calcular**. Un país con pocos casos puede tener pocos ataques, o víctimas que
pagan más rápido.

Y hay tres cautelas más:

1. **Es un recuento, no una tasa.** Una economía grande tiene más empresas que
   atacar. Que Brasil encabece la lista no significa que esté peor protegido.
2. **El país es el de la sede de la víctima**, no necesariamente donde ocurrió el
   ataque ni dónde estaban los sistemas.
3. **La fuente es el atacante.** Los grupos exageran, repiten víctimas viejas y a
   veces publican ataques que no ocurrieron. Lo que se observa con certeza es que
   **el grupo lo publicó**, no que el hecho sea como lo cuenta.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone

import comun
import geo

BASE = "https://api.ransomware.live/v2"
NAVEGADOR = comun.AGENTE
ESPERA = 0.5
REINTENTOS = 3

# La interfaz consulta por código de dos letras.
ISO2 = {
    "ARG": "AR", "BOL": "BO", "BRA": "BR", "CHL": "CL", "COL": "CO", "CRI": "CR",
    "CUB": "CU", "DOM": "DO", "ECU": "EC", "SLV": "SV", "GTM": "GT", "HND": "HN",
    "MEX": "MX", "NIC": "NI", "PAN": "PA", "PRY": "PY", "PER": "PE", "URY": "UY",
    "VEN": "VE", "HTI": "HT", "JAM": "JM", "TTO": "TT", "GUY": "GY", "SUR": "SR",
    "BLZ": "BZ", "BHS": "BS", "BRB": "BB", "ATG": "AG", "DMA": "DM", "GRD": "GD",
    "KNA": "KN", "LCA": "LC", "VCT": "VC",
}


def _pedir(ruta: str):
    """Consulta con reintento: la interfaz limita la tasa y devuelve 429."""
    ultimo = None
    for intento in range(REINTENTOS):
        try:
            pet = urllib.request.Request(f"{BASE}/{ruta}", headers={
                "User-Agent": NAVEGADOR, "Accept": "application/json"})
            with urllib.request.urlopen(pet, timeout=60) as r:
                return json.loads(r.read().decode("utf-8", "replace")), None
        except urllib.error.HTTPError as e:
            ultimo = f"HTTP {e.code}"
            if e.code == 429:
                time.sleep(3 * (intento + 1))
                continue
            return None, ultimo
        except Exception as e:  # noqa: BLE001 — la falla se declara, no se oculta
            ultimo = type(e).__name__
            time.sleep(1.5)
    return None, ultimo


def recolectar():
    padron = geo.padron()
    nombres = {p["iso"]: p["pais"] for p in padron}
    bloques = {p["iso"]: p["bloque"] for p in padron}
    anio_hoy = datetime.now(timezone.utc).year

    registros, caidos, sin_caso = [], [], []
    grupos_region, sectores_region = Counter(), Counter()
    total = 0

    for p in padron:
        iso = p["iso"]
        dos = ISO2.get(iso)
        if not dos:
            continue
        datos, falla = _pedir(f"countryvictims/{dos}")
        time.sleep(ESPERA)
        if falla:
            caidos.append(f"{nombres[iso]}: {falla}")
            continue
        victimas = datos or []
        if not victimas:
            sin_caso.append(nombres[iso])
            continue
        total += len(victimas)

        def anio(v):
            return (v.get("discovered") or v.get("attackdate") or "")[:4]

        por_anio = Counter(a for a in (anio(v) for v in victimas) if a.isdigit())
        sectores = Counter((v.get("activity") or "sin declarar").strip() for v in victimas)
        grupos = Counter((v.get("group") or v.get("group_name") or "sin identificar").strip()
                         for v in victimas)
        grupos_region.update(grupos)
        sectores_region.update(sectores)
        recientes = sum(n for a, n in por_anio.items() if int(a) >= anio_hoy - 1)

        registros.append({
            "iso": iso, "pais": nombres[iso], "bloque": bloques[iso],
            "victimas": len(victimas),
            "victimas_ultimos_dos_anios": recientes,
            "grupos_distintos": len(grupos),
            "primer_anio": min(por_anio) if por_anio else None,
            "ultimo_anio": max(por_anio) if por_anio else None,
            "serie": [{"anio": int(a), "valor": n} for a, n in sorted(por_anio.items())
                      if a.isdigit()],
            "sectores": [{"sector": s, "victimas": n} for s, n in sectores.most_common(6)],
            "grupos": [{"grupo": g, "victimas": n} for g, n in grupos.most_common(5)],
        })

    registros.sort(key=lambda r: -r["victimas"])

    vacios = [
        "ACA SOLO APARECE QUIEN NO PAGO RAPIDO. El atacante publica a la victima PARA "
        "PRESIONARLA: la empresa que paga enseguida y en silencio nunca aparece en "
        "ninguna lista. Esta cifra SUBESTIMA el fenomeno de manera sistematica y por "
        "una magnitud que nadie puede calcular. Un Estado con pocos casos puede tener "
        "pocos ataques, o victimas que pagan mas rapido.",
        "ES UN RECUENTO, NO UNA TASA. Una economia grande tiene mas empresas que atacar. "
        "Que Brasil encabece la lista NO significa que este peor protegido: significa "
        "que tiene mas objetivos. Para comparar hay que leer esto junto con el tamano "
        "de cada economia y con los usuarios de internet, que este registro publica.",
        "LA FUENTE ES EL ATACANTE. Los grupos exageran, repiten victimas viejas y a "
        "veces publican ataques que no ocurrieron. Lo que se observa CON CERTEZA es que "
        "el grupo lo publico, no que el hecho sea como lo cuenta. Por eso la "
        "credibilidad es 4 y no mejor.",
        "EL PAIS ES EL DE LA SEDE DE LA VICTIMA, no necesariamente donde ocurrio el "
        "ataque ni donde estaban los sistemas comprometidos. Una filial atacada puede "
        "figurar en el pais de la casa matriz.",
        "El sector lo clasifica la fuente, no la Fundacion, y su criterio no esta "
        "publicado en detalle.",
    ]
    if sin_caso:
        vacios.append("Sin ninguna victima registrada: " + ", ".join(sin_caso)
                      + ". Ausencia de registro no es ausencia de ataques.")
    if caidos:
        vacios.append("Estados que no se pudieron consultar en esta corrida: "
                      + "; ".join(caidos) + ". El dato anterior de esos Estados, si lo "
                      "hubiera, queda intacto.")

    calificacion = comun.calificar(
        fiabilidad="D",
        credibilidad=4,
        corroborado=False,
        nota=("Recopilacion de los sitios de extorsion de los propios grupos atacantes. "
              "La recopilacion es metodica y publica; el CONTENIDO lo declara el "
              "delincuente y no se puede corroborar de forma independiente. Se registra "
              "que la publicacion existe, no que el hecho sea como se cuenta."),
    )

    return comun.escribir(
        colector="ransomware",
        capa="publico",
        fuente="ransomware.live — recopilación de sitios de extorsión informática",
        url_fuente="https://api.ransomware.live/v2/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "victimas_registradas": total,
                "estados_con_caso": len(registros),
                "estados_del_padron": len(padron),
                "grupos_distintos_en_la_region": len(grupos_region),
                "anio_de_corte": anio_hoy,
            },
            "grupos_mas_activos": [{"grupo": g, "victimas": n}
                                   for g, n in grupos_region.most_common(12)],
            "sectores_mas_golpeados": [{"sector": s, "victimas": n}
                                       for s, n in sectores_region.most_common(12)],
            "metodo": (
                "Se consulta el listado de victimas por pais y se cuentan casos, grupos "
                "y sectores. NO se republica el nombre de ninguna victima: son empresas "
                "y organismos identificables, muchos de ellos damnificados, y nombrarlos "
                "aqui repetiria la presion que el atacante buscaba. Se publican "
                "recuentos y repartos."
            ),
        },
    )


if __name__ == "__main__":
    comun.correr("ransomware", recolectar)
