# -*- coding: utf-8 -*-
"""El índice de datos: el catálogo del registro, para una máquina y para una persona.

POR QUÉ EXISTE
--------------
Los archivos del registro ya son públicos y ya se sirven con las cabeceras que
permiten leerlos desde cualquier otro sitio —comprobado: `Access-Control-Allow-
Origin: *`, `application/json`, `max-age=600`—. Lo que faltaba era **decirlo**:
quien quisiera construir encima de SIWA tenía que adivinar qué archivos hay, qué
trae cada uno y si mañana van a seguir estando.

Esta herramienta escribe las dos declaraciones, del mismo recorrido:

  · `datos/publico/indice.json` — el catálogo que lee una máquina.
  · `datos/index.html` — la misma cosa explicada, para quien la abre a mano.

Se regeneran en cada corrida del robot, así que no pueden quedar viejas. Y NO se
escriben a mano por separado: el catálogo y su explicación salen del mismo
recorrido de archivos, que es la única forma de que digan lo mismo.

LO QUE SE PROMETE, Y LO QUE NO
------------------------------
Se promete que las direcciones no cambian y que la forma del bloque de
procedencia se mantiene: quien lea `procedencia.fuente.nombre` hoy va a poder
leerlo dentro de un año. No se promete que un indicador viva para siempre: si
una fuente cierra, el indicador desaparece y el índice lo va a decir con su
ausencia. Prometer lo contrario sería prometer sobre algo que no manejamos.
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PUBLICO = RAIZ / "datos" / "publico"
SALIDA = PUBLICO / "indice.json"
PAGINA = RAIZ / "datos" / "index.html"

sys.path.insert(0, str(RAIZ / "herramientas"))
import puertas  # noqa: E402  — el estilo y la cabecera de la casa viven ahí

BASE = puertas.BASE
esc = puertas.esc
DIR_DATOS = f"{BASE}/datos/publico"


# ---------------------------------------------------------------- el catálogo
def recorrer() -> list:
    """Un renglón por archivo publicado, leído del archivo mismo."""
    conjuntos = []
    for ruta in sorted(PUBLICO.glob("*.json")):
        if ruta.name == "indice.json":
            continue
        try:
            d = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 — un archivo ilegible se declara, no se calla
            conjuntos.append({"archivo": ruta.name, "estado": "ilegible",
                              "detalle": str(e)[:120]})
            continue
        if not isinstance(d, dict):
            continue
        proc = d.get("procedencia") or {}
        fuente = proc.get("fuente") or {}
        cal = proc.get("calificacion") or {}
        registros = d.get("registros")
        indicadores = d.get("indicadores") or d.get("catalogo") or []
        # LA FORMA DE LA FILA NO ES LA MISMA EN TODOS. Medido: los 45 archivos
        # traen «procedencia» y «registros», 41 identifican la fila por «iso» y
        # apenas seis publican un diccionario de indicadores; el resto pone sus
        # valores como campos propios. Declararlo acá le ahorra a quien consume
        # tener que abrir cada archivo para descubrirlo.
        campos: list = []
        if isinstance(registros, list):
            for fila in registros[:40]:
                if isinstance(fila, dict):
                    for k in fila:
                        if k not in campos:
                            campos.append(k)
        conjuntos.append({
            "archivo": ruta.name,
            "url": f"{DIR_DATOS}/{ruta.name}",
            "colector": proc.get("colector"),
            "fuente": fuente.get("nombre"),
            "url_fuente": fuente.get("url"),
            "calificacion": (f"{cal.get('fiabilidad')}-{cal.get('credibilidad')}"
                             if cal.get("fiabilidad") else None),
            "obtenido_en": proc.get("obtenido_en"),
            "registros": len(registros) if isinstance(registros, list) else None,
            "indicadores": (len(indicadores) or None) if isinstance(indicadores, list) else None,
            "por_estado": "iso" in campos,
            "campos_de_la_fila": campos,
            "vacios_declarados": len(proc.get("vacios_declarados") or []),
            "restriccion_de_uso": proc.get("restriccion_de_uso"),
            "bytes": ruta.stat().st_size,
        })
    return conjuntos


def catalogo(conjuntos: list) -> dict:
    return {
        "registro": "SIWA — Reporte de situación de América Latina y el Caribe",
        "de": "Fundación Sherman Kent, Oficina de Generación de Inteligencia",
        "sitio": BASE,
        "documentacion": f"{BASE}/datos/",
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "como_usarlo": (
            "Cada conjunto se descarga de su «url» y responde JSON con cabeceras abiertas: "
            "se puede leer desde cualquier sitio, sin credencial y sin registrarse. Todos "
            "traen el mismo bloque «procedencia» —fuente, url, calificación de Almirantazgo, "
            "fecha y vacíos declarados— y una lista «registros». Los campos de valor NO son "
            "los mismos en todos los conjuntos: cada uno declara acá los suyos en "
            "«campos_de_la_fila», y «por_estado» dice si la fila es un Estado identificado "
            "por su código ISO de tres letras."),
        "condicion": (
            "Uso libre citando a la Fundación Sherman Kent y a la fuente original de cada "
            "dato, que viaja en el propio archivo. Los conjuntos con «restriccion_de_uso» "
            "llevan además la condición de su fuente, y esa condición manda."),
        "estabilidad": (
            "Las direcciones no cambian y la forma del bloque de procedencia se mantiene. "
            "NO se promete que un indicador viva para siempre: si una fuente cierra, el "
            "indicador desaparece y este índice lo dirá con su ausencia."),
        "padron": f"{BASE}/sitio/geo/paises-alc.geojson",
        "novedades": f"{BASE}/novedades.xml",
        "conjuntos": conjuntos,
        "cuantos": len(conjuntos),
    }


# ------------------------------------------------------------------ la página
EXTRA = """
.tabla{width:100%;border-collapse:collapse;font-size:13.5px;
  border:1px solid var(--filete);background:var(--caja)}
