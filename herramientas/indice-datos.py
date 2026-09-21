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

import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PUBLICO = RAIZ / "datos" / "publico"
SALIDA = PUBLICO / "indice.json"
PAGINA = RAIZ / "datos" / "index.html"
CHECKSUMS = PUBLICO / "checksums.txt"

sys.path.insert(0, str(RAIZ / "herramientas"))
import puertas  # noqa: E402  — el estilo y la cabecera de la casa viven ahí

sys.path.insert(0, str(RAIZ / "colectores"))
import comun  # noqa: E402  — la lista de testigos, compartida con la auditoría
import geo  # noqa: E402  — el padrón de 33 Estados, la misma fuente que usa la auditoría

BASE = puertas.BASE
esc = puertas.esc
DIR_DATOS = f"{BASE}/datos/publico"

# Los archivos que NO son datos sino mediciones que esta casa hace de si misma.
# La lista vive en comun.py, que es de donde la toma tambien la auditoria: dos
# copias de la misma lista divergen el dia que aparece un testigo nuevo.
TESTIGOS = comun.TESTIGOS


# ---------------------------------------------------------------- el catálogo
def recorrer() -> list:
    """Un renglón por archivo publicado, leído del archivo mismo."""
    conjuntos = []
    for ruta in sorted(PUBLICO.glob("*.json")):
        # Los TESTIGOS DE CONTROL no son conjuntos de datos y no pueden entrar
        # al catálogo como si lo fueran: no tienen fuente ni calificación
        # porque no vienen de ninguna fuente —los produce esta casa
        # midiéndose a sí misma—. Se declaran aparte, en «controles».
        if ruta.name in TESTIGOS:
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
            "licencia": comun.ATRIBUCION["licencia"],
            "bytes": ruta.stat().st_size,
        })
    return conjuntos


# --------------------------------------------------------------- la integridad
def sellar() -> dict:
    """La huella SHA-256 de cada archivo publicado, para verificar integridad.

    Quien descarga un conjunto puede recalcular su huella y compararla con la de
    acá: si coincide, lo que recibió es exactamente lo que la casa publicó. Se
    escribe en el formato estándar de `sha256sum` —«huella  nombre»— para que
    cualquier herramienta común lo verifique sin código propio. NO se sella el
    propio índice ni este archivo de huellas, porque cambian después de esta
    corrida; sí los conjuntos de datos, que es lo que la gente descarga.
    """
    lineas, huellas = [], {}
    for ruta in sorted(PUBLICO.glob("*.json")):
        if ruta.name in ("indice.json",):
            continue
        h = hashlib.sha256(ruta.read_bytes()).hexdigest()
        huellas[ruta.name] = h
        lineas.append(f"{h}  {ruta.name}")
    CHECKSUMS.write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="")
    return huellas


# ------------------------------------------------------------------ los derechos
# El bloque de derechos, legible por máquina: quién es el titular, bajo qué
# licencia se publica el aporte de la casa, cómo se cita y qué pasa con el
# contenido de los datos. No es texto nuevo: es lo que ya dicen la página de
# licencia y el bloque ATRIBUCION de cada archivo, puesto donde una herramienta
# lo pueda leer sin adivinar.
def derechos() -> dict:
    return {
        "titular_del_aporte": comun.ATRIBUCION["autor"],
        "licencia": comun.ATRIBUCION["licencia"],
        "licencia_url": comun.ATRIBUCION["licencia_url"],
        "declaracion_de_derechos": f"{BASE}/sitio/licencia.html",
        "citar_como": "SIWA, Fundación Sherman Kent",
        "url_de_cita": BASE,
        "contenido_de_los_datos": (
            "Los valores del registro son hechos y cifras —tasas, recuentos, "
            "índices— sin derechos de autor sobre su contenido. El aporte de la "
            "Fundación (recolección, calificación y declaración de vacíos) va bajo "
            "CC BY 4.0. Los datos de base pertenecen a los productores citados en "
            "cada archivo y conservan la licencia de su fuente; cuando una fuente "
            "impone condiciones, viajan en «restriccion_de_uso» y esa condición manda."),
    }


# Palabras clave del registro, legibles por máquina, para que se encuentre y se
# entienda de qué trata sin abrir cada archivo.
KEYWORDS = [
    "América Latina", "Caribe", "datos abiertos", "situación regional",
    "seguridad", "crimen organizado", "homicidios", "violencia", "gobernanza",
    "corrupción", "derechos humanos", "conflictos", "desplazamiento",
    "economía", "inflación", "comercio", "energía", "minería", "salud",
    "desastres", "entorno digital", "indicadores comparables",
]


