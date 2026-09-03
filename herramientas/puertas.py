"""Las cuarenta puertas: una entrada propia por región, zona y Estado.

POR QUÉ EXISTE
--------------
SIWA es una página que sirve a los 33 Estados y a las 6 zonas cambiando lo que
muestra. Para el lector funciona; **para un buscador es un solo documento**, y el
ciudadano que escribe «homicidios Paraguay» no llega nunca.

La solución no es partir el registro en cuarenta. Es darle **cuarenta entradas al
mismo registro**: una página propia por ámbito, con su dirección, su rótulo y su
tarjeta social, que lleva los hechos de ese ámbito y manda al registro completo.

POR QUÉ LA PUERTA TIENE CONTENIDO Y NO ES UN REDIRECTOR
-------------------------------------------------------
Una puerta que solo redirige no sirve para nada de lo que se busca: el buscador
indexa el destino y no la puerta, y quien tenga el navegador sin JavaScript no ve
nada. **La puerta lleva hechos reales, escritos acá, sin ejecutar nada.** El
registro completo queda a un enlace.

DE DÓNDE SALE CADA HECHO
------------------------
De los archivos que el robot ya escribió. **Esta herramienta no calcula nada
nuevo**: si tuviera que recalcular el compuesto habría dos implementaciones de la
misma regla, que es exactamente la duplicación que este registro ya pagó dos
veces. Lo que no está en los datos, no va en la puerta: va el enlace al registro,
que sí lo calcula.
"""

from __future__ import annotations

import html
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos" / "publico"
SITIO = RAIZ / "sitio"
BASE = "https://fundacion-sherman-kent.github.io/siwa"

sys.path.insert(0, str(RAIZ / "colectores"))
import geo  # noqa: E402


def esc(t) -> str:
    return html.escape(str(t if t is not None else ""), quote=True)


def sello(t: str) -> str:
    """Nombre de archivo a partir de un nombre propio, sin tildes ni eñes."""
    t = unicodedata.normalize("NFKD", str(t))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t


def leer(nombre: str) -> dict:
    ruta = DATOS / nombre
    if not ruta.exists():
        return {}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — una puerta sin un dato es mejor que ninguna
        return {}


def porIso(d: dict) -> dict:
    return {r["iso"]: r for r in d.get("registros", []) if isinstance(r, dict) and r.get("iso")}


# Los cuatro indicadores que la casa declaró como titular de cada eje. Se toman
# tal cual del dato; NO se recalcula el compuesto.
TITULARES = [
    ("homicidios", "Seguridad"),
    ("estado_derecho", "Gobernanza"),
    ("pobreza", "Desarrollo"),
    ("gasto_militar", "Defensa"),
]

