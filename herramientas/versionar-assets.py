# -*- coding: utf-8 -*-
"""Versiona los archivos compartidos del sitio para que el navegador no sirva
versiones viejas de caché.

EL PROBLEMA. El asistente (guia-siwa.js), su catálogo (guia-siwa.json) y la
franja (cabecera-siwa.js) se cargan con una etiqueta fija. GitHub Pages los deja
en caché unos minutos, así que después de publicar un arreglo el navegador sigue
mostrando el viejo hasta que la persona fuerza el refresco. Pasó varias veces.

LA SALIDA. Se escribe un manifiesto chico, `sitio/_comun/assets.json`, con un
hash del CONTENIDO de cada archivo. Los cargadores del sitio lo leen SIN caché y
le pegan `?v=<hash>` a cada archivo. Cuando el archivo cambia, cambia el hash, y
el navegador baja el nuevo al instante; cuando no cambia, sigue usando la caché.
Solo se re-descarga lo que de verdad cambió.

Corre en cada publicación (a mano o en el robot). Sin dependencias externas.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
COMUN = RAIZ / "sitio" / "_comun"

# Los archivos compartidos que conviene versionar (los que se iteran y se cachean).
ARCHIVOS = ["guia-siwa.js", "guia-siwa.json", "cabecera-siwa.js"]


def hash_corto(ruta: Path) -> str:
    return hashlib.sha1(ruta.read_bytes()).hexdigest()[:10]


def main() -> int:
    versiones = {}
    for nombre in ARCHIVOS:
        f = COMUN / nombre
        if f.exists():
            versiones[nombre] = hash_corto(f)
    salida = COMUN / "assets.json"
    salida.write_text(json.dumps(versiones, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
    print("assets.json escrito:", versiones)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