# El esquema de identificadores y su forma de resolución: la fila de cada Estado
# se identifica con su código ISO 3166-1 alfa-3, y ese código se resuelve —a
# nombre y geometría— contra el padrón en GeoJSON. Así el identificador no es
# opaco: lleva a más información.
def identificadores() -> dict:
    return {
        "esquema": "ISO 3166-1 alfa-3",
        "que_identifica": "Cada Estado del padrón de 33 de América Latina y el Caribe.",
        "campo": "iso",
        "resolver_en": f"{BASE}/sitio/geo/paises-alc.geojson",
        "nota": ("El código de tres letras (p. ej. «ARG», «MEX») es estándar y estable; "
                 "el padrón en GeoJSON lo resuelve a nombre y geometría, y es el mismo "
                 "para todos los conjuntos que van por Estado."),
    }


# --------------------------------------------------- los totales de portada
# La home de SIWA y la web de presentación mostraban «186 indicadores · 74
# fuentes» escritos A MANO: no salían de ningún recorrido y no coincidían con
# el catálogo (verificado en vivo el 21/9/2026). Esto los calcula, para que
# nunca más haya que acordarse de actualizarlos.
#
# Fuentes = URLs de fuente distintas entre los conjuntos publicados.
#
# Indicadores = para cada conjunto: su «indicadores» declarado si es un
# número; si no lo declara, 1 —una serie temática comparable— salvo que el
# conjunto esté en EXCLUIDOS_DE_PORTADA, en cuyo caso vale 0 aunque declare un
# número (ver nota debajo de la lista).
#
# La lista NO se adivinó desde afuera del catálogo: se armó leyendo el
# propósito real de cada colector —su docstring y, para el Índice de
# Opacidad, la lista ACTOS de indice_opacidad.py, que nombra sus propios
# insumos—. Definición aprobada por la Dirección el 21/9/2026
# (`productos/siwa-certificaciones/siwa-contadores-fix.md`).
EXCLUIDOS_DE_PORTADA = {
    # Herramientas y procesos de la propia Oficina: no miden al país, miden
    # si una puerta responde, si algo se mencionó o si una fuente en prueba
    # ya contesta. «copernicus» declara en su propio docstring que «no mira
    # la imagen: dice que existe» — es disponibilidad, no una medición.
    "archivo", "cobertura", "consulta", "explorador", "memoria", "sondeo",
    "copernicus",
    # Los seis actos del Índice de Opacidad (indice_opacidad.py, lista ACTOS):
    # "explorador" y "archivo" ya están arriba; "armas" y "cites" SÍ quedan
    # afuera de esta lista porque además de alimentar el acto son, ellos
    # mismos, conjuntos sustantivos con cifra propia (comercio de armas,
    # comercio de especies) — «contratacion» y «oficiales» no tienen cifra
    # propia comparable, son el insumo del acto y nada más.
    "contratacion", "oficiales",
    # La materia Opacidad entera: es un puntaje de auditoría de LO QUE YA
    # SE CONTÓ arriba (los actos), no un indicador sustantivo adicional, y
    # su serie histórica es la misma cosa en el tiempo.
    "opacidad", "opacidad-historia", "indice_opacidad",
    # Variable declarada por su propio colector como "de la Oficina, no de
    # la fuente que la alimenta" (brecha.py).
    "brecha",
    # Serie histórica de un indicador que ya se cuenta una vez por su
    # archivo de corte más reciente (desplazamiento.py escribe los dos).
    "desplazamiento-serie",
    # El propio colector declara que NO reemplaza a la serie comparable y
    # que la acompaña porque no es comparable entre países (distinto
    # rezago y método en cada Estado).
    "reciente_oficial",
    # Registros administrativos de cumplimiento, no una situación del país.
    "contrataciones_abiertas", "censo_subnacional", "unidades",
    # No son una fila por Estado con una medición del país: "redes" y
    # "telegram" son un feed de circulación/menciones, "fundacion" es el
    # propio catálogo de publicaciones de la Fundación.
    "redes", "telegram", "fundacion",
    # Capa subnacional: es la versión fina de un indicador de país que ya
    # se cuenta arriba, o —"pdh_guatemala_subnacional" y
    # "subnacional_santafe"— el cruce de una sola jurisdicción contra sí
    # misma. Ninguno es comparable entre los 33 Estados.
    "subnacional", "subnacional_acled", "subnacional_datos",
    "subnacional_focos", "subnacional_homicidios", "subnacional_robos",
    "subnacional_santafe", "subnacional_vigia", "pdh_guatemala_subnacional",
}


def _indicadores_de_portada(conj: dict) -> int:
    if conj.get("colector") in EXCLUIDOS_DE_PORTADA:
        return 0
    if isinstance(conj.get("indicadores"), int):
        return conj["indicadores"]
    return 1  # serie temática de un indicador comparable, sin cifra declarada


