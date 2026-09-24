/* Guía SIWA — asistente de navegación. Fuente única.
   Una burbuja fija abajo a la derecha que abre una ventana de chat: conversa,
   entiende lo que el usuario escribe (tema, país, provincia/departamento/estado,
   herramienta o pregunta), lo cruza contra el catálogo real y lo lleva a la
   página que existe. Corre ENTERO en el navegador: no gasta un solo token, no
   consulta ninguna IA paga, no manda datos a ningún lado. Nunca inventa: si no
   encuentra, lo dice; y si hay más de un lugar con el mismo nombre (p. ej.
   Córdoba en Argentina y en Colombia), los muestra a los dos en vez de elegir
   uno por su cuenta.
   Se carga en cualquier página junto con la franja oficial (cabecera-siwa.js),
   y en el índice con <script defer src="_comun/guia-siwa.js"></script>. */
(function () {
  if (window.__guiaSiwa) return;            // una sola vez por página
  window.__guiaSiwa = true;

  var script = document.currentScript ||
    (function () { var s = document.getElementsByTagName("script"); return s[s.length - 1]; })();
  var base = script.src.replace(/_comun\/[^\/]*$/, "");   // carpeta sitio/
  var datosUrl = base + "_comun/guia-siwa.json";

  var norm = function (s) {
    return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
  };

  /* ---------- estilos (todo con prefijo gs- para no chocar con la página) ---------- */
  var css = "" +
  ".gs-lanzador{position:fixed;right:22px;bottom:22px;z-index:9000;width:60px;height:60px;border-radius:50%;" +
    "border:0;cursor:pointer;background:#FB6500;color:#fff;box-shadow:0 10px 26px rgba(251,101,0,.42);" +
    "display:flex;align-items:center;justify-content:center;transition:transform .15s,box-shadow .15s;" +
    "font-family:'Inter',system-ui,sans-serif;}" +
  ".gs-lanzador:hover{transform:translateY(-2px);box-shadow:0 14px 30px rgba(251,101,0,.5);}" +
  ".gs-lanzador svg{width:28px;height:28px;}.gs-lanzador .gs-cerrar{display:none;}" +
  ".gs-on .gs-lanzador .gs-abrir{display:none;}.gs-on .gs-lanzador .gs-cerrar{display:block;}" +
  ".gs-globo{position:fixed;right:92px;bottom:34px;z-index:9000;background:#00121E;color:#fff;font-size:12.5px;" +
    "font-family:'Inter',system-ui,sans-serif;padding:8px 12px;border-radius:12px;box-shadow:0 8px 20px rgba(0,18,30,.2);" +
    "max-width:200px;line-height:1.4;cursor:pointer;}" +
  ".gs-globo::after{content:'';position:absolute;right:-6px;bottom:16px;border:6px solid transparent;border-left-color:#00121E;}" +
  ".gs-on .gs-globo{display:none;}" +
  ".gs-pop{position:fixed;right:22px;bottom:94px;z-index:9001;width:376px;max-width:calc(100vw - 32px);" +
    "height:min(560px,calc(100vh - 130px));display:none;flex-direction:column;background:#fff;border:1px solid #dfdbcf;" +
    "border-radius:16px;overflow:hidden;box-shadow:0 20px 50px rgba(0,18,30,.28);" +
    "font-family:'Inter',system-ui,sans-serif;color:#12212b;}" +
  ".gs-on .gs-pop{display:flex;}" +
  ".gs-tope{background:#00121E;color:#fff;padding:13px 15px;display:flex;align-items:center;gap:9px;}" +
  ".gs-tope .gs-p{width:9px;height:9px;border-radius:50%;background:#3FA796;box-shadow:0 0 0 3px rgba(63,167,150,.25);}" +
  ".gs-tope .gs-t{font-weight:700;font-size:14px;}" +
  ".gs-tope .gs-g{margin-left:auto;font-size:10.5px;color:#9fb2be;}" +
  ".gs-tope .gs-x{background:transparent;border:0;color:#9fb2be;font-size:20px;cursor:pointer;line-height:1;margin-left:6px;font-family:inherit;}" +
  ".gs-tope .gs-x:hover{color:#fff;}" +
  ".gs-hilo{flex:1;padding:14px;overflow-y:auto;display:flex;flex-direction:column;gap:11px;}" +
  ".gs-msg{max-width:88%;padding:10px 12px;border-radius:14px;font-size:13.5px;line-height:1.48;white-space:pre-wrap;}" +
  ".gs-msg.gs-bot{align-self:flex-start;background:#eef1ee;border:1px solid #dfdbcf;border-bottom-left-radius:5px;}" +
  ".gs-msg.gs-yo{align-self:flex-end;background:#00121E;color:#fff;border-bottom-right-radius:5px;}" +
  ".gs-card{display:block;margin-top:8px;text-decoration:none;color:inherit;border:1px solid #dfdbcf;border-radius:10px;" +
    "padding:9px 11px;background:#fff;transition:.15s;}" +
  ".gs-card:hover{border-color:#FB6500;background:rgba(251,101,0,.05);}" +
  ".gs-card .gs-k{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#667B89;}" +
  ".gs-card .gs-v{font-weight:700;color:#00121E;margin-top:2px;font-size:13.5px;}" +
  ".gs-card .gs-ir{color:#FB6500;}" +
  ".gs-chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:2px;}" +
  ".gs-chip{border:1px solid #dfdbcf;background:#fff;color:#40525d;border-radius:999px;padding:6px 12px;font-size:12.5px;" +
    "cursor:pointer;font-family:inherit;transition:.15s;}" +
  ".gs-chip:hover{border-color:#FB6500;color:#00121E;background:rgba(251,101,0,.06);}" +
  ".gs-chip.gs-eje{border-color:rgba(140,0,224,.35);}" +
  ".gs-barra{display:flex;gap:7px;border-top:1px solid #dfdbcf;padding:10px;}" +
  ".gs-barra input{flex:1;border:1px solid #dfdbcf;border-radius:999px;padding:10px 14px;font-size:13.5px;" +
    "font-family:inherit;color:#12212b;outline:none;}" +
  ".gs-barra input:focus{border-color:#FB6500;}" +
  ".gs-barra button{background:#FB6500;color:#fff;border:0;border-radius:999px;padding:0 16px;font-weight:700;" +
    "font-size:13.5px;cursor:pointer;font-family:inherit;}" +
  "@media(max-width:460px){.gs-pop{right:8px;left:8px;bottom:84px;width:auto;height:min(70vh,520px);}" +
    ".gs-lanzador{right:16px;bottom:16px;}.gs-globo{display:none;}}" +
  "@media print{.gs-lanzador,.gs-globo,.gs-pop{display:none !important;}}";

  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  /* ---------- DOM ---------- */
  var raiz = document.createElement("div");
  raiz.innerHTML =
    '<div class="gs-globo" id="gs-globo">¿Te ayudo a encontrar algo?</div>' +
    '<button class="gs-lanzador" id="gs-lanzador" aria-label="Abrir la guía de SIWA">' +
      '<svg class="gs-abrir" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>' +
      '<svg class="gs-cerrar" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>' +
    '</button>' +
    '<div class="gs-pop" id="gs-pop" role="dialog" aria-label="Guía SIWA">' +
      '<div class="gs-tope"><span class="gs-p"></span><span class="gs-t">Guía SIWA</span>' +
        '<span class="gs-g">sin costo · sin IA paga</span>' +
        '<button class="gs-x" id="gs-x" aria-label="Cerrar">×</button></div>' +
      '<div class="gs-hilo" id="gs-hilo"></div>' +
      '<div class="gs-barra"><input id="gs-entrada" autocomplete="off" placeholder="Escribí: corrupción en México">' +
        '<button id="gs-ir">Ir</button></div>' +
    '</div>';
  function montarDom() { while (raiz.firstChild) document.body.appendChild(raiz.firstChild); }

  /* ---------- motor ---------- */
  var DATOS = null, hilo, entrada, ctxPais = null, arrancado = false;

  // Palabras de relleno del español: se descartan del cómputo de cobertura para
  // que la fracción se mida sobre las palabras que de verdad dicen algo. Si la
  // consulta queda vacía después de sacarlas (p. ej. el usuario escribió solo
  // "la"), se usan las palabras originales: es mejor buscar con la palabra
  // hueca que quedarse sin ninguna.
  var RELLENO = " que de del la las el los en un una y a al por para con ";
  function palabrasSignificativas(q) {
    var todas = q.split(" ").filter(Boolean);
    var sig = todas.filter(function (w) { return RELLENO.indexOf(" " + w + " ") < 0; });
    return sig.length ? sig : todas;
  }

  // Corrección del 24/9/2026. Antes: las palabras de 2 letras se ignoraban por
  // completo (por eso "fe" de "santa fe" no contaba y la consulta quedaba
  // reducida a "santa", que también matchea "Santa Lucía") y se puntuaba por
  // aciertos absolutos, no por cuánto de lo que el usuario escribió se explica
  // con el candidato. Ahora se cuentan, por separado, los aciertos EXACTOS
  // (palabra completa) y los de PREFIJO, y se miden dos coberturas: la exacta
  // (para decidir ENTRE categorías —país, tema, unidad— sin que un prefijo le
  // gane a una palabra completa de otra categoría) y la total, con prefijo
  // incluido (para elegir el mejor candidato DENTRO de una misma lista, de
  // respaldo cuando no hay ninguna palabra completa).
  function coincidencia(qt, texto) {
    var t = " " + norm(texto) + " ", exactos = 0, hits = 0;
    for (var i = 0; i < qt.length; i++) {
      var w = qt[i]; if (!w) continue;
      if (t.indexOf(" " + w + " ") >= 0) { exactos++; hits++; }
      else if (w.length > 2 && t.indexOf(" " + w) >= 0) { hits++; }
    }
    return { total: qt.length, exactos: exactos, hits: hits };
  }
  // DENTRO de una lista: la cobertura total (exacto + prefijo) manda, para no
  // quedarse sin nada ante una consulta parecida pero no exacta.
  function puntajeTotal(c) { return c.total ? (c.hits / c.total) * 1000 + c.exactos : 0; }
  // ENTRE listas distintas (país, tema, unidad, herramienta): sólo cuenta lo
  // EXACTO —"priorizar coincidencia de palabra completa/exacta por sobre
  // prefijo"—, para que un prefijo casual (p. ej. "provincia" ante un tema que
  // dice "observatorio provincial") no le robe la prioridad a la unidad
  // subnacional que matchea completa.
  function puntajeExacto(c) { return c.total ? (c.exactos / c.total) * 1000 + c.exactos : 0; }

  // Busca en una lista [{slug/archivo/iso, rotulo/nombre, s?, pais?}] y devuelve
  // el mejor puntaje MÁS todos los candidatos empatados en ese puntaje. Un
  // empate real (dos lugares con el mismo nombre, como "Córdoba" en Argentina y
  // en Colombia, o "San Juan" en Argentina y en República Dominicana) no se
  // resuelve solo: se avisa y se muestran los dos.
  function mejor(qt, lista, campoClave) {
    var mp = -1, empatados = [], mejorCoin = null;
    for (var i = 0; i < lista.length; i++) {
      var it = lista[i];
      var texto = (it.rotulo || it.nombre || "") + " " + (it.s || "") + " " + (it.pais || "") + " " +
        String(it[campoClave] || "").replace(/[_-]/g, " ");
      var c = coincidencia(qt, texto);
      if (c.hits <= 0) continue;
      var p = puntajeTotal(c);
      if (p > mp) { mp = p; empatados = [it]; mejorCoin = c; }
      else if (p === mp) { empatados.push(it); }
    }
    return mp > 0 ? { it: empatados[0], p: mp, pExacto: puntajeExacto(mejorCoin), empatados: empatados } : null;
  }

  function burbuja(clase, html) {
    var d = document.createElement("div"); d.className = "gs-msg " + clase; d.innerHTML = html;
    hilo.appendChild(d); hilo.scrollTop = hilo.scrollHeight; return d;
  }
  function chips(items) {
    var c = document.createElement("div"); c.className = "gs-chips";
    items.forEach(function (it) {
      var b = document.createElement("button"); b.className = "gs-chip" + (it.eje ? " gs-eje" : "");
      b.textContent = it.t; b.onclick = it.fn; c.appendChild(b);
    });
    hilo.appendChild(c); hilo.scrollTop = hilo.scrollHeight;
  }
  function card(k, r, url) {
    return '<a class="gs-card" href="' + url + '"><div class="gs-k">' + k + '</div>' +
      '<div class="gs-v">' + r + ' <span class="gs-ir">↗</span></div></a>';
  }
  // Muestra TODOS los empatados como tarjetas, en vez de adivinar cuál quiso
  // decir el usuario. armarCard recibe cada ítem y arma su tarjeta.
  function mostrarAmbiguedad(intro, empatados, armarCard) {
    var d = burbuja("gs-bot", intro);
    empatados.forEach(function (it) { d.innerHTML += armarCard(it); });
    seguir();
  }
  // Va DIRECTO al registro con el tema puesto y BAJA al gráfico (#tablero-siwa):
  // el stub t/<slug>.html rebota al índice pero deja al lector arriba de todo, sin
  // ver el gráfico. Con el ancla, aterriza en el tablero, que es lo que pidió.
  var uT = function (s) { return base + "index.html?tema=" + encodeURIComponent(s) + "&nivel=3#tablero-siwa"; };
  var uP = function (s) { return base + "pais/" + s + ".html"; };
  var uH = function (a) { return base + a; };
  // Corrección del 24/9/2026 (cobertura subnacional): lleva a la capa por
  // unidad, con el país puesto y el nombre de la unidad en `?unidad=`, que
  // subnacional.html usa para dejar la búsqueda de la página ya escrita y
  // resaltada —el mismo mecanismo que el cuadro "Buscar" de esa vista—.
  var uU = function (u) { return base + "subnacional.html?pais=" + encodeURIComponent(u.iso) + "&unidad=" + encodeURIComponent(u.nombre); };

  function saludar() {
    hilo.innerHTML = ""; ctxPais = null;
    burbuja("gs-bot", "Hola. Soy la guía de SIWA. Te llevo a un tema, a un país, a una provincia o a una herramienta —y te cuento cómo funciona el registro.\n\n¿Por dónde arrancamos?");
    var chipsEje = DATOS.ejes_orden.map(function (e) { return { t: e, eje: 1, fn: function () { abrirEje(e); } }; });
    chipsEje.push({ t: "Un país", fn: function () {
      burbuja("gs-yo", "Un país");
      burbuja("gs-bot", "Escribí el país abajo (p. ej. <b>Perú</b>) y te llevo a su ficha. O nombralo con un tema, como <i>“corrupción en México”</i>, o con una provincia, como <i>“Antioquia”</i>."); } });
    chipsEje.push({ t: "Herramientas", fn: mostrarHerr });
    chipsEje.push({ t: "¿Qué es SIWA?", fn: function () { responder("que es siwa"); } });
    chips(chipsEje);
  }
  function abrirEje(e) {
    burbuja("gs-yo", e);
    burbuja("gs-bot", "Temas de <b>" + e + "</b> —tocá uno:");
    var temas = DATOS.temas.filter(function (t) { return t.eje === e; });
    chips(temas.map(function (t) { return { t: t.rotulo, fn: function () { llevarTema(t); } }; }));
  }
  function mostrarHerr() {
    burbuja("gs-yo", "Herramientas");
    var d = burbuja("gs-bot", "SIWA tiene estas vistas para explorar:");
    DATOS.herramientas.forEach(function (h) { d.innerHTML += card("Herramienta", h.rotulo, uH(h.archivo)); });
    seguir();
  }
  function llevarTema(t, pais) {
    var d = burbuja("gs-bot", pais
      ? "Te dejo <b>" + t.rotulo + "</b> en la región y la ficha de <b>" + pais.rotulo + "</b>:"
      : "Ahí va <b>" + t.rotulo + "</b>:");
    d.innerHTML += card("Tema · región", t.rotulo, uT(t.slug));
    if (pais) d.innerHTML += card("País", pais.rotulo, uP(pais.slug));
    seguir();
  }
  function llevarPais(p) {
    var d = burbuja("gs-bot", "Ficha de <b>" + p.rotulo + "</b> —lo que publica y lo que no, con su fuente:");
    d.innerHTML += card("País", p.rotulo, uP(p.slug));
    ctxPais = p; seguir();
  }
  // Cobertura subnacional (24/9/2026): lleva a la provincia/departamento/estado
  // exacto dentro de la capa subnacional del país correspondiente.
  function llevarUnidad(u) {
    var d = burbuja("gs-bot", "Ahí va <b>" + u.nombre + "</b> (" + u.pais + "), en la capa subnacional:");
    d.innerHTML += card("Provincia / departamento / estado", u.nombre + " — " + u.pais, uU(u));
    seguir();
  }
  function seguir() {
    chips([
      { t: "Buscar otra cosa", fn: function () { burbuja("gs-bot", "Dale, escribila abajo."); entrada.focus(); } },
      { t: "¿De dónde salen los datos?", fn: function () { responder("de donde salen los datos"); } },
      { t: "Volver al inicio", fn: saludar }
    ]);
  }
  function responder(texto) {
    var q = norm(texto), qt = palabrasSignificativas(q);
    burbuja("gs-yo", texto);
    var ft = null, fp = 0;
    DATOS.faq.forEach(function (f) { var p = puntajeTotal(coincidencia(qt, f.q)); if (p > fp) { fp = p; ft = f; } });
    var tU = mejor(qt, DATOS.unidades || [], "iso");
    var tP = mejor(qt, DATOS.paises, "slug");
    var tT = mejor(qt, DATOS.temas, "slug");
    var tH = mejor(qt, DATOS.herramientas, "archivo");
    var pU = tU ? tU.p : -1, pP = tP ? tP.p : -1, pT = tT ? tT.p : -1;
    var mx = Math.max(pT, pP, pU, 0);
    if (ft && fp >= 2 && fp >= mx) { burbuja("gs-bot", ft.r); seguir(); return; }

    // 1) Unidad subnacional, sólo cuando su coincidencia EXACTA (sin prefijos)
    // explica la consulta mejor que un país o un tema. Así "méxico" —que
    // empata el país con el estado homónimo por partes iguales— sigue yendo a
    // la ficha del país, y "santa fe" —que empata la unidad con un tema que
    // sólo la nombra entre paréntesis— va a la provincia.
    var pUx = tU ? tU.pExacto : -1, pPx = tP ? tP.pExacto : -1, pTx = tT ? tT.pExacto : -1;
    if (tU && pUx > pPx && pUx >= pTx) {
      if (tU.empatados.length > 1) {
        mostrarAmbiguedad("Hay más de un lugar con ese nombre —tocá el que buscás:", tU.empatados,
          function (u) { return card("Provincia / departamento / estado", u.nombre + " — " + u.pais, uU(u)); });
      } else {
        llevarUnidad(tU.it);
      }
      return;
    }

    // 2) País ambiguo: si el empate lo produce una sola palabra corta y
    // genérica ("san", "santa"…), no se combina con el tema a ciegas —se
    // pregunta cuál país— (caso "san juan" cuando la provincia no ganó arriba).
    if (tP && tP.empatados.length > 1) {
      mostrarAmbiguedad("Hay más de un país que podría ser —tocá el que buscás:", tP.empatados,
        function (p) { return card("País", p.rotulo, uP(p.slug)); });
      return;
    }

    if (tP && tT) { llevarTema(tT.it, tP.it); return; }
    if (tT) { llevarTema(tT.it, ctxPais); return; }
    if (tP) { llevarPais(tP.it); return; }
    if (tH) { var d = burbuja("gs-bot", "Creo que buscás esta herramienta:");
      d.innerHTML += card("Herramienta", tH.it.rotulo, uH(tH.it.archivo)); seguir(); return; }
    burbuja("gs-bot", "No lo tengo con ese nombre —y prefiero no adivinar. Probá con un tema (homicidios, corrupción, agua potable…), un país, una provincia/departamento/estado, o una herramienta.");
    chips([{ t: "Ver los temas", fn: saludar }, { t: "Herramientas", fn: mostrarHerr }]);
  }

  /* ---------- arranque ---------- */
  function abrir() {
    document.body.classList.add("gs-on");
    if (!arrancado && DATOS) { saludar(); arrancado = true; }
    if (entrada) entrada.focus();
  }
  function cerrar() { document.body.classList.remove("gs-on"); }

  function iniciar() {
    montarDom();
    hilo = document.getElementById("gs-hilo");
    entrada = document.getElementById("gs-entrada");
    document.getElementById("gs-lanzador").onclick = function () {
      document.body.classList.contains("gs-on") ? cerrar() : abrir();
    };
    document.getElementById("gs-x").onclick = cerrar;
    document.getElementById("gs-globo").onclick = abrir;
    document.getElementById("gs-ir").onclick = function () {
      var v = entrada.value.trim(); if (v) { responder(v); entrada.value = ""; }
    };
    entrada.addEventListener("keydown", function (e) { if (e.key === "Enter") document.getElementById("gs-ir").click(); });
    // Traer el catálogo. Si falla, la burbuja no aparece: mejor nada que algo roto.
    fetch(datosUrl, { cache: "no-cache" }).then(function (r) { return r.json(); }).then(function (d) {
      DATOS = d;
    }).catch(function () {
      var l = document.getElementById("gs-lanzador"), g = document.getElementById("gs-globo");
      if (l) l.style.display = "none"; if (g) g.style.display = "none";
    });
  }

  if (document.body) iniciar();
  else document.addEventListener("DOMContentLoaded", iniciar);
})();
