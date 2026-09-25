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

  // Paleta del manual (idéntica a las variables de index.html)
  var M = {
    navy:        '#00121E', // azul de la casa
    navyHondo:   '#07131E',
    grisAzul:    '#667B89',
    purpura:     '#8C00E0', // violeta del símbolo
    purpuraClaro:'#BA66EC',
    violetaHondo:'#5B1E8C',
    teal:        '#3FA796', // "mejor" / ok
    naranja:     '#FB6500', // NARANJA = SEÑAL. No va en rotación.
    alerta:      '#C23B22',
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

  // Rotación categórica: SIN naranja (es señal).  Cada modo tiene la suya, porque
  // un color no se lee igual sobre blanco que sobre navy: en claro van tintas
  // oscuras de la paleta; en oscuro, tintes claros de la MISMA familia. El navy
  // #00121E no puede ser color de serie en oscuro -desaparece sobre el panel navy-.
  var ROTACION_CLARO = [
    M.navy, M.grisAzul, M.purpura, M.teal, M.purpuraClaro, M.violetaHondo, M.texto2
  ];
  var ROTACION_OSCURO = [
    '#A9BED0', // acero claro  (reemplaza al navy como ancla)
    '#4FBFAE', // teal claro   (aclarado de #3FA796)
    '#BA66EC', // violeta claro (token del manual)
    '#E0A6F7', // violeta más claro (tinte)
    '#7FB0D6', // azul medio claro
    '#C7D2E0'  // texto claro  (neutro)
  ];

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

      // Rampa secuencial (mapa coroplético / visualMap).  Claro -> navy.
      // El extremo "peor" puede reemplazarse a mano por naranja (señal).
      visualMap: {
        textStyle: { color: texto2, fontFamily: FUENTE_N },
        inRange: {
          color: oscuro
            ? ['#12324a', '#1f5f7a', '#3FA796', '#8FD6C8']
            : ['#DCEDEA', '#8FD0C4', '#3FA796', '#0E5C50', M.navy]
        }
      },

      // Barra de puntaje / gauge
      gauge: {
        axisLine: { lineStyle: { color: [[1, linea]] } },
        progress: { show: true, itemStyle: { color: M.teal } },
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
