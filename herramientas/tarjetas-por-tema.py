# -*- coding: utf-8 -*-
"""Una página y una imagen por tema, para que compartir un enlace muestre el tema.

EL PROBLEMA. Cuando alguien comparte el registro en una red o en un mensaje, la
tarjeta que aparece es siempre la misma tapa, se comparta homicidios o cocaína.
La causa es dura y no se arregla con más programación en la página: **los robots
de las redes no ejecutan el sitio**, leen el HTML crudo tal como viene del
servidor. Una página que arma su contenido al vuelo, como esta, les resulta
invisible.

LA SALIDA. Que el robot escriba de antemano **una página chiquita por tema**,
con el título, la descripción y la imagen de ESE tema ya escritos en el HTML, y
que esa página lleve al lector al registro filtrado por el tema. El robot de la
red lee la página chiquita; la persona aterriza en el registro.

LA IMAGEN ES DE VERDAD. No es la tapa con un rótulo encima: se abre el registro
en el tema, se espera a que el mapa termine de pintarse y se fotografía el
tablero. Lo que se comparte es lo que el lector va a ver.

POR QUÉ NO VA EN EL ROBOT DE CADA HORA. Abrir un navegador setenta veces lleva
minutos. Va con el control de pantallas, una vez por día: los temas no cambian
de nombre todos los días, y una tarjeta de ayer no engaña a nadie.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
SALIDA = RAIZ / "sitio" / "t"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
PUBLICA = "https://siwa.fundacionkent.org"

ANCHO, ALTO = 1200, 630   # la medida que piden las redes


def limpiar(t: str) -> str:
    """El texto que va adentro de una etiqueta HTML, sin romperla."""
    return (str(t or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def nombre_de_archivo(clave: str) -> str:
    # Solo lo que sobrevive intacto a una dirección web.
    return re.sub(r"[^a-z0-9_-]+", "-", str(clave).lower()).strip("-") or "tema"


PLANTILLA = """<!DOCTYPE html>
<html lang="es-AR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo} — SIWA</title>
<meta name="description" content="{bajada}">
<link rel="canonical" href="{destino}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="SIWA — Fundación Sherman Kent">
<meta property="og:locale" content="es_AR">
<meta property="og:url" content="{aqui}">
<meta property="og:title" content="{titulo} — SIWA">
<meta property="og:description" content="{bajada}">
<meta property="og:image" content="{imagen}">
<meta property="og:image:width" content="{ancho}">
<meta property="og:image:height" content="{alto}">
<meta property="og:image:alt" content="{titulo} en los 33 Estados de América Latina y el Caribe.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{titulo} — SIWA">
<meta name="twitter:description" content="{bajada}">
<meta name="twitter:image" content="{imagen}">
<!-- QUIEN LLEGA ACA SE VA AL REGISTRO. Esta pagina existe para el robot de la
     red social, que no ejecuta la pagina grande y necesita encontrar el titulo,
     la descripcion y la imagen escritos en el HTML. La persona no se queda. -->
