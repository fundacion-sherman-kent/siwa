/* Franja de cabecera OFICIAL de SIWA — fuente única.
   La misma franja del index (sitio/index.html): fondo blanco, logo FUSK completo,
   lockup SIWA en naranja (#FB6500, 19px) con el isotipo de ondas/radar después
   de la A, filete vertical naranja entre el logo y el lockup, control de tema,
   estado "al día" en vivo, reloj UTC + hora local, y el filete naranja del
   manual bajo toda la barra. Se inyecta en cualquier subpágina con
   <script src="_comun/cabecera-siwa.js"></script>. Actualizada el 23/9/2026 para
   igualar la cabecera nueva del index (antes: SIWA en navy, sin radar).
   Regla de la casa: toda página o subpágina conserva ESTA franja, idéntica. */
(function () {
  var script = document.currentScript;
  // Base = carpeta sitio/ (la que contiene _comun/). Robusto a cualquier profundidad.
  var base = script.src.replace(/_comun\/[^\/]*$/, "");
  var logo = base + "marca/fusk-logo-nombre-color.png";
  var ayuda = base + "index.html";
  var relojUrl = new URL("../datos/publico/reloj-actualidad.json", base).href;

  var css = "" +
    ".siwa-topbar{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;" +
      "padding:12px 28px;background:#FFFFFF;border-bottom:3px solid #FB6500;position:sticky;top:0;z-index:600;" +
      "font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;}" +
    ".siwa-topbar .brand{display:flex;align-items:center;gap:18px;}" +
    ".siwa-topbar .marca-enlace{display:inline-flex;text-decoration:none;}" +
    ".siwa-topbar .marca-enlace:hover img{opacity:.82;}" +
    ".siwa-topbar .brand img{height:72px;width:auto;flex:0 0 auto;object-fit:contain;display:block;}" +
    ".siwa-topbar .brand .sep{width:2px;height:44px;background:#FB6500;}" +
    ".siwa-topbar .brand h1{font-size:19px;margin:0;font-weight:700;letter-spacing:2px;color:#FB6500;" +
      "display:inline-flex;align-items:center;gap:.4em;line-height:1;}" +
    ".siwa-topbar .brand h1 .siwa-onda{width:1em;height:1em;flex:0 0 auto;display:block;overflow:visible;}" +
    ".siwa-topbar .brand small{display:block;color:#667B89;font-size:10.5px;font-weight:500;letter-spacing:.6px;text-transform:uppercase;}" +
    ".siwa-topbar-right{display:flex;gap:20px;align-items:center;font-size:11px;color:#667B89;}" +
    ".siwa-pill{background:none;border:1px solid rgba(0,18,30,.22);color:#00121E;border-radius:999px;" +
      "padding:6px 14px;font:inherit;font-size:11.5px;cursor:pointer;display:inline-flex;align-items:center;gap:7px;min-height:34px;text-decoration:none;}" +
    ".siwa-pill:hover{border-color:#00121E;}" +
    ".siwa-estado{display:inline-flex;align-items:center;white-space:nowrap;}" +
    ".siwa-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#3FA796;margin-right:6px;box-shadow:0 0 8px #3FA796;}" +
    ".siwa-dot.mal{background:#C23B22;box-shadow:0 0 8px #C23B22;}" +
    ".siwa-mono{font-family:'JetBrains Mono',ui-monospace,monospace;white-space:nowrap;}" +
    ".siwa-mono b{font-weight:600;}" +
    "@media(max-width:760px){.siwa-topbar{padding:8px 14px;gap:10px;}.siwa-topbar .brand img{height:44px;}" +
      ".siwa-topbar .brand .sep{display:none;}.siwa-topbar-right{gap:10px;}" +
      ".siwa-topbar-right .siwa-estado,.siwa-topbar-right .siwa-mono{display:none;}}";

  var st = document.createElement("style");
  st.textContent = css;
  document.head.appendChild(st);

  var bar = document.createElement("div");
  bar.className = "siwa-topbar";
  bar.innerHTML =
    '<div class="brand">' +
      '<a href="https://fundacionkent.org/" target="_blank" rel="noopener" class="marca-enlace" ' +
        'title="Ir a la web de la Fundación Sherman Kent">' +
        '<img src="' + logo + '" alt="FUSK · Fundación Sherman Kent"></a>' +
      '<div class="sep"></div>' +
      '<div><h1><span class="siwa-txt">SIWA</span><svg class="siwa-onda" viewBox="-6 -20 40 40" ' +
        'aria-hidden="true" focusable="false"><g transform="rotate(-15)">' +
        '<circle cx="0" cy="0" r="3.2" fill="#FB6500"/>' +
        '<path d="M0 -8  A8 8 0 0 1 0 8" fill="none" stroke="#00121E" stroke-width="2" stroke-linecap="round"/>' +
        '<path d="M0 -13 A13 13 0 0 1 0 13" fill="none" stroke="#33454F" stroke-width="2" stroke-linecap="round"/>' +
        '<path d="M0 -18 A18 18 0 0 1 0 18" fill="none" stroke="#7E8A94" stroke-width="2" stroke-linecap="round"/>' +
        '</g></svg></h1><small>Reporte de situación · ALC</small></div>' +
    '</div>' +
    '<div class="siwa-topbar-right">' +
      '<a class="siwa-pill" href="' + ayuda + '"><span aria-hidden="true">?</span><span>Cómo se usa</span></a>' +
      '<button class="siwa-pill" id="siwa-tema" type="button" aria-pressed="false">' +
        '<span id="siwa-tema-ico">◐</span><span id="siwa-tema-rot">Fondo oscuro</span></button>' +
      '<span class="siwa-estado" id="siwa-estado"><span class="siwa-dot"></span>Verificando…</span>' +
      '<span class="siwa-mono" id="siwa-reloj" title="Hora universal (UTC) y hora de tu dispositivo">—</span>' +
    '</div>';

  function montar() {
    document.body.insertBefore(bar, document.body.firstChild);
    function fijarAltura() {
      document.documentElement.style.setProperty("--siwa-topbar-h", (bar.offsetHeight || 100) + "px");
    }
    fijarAltura();
    // El logo entra a 72px; hasta que la imagen no carga, la franja mide menos y el
    // rail quedaría tapado. Se recalcula al cargar la imagen y al cargar la página.
    var img = bar.querySelector("img");
    if (img && !img.complete) img.addEventListener("load", fijarAltura);
    window.addEventListener("load", fijarAltura);
    window.addEventListener("resize", fijarAltura);
    // Tema
    var btn = document.getElementById("siwa-tema");
    var rot = document.getElementById("siwa-tema-rot");
    function esOscuro() {
      var t = document.documentElement.getAttribute("data-theme");
      if (t === "dark") return true;
      if (t === "light") return false;
      return window.matchMedia && window.matchMedia("(prefers-color-scheme:dark)").matches;
    }
    rot.textContent = esOscuro() ? "Fondo claro" : "Fondo oscuro";
    btn.setAttribute("aria-pressed", esOscuro() ? "true" : "false");
    btn.addEventListener("click", function () {
      var next = esOscuro() ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      document.body.classList.toggle("claro", next === "light");
      document.body.classList.toggle("oscuro", next === "dark");
      rot.textContent = next === "dark" ? "Fondo claro" : "Fondo oscuro";
      btn.setAttribute("aria-pressed", next === "dark" ? "true" : "false");
      if (typeof window.SIWA_onTema === "function") window.SIWA_onTema(next);
    });
    // Reloj UTC + local
    function dosd(n) { return (n < 10 ? "0" : "") + n; }
    function hhmm(d, utc) { return utc ? dosd(d.getUTCHours()) + ":" + dosd(d.getUTCMinutes()) : dosd(d.getHours()) + ":" + dosd(d.getMinutes()); }
    var reloj = document.getElementById("siwa-reloj");
    function tick() {
      var d = new Date();
      var fecha = d.toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "numeric" });
      reloj.innerHTML = fecha + " · <b>" + hhmm(d, true) + " UTC</b> · " + hhmm(d) + " tu hora";
    }
    tick(); setInterval(tick, 1000);
    // Estado "al día" en vivo, sin caché
    fetch(relojUrl, { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (d) {
      var res = d.resumen || {};
      var e = document.getElementById("siwa-estado");
      var atras = (res.siwa_atrasado || 0) > 0;
      var txt = (res.al_dia != null && res.comprobados != null)
        ? res.al_dia + "/" + res.comprobados + " al día" : "estado verificado";
      e.innerHTML = '<span class="siwa-dot' + (atras ? " mal" : "") + '"></span>' + txt;
      e.title = "SIWA tiene lo último que publican " + (res.al_dia || 0) + " de " + (res.comprobados || 0) + " fuentes comprobadas.";
    }).catch(function () {
      var e = document.getElementById("siwa-estado");
      if (e) e.innerHTML = '<span class="siwa-dot"></span>estado';
    });
  }

  // Cargar la Guía SIWA (asistente de navegación) junto con la franja oficial:
  // una burbuja abajo a la derecha, en toda página que lleve esta cabecera.
  if (!window.__guiaSiwaCargada) {
    window.__guiaSiwaCargada = true;
    // Se carga con la versión del manifiesto (sin caché) para no servir una vieja.
    var cargarGuia = function (v) {
      var gs = document.createElement("script");
      gs.src = base + "_comun/guia-siwa.js" + (v ? ("?v=" + v) : "");
      gs.defer = true;
      document.head.appendChild(gs);
    };
    fetch(base + "_comun/assets.json", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (m) { cargarGuia(m && m["guia-siwa.js"]); })
      .catch(function () { cargarGuia(); });
  }

  if (document.body) montar();
  else document.addEventListener("DOMContentLoaded", montar);
})();