def totales_portada(conjuntos: list, generado: str) -> dict:
    """Los tres números de portada, calculados por la máquina y no a mano.

    ATENCIÓN — lo que este cálculo da hoy (21/9/2026) es más alto que el
    rango de 65 a 70 que se anticipaba al aprobar la definición: contando
    literalmente el «indicadores» que cada conjunto declara, cinco conjuntos
    grandes (Banco Mundial 51, ONU-ODS 15, CEPAL 17, OWD 22, Índice de Crimen
    Organizado 36) ya suman 141 por sí solos. Excluir la capa subnacional y
    lo utilitario no podía bajar eso, porque esos conjuntos ya estaban en
    null y sumaban 0 o 1 antes del arreglo. Se declara acá, no se ajusta a
    ojo: la definición aprobada se aplicó literal y el número que sale es
    este. Queda para que la Dirección lo confirme o pida otra unidad de
    conteo (por conjunto en vez de por indicador declarado).
    """
    return {
        "estados": len(geo.padron()),
        "indicadores": sum(_indicadores_de_portada(c) for c in conjuntos),
        "fuentes": len({c["url_fuente"] for c in conjuntos if c.get("url_fuente")}),
        "generado": generado,
    }


def catalogo(conjuntos: list) -> dict:
    return {
        "registro": "SIWA — Reporte de situación de América Latina y el Caribe",
        "de": "Fundación Sherman Kent, Oficina de Generación de Inteligencia",
        "sitio": BASE,
        "documentacion": f"{BASE}/datos/",
        "generado": (generado := datetime.now(timezone.utc).isoformat(timespec="seconds")),
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
        "derechos": derechos(),
        "keywords": KEYWORDS,
        "identificadores": identificadores(),
        "integridad": {
            "que_es": ("La huella SHA-256 de cada archivo publicado. Quien descarga un "
                       "conjunto puede recalcular su huella y compararla con esta para "
                       "confirmar que recibió exactamente lo que la casa publicó."),
            "archivo": f"{DIR_DATOS}/checksums.txt",
            "algoritmo": "SHA-256",
            "formato": "sha256sum (huella  nombre), verificable con herramientas comunes",
        },
        "herramientas": {
            "que_es": ("Los conjuntos son JSON plano servido con cabeceras abiertas: se "
                       "leen con las librerías habituales de cualquier lenguaje, sin "
                       "cliente propio."),
            "donde": f"{BASE}/datos/",
            "ejemplos": {
                "Python": "requests + json (o pandas.read_json para tabla)",
                "R": "jsonlite::fromJSON(url)",
                "JavaScript": "fetch(url).then(r => r.json())",
                "línea de comandos": "curl -s <url> | jq",
            },
        },
        "controles": {
            "que_son": "Mediciones que el registro hace de si mismo. No son datos de terceros: "
                       "no tienen fuente ni calificacion, y por eso no cuentan como conjuntos. "
                       "Se publican para que el objetivo declarado pueda controlarse desde afuera.",
            "donde": {nombre: {"url": f"{DIR_DATOS}/{nombre}", "que_es": que}
                      for nombre, que in sorted(TESTIGOS.items()) if nombre != "indice.json"},
        },
        "conjuntos": conjuntos,
        "cuantos": len(conjuntos),
        # Totales de portada — única fuente de verdad de los tres números que
        # muestran la home de SIWA y la web de presentación. Ver totales_portada().
        "cuantos_portada": totales_portada(conjuntos, generado),
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

<h2>Herramientas para usarlo</h2>
<p>Al ser JSON plano con cabeceras abiertas, se lee con las librerías habituales de
  cualquier lenguaje, sin cliente propio:</p>
<div class="filas">
  <div><b>Python</b><span><code>requests</code> + <code>json</code>, o
    <code>pandas.read_json(url)</code> para tenerlo como tabla.</span></div>
  <div><b>R</b><span><code>jsonlite::fromJSON(url)</code>.</span></div>
  <div><b>JavaScript</b><span><code>fetch(url).then(r =&gt; r.json())</code>, desde
    cualquier dominio.</span></div>
  <div><b>Línea de comandos</b><span><code>curl -s &lt;url&gt; | jq</code>.</span></div>
</div>

<h2>Verificar que es lo que publicamos</h2>
<p>Cada archivo lleva su huella <b>SHA-256</b> en
  <a class="enlace" href="{DIR_DATOS}/checksums.txt">checksums.txt</a>, en el formato de
  <code>sha256sum</code>. Quien descarga un conjunto puede recalcular la huella y
  compararla: si coincide, recibió exactamente lo que la casa publicó. El propio
  <a class="enlace" href="{DIR_DATOS}/indice.json">catálogo</a> declara además, en formato
  máquina, los <code>derechos</code> (titular, licencia y cómo citar), las
  <code>keywords</code> del registro y el esquema de <code>identificadores</code>
  (código ISO de Estado y dónde se resuelve).</p>

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
    conjuntos = recorrer()
    huellas = sellar()  # las huellas de los datos, antes de escribir el índice
    indice = catalogo(conjuntos)
    SALIDA.write_text(json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8",
                      newline="")
    PAGINA.write_text(pagina(indice), encoding="utf-8", newline="")
    print(f"[indice] {indice['cuantos']} conjuntos · {len(huellas)} huellas · "
          f"{SALIDA.relative_to(RAIZ)}, {PAGINA.relative_to(RAIZ)} y "
          f"{CHECKSUMS.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
