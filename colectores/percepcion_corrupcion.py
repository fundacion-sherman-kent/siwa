"""Percepción de corrupción — el índice de Transparency International.

El registro ya mide corrupción de dos maneras: **control de la corrupción** del
Banco Mundial y **corrupción política** de V-Dem. Faltaba la tercera, que además
es la más citada del mundo: el **Índice de Percepción de la Corrupción (IPC)**.

Tres medidas de lo mismo que no siempre coinciden
-------------------------------------------------
Y eso no es un defecto: es el dato. Las tres se construyen distinto y a veces
ordenan distinto a los mismos Estados. **Cuando coinciden, el juicio se apoya
mejor; cuando discrepan, el analista tiene que ir a ver por qué.** El registro
publica las tres por separado y no las promedia.

Lo que el índice mide, y lo que no
----------------------------------
**Mide percepción, no hechos.** Es un promedio de evaluaciones de especialistas
y de encuestas a empresarios sobre cuánta corrupción creen que hay en el sector
público. **No cuenta casos, ni condenas, ni dinero.** Un país que empieza a
perseguir la corrupción puede empeorar su puntaje porque se habla más del tema.

Y lleva su propia incertidumbre declarada: cada puntaje viene con **error
estándar** y con un **intervalo de confianza** que el propio productor calcula.
Dos Estados cuyos intervalos se superponen **no están ordenados entre sí**, por
más que la tabla los muestre uno arriba del otro. Esa advertencia viaja en cada
ficha.

La licencia manda una regla
---------------------------
Transparency International publica bajo **CC BY-ND 4.0**: se puede reproducir y
redistribuir, **no derivar**. Por eso los valores se publican **tal cual**, con
su atribución, y **este índice NO entra a ningún cálculo compuesto** del
registro. Es la misma prudencia que ya se aplica con otras fuentes de licencia
restrictiva.
"""

from __future__ import annotations

import io
import re
import ssl
import urllib.error
import urllib.request
import zipfile

import comun
import geo

URL = "https://images.transparencycdn.org/images/CPI2024-Results-and-trends.xlsx"
FUENTE = "Transparency International — Índice de Percepción de la Corrupción"
URL_FUENTE = "https://www.transparency.org/en/cpi"
LICENCIA = "CC BY-ND 4.0 © Transparency International"
NAVEGADOR = comun.AGENTE

HOJA_ANIO = 1        # «CPI 2024»: puntaje, puesto, error e intervalo
HOJA_SERIE = 2       # «CPI Timeseries»: la serie por año
CONTROL = "URY"      # está en el índice desde el comienzo; si falta, falló la lectura
MINIMO_PAISES = 150  # la edición verificada trae 180

# El encabezado que se verificó. Si la planilla cambia de forma, se declara en
# vez de leer columnas por su posición y publicar el puesto como si fuera el
# puntaje, que es exactamente el error que una lectura posicional comete sola.
ESPERADO = {"A": "country", "B": "iso3", "D": "cpi 2024 score", "E": "rank"}


def _ficha(serie, campo):
    """La forma que usa todo el registro para cualquier serie."""
    puntos = [(x["anio"], x[campo]) for x in serie
              if x.get(campo) is not None and x.get("anio")]
    if not puntos:
        return None
    puntos.sort()
    anio, valor = puntos[-1]
    ant = puntos[-2] if len(puntos) >= 2 else None
    return {
        "valor": valor, "anio": anio,
        "anio_anterior": ant[0] if ant else None,
        "valor_anterior": ant[1] if ant else None,
        "variacion_pct": (round((valor - ant[1]) / abs(ant[1]) * 100, 1)
                          if ant and ant[1] else None),
        "anio_inicial": puntos[0][0], "valor_inicial": puntos[0][1],
        "tendencia_ventana_pct": (round((valor - puntos[0][1]) / abs(puntos[0][1]) * 100, 1)
                                  if len(puntos) >= 3 and puntos[0][1] else None),
        "serie": [{"anio": a, "valor": v} for a, v in puntos],
    }


