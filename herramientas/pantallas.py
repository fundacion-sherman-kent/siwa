# -*- coding: utf-8 -*-
"""El control de pantallas: «se adapta a cualquier dispositivo», comprobado solo.

POR QUÉ EXISTE
--------------
El diseño adaptable no se rompe de golpe: se rompe de a un cambio por vez, y
casi siempre en un tamaño que quien programó no abrió esa tarde. En este mismo
registro pasó tres veces —una línea que desbordaba el teléfono, una barra de
220 px de alto, una dirección con etiquetas de campaña que corría la página de
costado— y las tres se descubrieron porque la Dirección mandó una captura.

Eso no escala. Este archivo abre la página en varios anchos, con los dos fondos
y los tres niveles de lectura, y **falla si algo se sale**. Lo corre GitHub en
cada cambio: el aviso llega antes de publicar, no después de que alguien lo vea
en su teléfono.

QUÉ SE MIDE, Y POR QUÉ CADA COSA
---------------------------------
  · **Desborde horizontal.** Es el defecto que arruina la lectura en teléfono:
    la página se corre de costado y el texto se va del borde. Se mide el
    documento contra la ventana, y cuando hay desborde se nombra al elemento
    culpable, que es lo único que hace arreglable el aviso.
  · **Texto cortado en los controles.** Un desplegable más bajo que su propia
    letra corta las colas de las palabras. Ya pasó con «Empezá acá».
  · **La ayuda, siempre visible.** Si el botón de ayuda desaparece en algún
    tamaño, el lector que no entiende la plataforma se queda sin salida.
  · **La barra de arriba, contenida en teléfono.** Es fija: si crece, se come
    la pantalla en la que hay que leer.

LO QUE ESTE CONTROL NO DICE
----------------------------
No dice si la página es linda ni si se entiende. Dice que **entra**. Son cosas
distintas y conviene no confundirlas: un tablero puede pasar este control
entero y seguir siendo confuso. Para eso están los lectores de carne y hueso.
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "datos" / "publico" / "pantallas.json"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
DIRECCION = BASE.rstrip("/") + "/sitio/index.html"

# Los anchos no son caprichosos: 360 es el teléfono chico que todavía se usa en
# la región, 390 el corriente, 768 la tableta vertical, 1024 la horizontal y el
# portátil chico, 1440 el monitor. Entre medio no hay saltos que probar porque
# la maqueta no tiene medidas mágicas: se acomoda sola.
ANCHOS = [(360, 780), (390, 844), (768, 1024), (1024, 768), (1440, 900)]
NIVELES = [1, 2, 3]

MEDIDA = """
() => {
  const malos = [];
  const V = window.innerWidth;
  // El culpable del desborde: el elemento mas ancho que la ventana. Sin
  // nombrarlo, el aviso no se puede arreglar.
  if(document.documentElement.scrollWidth > V + 1){
    let peor = null, ancho = 0;
    document.querySelectorAll('body *').forEach(el => {
      const r = el.getBoundingClientRect();
      if(r.width > ancho && (r.right > V + 1 || r.left < -1) &&
         getComputedStyle(el).position !== 'fixed'){ ancho = r.width; peor = el; }
    });
    const nombre = peor ? (peor.tagName.toLowerCase()
      + (peor.id ? '#' + peor.id : '')
      + (peor.className && typeof peor.className === 'string'
         ? '.' + peor.className.trim().split(/\\s+/).slice(0,2).join('.') : '')) : '(no hallado)';
    malos.push({que:'desborde horizontal', cuanto: document.documentElement.scrollWidth - V,
                quien: nombre, ancho_del_elemento: Math.round(ancho)});
  }
  // Texto cortado en un control: el desplegable mas bajo que su propia letra.
  document.querySelectorAll('select, input, button').forEach(el => {
    const r = el.getBoundingClientRect();
    if(!r.height) return;
    if(el.scrollHeight > el.clientHeight + 2 && el.tagName !== 'BUTTON')
      malos.push({que:'texto cortado en un control',
                  quien: el.tagName.toLowerCase() + (el.id ? '#' + el.id : ''),
                  alto_del_control: Math.round(r.height), hace_falta: el.scrollHeight});
  });
  // TEXTO SUELTO DENTRO DE UN FLEX, que es una trampa silenciosa: un texto sin
  // envoltorio, puesto al lado de dos o mas elementos dentro de una caja flex o
  // grid, SE CONVIERTE EN OTRA COLUMNA. La caja que el autor penso de dos
  // columnas sale de tres, con el rotulo estrujado en un ancho ridiculo y la
  // explicacion al costado. No rompe nada, no da error y se ve mal solo en
  // pantallas angostas: la encontro un lector, no una prueba. Ahora la encuentra
  // esta prueba. Con un solo elemento hijo no molesta —icono y texto es lo
  // normal—, asi que se avisa desde dos.
  document.querySelectorAll('body *').forEach(el => {
    const d = getComputedStyle(el).display;
    if(!/^(flex|inline-flex|grid|inline-grid)$/.test(d)) return;
    if(el.children.length < 2) return;
    if(!el.getBoundingClientRect().height) return;
    const suelto = [...el.childNodes].some(
      n => n.nodeType === 3 && n.textContent.trim().length > 2);
    if(suelto) malos.push({que:'texto suelto dentro de una caja flex: se vuelve otra columna',
      quien: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '')
             + (el.className && typeof el.className === 'string'
                ? '.' + el.className.trim().split(' ').filter(Boolean).slice(0,2).join('.') : ''),
      texto: el.textContent.trim().split(/[ \\n\\t]+/).join(' ').slice(0, 60)});
  });
  // VINETAS VACIAS. Una lista con renglones en blanco no informa: desconcierta.
  // Aparecen cuando el codigo que las dibuja busca un campo que el dato no tiene,
  // que es un error que no falla ni avisa: la lista sale, con nada adentro. Pasó
  // en la ficha del Indice de Opacidad, con tres renglones vacios en la Argentina
  // y en Mexico. No se cuentan las que llevan una imagen, un control o un dibujo.
  document.querySelectorAll('li').forEach(li => {
    if(!li.getBoundingClientRect().height) return;
    if(li.textContent.trim()) return;
    if(li.querySelector('img, svg, input, button, canvas, select, textarea')) return;
    const p = li.parentElement;
    malos.push({que:'vinieta vacia en una lista',
      quien: (p ? p.tagName.toLowerCase() + (p.id ? '#' + p.id : '')
                  + (p.className && typeof p.className === 'string'
                     ? '.' + p.className.trim().split(' ').filter(Boolean).slice(0,2).join('.') : '')
                : 'li')});
  });
  // La ayuda tiene que verse en cualquier tamanio.
  const ayuda = document.getElementById('abrir-ayuda');
  if(!ayuda || ayuda.getBoundingClientRect().height === 0)
    malos.push({que:'el boton de ayuda no se ve', quien:'#abrir-ayuda'});
  // La barra de arriba es fija: en telefono no puede comerse la pantalla.
  const barra = document.querySelector('.topbar');
  const alto = barra ? Math.round(barra.getBoundingClientRect().height) : 0;
  if(V < 500 && alto > 140)
    malos.push({que:'la barra fija ocupa demasiado en telefono', quien:'.topbar',
                alto_de_la_barra: alto});
  return {malos, alto_barra: alto, doc: document.documentElement.scrollWidth, ventana: V};
}
"""


# Se elige la Argentina porque su ficha del Indice de Opacidad tiene rastro de
# busquedas: ejercita el camino que se rompio, con viñetas de verdad.
PAIS_ELEGIDO = """
() => { const s = document.getElementById('ambito');
        if(s){ s.value = 'p:ARG'; s.dispatchEvent(new Event('change', {bubbles:true})); } }