.tabla th{text-align:left;font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--tinta-3);font-weight:700;padding:9px 11px;border-bottom:1px solid var(--filete)}
.tabla td{padding:9px 11px;border-bottom:1px solid var(--filete);vertical-align:top}
.tabla tr:last-child td{border-bottom:none}
.tabla a{color:var(--tinta);text-decoration:none;border-bottom:1px solid var(--naranja)}
.tabla .n{text-align:right;font-variant-numeric:tabular-nums;color:var(--tinta-2);
  white-space:nowrap}
.tabla .f{color:var(--tinta-2);font-size:12.5px}
.cal{font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
.marca{display:inline-block;background:var(--violeta);color:#fff;font-size:10px;
  font-weight:700;letter-spacing:.05em;padding:1px 6px;border-radius:3px;margin-left:6px;
  vertical-align:1px}
.rueda{overflow-x:auto;-webkit-overflow-scrolling:touch}
pre{background:var(--caja);border:1px solid var(--filete);border-left:3px solid var(--naranja);
  padding:13px 15px;overflow-x:auto;font-size:13px;line-height:1.55;margin:0 0 16px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.92em}
p code{background:var(--caja);border:1px solid var(--filete);padding:1px 5px}
.dice{border-left:3px solid var(--naranja);padding-left:14px;max-width:64ch}
.dice p{margin:0 0 10px}
a.enlace{color:var(--tinta);border-bottom:1px solid var(--naranja);text-decoration:none}
"""

EJEMPLO = """fetch('https://siwa.fundacionkent.org/datos/publico/indice.json')
  .then(r =&gt; r.json())
  .then(indice =&gt; {
    // el catalogo dice que hay: direccion, fuente, fecha y forma de la fila
    const c = indice.conjuntos.find(x =&gt; x.archivo === 'oms_homicidios.json');
    console.log(c.campos_de_la_fila);   // ['iso','pais','bloque','estado','tasa','serie',...]
    return fetch(c.url).then(r =&gt; r.json());
  })
  .then(d =&gt; {
    console.log(d.procedencia.fuente.nombre);   // de donde sale
    console.log(d.procedencia.obtenido_en);     // de cuando es
    d.registros.forEach(r =&gt; console.log(r.iso, r.tasa));
  });"""


def _cuando(iso) -> str:
    return (iso or "")[:10] or "—"


def _peso(b) -> str:
    if not b:
        return "—"
    return f"{b/1024:.0f} kB" if b < 1024 * 1024 else f"{b/1048576:.1f} MB"


def pagina(indice: dict) -> str:
    conjuntos = [c for c in indice["conjuntos"] if c.get("url")]
    con_restriccion = [c for c in conjuntos if c.get("restriccion_de_uso")]
    filas = ""
    for c in sorted(conjuntos, key=lambda x: (x.get("fuente") or "").lower()):
        marca = '<span class="marca">condición</span>' if c.get("restriccion_de_uso") else ""
        fuente = esc(c.get("fuente") or "—")
        if c.get("url_fuente"):
            fuente = f'<a class="enlace" href="{esc(c["url_fuente"])}" rel="noopener">{fuente}</a>'
        cuenta = c.get("indicadores")
        filas += (
            "<tr>"
            f'<td><a href="{esc(c["url"])}">{esc(c["archivo"])}</a>{marca}</td>'
            f'<td class="f">{fuente}</td>'
            f'<td class="cal">{esc(c.get("calificacion") or "—")}</td>'
            f'<td class="n">{c.get("registros") or "—"}</td>'
            f'<td class="n">{cuenta or "—"}</td>'
            f'<td class="n">{_cuando(c.get("obtenido_en"))}</td>'
            f'<td class="n">{_peso(c.get("bytes"))}</td>'
            "</tr>")

    titulo = "Los datos de SIWA, abiertos y documentados"
    descripcion = (f"Los {len(conjuntos)} conjuntos del registro de América Latina y el Caribe, "
                   "en JSON, sin credencial y sin registrarse: dirección, fuente, calificación "
                   "y fecha de cada uno.")
    ld = {
        "@context": "https://schema.org",
        "@type": "DataCatalog",
        "name": "SIWA — datos abiertos del registro de América Latina y el Caribe",
        "description": descripcion,
        "url": f"{BASE}/datos/",
        "publisher": {"@type": "Organization", "name": "Fundación Sherman Kent",
                      "url": "https://fundacionkent.org"},
        "isAccessibleForFree": True,
        "dataset": [{"@type": "Dataset", "name": c.get("fuente") or c["archivo"],
                     "distribution": {"@type": "DataDownload", "contentUrl": c["url"],
                                      "encodingFormat": "application/json"}}
                    for c in conjuntos],
    }
    total = sum(c.get("registros") or 0 for c in conjuntos)
    indicadores = sum(c.get("indicadores") or 0 for c in conjuntos)
    por_estado = sum(1 for c in conjuntos if c.get("por_estado"))
    con_indicadores = sum(1 for c in conjuntos if c.get("indicadores"))

    cuerpo = f"""
<p class="zona">Interfaz pública de datos</p>
<h1>Los datos, abiertos y documentados</h1>
<p class="bajada">Todo lo que SIWA muestra está publicado en archivos JSON que
  cualquiera puede leer: sin credencial, sin registrarse, sin pedir permiso y sin
  límite de consultas. Esta página dice qué hay, dónde está y qué se promete de ello.</p>

<div class="rejilla">
  <div><span class="q">Conjuntos</span><span class="v">{len(conjuntos)}</span>
       <span class="c">un archivo por fuente</span></div>
  <div><span class="q">Filas publicadas</span><span class="v">{total}</span>
       <span class="c">{por_estado} conjuntos van por Estado</span></div>
  <div><span class="q">Indicadores descriptos</span><span class="v">{indicadores}</span>
       <span class="c">con su rótulo y su unidad</span></div>
  <div><span class="q">Se rehacen</span><span class="v">cada hora</span>
       <span class="c">y traen la fecha de su corrida</span></div>
</div>

<h2>Cómo se lee</h2>
<p>Cada conjunto se descarga de su dirección y responde JSON. Las cabeceras están
  abiertas —<code>Access-Control-Allow-Origin: *</code>—, así que se puede leer desde
  una página de otro dominio sin intermediario. El servidor pide que se guarde en
  memoria diez minutos (<code>max-age=600</code>): respetarlo alcanza y sobra, porque
  el robot recolecta una vez por hora.</p>
<pre><code>{EJEMPLO}</code></pre>
<p>Empezar por <a class="enlace" href="{DIR_DATOS}/indice.json">indice.json</a> evita
  escribir a mano cuarenta direcciones y hace que un conjunto nuevo aparezca solo.</p>

<h2>Qué trae adentro cada archivo</h2>
<p>Dos bloques están en los {len(conjuntos)}, sin excepción, y son los que conviene
  programar contra ellos:</p>
<div class="filas">
  <div><b>procedencia</b><span>De dónde sale y de cuándo es.<i>fuente.nombre, fuente.url,
    colector, obtenido_en, calificacion (Almirantazgo: letra de fiabilidad y número de
    credibilidad) y vacios_declarados.</i></span></div>
  <div><b>registros</b><span>La lista de filas. En {por_estado} de los
    {len(conjuntos)} conjuntos cada fila es un Estado y se identifica con <code>iso</code>,
    su código de tres letras.<i>Un Estado sin dato no aparece con cero: no aparece.</i></span></div>
</div>
<p style="margin-top:14px"><b>Los campos de valor no son los mismos en todos.</b> Un
  conjunto de homicidios trae <code>tasa</code> y <code>serie</code>; uno de indicadores
  comparables trae un diccionario <code>indicadores</code> —{con_indicadores} conjuntos lo
  traen—. En lugar de pedirle a quien consume que abra los {len(conjuntos)} archivos para
  averiguarlo, el catálogo lo declara: cada conjunto lleva
  <code>campos_de_la_fila</code> con los nombres que efectivamente aparecen, y
  <code>por_estado</code> para saber si la fila es un Estado.</p>
<p style="margin-top:14px">Además del registro: el
  <a class="enlace" href="{BASE}/sitio/geo/paises-alc.geojson">padrón de los 33 Estados en
  GeoJSON</a> y el <a class="enlace" href="{BASE}/novedades.xml">canal de novedades</a>,
  que anuncia qué cambió en cada corrida.</p>

<h2>Lo que se promete, y lo que no</h2>
<div class="dice">
  <p><b>Las direcciones no cambian.</b> Un archivo publicado conserva su nombre y su
     ubicación, y la forma del bloque de procedencia se mantiene: quien lea
     <code>procedencia.fuente.nombre</code> hoy va a poder leerlo dentro de un año.</p>
  <p><b>No se promete que un indicador viva para siempre.</b> Si una fuente cierra o deja
     de publicar, el indicador desaparece del archivo y este índice lo dice con su
     ausencia. Prometer lo contrario sería prometer sobre algo que no manejamos.</p>
  <p><b>Un dato viejo no se esconde ni se rellena.</b> Viaja con su año para que quien lo
     use decida si le sirve. Lo que falta se declara en <code>vacios_declarados</code>.</p>
</div>

<h2>Condición de uso</h2>
<p>Uso libre, citando a la <b>Fundación Sherman Kent</b> y a la fuente original de cada
  dato, que viaja en el propio archivo. SIWA no cobra por esto y no piensa cobrarlo.</p>
<p>{len(con_restriccion)} de los {len(conjuntos)} conjuntos llevan además una condición de
  su fuente, marcada abajo y escrita entera en el campo <code>restriccion_de_uso</code> del
  archivo: <b>esa condición manda sobre esta página</b>. Se resumen en que el dato no puede
  viajar a un producto pago sin tomar antes la licencia que corresponda.</p>

<h2>Los {len(conjuntos)} conjuntos</h2>
<div class="rueda"><table class="tabla">
  <thead><tr><th>Archivo</th><th>Fuente</th><th>Calif.</th><th>Estados</th>
    <th>Indic.</th><th>Recolectado</th><th>Peso</th></tr></thead>
  <tbody>{filas}</tbody>
</table></div>

<h2>Si construís algo con esto</h2>
<p>Escribinos y lo enlazamos desde el registro. También sirve el camino inverso: si tenés
  una serie de la región que no está acá, es material para sumar. El registro crece por
  donde alguien mira.</p>
<a class="ir" href="{BASE}/sitio/index.html">Ver el registro completo →</a>
"""
    # El pie de las puertas habla de «una entrada al registro», que acá no
    # corresponde: esta página no muestra hechos, declara cómo se accede a ellos.
    pie = f"""
<div class="pie">
  <p><b>Esta página se genera sola.</b> La escribe la misma herramienta que arma el
     catálogo, recorriendo los archivos publicados: no hay una lista escrita a mano que
     pueda quedar vieja. Si un conjunto aparece o desaparece, aparece o desaparece acá.</p>
  <p><b>Acceso libre y gratuito.</b> Citar como «SIWA, Fundación Sherman Kent», y a la
     fuente original de cada dato. Catálogo generado el {esc(indice["generado"][:10])} a
     partir de {len(conjuntos)} archivos.</p>
</div>
</main>
</body>
</html>
"""
    cabeza = puertas.cabeza(titulo, descripcion, "datos/", ld)
    cabeza = cabeza.replace("</head>", f"<style>{EXTRA}</style>\n</head>", 1)
    return cabeza + cuerpo + pie


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    indice = catalogo(recorrer())
    SALIDA.write_text(json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8",
                      newline="")
    PAGINA.write_text(pagina(indice), encoding="utf-8", newline="")
    print(f"[indice] {indice['cuantos']} conjuntos · {SALIDA.relative_to(RAIZ)} "
          f"y {PAGINA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
