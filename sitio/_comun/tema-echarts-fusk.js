/* ============================================================================
   TEMA ECHARTS · IDENTIDAD FUSK  (prototipo, acta 25/9/2026)
   ----------------------------------------------------------------------------
   Un solo archivo con la paleta del manual. Registra dos temas en ECharts:
     · 'fusk'         -> fondo claro (rige por defecto)
     · 'fusk-oscuro'  -> fondo oscuro (opcional, lo elige quien mira)

   La idea es la misma que _comun/sistema-visual.js pero para los gráficos: la
   paleta se carga UNA vez acá y rige en el tablero de SIWA y en los informes,
   para que se vean iguales adentro y afuera.

   REGLA DE LA CASA que el tema respeta:
   - El NARANJA #FB6500 es SEÑAL, no color de rotación. No entra en la lista de
     series. Se usa a mano para resaltar la serie/barra que importa (`colorSenal`
     queda expuesto para eso).
   - Tipografía Inter; los ejes de valor y los números en JetBrains Mono.
   - Fondo transparente: el gráfico se apoya en el panel de la página.
   ========================================================================== */
(function (global) {
  'use strict';

  var FUENTE  = "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
  var FUENTE_N = "'JetBrains Mono', ui-monospace, 'Consolas', monospace";

  // FUENTE ÚNICA DE LA PALETA: se lee de `_comun/paleta-fusk.css` en vivo (los tokens
  // --fusk-*), con los valores del manual como respaldo si ese CSS no está cargado
  // (por ejemplo en una demostración suelta). Así el tema de gráficos y las páginas
  // usan exactamente el MISMO archivo de paleta.
  function cvar(nombre, respaldo){
    try{
      var v = getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
      return v || respaldo;
    }catch(e){ return respaldo; }
  }
  var M = {
    navy:        cvar('--fusk-navy',          '#00121E'), // azul de la casa
    navyHondo:   cvar('--fusk-navy-hondo',    '#07131E'),
    grisAzul:    cvar('--fusk-gris-azul',     '#667B89'), // secundario (filetes = este gris con opacidad)
    violetaHondo:cvar('--fusk-violeta-hondo', '#460070'),
    purpura:     cvar('--fusk-violeta',       '#8C00E0'), // violeta del símbolo
    purpuraClaro:cvar('--fusk-violeta-claro', '#BA66EC'),
    naranja:     cvar('--fusk-naranja',       '#FB6500'), // NARANJA = SEÑAL. No va en rotación.
    crema:       cvar('--fusk-crema',         '#F9F9F7'),
    grisTitulo:  cvar('--fusk-gris-titulo',   '#C6C6C5'),
    // --- Los nueve de arriba son la PALETA CERRADA del manual (paleta-fusk.css). ---
    // Abajo van sólo neutros de TEXTO e interfaz (tinta y separadores), no colores
    // de marca. El verde/rojo del semáforo del sitio NO entran acá: son funcionales.
    // claro
    papel:       '#F7F7F5',
    panel:       '#FFFFFF',
    texto:       '#1A2430',
    texto2:      '#46566A',
    tenue:       '#5A6B7D',
    linea:       '#E3DCD0',
    lineaSuave:  '#EFEAE0',
    // oscuro
    textoOsc:    '#C7D2E0',
    texto2Osc:   '#9FB0C4',
    tenueOsc:    '#7D90A8',
    lineaOsc:    'rgba(255,255,255,.16)',
    lineaSuaveOsc:'rgba(255,255,255,.07)'
  };

  // Rotación categórica: SÓLO colores del manual, SIN naranja (es señal). Cada modo
  // usa los que se leen sobre su fondo: el navy no puede ser color de serie en
  // oscuro (desaparece sobre el panel navy), así que en oscuro entran los violetas
  // claros y los neutros claros del manual. NO se inventan colores intermedios.
  var ROTACION_CLARO = [
    M.navy,          // #00121E
    M.grisAzul,      // #667B89
    M.purpura,       // #8C00E0
    M.purpuraClaro,  // #BA66EC
    M.violetaHondo   // #460070
  ];
  var ROTACION_OSCURO = [
    M.purpuraClaro,  // #BA66EC
    M.grisTitulo,    // #C6C6C5
    M.purpura,       // #8C00E0
    M.grisAzul,      // #667B89
    M.crema          // #F9F9F7
  ];
  // Rampa secuencial (mapa / visualMap): un solo tono, el VIOLETA -«la energía de
  // marca»-, del claro al navy. Todos son colores del manual.
  var RAMPA_CLARO  = [M.crema, M.purpuraClaro, M.purpura, M.violetaHondo, M.navy];
  var RAMPA_OSCURO = [M.violetaHondo, M.purpura, M.purpuraClaro];

  function tema(modo) {
    var oscuro = modo === 'oscuro';
    var texto   = oscuro ? M.textoOsc  : M.texto;
    var texto2  = oscuro ? M.texto2Osc : M.texto2;
    var tenue   = oscuro ? M.tenueOsc  : M.tenue;
    var linea   = oscuro ? M.lineaOsc  : M.linea;
    var lineaSuave = oscuro ? M.lineaSuaveOsc : M.lineaSuave;
    var panelTip = oscuro ? '#0E2135' : '#FFFFFF';

    var ejeLinea = { show: true, lineStyle: { color: linea } };
    var ejeLabel = { color: texto2, fontFamily: FUENTE, fontSize: 12 };
    var ejeLabelN = { color: texto2, fontFamily: FUENTE_N, fontSize: 12 };
    var partido  = { show: true, lineStyle: { color: lineaSuave, type: 'dashed' } };

    return {
      color: oscuro ? ROTACION_OSCURO : ROTACION_CLARO,
      backgroundColor: 'transparent',
      textStyle: { fontFamily: FUENTE, color: texto },

      title: {
        textStyle: { fontFamily: FUENTE, color: texto, fontWeight: 700, fontSize: 16 },
        subtextStyle: { fontFamily: FUENTE, color: tenue, fontSize: 12 }
      },

      legend: {
        textStyle: { fontFamily: FUENTE, color: texto2, fontSize: 12 },
        icon: 'roundRect', itemWidth: 12, itemHeight: 8
      },

      tooltip: {
        backgroundColor: panelTip,
        borderColor: linea,
        borderWidth: 1,
        textStyle: { fontFamily: FUENTE, color: texto, fontSize: 12 },
        extraCssText: 'box-shadow:0 6px 24px rgba(0,18,30,.12); border-radius:8px;',
        axisPointer: { lineStyle: { color: tenue }, crossStyle: { color: tenue } }
      },

      categoryAxis: {
        axisLine: ejeLinea, axisTick: { show: false },
        axisLabel: ejeLabel, splitLine: { show: false },
        splitArea: { show: false }
      },
      valueAxis: {
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: ejeLabelN, splitLine: partido
      },
      logAxis:  { axisLabel: ejeLabelN, splitLine: partido },
      timeAxis: { axisLine: ejeLinea, axisLabel: ejeLabel, splitLine: { show: false } },

      // Series
      line: {
        smooth: false, symbol: 'circle', symbolSize: 6,
        lineStyle: { width: 2.5 },
        emphasis: { focus: 'series' }
      },
      bar: {
        itemStyle: { borderRadius: [3, 3, 0, 0] },
        emphasis: { focus: 'series' }
      },
      pie: {
        itemStyle: { borderColor: oscuro ? M.navyHondo : M.panel, borderWidth: 2 },
        label: { color: texto2, fontFamily: FUENTE }
      },
      scatter: { itemStyle: { opacity: 0.85 } },
      radar: {
        axisName: { color: texto2, fontFamily: FUENTE },
        splitLine: { lineStyle: { color: lineaSuave } },
        splitArea: { areaStyle: { color: ['transparent'] } }
      },

      // Rampa secuencial (mapa coroplético / visualMap): un solo tono, el violeta
      // del manual, del claro al navy. Todos colores del manual.
      visualMap: {
        textStyle: { color: texto2, fontFamily: FUENTE_N },
        inRange: { color: oscuro ? RAMPA_OSCURO : RAMPA_CLARO }
      },

      // Barra de puntaje / gauge -> violeta de marca (no verde).
      gauge: {
        axisLine: { lineStyle: { color: [[1, linea]] } },
        progress: { show: true, itemStyle: { color: M.purpura } },
        detail: { fontFamily: FUENTE_N, color: texto },
        title:  { fontFamily: FUENTE, color: texto2 }
      }
    };
  }

  function registrar(echarts) {
    if (!echarts || !echarts.registerTheme) return false;
    echarts.registerTheme('fusk',        tema('claro'));
    echarts.registerTheme('fusk-oscuro', tema('oscuro'));
    return true;
  }

  // Se expone la paleta y el color de señal para uso a mano en cada gráfico.
  var API = {
    registrar: registrar,
    rotacionClaro: ROTACION_CLARO.slice(),
    rotacionOscuro: ROTACION_OSCURO.slice(),
    colorSenal: M.naranja,   // NARANJA = resaltar la serie/barra que importa
    paleta: M
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  global.TemaEchartsFUSK = API;

  // Autorregistro si ECharts ya está cargado
  if (global.echarts) registrar(global.echarts);

})(typeof window !== 'undefined' ? window : this);