"""
SIN_PAIS = """
() => { const s = document.getElementById('ambito');
        if(s){ s.value = ''; s.dispatchEvent(new Event('change', {bubbles:true})); } }
"""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[pantallas] falta playwright: pip install playwright && playwright install chromium",
              file=sys.stderr)
        sys.exit(2)

    fallas, probadas = [], []
    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        for ancho, alto in ANCHOS:
            pagina = navegador.new_page(viewport={"width": ancho, "height": alto})
            try:
                pagina.goto(DIRECCION, wait_until="load")
            except Exception as e:  # noqa: BLE001 — un servidor apagado no es una falla de maqueta
                print(f"[pantallas] no se pudo abrir {DIRECCION}: {type(e).__name__}. "
                      "¿Está corriendo el servidor? Desde la raíz del repositorio: "
                      "python -m http.server 8000", file=sys.stderr)
                navegador.close()
                sys.exit(2)
            # Se espera a que el registro TERMINE de cargarse: medir una página a
            # medio pintar da un resultado que no le corresponde a nadie.
            try:
                pagina.wait_for_function(
                    "() => document.querySelectorAll('.sel-slot select').length > 0", timeout=45000)
            except Exception:  # noqa: BLE001
                fallas.append({"ancho": ancho, "tema": "—", "nivel": "—",
                               "que": "la página no terminó de cargar", "quien": DIRECCION})
                pagina.close()
                continue
            pagina.wait_for_timeout(2500)
            for claro in (False, True):
                pagina.evaluate("c => document.body.classList.toggle('claro', c)", claro)
                for nivel in NIVELES:
                    pagina.evaluate(
                        """n => { const b=[...document.querySelectorAll('.nivel')][n-1];
                                  if(b) b.click(); }""", nivel)
                    pagina.wait_for_timeout(700)
                    r = pagina.evaluate(MEDIDA)
                    probadas.append({"ancho": ancho, "tema": "claro" if claro else "oscuro",
                                     "nivel": nivel, "barra": r["alto_barra"]})
                    for m in r["malos"]:
                        fallas.append({**m, "ancho": ancho,
                                       "tema": "claro" if claro else "oscuro", "nivel": nivel})

                # Y AHORA CON UN PAIS ELEGIDO, que es media aplicacion que antes
                # no se miraba: la ficha del Estado, sus ejes y el Indice de
                # Opacidad solo se dibujan cuando hay uno seleccionado.
                pagina.evaluate(PAIS_ELEGIDO)
                pagina.wait_for_timeout(1800)
                r = pagina.evaluate(MEDIDA)
                probadas.append({"ancho": ancho, "tema": "claro" if claro else "oscuro",
                                 "nivel": "3 · con país", "barra": r["alto_barra"]})
                for m in r["malos"]:
                    fallas.append({**m, "ancho": ancho,
                                   "tema": "claro" if claro else "oscuro",
                                   "nivel": "3 · con país"})
                pagina.evaluate(SIN_PAIS)
                pagina.wait_for_timeout(900)
            pagina.close()
        navegador.close()

    salida = {
        "que_es": "Control de diseño adaptable. La página se abre en varios anchos, con los dos "
                  "fondos, los tres niveles de lectura y también con un país elegido —que es "
                  "media aplicación que de otro modo no se mira—, y se mide que nada se salga.",
        "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "anchos": [a for a, _ in ANCHOS],
        "combinaciones": len(probadas),
        "fallas": fallas,
        "veredicto": "entra en todas" if not fallas else f"{len(fallas)} problema"
                     + ("" if len(fallas) == 1 else "s"),
        "lo_que_no_dice": "Que la página sea clara o linda. Dice que entra, que es otra cosa.",
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8",
                      newline="")

    print(f"[pantallas] {len(probadas)} combinaciones · {salida['veredicto']}")
    for f in fallas[:15]:
        print(f"  PROBLEMA · {f['ancho']} px · tema {f['tema']} · nivel {f['nivel']} · "
              f"{f['que']} · {f.get('quien', '')}")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