def _cadenas(z: zipfile.ZipFile) -> list:
    """Una entrada por cadena, aunque el formato la parta en fragmentos."""
    crudo = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
    return ["".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)).strip()
            for si in re.findall(r"<si>(.*?)</si>", crudo, re.S)]


def _leer(z: zipfile.ZipFile, hoja: int) -> dict:
    comp = _cadenas(z)
    crudo = z.read(f"xl/worksheets/sheet{hoja}.xml").decode("utf-8", "replace")
    filas = {}
    for numero, cuerpo in re.findall(r"<row[^>]*r=\"(\d+)\"[^>]*>(.*?)</row>", crudo, re.S):
        celdas = {}
        for col, atributos, valor in re.findall(
                r'<c r="([A-Z]+)\d+"([^>]*)>(.*?)</c>', cuerpo, re.S):
            v = re.search(r"<v>(.*?)</v>", valor, re.S)
            if not v:
                continue
            if 't="s"' in atributos:
                try:
                    celdas[col] = comp[int(v.group(1))]
                except (ValueError, IndexError):
                    continue
            else:
                celdas[col] = v.group(1)
        if celdas:
            filas[int(numero)] = celdas
    return filas


def _numero(valor):
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return None
    return int(n) if n == int(n) else round(n, 4)


def _encabezado(filas: dict) -> tuple:
    """La fila de encabezado, hallada por lo que dice y no por su número."""
    for numero in sorted(filas):
        celdas = filas[numero]
        rotulos = {c: str(v).strip().lower() for c, v in celdas.items()}
        if rotulos.get("B") == "iso3" and "country" in rotulos.get("A", ""):
            return numero, rotulos
    raise RuntimeError(
        "No se halló la fila de encabezado con «ISO3». La planilla cambió de forma "
        "y NO se leen columnas por su posición: eso publicaría el puesto como si "
        "fuera el puntaje.")


