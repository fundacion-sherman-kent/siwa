"""Padrón de fuentes oficiales — catálogos de datos abiertos de los Estados.

**Esto no publica datos: publica dónde están los datos.** Es un índice
verificado de qué conjuntos oficiales existen en cada país para cada materia del
registro, con su nombre y su dirección, para que el analista vaya al original.

Se hace así, y no descargando las cifras, por una razón de método: **el dato de
seguridad existe país por país pero no está homologado.** Cada Estado define el
homicidio a su manera, lo publica con su cadencia y lo cuenta desde su año. Una
serie regional armada sumando esas cifras sería una serie falsa. El índice
manda al analista al original, donde la definición está escrita.

Consulta portales CKAN y Socrata, que son interfaces estándar. El padrón vive en
`colectores/oficiales.json` y lo mantiene el equipo analítico.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import comun
import geo

PADRON = Path(__file__).resolve().parent / "oficiales.json"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
EJEMPLOS = 4


def _consultar(portal: dict, consulta: str) -> tuple:
    """Devuelve (cantidad, ejemplos, falla) para una materia en un portal."""
    base = portal["base"].rstrip("/")
    termino = urllib.parse.quote(consulta)
    if portal["tipo"] == "CKAN":
        url = f"{base}/api/3/action/package_search?q={termino}&rows={EJEMPLOS}"
    else:
        url = f"{base}/api/catalog/v1?q={termino}&limit={EJEMPLOS}"
    try:
        peticion = urllib.request.Request(
            url, headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            crudo = json.loads(respuesta.read(400_000).decode("utf-8", "replace"))
    except Exception as error:  # noqa: BLE001 — la falla del portal se declara
        return (0, [], f"{type(error).__name__}")

    ejemplos = []
    if portal["tipo"] == "CKAN":
        if not crudo.get("success"):
            return (0, [], "respuesta sin exito")
        resultado = crudo["result"]
        cantidad = resultado.get("count", 0)
        for conjunto in resultado.get("results", [])[:EJEMPLOS]:
            ejemplos.append({
                "titulo": (conjunto.get("title") or conjunto.get("name") or "").strip(),
                "organismo": (conjunto.get("organization") or {}).get("title", ""),
                "enlace": f"{base}/dataset/{conjunto.get('name','')}",
            })
    else:
        cantidad = crudo.get("resultSetSize", 0)
        for conjunto in crudo.get("results", [])[:EJEMPLOS]:
            recurso = conjunto.get("resource", {})
            ejemplos.append({
                "titulo": (recurso.get("name") or "").strip(),
                "organismo": (conjunto.get("owner") or {}).get("display_name", ""),
                "enlace": conjunto.get("permalink", base),
            })
    return (cantidad, ejemplos, None)


def recolectar():
    padron = json.loads(PADRON.read_text(encoding="utf-8"))
    portales, materias = padron["portales"], padron["materias"]
    nombres = {p["iso"]: p for p in geo.padron()}

    tareas = [(p, m) for p in portales for m in materias]
    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        crudos = list(ejecutor.map(lambda t: (t[0], t[1]) + _consultar(t[0], t[1]["consulta"]), tareas))

    por_pais, caidos = {}, []
    for portal, materia, cantidad, ejemplos, falla in crudos:
        iso = portal["iso"]
        ficha = por_pais.setdefault(iso, {
            **nombres.get(iso, {"iso": iso, "pais": iso, "bloque": "—"}),
            "organismo": portal["organismo"],
            "tipo": portal["tipo"],
            "portal": portal["base"],
            "materias": [],
            "conjuntos_hallados": 0,
        })
        if falla:
            caidos.append(f"{iso}/{materia['materia']}: {falla}")
            continue
        ficha["materias"].append({
            "materia": materia["materia"],
            "eje": materia["eje"],
            "consulta": materia["consulta"],
            "cantidad": cantidad,
            "ejemplos": ejemplos,
        })
        ficha["conjuntos_hallados"] += cantidad

    registros = sorted(por_pais.values(), key=lambda r: r["conjuntos_hallados"], reverse=True)
    for ficha in registros:
        ficha["materias"].sort(key=lambda m: m["cantidad"], reverse=True)

    con_portal = {r["iso"] for r in registros}
    sin_portal = [p["pais"] for p in geo.padron() if p["iso"] not in con_portal]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=(
            "Catálogos oficiales de los propios Estados: registro primario. Lo que se "
            "consigna es la EXISTENCIA del conjunto de datos y su dirección, no su "
            "contenido. Fuente única por naturaleza: solo el Estado publica su catálogo."
        ),
    )

    vacios = [
        "ESTO NO PUBLICA DATOS, PUBLICA DÓNDE ESTÁN. Es un índice de conjuntos "
        "oficiales con su dirección, para que el analista vaya al original.",
        "**Las cifras de estos catálogos NO son comparables entre países.** Cada Estado "
        "define el delito a su manera, lo publica con su cadencia y lo cuenta desde su "
        "año. Sumarlas para armar una serie regional produciría una serie falsa.",
        (
            f"Solo {len(con_portal)} de los 33 Estados tienen portal oficial con interfaz "
            f"de consulta verificada. Sin portal verificado: {', '.join(sin_portal)}."
        ),
        "Que un Estado no figure NO prueba que carezca de portal. De los que no figuran: "
        "Brasil exige clave gratuita con registro; Guatemala, Costa Rica, Bolivia y Ecuador "
        "interponen protección contra acceso automatizado, que NO se esquiva por decisión "
        "de doctrina (límites.md) y se gestiona por vía oficial; Perú y Jamaica tienen "
        "portal cuya plataforma no se identificó. El resto no expuso dirección alguna.",
        "La búsqueda es por palabra en el título y la descripción del conjunto. Un "
        "conjunto rotulado con otro vocabulario no aparece, y uno que menciona la "
        "palabra al pasar aparece sin corresponder.",
        "El recuento es de conjuntos publicados, no de calidad ni de vigencia: un "
        "catálogo puede listar un conjunto abandonado hace años.",
    ]
    if caidos:
        vacios.append(f"{len(caidos)} consultas fallaron en esta corrida: {'; '.join(caidos)}.")

    return comun.escribir(
        colector="oficiales",
        capa="publico",
        fuente="Catálogos oficiales de datos abiertos de los Estados del padrón",
        url_fuente="colectores/oficiales.json",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados_con_portal": len(con_portal),
                "estados_del_padron": 33,
                "conjuntos_hallados": sum(r["conjuntos_hallados"] for r in registros),
                "materias_consultadas": len(materias),
            },
            "sectoriales_verificados": padron.get("sectoriales_verificados", []),
            "sin_acceso_automatizado": padron.get("_bloqueados", {}),
        },
    )


if __name__ == "__main__":
    comun.correr("oficiales", recolectar)