ESTILO = """
:root{
  --navy:#00121E;--naranja:#FB6500;--violeta:#8C00E0;
  --papel:#F2EFE8;--papel-2:#E8E4DA;--tinta:#00121E;--tinta-2:#4A5A66;
  --tinta-3:#77848D;--filete:#D6D0C4;--caja:#FBF9F5;--verde:#2E7D6E;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --papel:#00121E;--papel-2:#031C2B;--tinta:#F4F2EC;--tinta-2:#A9B8C4;
  --tinta-3:#7D90A0;--filete:#123044;--caja:#04202F;--verde:#4FB8A4;}}
:root[data-theme="dark"]{
  --papel:#00121E;--papel-2:#031C2B;--tinta:#F4F2EC;--tinta-2:#A9B8C4;
  --tinta-3:#7D90A0;--filete:#123044;--caja:#04202F;--verde:#4FB8A4;}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);
  font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:16px;line-height:1.62;-webkit-font-smoothing:antialiased}
.banda{background:var(--navy);border-bottom:3px solid var(--naranja)}
.banda .dentro{max-width:880px;margin:0 auto;padding:16px 24px;display:flex;
  flex-wrap:wrap;gap:12px;justify-content:space-between;align-items:baseline}
.banda a{color:#F4F2EC;text-decoration:none;font-size:11px;font-weight:700;
  letter-spacing:.16em;text-transform:uppercase}
.banda a span{color:var(--naranja)}
.banda .vuelta{color:#7D90A0;font-weight:500;letter-spacing:.08em}
main{max-width:880px;margin:0 auto;padding:34px 24px 76px}
h1{font-size:clamp(28px,5vw,44px);line-height:1.08;letter-spacing:-.025em;
  font-weight:800;margin:0 0 6px;text-wrap:balance}
.zona{font-size:11px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--naranja);font-weight:700;margin:0 0 16px}
.bajada{font-size:17px;color:var(--tinta-2);margin:0 0 26px;max-width:62ch}
h2{font-size:11.5px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;
  color:var(--naranja);margin:34px 0 12px}
.rejilla{display:grid;grid-template-columns:repeat(auto-fit,minmax(196px,1fr));
  gap:1px;background:var(--filete);border:1px solid var(--filete)}
.rejilla div{background:var(--caja);padding:13px 15px}
.rejilla .q{font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;
  color:var(--tinta-3);display:block;margin-bottom:3px}
.rejilla .v{font-size:21px;font-weight:700;letter-spacing:-.02em;display:block;
  line-height:1.2;font-variant-numeric:tabular-nums}
.rejilla .c{font-size:12px;color:var(--tinta-2);display:block;margin-top:3px}
.filas{border:1px solid var(--filete);background:var(--caja)}
.filas div{padding:12px 15px;border-bottom:1px solid var(--filete);
  display:grid;grid-template-columns:minmax(150px,1fr) 2fr;gap:14px}
.filas div:last-child{border-bottom:none}
.filas b{font-weight:600;font-size:14px}
.filas span{font-size:14px;color:var(--tinta-2)}
.filas i{font-style:normal;color:var(--tinta-3);font-size:12.5px;display:block}
.ir{display:inline-block;margin:22px 0 0;background:var(--naranja);color:#fff;
  text-decoration:none;font-weight:600;font-size:15px;padding:12px 20px}
.ir:hover{background:#d95900}
.vecinos{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px}
.vecinos a{font-size:13px;text-decoration:none;color:var(--tinta-2);
  border:1px solid var(--filete);padding:5px 11px;border-radius:999px}
.vecinos a:hover{border-color:var(--naranja);color:var(--tinta)}
.pie{margin-top:40px;padding-top:18px;border-top:3px solid var(--naranja);
  font-size:12.5px;color:var(--tinta-2);max-width:64ch}
.pie b{color:var(--tinta)}
@media (max-width:560px){.filas div{grid-template-columns:1fr;gap:3px}
  main,.banda .dentro{padding-left:17px;padding-right:17px}}
"""


