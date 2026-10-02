# -*- coding: utf-8 -*-
"""Termómetro de frescura de los CORREDORES DE FLUJOS ILÍCITOS (automejora).

Igual que herramientas/frescura.py para los indicadores, pero para las rutas del
producto «Trayectorias de flujos ilícitos». Mide, por familia, qué tan fresca está
la cobertura (año `desde` de cada ruta), cuántas son históricas o de baja confianza,
y deja un ranking de lo más atrasado para refrescar. NO publica ni incorpora nada:
sólo mide y declara, con la compuerta humana en el juicio (acta 1/10, automejora).

Es el primer ladrillo hacia el dato en tiempo real: declara qué corredores están
viejos para que la próxima recolección (o el buscador) los priorice.

Corre en recolectar.yml. Escribe datos/publico/frescura-flujos.json.
"""
from __future__ import annotations
import json, datetime, statistics
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
SIT = RAIZ / "sitio"
SALIDA = RAIZ / "datos" / "publico" / "frescura-flujos.json"
ANIO = datetime.datetime.now(datetime.timezone.utc).year

# familia -> archivos de datos que la componen (país + infraestructura)
FAM = {
    "narcotrafico": ["cocaina", "opioides", "marihuana", "sinteticos", "precursores"],
    "armas": ["armas"], "migracion": ["migracion"], "minerales": ["minerales"],
    "especies": ["especies"], "contrabando": ["contrabando"], "trata": ["trata"],
}
ROTULO = {"narcotrafico": "Narcotráfico", "armas": "Armas", "migracion": "Migración",
          "minerales": "Oro y minerales", "especies": "Especies",
          "contrabando": "Contrabando", "trata": "Trata"}

def cargar(prefijo, f):
    p = SIT / f"{prefijo}-rutas-{f}.json"
    if not p.exists():
        return []
    rutas = json.loads(p.read_text(encoding="utf-8")).get("rutas", [])
    return [r for r in rutas if not r.get("no_publicar")]

def rutas_de_familia(fam):
    out = []
    for f in FAM[fam]:
        for niv, pref in (("pais", "flujos"), ("infraestructura", "infra")):
            for r in cargar(pref, f):
                out.append({**r, "_nivel": niv, "_archivo": f})
    return out

def main():
    familias = {}
    todas = []
    for fam in FAM:
        rs = rutas_de_familia(fam)
        todas += rs
        desdes = [int(r["desde"]) for r in rs if isinstance(r.get("desde"), int)]
        hist = sum(1 for r in rs if r.get("estado") == "historica")
        baja = sum(1 for r in rs if r.get("confianza") == "baja")
        infra = sum(1 for r in rs if r["_nivel"] == "infraestructura")
        reciente = sum(1 for d in desdes if d >= ANIO - 2)   # ≤24 meses
        med = statistics.median(desdes) if desdes else None
        familias[fam] = {
            "familia": fam, "rotulo": ROTULO[fam],
            "rutas": len(rs), "a_nivel_pais": len(rs) - infra, "a_nivel_infraestructura": infra,
            "anio_mediano_desde": med,
            "antiguedad_mediana_anios": (ANIO - med) if med else None,
            "recientes_24m": reciente, "pct_recientes": round(reciente / len(rs) * 100, 1) if rs else 0,
            "historicas": hist, "confianza_baja": baja,
            "mas_viejo": min(desdes) if desdes else None,
            "mas_nuevo": max(desdes) if desdes else None,
        }
    # ranking de las rutas más atrasadas (año desde más viejo, o históricas)
    conf = {"alta": 3, "media": 2, "baja": 1}
    ranked = sorted(
        (r for r in todas if isinstance(r.get("desde"), int)),
        key=lambda r: (r.get("estado") == "historica", r["desde"], conf.get(r.get("confianza"), 2)),
    )
    ranking = [{"id": r.get("id"), "nombre": r.get("nombre", "")[:80], "familia": r["_archivo"],
                "desde": r["desde"], "antiguedad_anios": ANIO - r["desde"],
                "confianza": r.get("confianza"), "nivel": r["_nivel"],
                "historica": r.get("estado") == "historica"} for r in ranked[:20]]

    desdes_all = [int(r["desde"]) for r in todas if isinstance(r.get("desde"), int)]
    resumen = {
        "rutas_publicables": len(todas),
        "a_nivel_pais": sum(1 for r in todas if r["_nivel"] == "pais"),
        "a_nivel_infraestructura": sum(1 for r in todas if r["_nivel"] == "infraestructura"),
        "antiguedad_mediana_anios": (ANIO - statistics.median(desdes_all)) if desdes_all else None,
        "recientes_24m": sum(1 for d in desdes_all if d >= ANIO - 2),
        "historicas": sum(1 for r in todas if r.get("estado") == "historica"),
        "confianza_baja": sum(1 for r in todas if r.get("confianza") == "baja"),
    }
    vacios = []
    for fam, d in familias.items():
        if d["rutas"] < 20:
            vacios.append(f"{d['rotulo']}: sólo {d['rutas']} corredores publicados; conviene profundizar.")
        if d["antiguedad_mediana_anios"] and d["antiguedad_mediana_anios"] >= 4:
            vacios.append(f"{d['rotulo']}: antigüedad mediana de {d['antiguedad_mediana_anios']} años; "
                          "la familia pide refresco de fuentes.")

    salida = {
        "que_es": "Termómetro de frescura de los corredores de flujos ilícitos. Mide, por familia, qué tan "
                  "reciente es el año de registro de cada ruta, cuántas son históricas o de baja confianza, y "
                  "deja un ranking de lo más atrasado para que la próxima recolección lo priorice. Mide y "
                  "declara; no incorpora ni publica nada solo.",
        "corrida": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "anio_de_referencia": ANIO,
        "resumen": resumen,
        "por_familia": list(familias.values()),
        "ranking_mas_atrasadas": ranking,
        "vacios_declarados": vacios,
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    print(f"frescura-flujos.json: {resumen['rutas_publicables']} rutas, "
          f"antigüedad mediana {resumen['antiguedad_mediana_anios']} años, "
          f"{len(vacios)} vacíos declarados")

if __name__ == "__main__":
    main()