<meta http-equiv="refresh" content="0; url={destino}">
<script>location.replace({destino_js});</script>
<style>
 body{{margin:0;font:16px/1.6 system-ui,sans-serif;background:#00121E;color:#E8EEF4;
      display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px;}}
 a{{color:#FB6500;}}
</style>
</head>
<body>
<p>Llevándote a <b>{titulo}</b> en el registro…
  <br>Si no pasa nada, <a href="{destino}">entrá acá</a>.</p>
</body>
</html>
"""


PREPARAR_FOTO = """
(rotulo) => {
  // La ayuda se abre sola en la primera visita, y un navegador recien abierto
  // siempre es una primera visita: sin esto la tarjeta sale tapada.
  document.querySelectorAll('dialog[open]').forEach(d => { try{ d.close(); }catch(e){} });
  try{ localStorage.setItem('siwa-ayuda-vista', '1'); }catch(e){}

  // La barra de arriba es fija y se monta encima de lo que se fotografia,
  // tapando el rotulo. No es parte de la tarjeta: se apaga.
  document.querySelectorAll('.topbar').forEach(e => { e.style.display = 'none'; });

  const mapa = document.getElementById('mapa');
  const caja = mapa && mapa.closest('.tablero-mapa');
  if(!caja) return null;

  // NO SE TOCA LA MAQUETA, solo se apaga lo que invita a tocar la pantalla: en
  // una imagen compartida, un boton no lleva a ningun lado y una casilla de
  // tildar es ruido. Reacomodar columnas para que el mapa quede mas ancho se
  // probo y salio peor: la maqueta se defiende sola y termina rompiendose.
  const fuera = ['.leaflet-control-container', '.llevar-mapa', '.tocar-comparar',
                 '#seleccion', '.modos', '#cuando', '.leaflet-popup'];
  fuera.forEach(q => caja.querySelectorAll(q).forEach(e => { e.style.display = 'none'; }));
  caja.querySelectorAll('.mapa-caja > *').forEach(e => {
    if(e.id !== 'mapa') e.style.display = 'none';
  });

  // El rotulo va ADENTRO de lo que se fotografia: un mapa sin titulo no dice
  // de que es, y una franja fija de la ventana no entra en la foto del elemento.
  let r = caja.querySelector('#rotulo-tarjeta');
  if(!r){
    r = document.createElement('div');
    r.id = 'rotulo-tarjeta';
    caja.insertBefore(r, caja.firstChild);
  }
  r.style.cssText = 'display:flex;align-items:baseline;justify-content:space-between;'
    + 'gap:14px;background:#00121E;color:#fff;padding:12px 16px;margin:0 0 10px;'
    + 'border-radius:10px;font:700 21px/1.25 Inter,system-ui,sans-serif;';
  r.innerHTML = '<span></span><span style="font:600 11px/1.2 Inter,system-ui,sans-serif;'
    + 'letter-spacing:.14em;text-transform:uppercase;opacity:.75;white-space:nowrap">'
    + 'SIWA · 33 Estados</span>';
  r.firstChild.textContent = rotulo;
  caja.scrollIntoView({block: 'center'});
  return true;
}
"""


FIRMA_PNG = bytes([137, 80, 78, 71, 13, 10, 26, 10])


def medida_del_png(ruta: Path):
    """El ancho y el alto que el archivo tiene de verdad.

    Se leen del propio PNG y no se suponen: una medida declarada que no coincide
    con el archivo hace que varias redes descarten la imagen sin decir por qué.
    """
    b = ruta.read_bytes()[:33]
    if len(b) < 33 or b[:8] != FIRMA_PNG:
        return None, None
    return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[tarjetas] falta playwright: pip install playwright && playwright install chromium",
              file=sys.stderr)
        sys.exit(2)

    hechas, fallas = [], []
    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        pagina = navegador.new_page(viewport={"width": ANCHO, "height": ALTO},
                                    device_scale_factor=1)
        try:
            pagina.goto(f"{BASE}/sitio/index.html?nivel=3", wait_until="load")
            pagina.wait_for_function(
                "() => document.querySelectorAll('#tema-principal option').length > 3",
                timeout=45000)
        except Exception as e:  # noqa: BLE001
            print(f"[tarjetas] no se pudo abrir el registro: {type(e).__name__}. "
                  "¿Está corriendo el servidor? Desde la raíz: python -m http.server 8000",
                  file=sys.stderr)
            navegador.close()
            sys.exit(2)

        # LA LISTA DE TEMAS SE LE PREGUNTA AL PROPIO REGISTRO. Copiarla acá la
        # dejaría vieja el día que se agregue un tema, y nadie se enteraría.
        temas = pagina.evaluate(
            """() => [...document.querySelectorAll('#tema-principal option')]
                     .map(o => ({clave: o.value, rotulo: o.text.trim(),
                                 eje: (o.parentElement.label || '').trim()}))
                     .filter(x => x.clave)""")

        # Se vacía el contenido, no se borra la carpeta: un tema que ya no
        # existe no debe quedar publicado, pero borrar el directorio entero
        # falla cuando está sincronizado con la nube, y esa falla tiraba la
        # corrida completa por una carpeta que igual se iba a volver a llenar.
        SALIDA.mkdir(parents=True, exist_ok=True)
        for viejo in SALIDA.iterdir():
            if viejo.is_file():
                try:
                    viejo.unlink()
                except OSError:
                    pass

        for t in temas:
            archivo = nombre_de_archivo(t["clave"])
            try:
                pagina.goto(f"{BASE}/sitio/index.html?tema={t['clave']}&nivel=3",
                            wait_until="load")
                pagina.wait_for_timeout(2600)   # que el mapa termine de pintarse
                if not pagina.query_selector("#mapa"):
                    fallas.append(f"{t['rotulo']}: no se encontró el mapa")
                    continue
                # Se prepara la foto: fuera los controles y las ayudas de uso,
                # que en una tarjeta compartida son ruido, y un rótulo arriba con
                # el nombre del tema, porque un mapa sin título no dice de qué es.
                if not pagina.evaluate(PREPARAR_FOTO, t["rotulo"]):
                    fallas.append(f"{t['rotulo']}: no se encontró la caja del mapa")
                    continue
                pagina.wait_for_timeout(600)
                destino_png = SALIDA / f"{archivo}.png"
                pagina.query_selector(".tablero-mapa").screenshot(path=str(destino_png))
                ancho_real, alto_real = medida_del_png(destino_png)
                if not ancho_real:
                    fallas.append(f"{t['rotulo']}: la imagen salió ilegible")
                    continue

                bajada = (f"{t['rotulo']} en los 33 Estados de América Latina y el Caribe, "
                          "con la fuente y la fecha de cada cifra. Registro público y gratuito "
                          "de la Fundación Sherman Kent.")
                destino = f"{PUBLICA}/sitio/index.html?tema={t['clave']}&nivel=3"
                (SALIDA / f"{archivo}.html").write_text(PLANTILLA.format(
                    titulo=limpiar(t["rotulo"]),
                    bajada=limpiar(bajada),
                    destino=limpiar(destino),
                    destino_js=json.dumps(destino),
                    aqui=limpiar(f"{PUBLICA}/sitio/t/{archivo}.html"),
                    imagen=limpiar(f"{PUBLICA}/sitio/t/{archivo}.png"),
                    ancho=ancho_real, alto=alto_real,
                ), encoding="utf-8", newline="")
                hechas.append({"clave": t["clave"], "rotulo": t["rotulo"],
                               "eje": t["eje"], "pagina": f"sitio/t/{archivo}.html"})
            except Exception as e:  # noqa: BLE001 — un tema caído no tumba la corrida
                fallas.append(f"{t['rotulo']}: {type(e).__name__}")
        navegador.close()

    if not hechas:
        print("[tarjetas] no se pudo armar una sola tarjeta. No se escribe el índice.",
              file=sys.stderr)
        sys.exit(1)

    (SALIDA / "indice.json").write_text(json.dumps({
        "que_es": "Una página y una imagen por tema, para que al compartir un enlace la "
                  "tarjeta muestre ese tema y no siempre la misma tapa. Existen porque los "
                  "robots de las redes leen el HTML crudo y no ejecutan el registro.",
        "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cuantas": len(hechas),
        "fallas": fallas,
        "temas": hechas,
    }, ensure_ascii=False, indent=2), encoding="utf-8", newline="")

    aviso = f" · {len(fallas)} sin tarjeta" if fallas else ""
    print(f"[tarjetas] {len(hechas)} temas con página e imagen{aviso}")
    for f in fallas[:8]:
        print("  SIN TARJETA ·", f)


if __name__ == "__main__":
    main()
