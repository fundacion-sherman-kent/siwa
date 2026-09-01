"""Índice de Transformación Bertelsmann (BTI).

Qué es
------
Evaluación experta de **137 Estados en desarrollo y en transición**, hecha por dos
especialistas por país —uno del país, uno de fuera— y armonizada en revisión
regional. Publica en escala de 1 a 10 el estado de la democracia, de la economía
y de la **gobernanza**, con un desglose muy fino.

Qué aporta que el registro no tenía
-----------------------------------
1. **Monopolio en el uso de la fuerza.** Si el Estado controla efectivamente su
   territorio, o si hay zonas donde no manda. Es **lo más cercano al control
   territorial** que se encontró gratuito y comparable, y era un vacío declarado:
   el conflicto entre grupos armados cuenta muertes, no territorio.
2. **Aprobación de la democracia.** Otro vacío declarado. **Con una salvedad que
   importa**: no es una encuesta de opinión, es la evaluación de un especialista
   sobre cuánto respaldo social tiene el régimen democrático. No reemplaza a
   Latinobarómetro; se acerca.
3. **Persecución del abuso de función** y **política anticorrupción**, que miden
   impunidad de funcionarios, no percepción de corrupción.

Lo que hay que saber para leerlo
--------------------------------
- **Es evaluación experta, no recuento de hechos.** Dos personas por país.
- **Es bienal y sin serie**: se publica una foto cada dos años, no una línea de
  tiempo. Este registro toma la edición 2024.
- **Solo cubre Estados «en desarrollo o transición»**: los Estados chicos del
  Caribe y los de renta alta quedan fuera del proyecto, no del registro.

Un error propio que quedó documentado
-------------------------------------
La planilla guarda los textos en una tabla compartida, y **una cadena con formato
se parte en varios fragmentos**. Al contarlos como cadenas distintas, **todos los
nombres y rótulos quedaban corridos**: Cuba aparecía con 8,55 de democracia y
Chile con 2,37. Se detectó porque **los números eran imposibles**, no porque el
programa fallara: había leído bien un archivo mal interpretado.
"""

from __future__ import annotations

import io
import re
import urllib.error
import urllib.request
import zipfile

import comun
import geo

URL = "https://bti-project.org/content/en/downloads/data/BTI_2024_Scores.xlsx"
EDICION = 2024
NAVEGADOR = comun.AGENTE

# Nombre en la planilla → ISO del padrón.
NOMBRES = {
    "Argentina": "ARG", "Bolivia": "BOL", "Brazil": "BRA", "Chile": "CHL",
    "Colombia": "COL", "Costa Rica": "CRI", "Cuba": "CUB",
    "Dominican Republic": "DOM", "Ecuador": "ECU", "El Salvador": "SLV",
    "Guatemala": "GTM", "Haiti": "HTI", "Honduras": "HND", "Jamaica": "JAM",
    "Mexico": "MEX", "Nicaragua": "NIC", "Panama": "PAN", "Paraguay": "PRY",
    "Peru": "PER", "Trinidad and Tobago": "TTO", "Uruguay": "URY",
    "Venezuela": "VEN", "Guyana": "GUY", "Suriname": "SUR", "Belize": "BLZ",
}

