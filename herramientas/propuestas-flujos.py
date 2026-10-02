# -*- coding: utf-8 -*-
"""Proponedor de refresco de los CORREDORES DE FLUJOS ILÍCITOS (automejora, fase 2).

Lee el termómetro (frescura-flujos.json) y, por familia, arma una COLA DE BÚSQUEDA
priorizada: qué corredores están más viejos y qué habría que buscar para
refrescarlos (decomisos, operativos, reportes recientes), con los términos exactos.
PROPONE, NO INCORPORA: declara qué buscar; el scanner (Llama, gratis) lo levanta y
deja candidatos en una rama aparte, y la incorporación sigue siendo juicio humano
(dos fuentes o rótulo, décimo hombre, visto bueno). Es el puente del motor de
frescura hacia el dato en tiempo real de los flujos.

Corre en recolectar.yml, después de frescura-flujos.py. Escribe
datos/publico/propuestas-flujos.json.
"""
from __future__ import annotations
import json, datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
SIT = RAIZ / "sitio"
FRESCURA = RAIZ / "datos" / "publico" / "frescura-flujos.json"
SALIDA = RAIZ / "datos" / "publico" / "propuestas-flujos.json"
ANIO = datetime.datetime.now(datetime.timezone.utc).year

FAM = {
    "narcotrafico": ["cocaina", "opioides", "marihuana", "sinteticos", "precursores"],
    "armas": ["armas"], "migracion": ["migracion"], "minerales": ["minerales"],
    "especies": ["especies"], "contrabando": ["contrabando"], "trata": ["trata"],
}
# término genérico de evento por familia, para la búsqueda del scanner
EVENTO = {
    "narcotrafico": "decomiso incautación de droga", "armas": "incautación de armas tráfico",
    "migracion": "operativo tráfico de migrantes rescate", "minerales": "decomiso de oro minería ilegal",
    "especies": "decomiso de fauna tráfico de especies", "contrabando": "decomiso de contrabando",
    "trata": "rescate víctimas trata de personas operativo",
}
ARCH_A_FAM = {a: fam for fam, archs in FAM.items() for a in archs}

def cargar(pref, f):
    p = SIT / f"{pref}-rutas-{f}.json"
    if not p.exists():
        return []
    return [r for r in json.loads(p.read_text(encoding="utf-8")).get("rutas", []) if not r.get("no_publicar")]

def corredor(r):
    w = r.get("waypoints", [])
    if len(w) < 2:
        return None, None
    return (w[0][2] if len(w[0]) >= 3 else None), (w[-1][2] if len(w[-1]) >= 3 else None)

def main():
    fr = json.loads(FRESCURA.read_text(encoding="utf-8")) if FRESCURA.exists() else {"por_familia": []}
    stale_fams = {f["familia"] for f in fr.get("por_familia", [])
                  if (f.get("antiguedad_mediana_anios") or 0) >= 4 or (f.get("pct_recientes") or 100) < 40}

    propuestas = []
    for fam, archs in FAM.items():
        rutas = []
        for a in archs:
            for pref in ("flujos", "infra"):
                for r in cargar(pref, a):
                    rutas.append(r)
        # las más viejas de la familia (año desde más antiguo)
        con_desde = [r for r in rutas if isinstance(r.get("desde"), int)]
        con_desde.sort(key=lambda r: (r.get("estado") == "historica", r["desde"]))
        objetivo = []
        for r in con_desde[:8]:   # hasta 8 corredores por familia a refrescar
            o, d = corredor(r)
            lugares = " ".join(x for x in (o, d) if x)
            objetivo.append({
                "id": r.get("id"), "nombre": r.get("nombre", "")[:80],
                "corredor": f"{o} → {d}" if o and d else (o or d or "—"),
                "desde": r.get("desde"), "antiguedad_anios": ANIO - r["desde"],
                "confianza": r.get("confianza"),
                "terminos_de_busqueda": f"{EVENTO[fam]} {lugares} {ANIO-1} {ANIO}".strip(),
            })
        propuestas.append({
            "familia": fam,
            "prioridad": "alta" if fam in stale_fams else "media",
            "corredores_a_refrescar": objetivo,
            "que_falta": "Buscar operativos/decomisos recientes en estos corredores (el scanner Llama o una "
                         "investigación), proponer la actualización en rama aparte y calificarla a mano: dos "
                         "fuentes o rótulo, décimo hombre y visto bueno antes de incorporar. No se dispara nada "
                         "automáticamente desde acá.",
        })

    salida = {
        "que_es": "Cola de búsqueda para refrescar los corredores de flujos ilícitos. Toma lo más atrasado de "
                  "frescura-flujos.json y, por familia, dice qué corredores refrescar y con qué términos buscar "
                  "eventos recientes. Propone; no incorpora ni dispara búsquedas solo.",
        "corrida": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "resumen": {"familias": len(propuestas),
                    "familias_prioridad_alta": sum(1 for p in propuestas if p["prioridad"] == "alta"),
                    "corredores_en_cola": sum(len(p["corredores_a_refrescar"]) for p in propuestas)},
        "propuestas": propuestas,
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    print(f"propuestas-flujos.json: {salida['resumen']['corredores_en_cola']} corredores en cola, "
          f"{salida['resumen']['familias_prioridad_alta']} familias en prioridad alta")

if __name__ == "__main__":
    main()
