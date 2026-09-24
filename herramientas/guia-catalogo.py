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

Las provincias/departamentos/estados (bloque "unidades", corrección del
24/9/2026) se leen directo de los MISMOS archivos de datos que alimenta
sitio/subnacional.html —su propia lista FUENTES—, sin navegador: es más rápido
y, si algún archivo falta o cambia de forma, el resto del catálogo (temas,
países, herramientas) sale igual.

QUÉ NO HACE. No inventa sinónimos ni respuestas: el asistente busca por el
rótulo real y por el slug. Los sinónimos finos y las respuestas frecuentes más
ricas los puede sumar después el robot con el modelo local; esto asegura, como
mínimo, que TODOS los temas vigentes estén siempre en el asistente.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
SALIDA = RAIZ / "sitio" / "_comun" / "guia-siwa.json"
DATOS_PUBLICO = RAIZ / "datos" / "publico"
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

# ---------------------------------------------------------------------------
# Unidades subnacionales (provincia/departamento/estado). Corrección del
# 24/9/2026: hasta hoy el catálogo del asistente no tenía NINGUNA, así que
# "córdoba", "jalisco" o "santa fe" (como provincia) no resolvían nada propio
# y la búsqueda caía sobre países o temas por casualidad de letras.
#
# LA MISMA LISTA de archivos que sitio/subnacional.html lee en su propio
# FUENTES (JS): si esa lista cambia allá, hay que actualizar esta también —
# es la fuente que el pedido señaló como "los mismos datos que alimentan
# subnacional.html". No se amplía a otros archivos "subnacional_*.json" del
# repositorio (hay varios con otro esquema, p. ej. el censo de cobertura o el
# índice de apertura) porque esos NO son los que arma la vista subnacional.
UNIDADES_ARCHIVOS = [
    "subnacional_homicidios.json", "subnacional_robos.json", "subnacional_acled.json",
    "subnacional_focos.json",
    "subnacional_colombia_incautacion_basuco.json",
    "subnacional_colombia_incautacion_cocaina.json",
    "subnacional_colombia_incautacion_marihuana.json",
    "subnacional_colombia_incautacion_base_coca.json",
    "subnacional_colombia_incautacion_insumos_liquidos.json",
    "subnacional_colombia_secuestro.json", "subnacional_colombia_extorsion.json",
    "subnacional_colombia_terrorismo.json",
    "pdh_guatemala_subnacional.json", "subnacional_viales.json",
]

# Unidades que NO son un territorio del mapa (categorías de la propia fuente):
# mismo criterio y mismos casos que GEO_SKIP en sitio/subnacional.html. Si se
# dejaran, el asistente ofrecería "llevarte a la unidad «Sin establecer»",
# que no existe en ningún mapa.
UNIDAD_SKIP = {
    "COL": {"sin establecer"},
    "URY": {"centros carcelarios"},
    "DOM": {"san cristonal"},
}

# Nombre lindo cuando el dato viene como sigla o código: mismo criterio que
# nombreUnidad() en sitio/subnacional.html.
BRA_NOM = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
    "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia", "RR": "Roraima",
    "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
    "TO": "Tocantins",
}
PER_COD = {
    "1": "Amazonas", "2": "Ancash", "3": "Apurimac", "4": "Arequipa", "5": "Ayacucho",
    "6": "Cajamarca", "7": "El Callao", "8": "Cusco", "9": "Huancavelica", "10": "Huanuco",
    "11": "Ica", "12": "Junin", "13": "La Libertad", "14": "Lambayeque", "16": "Loreto",
    "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura", "21": "Puno",
    "22": "San Martin", "23": "Tacna", "24": "Tumbes", "25": "Ucayali",
    "1501": "Municipalidad Metropolitana de Lima", "1599": "Lima",
}

# Palabras que no llevan mayúscula salvo que abran el nombre — solo para
# prolijar los nombres que la fuente entrega TODO EN MAYÚSCULAS (Colombia vía
# Socrata, algunos países en ACLED). No se toca el nombre si ya viene con
# mayúsculas y minúsculas mezcladas: eso es cosa de la fuente, no del catálogo.
_CONECTORES = {"de", "del", "la", "las", "los", "y", "en", "el"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def _bonito(nombre: str) -> str:
    if not nombre or nombre != nombre.upper() or nombre == nombre.lower():
        return nombre
    palabras = nombre.split(" ")
    return " ".join(
        w.lower() if i > 0 and w.lower() in _CONECTORES else w.capitalize()
        for i, w in enumerate(palabras)
    )


def unidades_subnacionales() -> list:
    """Provincias/departamentos/estados YA visibles en sitio/subnacional.html,
    leídos de sus mismos archivos de datos. Homónimos entre países (p. ej.
    Córdoba en Argentina y en Colombia) quedan como DOS entradas separadas: el
    asistente los muestra a los dos, nunca elige uno por su cuenta."""
    vistos: dict[tuple, dict] = {}
    for archivo in UNIDADES_ARCHIVOS:
        ruta = DATOS_PUBLICO / archivo
        if not ruta.exists():
            print(f"[guia] {archivo}: no existe, se saltea (no bloquea el resto)", file=sys.stderr)
            continue
        try:
            contenido = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"[guia] {archivo}: no se pudo leer ({e}), se saltea", file=sys.stderr)
            continue
        for reg in contenido.get("registros") or []:
            iso, pais = reg.get("iso"), reg.get("pais")
            if not iso or not pais:
                continue
            for u in reg.get("unidades") or []:
                crudo = u.get("nombre")
                if not crudo:
                    continue
                n = _norm(crudo)
                if n in UNIDAD_SKIP.get(iso, set()):
                    continue
                if iso == "BRA" and crudo in BRA_NOM:
                    nombre = BRA_NOM[crudo]
                elif iso == "PER" and crudo in PER_COD:
                    nombre = PER_COD[crudo]
                else:
                    nombre = _bonito(crudo)
                clave = (iso, _norm(nombre))
                vistos.setdefault(clave, {"nombre": nombre, "iso": iso, "pais": pais})
    return sorted(vistos.values(), key=lambda x: (x["pais"], x["nombre"]))


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

    unidades = unidades_subnacionales()
    if not unidades:
        # No bloquea (temas/países/herramientas son lo esencial), pero se avisa:
        # si esto da 0 con los archivos presentes, algo cambió de esquema.
        print("[guia] 0 unidades subnacionales; se publica igual sin ese bloque.", file=sys.stderr)

    catalogo = {
        "generado_nota": "Catálogo del asistente Guía SIWA. Temas tomados del selector "
                         "del índice (#tema-principal), como las tarjetas por tema; unidades "
                         "subnacionales tomadas de los mismos archivos que lee subnacional.html.",
        "ejes_orden": EJES_ORDEN,
        "temas": temas,
        "paises": paises(),
        "unidades": unidades,
        "herramientas": HERRAMIENTAS,
        "faq": FAQ,
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(catalogo, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
    print(f"[guia] catálogo escrito: {len(temas)} temas, {len(catalogo['paises'])} países, "
          f"{len(unidades)} unidades subnacionales, {len(HERRAMIENTAS)} herramientas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