def recolectar():
    try:
        peticion = urllib.request.Request(URL, headers={"User-Agent": NAVEGADOR})
        with urllib.request.urlopen(peticion, timeout=180,
                                    context=ssl.create_default_context()) as r:
            crudo = r.read(20_000_000)
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"No se pudo traer la planilla de Transparency International: HTTP {e.code}"
        ) from e

    z = zipfile.ZipFile(io.BytesIO(crudo))
    filas = _leer(z, HOJA_ANIO)
    cabeza, rotulos = _encabezado(filas)
    if not str(rotulos.get("D", "")).startswith("cpi"):
        raise RuntimeError(
            f"La columna del puntaje no dice lo esperado: «{rotulos.get('D')}». "
            "No se publica una lectura a ciegas.")

    # El año sale del propio rótulo —«CPI 2024 score»— y no se fija a mano: el día
    # que salga la edición siguiente, el registro lo dice solo.
    anio = None
    hallado = re.search(r"(20\d\d)", rotulos.get("D", ""))
    if hallado:
        anio = int(hallado.group(1))

    columnas = {v: c for c, v in rotulos.items()}
    col_iso = "B"
    col_puntaje = "D"
    col_puesto = columnas.get("rank", "E")
    col_error = next((c for c, v in rotulos.items() if "standard error" in v), None)
    col_fuentes = next((c for c, v in rotulos.items() if "number of sources" in v), None)
    col_bajo = next((c for c, v in rotulos.items() if v.startswith("lower")), None)
    col_alto = next((c for c, v in rotulos.items() if v.startswith("upper")), None)

    porIso, total = {}, 0
    for numero in sorted(filas):
        if numero <= cabeza:
            continue
        celdas = filas[numero]
        iso = str(celdas.get(col_iso) or "").strip().upper()
        if len(iso) != 3:
            continue
        total += 1
        porIso[iso] = {
            "puntaje": _numero(celdas.get(col_puntaje)),
            "puesto": _numero(celdas.get(col_puesto)),
            "error_estandar": _numero(celdas.get(col_error)) if col_error else None,
            "fuentes_del_indice": _numero(celdas.get(col_fuentes)) if col_fuentes else None,
            "intervalo_bajo": _numero(celdas.get(col_bajo)) if col_bajo else None,
            "intervalo_alto": _numero(celdas.get(col_alto)) if col_alto else None,
            "nombre_en_la_fuente": str(celdas.get("A") or "").strip(),
        }

    # PROBAR ANTES DE AFIRMAR: sin el control o con pocos países, falló la lectura.
    if total < MINIMO_PAISES or CONTROL not in porIso or porIso[CONTROL]["puntaje"] is None:
        raise RuntimeError(
            f"Se leyeron {total} países y el control ({CONTROL}) "
            f"{'no tiene puntaje' if CONTROL in porIso else 'NO está'}. Con menos de "
            f"{MINIMO_PAISES} o sin el control, lo que falló es la lectura de la "
            "planilla y no el índice. No se publica.")

    # La serie por año, leída por el rótulo de cada columna y no por su lugar.
    serie_filas = _leer(z, HOJA_SERIE)
    try:
        cabeza_s, rotulos_s = _encabezado(serie_filas)
    except RuntimeError:
        cabeza_s, rotulos_s = None, {}
    porAnio = {}
    if cabeza_s:
        for col, rotulo in rotulos_s.items():
            m = re.match(r"cpi score (20\d\d)", rotulo)
            if m:
                porAnio[col] = int(m.group(1))
    series: dict = {}
    if porAnio:
        for numero in sorted(serie_filas):
            if numero <= (cabeza_s or 0):
                continue
            celdas = serie_filas[numero]
            iso = str(celdas.get("B") or "").strip().upper()
            if len(iso) != 3:
                continue
            puntos = [{"anio": a, "puntaje": _numero(celdas.get(c))}
                      for c, a in sorted(porAnio.items(), key=lambda x: x[1])
                      if _numero(celdas.get(c)) is not None]
            if puntos:
                series[iso] = puntos

    registros = []
    for pais in geo.padron():
        dato = porIso.get(pais["iso"])
        registro = {"iso": pais["iso"], "pais": pais["pais"], "bloque": pais["bloque"],
                    "en_el_indice": bool(dato and dato["puntaje"] is not None)}
        if registro["en_el_indice"]:
            registro.update(dato)
            serie = series.get(pais["iso"]) or []
            if len(serie) > 1:
                registro["serie"] = serie
                registro["variacion"] = round(serie[-1]["puntaje"] - serie[0]["puntaje"], 1)
                registro["desde"] = serie[0]["anio"]
        else:
            registro["por_que_no"] = (
                "El índice no evalúa a este Estado en esta edición: no alcanza la "
                "cantidad mínima de fuentes independientes que exige el método.")
        registros.append(registro)
    registros.sort(key=lambda r: (not r["en_el_indice"], -(r.get("puntaje") or 0), r["pais"]))

    evaluados = [r for r in registros if r["en_el_indice"]]
    sin_evaluar = [r["pais"] for r in registros if not r["en_el_indice"]]

    vacios = [
        "**Mide percepción, no hechos.** Es un promedio de evaluaciones de "
        "especialistas y de encuestas a empresarios sobre cuánta corrupción creen que "
        "hay en el sector público. **No cuenta casos, ni condenas, ni dinero.** Un país "
        "que empieza a perseguir la corrupción puede empeorar su puntaje porque se "
        "habla más del tema.",
        "**Dos Estados cuyos intervalos de confianza se superponen NO están ordenados "
        "entre sí**, por más que la tabla los muestre uno arriba del otro. El propio "
        "productor publica el error estándar y el intervalo, y acá se publican con el "
        "puntaje para que la comparación se haga con ellos a la vista.",
        "**El registro mide corrupción de tres maneras y no las promedia.** Están "
        "también el control de la corrupción del Banco Mundial y la corrupción política "
        "de V-Dem. Se construyen distinto y a veces ordenan distinto a los mismos "
        "Estados: **cuando coinciden, el juicio se apoya mejor; cuando discrepan, hay "
        "que ir a ver por qué.**",
        "**La licencia del productor es CC BY-ND 4.0: permite reproducir, no derivar.** "
        "Por eso los valores se publican tal cual, con su atribución, y **este índice no "
        "entra a ningún cálculo compuesto** del registro.",
        "**El puntaje no es comparable hacia atrás sin cuidado.** El método se rehizo en "
        "2012 y la serie que se publica arranca ahí. Aun dentro de la serie, un cambio "
        "de uno o dos puntos suele estar dentro del error del propio índice.",
        "La cantidad de fuentes que alimentan el puntaje de cada Estado varía —se "
        "publica en cada ficha—: un puntaje construido con tres fuentes es más frágil "
        "que uno construido con nueve, aunque la tabla los muestre igual.",
    ]
    if sin_evaluar:
        vacios.append(
            f"**{len(sin_evaluar)} Estados del padrón no están en el índice**: "
            f"{', '.join(sin_evaluar)}. No dice nada sobre su corrupción: dice que no "
            "alcanzan la cantidad mínima de fuentes independientes que el método exige.")

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=2,
        corroborado=False,
        nota=("Organización no gubernamental con metodología publicada, revisada por "
              "terceros y estable desde 2012. Fiabilidad B y no A porque es un índice "
              "compuesto de percepciones, no una medición directa. Lo que se registra es "
              "el puntaje que el índice asignó, con su incertidumbre declarada."),
    )

    for r in registros:
        f = _ficha(r.get("serie") or [], "puntaje")
        r["indicadores"] = {"percepcion_corrupcion": f} if f else {}

    return comun.escribir(
        colector="percepcion_corrupcion",
        capa="publico",
        fuente=FUENTE,
        url_fuente=URL_FUENTE,
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            # LA MATERIA. El conjunto existía y no se podía pintar, cruzar ni contar:
            # alimentaba una vista propia. La corrupción la medían el Banco Mundial y
            # V-Dem, las dos por evaluación de especialistas; esta combina trece
            # fuentes independientes y publica su error estándar.
            "indicadores": [{
                "clave": "percepcion_corrupcion",
                "rotulo": "Percepción de corrupción",
                "eje": "Gobernanza",
                "unidad": "puntaje de 0 a 100",
                "mas_es_peor": False,
                "origen": "Transparency International — Índice de Percepción de la Corrupción",
                "cautela": "MIDE PERCEPCIÓN, no hechos: combina evaluaciones de especialistas "
                           "y encuestas a empresarios. Cien es el mejor puntaje posible. No "
                           "se compara con el Índice de Opacidad de esta casa, que mide actos "
                           "observables: son dos cosas distintas y confundirlas seria un error.",
            }],
            "cobertura": {"percepcion_corrupcion": sum(
                1 for r in registros if (r.get("indicadores") or {}).get("percepcion_corrupcion"))},
            "resumen": {
                "anio": anio,
                "estados_en_el_indice": len(evaluados),
                "estados_del_padron": len(registros),
                "paises_en_el_indice": total,
                "mejor": evaluados[0]["pais"] if evaluados else None,
                "peor": evaluados[-1]["pais"] if evaluados else None,
                "consultado": comun.ahora(),
            },
            "licencia": LICENCIA,
            "escala": ("De 0 a 100, donde 0 es la percepción de mayor corrupción y 100 "
                       "la de menor. No entra a ningún índice compuesto del registro."),
        },
    )


if __name__ == "__main__":
    comun.correr("percepcion_corrupcion", recolectar)
