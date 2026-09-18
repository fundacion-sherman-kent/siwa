# -*- coding: utf-8 -*-
"""Regenera el catálogo del asistente "Guía SIWA" (sitio/_comun/guia-siwa.json).

POR QUÉ EXISTE. El asistente de navegación conoce los temas por un archivo,
guia-siwa.json. Si ese archivo se escribe a mano, envejece solo: el día que se
agrega un tema al registro, el asistente sigue sin conocerlo y nadie se entera.

CÓMO. La lista de temas se le pregunta AL PROPIO REGISTRO —el mismo selector
#tema-principal del índice del que sale cada tarjeta por tema—, así que este
generador comparte la fuente con tarjetas-por-tema.py y no puede quedar
desincronizado. Corre en el mismo robot (el control de pantallas), que ya tiene
el navegador de prueba montado y el registro servido.

QUÉ NO HACE. No inventa sinónimos ni respuestas: el asistente busca por el
rótulo real y por el slug. Los sinónimos finos y las respuestas frecuentes más
ricas los puede sumar después el robot con el modelo local; esto asegura, como
mínimo, que TODOS los temas vigentes estén siempre en el asistente.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
SALIDA = RAIZ / "sitio" / "_comun" / "guia-siwa.json"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

# Nombre de cada país por su slug de página (sitio/pais/<slug>.html). Si mañana
# se agrega un país que no está acá, cae al slug con mayúsculas: el asistente lo
# encuentra igual, solo con un rótulo menos prolijo hasta que se lo agregue.
NOMBRE_PAIS = {
    "antigua-y-barbuda": "Antigua y Barbuda", "argentina": "Argentina", "bahamas": "Bahamas",
    "barbados": "Barbados", "belice": "Belice", "bolivia": "Bolivia", "brasil": "Brasil",
    "chile": "Chile", "colombia": "Colombia", "costa-rica": "Costa Rica", "cuba": "Cuba",
    "dominica": "Dominica", "ecuador": "Ecuador", "el-salvador": "El Salvador", "granada": "Granada",
    "guatemala": "Guatemala", "guyana": "Guyana", "haiti": "Haití", "honduras": "Honduras",
    "jamaica": "Jamaica", "mexico": "México", "nicaragua": "Nicaragua", "panama": "Panamá",
    "paraguay": "Paraguay", "peru": "Perú", "republica-dominicana": "República Dominicana",
    "san-cristobal-y-nieves": "San Cristóbal y Nieves",
    "san-vicente-y-las-granadinas": "San Vicente y las Granadinas",
    "santa-lucia": "Santa Lucía", "surinam": "Surinam", "trinidad-y-tobago": "Trinidad y Tobago",
    "uruguay": "Uruguay", "venezuela": "Venezuela",
}

# Los ejes que van como accesos rápidos (chips) en el asistente. El resto de los
# temas (Situación, Fuentes) igual entra al buscador, solo no tiene chip propio.
EJES_ORDEN = ["Seguridad", "Gobernanza", "Desarrollo", "Defensa"]

HERRAMIENTAS = [
    {"archivo": "opacidad.html", "rotulo": "Índice de opacidad",
     "s": "opacidad ranking transparencia puntaje que publica el estado"},
    {"archivo": "mapa.html", "rotulo": "Mapa de opacidad",
     "s": "mapa opacidad region colores"},
    {"archivo": "tendencias.html", "rotulo": "Tendencias y reloj",
     "s": "tendencia evolucion en el tiempo reloj actualidad al dia"},
    {"archivo": "subnacional.html", "rotulo": "Datos subnacionales",
     "s": "subnacional provincia departamento estado municipio unidad territorio mapa por unidad"},
]

FAQ = [
    {"q": "de donde salen los datos fuente fuentes",
     "r": "Cada cifra viene de una fuente oficial o de un organismo internacional, con su fecha y su "
          "calificación de fiabilidad a la vista. Ninguna se inventa: si no se encontró, se dice."},
    {"q": "es gratis precio pagar cuesta registro suscripcion",
     "r": "Sí. El acceso a SIWA es libre y completo, sin registro y sin costo."},
    {"q": "como se mide la opacidad que es la opacidad",
     "r": "El Índice de Opacidad mide actos observables —qué publica cada Estado y qué no—, no "
          "opiniones. 0 = transparente, 100 = opaco."},
    {"q": "que es siwa que es esto para que sirve",
     "r": "SIWA es el reporte de situación de los 33 Estados de América Latina y el Caribe: los "
          "mismos temas con la misma vara, cada dato con su fuente, su fecha y lo que no cubre."},
    {"q": "cada cuanto se actualiza al dia fresco",
     "r": "Se actualiza solo, de forma continua: un robot revisa las fuentes y publica lo nuevo. "
          "Arriba de cada página, «X/X al día» dice cuántas fuentes están al día."},
]


def paises() -> list:
    """Los 33 países, por el slug de su página (sitio/pais/<slug>.html)."""
    salida = []
    carpeta = RAIZ / "sitio" / "pais"
    for f in sorted(carpeta.glob("*.html")):
        slug = f.stem
        salida.append({"slug": slug, "rotulo": NOMBRE_PAIS.get(slug, slug.replace("-", " ").title())})
    return salida


def temas_del_registro() -> list:
    """Le pregunta los temas al propio índice, con el navegador de prueba."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:  # noqa: BLE001
        print("[guia] falta playwright: pip install playwright && playwright install chromium",
              file=sys.stderr)
        sys.exit(2)

    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        pagina = navegador.new_page()
        try:
            pagina.goto(f"{BASE}/sitio/index.html?nivel=3", wait_until="load")
            pagina.wait_for_function(
                "() => document.querySelectorAll('#tema-principal option').length > 3",
                timeout=45000)
        except Exception as e:  # noqa: BLE001
            print(f"[guia] no se pudo abrir el registro: {type(e).__name__}. "
                  "¿Está corriendo el servidor?", file=sys.stderr)
            navegador.close()
            sys.exit(2)
        temas = pagina.evaluate(
            """() => [...document.querySelectorAll('#tema-principal option')]
                     .map(o => ({slug: o.value, rotulo: o.text.trim(),
                                 eje: (o.parentElement.label || '').trim()}))
                     .filter(x => x.slug)""")
        navegador.close()
    return temas


def main() -> int:
    temas = temas_del_registro()
    if len(temas) < 50:
        # Sospechoso: el índice trae 200 y pico. Si vinieron cuatro, algo salió
        # mal y es mejor no pisar el catálogo bueno con uno mutilado.
        print(f"[guia] solo {len(temas)} temas; no se reescribe el catálogo.", file=sys.stderr)
        return 2

    catalogo = {
        "generado_nota": "Catálogo del asistente Guía SIWA. Temas tomados del selector "
                         "del índice (#tema-principal), como las tarjetas por tema.",
        "ejes_orden": EJES_ORDEN,
        "temas": temas,
        "paises": paises(),
        "herramientas": HERRAMIENTAS,
        "faq": FAQ,
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(catalogo, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
    print(f"[guia] catálogo escrito: {len(temas)} temas, {len(catalogo['paises'])} países, "
          f"{len(HERRAMIENTAS)} herramientas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