# Se identifican por su ROTULO, no por la letra de columna: si el proyecto
# reordena la planilla, el colector falla ruidosamente en vez de leer otra cosa.
INDICADORES = [
    {"clave": "monopolio_fuerza", "rotulo_origen": "Q1.1 | Monopoly on the use of force",
     "rotulo": "Monopolio del Estado en el uso de la fuerza", "eje": "Seguridad",
     "unidad": "escala de 1 a 10", "mas_es_peor": False,
     "cautela": "Mide si el Estado controla efectivamente TODO su territorio, o si hay "
                "zonas donde no manda. Es lo mas cercano al CONTROL TERRITORIAL que se "
                "encontro gratuito y comparable: el conflicto entre grupos armados cuenta "
                "muertes, no territorio. Es evaluacion experta, no medicion de campo."},
    {"clave": "intensidad_conflicto", "rotulo_origen": "Q13.3 | Conflict intensity",
     "rotulo": "Intensidad del conflicto interno", "eje": "Seguridad",
     "unidad": "escala de 1 a 10, más alto es menos conflicto", "mas_es_peor": False,
     "cautela": "ATENCION A LA ESCALA: en este indicador un valor ALTO significa MENOS "
                "conflicto. Mide cuanto pesan las divisiones etnicas, religiosas o "
                "sociales en la vida politica."},
    {"clave": "administracion_basica", "rotulo_origen": "Q1.4 | Basic administration",
     "rotulo": "Administracion basica del Estado", "eje": "Gobernanza",
     "unidad": "escala de 1 a 10", "mas_es_peor": False,
     "cautela": "Si existe una estructura administrativa que funcione en todo el "
                "territorio: no si las leyes son buenas, sino si hay quien las aplique "
                "donde tiene que aplicarlas."},
    {"clave": "aprobacion_democracia", "rotulo_origen": "Q5.3 | Approval of democracy",
     "rotulo": "Aprobacion social de la democracia", "eje": "Gobernanza",
     "unidad": "escala de 1 a 10", "mas_es_peor": False,
     "cautela": "NO ES UNA ENCUESTA. Es la evaluacion de un especialista sobre cuanto "
                "respaldo social tiene el regimen democratico en ese pais. Se acerca a la "
                "PERCEPCION DEMOCRATICA que este registro declaraba como vacio, pero NO "
                "la reemplaza: Latinobarometro y el Barometro de las Americas preguntan a "
                "la gente, esto no."},
    {"clave": "persecucion_abuso", "rotulo_origen": "Q3.3 | Prosecution of office abuse",
     "rotulo": "Persecución del abuso de función pública", "eje": "Gobernanza",
     "unidad": "escala de 1 a 10", "mas_es_peor": False,
     "cautela": "Si los funcionarios que abusan de su cargo son efectivamente procesados. "
                "Mide IMPUNIDAD, que es distinto de percepcion de corrupcion: un pais "
                "puede tener mala fama y buena persecucion, o al reves."},
    {"clave": "politica_anticorrupcion", "rotulo_origen": "Q15.3 | Anti-corruption policy",
     "rotulo": "Politica anticorrupcion", "eje": "Gobernanza",
     "unidad": "escala de 1 a 10", "mas_es_peor": False,
     "cautela": "Si existen y funcionan los mecanismos de integridad: declaraciones "
                "patrimoniales, auditoria, contrataciones abiertas. Mide el andamiaje, no "
                "el resultado."},
    {"clave": "actores_antidemocraticos", "rotulo_origen": "Q16.2 | Anti-democratic actors",
     "rotulo": "Control sobre actores antidemocraticos", "eje": "Gobernanza",
     "unidad": "escala de 1 a 10", "mas_es_peor": False,
     "cautela": "Capacidad del gobierno de contener a quienes buscan bloquear o revertir "
                "el orden democratico. Un valor bajo indica actores con poder de veto "
                "fuera de las urnas."},
    {"clave": "indice_gobernanza", "rotulo_origen": "G | Governance Index",
     "rotulo": "Indice de gobernanza", "eje": "Gobernanza",
     "unidad": "escala de 1 a 10", "mas_es_peor": False,
     "cautela": "Resumen de conduccion, uso de recursos, construccion de consensos y "
                "cooperacion internacional. Es un promedio de evaluaciones expertas: "
                "sirve para ordenar, no para medir con precision de decimales."},
]


def _cadenas(z: zipfile.ZipFile) -> list:
    """Una entrada por cadena, aunque el formato la parta en fragmentos.

    Este es el punto donde se cometio el error: contar cada fragmento como una
    cadena distinta corre TODOS los indices y hace que la planilla se lea
    entera pero mal. Se resuelve juntando los fragmentos de cada <si>.
    """
    crudo = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
    return ["".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)).strip()
            for si in re.findall(r"<si>(.*?)</si>", crudo, re.S)]


def _leer(z: zipfile.ZipFile) -> dict:
    comp = _cadenas(z)
    hoja = z.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace")
    filas = {}
    for numero, cuerpo in re.findall(r"<row[^>]*r=\"(\d+)\"[^>]*>(.*?)</row>", hoja, re.S):
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