def cabeza(titulo: str, descripcion: str, ruta: str, ld: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="es-AR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)}</title>
<meta name="description" content="{esc(descripcion)}">
<link rel="canonical" href="{BASE}/{ruta}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(titulo)}">
<meta property="og:description" content="{esc(descripcion)}">
<meta property="og:url" content="{BASE}/{ruta}">
<meta property="og:image" content="{BASE}/sitio/tarjeta.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(titulo)}">
<meta name="twitter:description" content="{esc(descripcion)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{ESTILO}</style>
</head>
<body>
<div class="banda"><div class="dentro">
  <a href="{BASE}/sitio/index.html">SIWA · <span>Fundación Sherman Kent</span></a>
  <a class="vuelta" href="{BASE}/sitio/index.html">Registro completo →</a>
</div></div>
<main>
"""


def pie(cuando: str) -> str:
    return f"""
<div class="pie">
  <p><b>Esta página es una entrada al registro, no un resumen de opinión.</b> Cada
     cifra sale del archivo que el robot recolectó, con su fuente y su fecha; el
     ordenamiento dentro de la región, las proyecciones y los vacíos declarados
     viven en el registro completo, que se calcula al abrirlo.</p>
  <p><b>Acceso libre y gratuito.</b> Citar como «SIWA, Fundación Sherman Kent».
     Página generada el {esc(cuando)} desde el padrón de los 33 Estados.</p>
</div>
</main>
</body>
</html>
"""


def fila(rot: str, valor: str, nota: str = "") -> str:
    return (f'<div><b>{esc(rot)}</b><span>{valor}'
            + (f'<i>{esc(nota)}</i>' if nota else "") + "</span></div>")


def construir():
    padron = geo.padron()
    op = porIso(leer("opacidad.json"))
    ar = porIso(leer("archivo.json"))
    co = porIso(leer("contratacion.json"))
    re_ = porIso(leer("reciente_oficial.json"))
    cop = porIso(leer("copernicus.json"))
    cib = porIso(leer("ciber.json"))
    mem = leer("memoria.json")
    desde = mem.get("desde", {})
    materias = mem.get("materias", {})

    # Los indicadores titulares, de donde estén.
    titular = {}
    for nombre in ("banco-mundial.json", "owd.json", "onu-ods.json", "bti.json"):
        d = leer(nombre)
        meta = {i["clave"]: i for i in d.get("indicadores", [])}
        for r in d.get("registros", []):
            for clave, _eje in TITULARES:
                c = (r.get("indicadores") or {}).get(clave)
                if c and c.get("valor") is not None:
                    titular.setdefault(r["iso"], {})[clave] = {
                        "valor": c["valor"], "anio": c.get("anio"),
                        "rotulo": meta.get(clave, {}).get("rotulo", clave),
                        "unidad": meta.get(clave, {}).get("unidad", ""),
                    }

    cuando = datetime.now(timezone.utc).date().isoformat()
    (SITIO / "pais").mkdir(parents=True, exist_ok=True)
    (SITIO / "zona").mkdir(parents=True, exist_ok=True)

    porZona: dict[str, list] = {}
    for p in padron:
        porZona.setdefault(p["bloque"], []).append(p)

    direcciones = []

    # ── Puertas de Estado ────────────────────────────────────────────────────
    for p in padron:
        iso, nombre, zona = p["iso"], p["pais"], p["bloque"]
        s = sello(nombre)
        ruta = f"sitio/pais/{s}.html"

        cifras = []
        for clave, eje in TITULARES:
            t = (titular.get(iso) or {}).get(clave)
            if not t:
                continue
            v = t["valor"]
            v = f"{v:,.1f}".replace(",", ".") if isinstance(v, float) else f"{v:,}".replace(",", ".")
            cifras.append(
                f'<div><span class="q">{esc(eje)}</span>'
                f'<span class="v">{esc(v)}</span>'
                f'<span class="c">{esc(t["rotulo"])}'
                + (f' · {t["anio"]}' if t.get("anio") else "") + "</span></div>")

        hechos = []
        o = op.get(iso)
        if o:
            hechos.append(fila("Acceso a la información",
                               esc((materias.get("opacidad", {}).get("significa") or {})
                                   .get(o["estado"], o["estado"])),
                               "«Sin verificar» no es «opaco»: es que la Oficina todavía "
                               "no revisó los cuatro pasos." if o["estado"] == "sin_verificar" else ""))
        a = ar.get(iso)
        if a and a.get("sitios"):
            si = a["sitios"][0]
            d = (desde.get("archivo") or {}).get(iso) or {}
            hechos.append(fila(
                "Sitio oficial",
                f'{esc(si.get("organismo") or si.get("dominio"))} — '
                f'<b>{esc((materias.get("archivo", {}).get("significa") or {}).get(si["estado"], si["estado"]))}</b>',
                (f'Así desde el {d["desde"]}'
                 + (" — desde que lo miramos, no desde que está así"
                    if d.get("solo_desde_que_miramos") else "")) if d.get("desde") else ""))
        c = co.get(iso)
        if c:
            hechos.append(fila(
                "Compras públicas",
                f'<b>{c["publicadores"]}</b> publicador' + ("" if c["publicadores"] == 1 else "es")
                + " en formato comparable" if c["publicadores"] else
                "<b>Sin publicador</b> en formato comparable",
                "No prueba que no publique: prueba que no publica en el formato que "
                "permite compararlo." if not c["publicadores"] else ""))
        r = re_.get(iso)
        if r and r.get("conjuntos"):
            k = r["conjuntos"][0]
            hechos.append(fila("Lo último que publicó de sí mismo",
                               f'<a href="{esc(k["enlace"])}">{esc(k["titulo"][:70])}</a>',
                               f'{k.get("organismo","")} · actualizado {k.get("actualizado","")}'))
        cp = cop.get(iso)
        if cp and cp.get("escenas"):
            dd = cp.get("dias_desde_la_ultima")
            hechos.append(fila("Imagen satelital libre",
                               f'<b>{cp["escenas"]:,}</b>'.replace(",", ".") + " escenas en 15 días",
                               f'La última, {"de hoy" if dd == 0 else "de ayer" if dd == 1 else f"hace {dd} días"}'
                               if dd is not None else ""))
        cb = cib.get(iso)
        if cb and cb.get("mediciones"):
            hechos.append(fila("Medición de red",
                               f'<b>{cb["anomalias_pct"]} %</b> de anomalías · '
                               f'{cb["bloqueos_confirmados"]} bloqueo'
                               + ("" if cb["bloqueos_confirmados"] == 1 else "s") + " confirmado"
                               + ("" if cb["bloqueos_confirmados"] == 1 else "s"),
                               "La muestra la hacen voluntarios: no ordena Estados."))

        vecinos = "".join(
            f'<a href="{BASE}/sitio/pais/{sello(x["pais"])}.html">{esc(x["pais"])}</a>'
            for x in porZona[zona] if x["iso"] != iso)

        titulo = f"{nombre} — SIWA, reporte de situación"
        desc = (f"Qué publica {nombre} y qué no: acceso a la información, compras públicas, "
                f"sitio oficial y cifras comparables con su fuente y su fecha. "
                f"Registro público y gratuito de la Fundación Sherman Kent.")
        ld = {"@context": "https://schema.org", "@type": "Dataset",
              "name": f"SIWA — {nombre}", "description": desc,
              "url": f"{BASE}/{ruta}", "isAccessibleForFree": True,
              "spatialCoverage": {"@type": "Country", "name": nombre},
              "creator": {"@type": "Organization", "name": "Fundación Sherman Kent"},
              "isPartOf": {"@type": "Dataset", "name": "SIWA", "url": f"{BASE}/sitio/index.html"}}

        cuerpo = cabeza(titulo, desc, ruta, ld)
        cuerpo += f'<h1>{esc(nombre)}</h1>\n<p class="zona">{esc(zona)}</p>\n'
        cuerpo += ('<p class="bajada">Lo que este Estado publica de sí mismo, lo que no '
                   'publica, y las cifras comparables con las que entra al registro '
                   'regional. Cada una con su fuente y su fecha.</p>\n')
        if cifras:
            cuerpo += "<h2>Cifra por eje</h2>\n<div class=\"rejilla\">" + "".join(cifras) + "</div>\n"
        if hechos:
            cuerpo += "<h2>Qué publica y qué no</h2>\n<div class=\"filas\">" + "".join(hechos) + "</div>\n"
        cuerpo += (f'<a class="ir" href="{BASE}/sitio/index.html?pais={iso}">'
                   f'Ver el registro completo de {esc(nombre)} →</a>\n')
        cuerpo += (f'<h2>Su zona</h2>\n<p><a href="{BASE}/sitio/zona/{sello(zona)}.html">'
                   f'{esc(zona)}</a> — los otros Estados con los que se lo compara:</p>'
                   f'<div class="vecinos">{vecinos}</div>\n')
        cuerpo += pie(cuando)
        (SITIO / "pais" / f"{s}.html").write_text(cuerpo, encoding="utf-8")
        direcciones.append(ruta)

    # ── Puertas de zona ──────────────────────────────────────────────────────
    for zona, estados in sorted(porZona.items()):
        s = sello(zona)
        ruta = f"sitio/zona/{s}.html"
        isos = [x["iso"] for x in estados]

        cuenta = {"publicado": 0, "parcial": 0, "sin_verificar": 0}
        for i in isos:
            e = (op.get(i) or {}).get("estado")
            if e in cuenta:
                cuenta[e] += 1
        conPub = sum(1 for i in isos if (co.get(i) or {}).get("publicadores"))
        retirados = [i for i in isos if (ar.get(i) or {}).get("estado") == "retirado"]

        titulo = f"{zona} — SIWA, reporte de situación"
        desc = (f"Los {len(estados)} Estados de {zona}: qué publican y qué no, con su fuente "
                f"y su fecha. Registro público y gratuito de la Fundación Sherman Kent.")
        ld = {"@context": "https://schema.org", "@type": "Dataset",
              "name": f"SIWA — {zona}", "description": desc, "url": f"{BASE}/{ruta}",
              "isAccessibleForFree": True,
              "creator": {"@type": "Organization", "name": "Fundación Sherman Kent"},
              "isPartOf": {"@type": "Dataset", "name": "SIWA", "url": f"{BASE}/sitio/index.html"}}

        cuerpo = cabeza(titulo, desc, ruta, ld)
        cuerpo += f'<h1>{esc(zona)}</h1>\n<p class="zona">{len(estados)} Estados</p>\n'
        cuerpo += ('<p class="bajada">Una zona del padrón de los 33. Acá se cuenta qué '
                   'publica cada uno de sus Estados y qué no — la ausencia también es dato, '
                   'y se declara.</p>\n')
        cuerpo += ("<h2>Qué publica la zona</h2>\n<div class=\"rejilla\">"
                   f'<div><span class="q">Publican el consolidado</span>'
                   f'<span class="v">{cuenta["publicado"]}<span style="font-size:13px;font-weight:400"> de {len(estados)}</span></span>'
                   f'<span class="c">acceso a la información</span></div>'
                   f'<div><span class="q">Sin verificar</span>'
                   f'<span class="v">{cuenta["sin_verificar"]}</span>'
                   f'<span class="c">no es lo mismo que opaco</span></div>'
                   f'<div><span class="q">Publican sus compras</span>'
                   f'<span class="v">{conPub}<span style="font-size:13px;font-weight:400"> de {len(estados)}</span></span>'
                   f'<span class="c">en formato comparable</span></div>'
                   f'<div><span class="q">Sitios retirados</span>'
                   f'<span class="v">{len(retirados)}</span>'
                   f'<span class="c">publicaban y dejaron de hacerlo</span></div>'
                   "</div>\n")
        cuerpo += ('<h2>Sus Estados</h2>\n<div class="vecinos">' + "".join(
            f'<a href="{BASE}/sitio/pais/{sello(x["pais"])}.html">{esc(x["pais"])}</a>'
            for x in estados) + "</div>\n")
        cuerpo += (f'<a class="ir" href="{BASE}/sitio/index.html?zona={esc(zona)}">'
                   f'Ver el registro completo de {esc(zona)} →</a>\n')
        cuerpo += pie(cuando)
        (SITIO / "zona" / f"{s}.html").write_text(cuerpo, encoding="utf-8")
        direcciones.append(ruta)

    # ── El mapa del sitio, con las cuarenta ──────────────────────────────────
    urls = ["sitio/index.html", "index.html"] + direcciones
    mapa = ['<?xml version="1.0" encoding="UTF-8"?>',
            "<!--", "  Mapa del sitio de SIWA. Se GENERA con herramientas/puertas.py:",
            "  escribirlo a mano lo deja viejo, y ya pasó una vez.", "-->",
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        pri = "1.0" if u.startswith("sitio/index") else ("0.8" if "/zona/" in u else "0.7")
        mapa += ["  <url>", f"    <loc>{BASE}/{u}</loc>",
                 f"    <lastmod>{cuando}</lastmod>",
                 "    <changefreq>daily</changefreq>",
                 f"    <priority>{pri}</priority>", "  </url>"]
    mapa.append("</urlset>")
    (RAIZ / "sitemap.xml").write_text("\n".join(mapa) + "\n", encoding="utf-8")

    print(f"[puertas] {len(padron)} Estados + {len(porZona)} zonas = "
          f"{len(direcciones)} puertas · mapa del sitio con {len(urls)} direcciones")
    return len(direcciones)


if __name__ == "__main__":
    construir()