def recolectar():
    padron = geo.padron()
    nombres = {p["iso"]: p["pais"] for p in padron}
    bloques = {p["iso"]: p["bloque"] for p in padron}

    try:
        peticion = urllib.request.Request(URL, headers={"User-Agent": NAVEGADOR})
        with urllib.request.urlopen(peticion, timeout=180) as r:
            crudo = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"No se pudo traer la planilla del BTI: HTTP {e.code}") from e

    filas = _leer(zipfile.ZipFile(io.BytesIO(crudo)))
    if 1 not in filas:
        raise RuntimeError("La planilla del BTI no trae fila de encabezados")
    cabecera = filas[1]

    # Cada indicador se ata a su rotulo. Si el proyecto reordena las columnas,
    # esto falla y se ve; no lee en silencio la columna equivocada.
    columna, faltantes = {}, []
    for i in INDICADORES:
        col = next((c for c, v in cabecera.items()
                    if str(v).strip() == i["rotulo_origen"]), None)
        if col:
            columna[i["clave"]] = col
        else:
            faltantes.append(i["rotulo_origen"])

    datos = {}
    sin_cubrir = []
    for numero in sorted(filas):
        if numero == 1:
            continue
        nombre = str(filas[numero].get("A", "")).strip()
        iso = NOMBRES.get(nombre)
        if not iso:
            continue
        registro = {}
        for i in INDICADORES:
            col = columna.get(i["clave"])
            if not col:
                continue
            bruto = filas[numero].get(col)
            try:
                valor = float(bruto)
            except (TypeError, ValueError):
                continue
            if valor != valor or not (0 <= valor <= 10):
                continue
            registro[i["clave"]] = {"valor": round(valor, 2), "anio": EDICION}
        if registro:
            datos[iso] = registro

    registros = [{"iso": p["iso"], "pais": nombres[p["iso"]], "bloque": bloques[p["iso"]],
                  "indicadores": datos[p["iso"]]}
                 for p in padron if p["iso"] in datos]
    sin_cubrir = sorted(nombres[p["iso"]] for p in padron if p["iso"] not in datos)
    cobertura = {i["clave"]: sum(1 for r in registros if i["clave"] in r["indicadores"])
                 for i in INDICADORES if i["clave"] in columna}

    vacios = [
        "ES EVALUACION EXPERTA, NO RECUENTO DE HECHOS. Dos especialistas por pais —uno "
        "del pais y uno de fuera— puntuan de 1 a 10, y el resultado se armoniza en "
        "revision regional. Es un juicio informado y metodico, no una medicion de campo.",
        f"ES UNA FOTO, NO UNA SERIE. El proyecto publica cada dos anios; este registro "
        f"toma la edicion {EDICION}. NO hay linea de tiempo y por lo tanto NO se puede "
        "proyectar sobre estos indicadores.",
        "SOLO CUBRE ESTADOS «EN DESARROLLO O EN TRANSICION». Los Estados chicos del "
        "Caribe y los de renta alta quedan fuera DEL PROYECTO, no del registro. Sin "
        "cobertura: " + (", ".join(sin_cubrir) if sin_cubrir else "ninguno") + ".",
        "LA APROBACION DE LA DEMOCRACIA NO ES UNA ENCUESTA. Es la evaluacion de un "
        "especialista sobre cuanto respaldo social tiene el regimen. Se acerca a la "
        "percepcion democratica que este registro declara como vacio, pero NO la "
        "reemplaza: Latinobarometro y el Barometro de las Americas preguntan a la gente; "
        "esto no.",
        "EN «INTENSIDAD DEL CONFLICTO» UN VALOR ALTO SIGNIFICA MENOS CONFLICTO, al reves "
        "que en la intuicion. La escala es la del proyecto y no se altera.",
        "ERROR PROPIO, DOCUMENTADO: la planilla guarda los textos en una tabla compartida "
        "y una cadena con formato se parte en fragmentos. Al contarlos como cadenas "
        "distintas TODOS los nombres y rotulos quedaban corridos: Cuba aparecia con 8,55 "
        "de democracia y Chile con 2,37. Se detecto porque los numeros eran IMPOSIBLES, "
        "no porque el programa fallara. El colector ahora junta los fragmentos y ata cada "
        "indicador a su ROTULO y no a la letra de columna.",
    ]
    if faltantes:
        vacios.append("Indicadores cuyo rotulo ya no aparece en la planilla —el proyecto "
                      "pudo haberla reordenado—: " + "; ".join(faltantes))

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=3,
        corroborado=False,
        nota=("Proyecto academico de la Fundacion Bertelsmann con metodo publicado y "
              "revision cruzada entre especialistas. Credibilidad 3 porque el dato es un "
              "juicio experto: no puede corroborarse contra una medicion independiente "
              "porque no existe una."),
    )

    return comun.escribir(
        colector="bti",
        capa="publico",
        fuente=f"Indice de Transformacion Bertelsmann (BTI), edicion {EDICION}",
        url_fuente="https://bti-project.org/en/downloads",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": [{k: i[k] for k in
                             ("clave", "rotulo", "eje", "unidad", "mas_es_peor", "cautela")}
                            | {"origen": f"Indice de Transformacion Bertelsmann {EDICION}"}
                            for i in INDICADORES if i["clave"] in columna],
            "cobertura": cobertura,
            "edicion": EDICION,
            "estados_cubiertos": len(registros),
            "metodo": ("Se descarga la planilla oficial y se lee con biblioteca estandar. "
                       "Cada indicador se ata a su ROTULO en la fila de encabezados, no a "
                       "la letra de columna: si el proyecto reordena la planilla el "
                       "colector lo declara en lugar de leer otra cosa."),
        },
    )


if __name__ == "__main__":
    comun.correr("bti", recolectar)
