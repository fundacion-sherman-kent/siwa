# -*- coding: utf-8 -*-
"""Inteligencia artificial: cuánto se usa en cada país y quién pone la nube.

POR QUÉ EXISTE
--------------
La dirección pidió saber, país por país, qué inteligencias artificiales se usan
y de qué país son (autorizado el 13/9/2026). Se exploró qué se puede contestar
con datos abiertos, y la respuesta honesta es: una parte.

QUÉ PUBLICA
-----------
  · **Uso de IA generativa**, de cualquier marca, según Microsoft. Es la única
    medida que no depende de una sola empresa de IA. Es una ESTIMACIÓN modelada
    por Microsoft, no una encuesta.
  · **Uso de ChatGPT** (OpenAI) y **uso de Claude** (Anthropic), cada uno aparte.
    Son servicios de dos empresas de Estados Unidos y miden SOLO su servicio: no
    son segunda fuente de la anterior ni entre sí.
  · **Regiones de nube de empresas de Estados Unidos y de China** en cada país,
    según la documentación oficial de siete empresas.

QUÉ NO PUEDE PUBLICAR, Y SE DECLARA
-----------------------------------
Qué parte del uso de IA de cada país va a empresas de Estados Unidos, de China,
de Europa o de la región: **ninguna fuente abierta lo mide**. Tampoco los
acuerdos de los gobiernos con proveedores. Y el riesgo de dependencia o de
soberanía de datos es un juicio: no entra en este registro.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import geo  # noqa: E402

COLECTOR = "ia"
CAPA = "publico"
AQUI = Path(__file__).resolve().parent

MICROSOFT_LISTA = "https://api.github.com/repos/microsoft/ai-diffusion-report/contents/data"
MICROSOFT_RAW = "https://raw.githubusercontent.com/microsoft/ai-diffusion-report/main/data/{nombre}"
MICROSOFT_RESPALDO = "AI_Diffusion_Q12026_Update.csv"
OPENAI_ZIP = "https://cdn.openai.com/signals/data-download-csv.zip"
OPENAI_RANK = "public_release_csv/share_of_messages_by_country_quarter_rank.csv"
ANTHROPIC_ARBOL = "https://huggingface.co/api/datasets/Anthropic/EconomicIndex/tree/main"
ANTHROPIC_ARCHIVO = "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/{ruta}"
AWS_IP = "https://ip-ranges.amazonaws.com/ip-ranges.json"
GOOGLE_IP = "https://www.gstatic.com/ipranges/cloud.json"
TABLA_NUBE = AQUI / "fijas" / "nube-regiones" / "regiones.json"
# Pasados estos días sin volver a revisar la tabla a mano, se avisa en rojo.
VIGENCIA_TABLA = 120

# Cómo escribe Microsoft a los Estados del padrón.
EN_INGLES = {
    "Argentina": "ARG", "Bolivia": "BOL", "Brazil": "BRA", "Chile": "CHL", "Colombia": "COL",
    "Costa Rica": "CRI", "Cuba": "CUB", "Dominican Republic": "DOM", "Ecuador": "ECU",
    "El Salvador": "SLV", "Guatemala": "GTM", "Guyana": "GUY", "Haiti": "HTI", "Honduras": "HND",
    "Jamaica": "JAM", "Mexico": "MEX", "Nicaragua": "NIC", "Panama": "PAN", "Paraguay": "PRY",
    "Peru": "PER", "Suriname": "SUR", "Trinidad and Tobago": "TTO", "Uruguay": "URY",
    "Venezuela": "VEN", "Belize": "BLZ", "Bahamas": "BHS", "The Bahamas": "BHS",
    "Barbados": "BRB", "Antigua and Barbuda": "ATG", "Dominica": "DMA", "Grenada": "GRD",
    "Saint Kitts and Nevis": "KNA", "Saint Lucia": "LCA", "Saint Vincent and the Grenadines": "VCT",
}


def pedir(url: str, espera: int = 120) -> bytes:
    peticion = urllib.request.Request(url, headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=espera) as respuesta:
        return respuesta.read()


def ficha(puntos: list, periodo: str | None = None, nota: str | None = None) -> dict:
    """La forma común del registro: último valor, anterior y serie por año."""
    puntos = sorted(puntos)
    anio, valor = puntos[-1]
    ant = puntos[-2] if len(puntos) > 1 else None
    f = {"valor": valor, "anio": anio,
         "anio_anterior": ant[0] if ant else None, "valor_anterior": ant[1] if ant else None,
         "serie": [{"anio": a, "valor": v} for a, v in puntos]}
    if periodo:
        f["periodo"] = periodo
    if nota:
        f["nota"] = nota
    return f


# ── Microsoft: uso de IA generativa, cualquier marca ────────────────────────
def microsoft() -> tuple:
    nombre = MICROSOFT_RESPALDO
    try:
        archivos = [a["name"] for a in json.loads(pedir(MICROSOFT_LISTA, 60))
                    if re.match(r"AI_Diffusion_.*\.csv$", a.get("name", ""))]
        if archivos:
            nombre = sorted(archivos)[-1]
    except Exception:  # noqa: BLE001 — sin la lista, se usa el último nombre conocido
        pass
    texto = pedir(MICROSOFT_RAW.format(nombre=nombre)).decode("utf-8-sig", "replace")
    filas = list(csv.reader(io.StringIO(texto)))
    cabeza = filas[0]
    periodos = []
    for i, col in enumerate(cabeza[1:], start=1):
        m = re.search(r"(H[12]|Q[1-4])\s+(\d{4})", col)
        if m:
            periodos.append((i, m.group(1) + " " + m.group(2), int(m.group(2))))
    if not periodos:
        raise RuntimeError(f"Microsoft cambió la forma del archivo: cabecera {cabeza}")
    por_iso = {}
    for f in filas[1:]:
        iso = EN_INGLES.get(f[0].strip())
        if not iso:
            continue
        valores = {}
        for i, rot, anio in periodos:
            try:
                valores[rot] = (anio, float(f[i].replace("%", "").strip()))
            except (ValueError, IndexError):
                continue
        if valores:
            por_iso[iso] = valores
    if len(por_iso) < 15:
        raise RuntimeError(f"Microsoft dejó solo {len(por_iso)} Estados del padrón: lectura fallida")
    return por_iso, [p[1] for p in periodos], nombre


# ── OpenAI: puesto de ChatGPT, pasado a percentil ───────────────────────────
def openai() -> tuple:
    z = zipfile.ZipFile(io.BytesIO(pedir(OPENAI_ZIP, 180)))
    filas = list(csv.DictReader(io.StringIO(z.read(OPENAI_RANK).decode("utf-8-sig", "replace"))))
    dos = {v: k for k, v in comun.DOS_LETRAS.items()}
    por_trimestre = {}
    for f in filas:
        por_trimestre.setdefault(f["quarter"], []).append(f)
    salida = {}
    for trimestre, lista in por_trimestre.items():
        total = len(lista)
        for f in lista:
            iso = dos.get((f.get("country") or "").strip().upper())
            if not iso or total < 2:
                continue
            puesto = int(f["rank"])
            # EL PUESTO SE PASA A PERCENTIL para que «más alto» signifique «más uso»:
            # un puesto 1 es el país con más mensajes por persona. Se publica el
            # puesto original junto al valor.
            percentil = round(100 * (total - puesto) / (total - 1), 1)
            salida.setdefault(iso, {})[trimestre] = (puesto, total, percentil)
    if len(salida) < 12:
        raise RuntimeError(f"OpenAI dejó solo {len(salida)} Estados del padrón: lectura fallida")
    return salida


# ── Anthropic: índice de uso de Claude por habitante ────────────────────────
def anthropic() -> tuple:
    raices = json.loads(pedir(ANTHROPIC_ARBOL, 60))
    entregas = sorted(x["path"] for x in raices if x.get("type") == "directory"
                      and x["path"].startswith("release_"))
    if not entregas:
        raise RuntimeError("Anthropic no lista ninguna entrega")
    ultima = entregas[-1]
    datos = json.loads(pedir(f"{ANTHROPIC_ARBOL}/{ultima}/data", 60))
    ruta = next((x["path"] for x in datos if re.search(r"aei_claude_ai_.*\.csv$", x["path"])), None)
    if not ruta:
        raise RuntimeError(f"La entrega {ultima} no trae el archivo de uso de Claude")
    peticion = urllib.request.Request(ANTHROPIC_ARCHIVO.format(ruta=ruta),
                                      headers={"User-Agent": comun.AGENTE})
    salida = {}
    # Se lee de a una fila, sin bajar el archivo entero a memoria: pesa unos 220 MB.
    with urllib.request.urlopen(peticion, timeout=600) as respuesta:
        for f in csv.DictReader(io.TextIOWrapper(respuesta, encoding="utf-8", newline="")):
            if (f.get("geo_level") == "country" and f.get("metric_id") == "usage_per_capita_index"
                    and f.get("category_name") == "overall"):
                try:
                    salida.setdefault(f["geo_id"], {})[f["date_start"][:7]] = float(f["value"])
                except (ValueError, KeyError):
                    continue
    if len(salida) < 50:
        raise RuntimeError(f"Anthropic dejó solo {len(salida)} países en total: lectura fallida")
    return salida, ultima


# ── Nube: regiones de empresas de EE. UU. y de China ────────────────────────
def nube() -> tuple:
    tabla = json.loads(TABLA_NUBE.read_text(encoding="utf-8"))
    avisos = []
    revisado = datetime.fromisoformat(tabla["revisado"]).replace(tzinfo=timezone.utc)
    dias = (datetime.now(timezone.utc) - revisado).days
    if dias > VIGENCIA_TABLA:
        avisos.append(f"LA TABLA DE REGIONES DE NUBE TIENE {dias} DÍAS sin revisión a mano. "
                      "Se publica igual, pero puede haber regiones nuevas sin contar.")
    conocidas = {r["codigo"] for e in tabla["empresas"] for r in e["regiones"]}
    # Las dos empresas que publican su lista para programas se miran solas, cada
    # corrida: si aparece una región de la región que la tabla no tiene, se avisa.
    try:
        aws = {p["region"] for p in json.loads(pedir(AWS_IP))["prefixes"]}
        nuevas = sorted(c for c in aws if c.startswith(("sa-", "mx-")) and c not in conocidas)
        if nuevas:
            avisos.append("Amazon lista en sus direcciones IP regiones de la región que no figuran "
                          "en su documentación ni se cuentan: " + ", ".join(nuevas) + ".")
    except Exception as error:  # noqa: BLE001
        avisos.append(f"No se pudo mirar la lista de Amazon: {type(error).__name__}.")
    try:
        gcp = {p["scope"] for p in json.loads(pedir(GOOGLE_IP))["prefixes"]}
        nuevas = sorted(c for c in gcp if c.startswith(("southamerica", "northamerica-south"))
                        and c not in conocidas)
        if nuevas:
            avisos.append("REGIÓN NUEVA DE GOOGLE SIN REVISAR: " + ", ".join(nuevas)
                          + ". Hay que agregarla a la tabla a mano.")
    except Exception as error:  # noqa: BLE001
        avisos.append(f"No se pudo mirar la lista de Google: {type(error).__name__}.")
    return tabla, avisos


def construir() -> Path:
    padron = geo.padron()
    caidos = []

    try:
        ms, periodos_ms, archivo_ms = microsoft()
    except Exception as error:  # noqa: BLE001
        caidos.append(f"Microsoft, uso de IA generativa: {type(error).__name__}: {error}")
        ms, periodos_ms, archivo_ms = {}, [], None
    try:
        oa = openai()
    except Exception as error:  # noqa: BLE001
        caidos.append(f"OpenAI, uso de ChatGPT: {type(error).__name__}: {error}")
        oa = {}
    try:
        an, entrega_an = anthropic()
    except Exception as error:  # noqa: BLE001
        caidos.append(f"Anthropic, uso de Claude: {type(error).__name__}: {error}")
        an, entrega_an = {}, None
    tabla, avisos_nube = nube()

    # Microsoft repite cifras idénticas en Estados distintos: es la marca de un
    # valor imputado por grupo, no medido. Se detecta y se dice en la ficha.
    firmas = {}
    for iso, v in ms.items():
        firmas.setdefault(tuple(sorted(x[1] for x in v.values())), []).append(iso)
    imputados = {iso for grupo in firmas.values() if len(grupo) > 1 for iso in grupo}

    por_origen = {}
    for e in tabla["empresas"]:
        for r in e["regiones"]:
            d = por_origen.setdefault(r["iso"], {}).setdefault(e["origen"], [])
            d.append(e["empresa"] + " (" + r["lugar"] + (", acceso restringido" if r.get("restringida") else "") + ")")

    anio_nube = datetime.now(timezone.utc).year
    registros, cobertura = [], {}
    for p in padron:
        iso = p["iso"]
        f = {"iso": iso, "pais": p["pais"], "bloque": p.get("bloque"), "indicadores": {}}
        if iso in ms:
            puntos = {}
            for rot, (anio, valor) in ms[iso].items():
                puntos[anio] = (valor, rot)   # el último período de cada año queda
            ultimo_rot = list(ms[iso].keys())[-1]
            f["indicadores"]["uso_ia_generativa"] = ficha(
                [(a, v[0]) for a, v in puntos.items()], periodo=ultimo_rot,
                nota=("cifra idéntica a la de otros Estados: probable estimación por grupo"
                      if iso in imputados else None))
        if iso in oa:
            trimestres = sorted(oa[iso])
            por_anio = {}
            for t in trimestres:
                por_anio[int(t[:4])] = oa[iso][t][2]
            puesto, total, _ = oa[iso][trimestres[-1]]
            f["indicadores"]["uso_chatgpt"] = ficha(
                list(por_anio.items()), periodo="trimestre de " + trimestres[-1][:7],
                nota=f"puesto {puesto} de {total} países")
        if iso in an:
            meses = sorted(an[iso])
            por_anio = {int(m[:4]): an[iso][m] for m in meses}
            f["indicadores"]["uso_claude"] = ficha(list(por_anio.items()), periodo="mes " + meses[-1])
        origenes = por_origen.get(iso, {})
        for clave, origen in (("nube_eeuu", "Estados Unidos"), ("nube_china", "China")):
            lista = origenes.get(origen, [])
            f["indicadores"][clave] = ficha([(anio_nube, len(lista))],
                                            nota="; ".join(lista) if lista else None)
        for c in f["indicadores"]:
            cobertura[c] = cobertura.get(c, 0) + 1
        registros.append(f)

    medidas = [
        {"clave": "uso_ia_generativa", "rotulo": "Uso de inteligencia artificial generativa",
         "eje": "Desarrollo", "unidad": "% de las personas", "mas_es_peor": False,
         "sin_direccion": True, "origen": "Microsoft AI Economy Institute — AI Diffusion Report",
         "cautela": "Qué parte de las personas usó algún producto de IA generativa en el período. "
                    "ESTIMACIÓN DE MICROSOFT, no encuesta: parte de datos de uso de sus propios "
                    "productos, ajustados por población, acceso a internet y cuota de dispositivos de "
                    "cada país. Cuenta cualquier marca de IA. Varios Estados tienen cifras idénticas "
                    "entre sí, marca de un valor estimado por grupo: su ficha lo dice. Faltan diez "
                    "Estados, casi todo el Caribe oriental."},
        {"clave": "uso_chatgpt", "rotulo": "Intensidad de uso de ChatGPT",
         "eje": "Desarrollo", "unidad": "percentil mundial (100 = el país con más uso)",
         "unidad_singular": "percentil", "mas_es_peor": False, "sin_direccion": True,
         "origen": "OpenAI — Signals, datos abiertos (CC BY 4.0)",
         "cautela": "SOLO CHATGPT, un servicio de una empresa de Estados Unidos. OpenAI publica el "
                    "PUESTO de cada país según los mensajes por persona, no la cantidad; el registro "
                    "lo pasa a percentil para que el valor alto signifique más uso, y la ficha "
                    "conserva el puesto original. No es segunda fuente del uso de IA en general: un "
                    "país puede usar poco ChatGPT y mucho otra IA. Cuba y Venezuela no figuran."},
        {"clave": "uso_claude", "rotulo": "Intensidad de uso de Claude por habitante",
         "eje": "Desarrollo", "unidad": "índice (1 = el uso que corresponde a su población)",
         "unidad_singular": "índice", "mas_es_peor": False, "sin_direccion": True,
         "origen": "Anthropic — Economic Index (CC BY)",
         "cautela": "SOLO CLAUDE, un servicio de una empresa de Estados Unidos. El índice compara la "
                    "parte del uso mundial de Claude que tiene el país con su parte de la población "
                    "en edad de trabajar: 2 es el doble de lo esperable; 0,5, la mitad. Un país que "
                    "no figura no tiene uso cero: la empresa no publica esa fila."},
        {"clave": "nube_eeuu", "rotulo": "Regiones de nube de empresas de Estados Unidos",
         "eje": "Defensa", "unidad": "regiones de nube", "unidad_singular": "región de nube",
         "mas_es_peor": False, "sin_direccion": True,
         "origen": "Documentación oficial de Amazon, Google, Microsoft y Oracle",
         "cautela": "Cuenta las regiones públicas de nube que cuatro empresas de Estados Unidos "
                    "declaran en su documentación técnica. NO dice dónde se procesan los datos del "
                    "país ni de su Estado: una empresa o un gobierno puede usar una región de otro "
                    "país. Un cero significa que ninguna de las cuatro tiene región en el país."},
        {"clave": "nube_china", "rotulo": "Regiones de nube de empresas de China",
         "eje": "Defensa", "unidad": "regiones de nube", "unidad_singular": "región de nube",
         "mas_es_peor": False, "sin_direccion": True,
         "origen": "Documentación oficial de Huawei, Alibaba y Tencent",
         "cautela": "Cuenta las regiones públicas de nube que tres empresas de China declaran en su "
                    "documentación. Igual que la de Estados Unidos: no dice dónde se procesan los "
                    "datos del país ni si su Estado las usa."},
    ]
    publicables = [m for m in medidas if cobertura.get(m["clave"])]

    vacios = [
        "QUÉ PARTE DEL USO DE IA DE CADA PAÍS VA A EMPRESAS DE ESTADOS UNIDOS, DE CHINA, DE EUROPA O "
        "DE LA REGIÓN: NINGUNA FUENTE ABIERTA LO MIDE. OpenAI y Anthropic publican solo su propio "
        "servicio; DeepSeek, Qwen, Mistral y Gemini no publican datos por país.",
        "LOS ACUERDOS DE LOS GOBIERNOS CON PROVEEDORES DE IA O DE NUBE no tienen un registro "
        "sistemático abierto: no se publican.",
        "EL RIESGO DE DEPENDENCIA TECNOLÓGICA O DE SOBERANÍA DE DATOS ES UN JUICIO y este registro "
        "no emite juicios. Estas cifras son el insumo de ese análisis, no su conclusión.",
        "UNA REGIÓN DE NUBE NO DICE DÓNDE SE PROCESAN LOS DATOS. Que exista una región en São Paulo "
        "no significa que la IA usada en Brasil corra ahí.",
        "LA TABLA DE REGIONES DE NUBE SE REVISA A MANO contra la documentación de cada empresa "
        f"(última revisión: {tabla['revisado']}). Amazon y Google se vigilan solos en cada corrida. "
        + " ".join(e["empresa"] + ": " + e["nota"] for e in tabla["empresas"] if e.get("nota")),
        "EL CARIBE ORIENTAL NO FIGURA en ninguna de las tres mediciones de uso.",
    ] + avisos_nube + caidos

    return comun.escribir(
        colector=COLECTOR,
        capa=CAPA,
        fuente="Microsoft AI Economy Institute; OpenAI Signals; Anthropic Economic Index; "
               "documentación oficial de siete empresas de nube",
        url_fuente="https://github.com/microsoft/ai-diffusion-report",
        calificacion=comun.calificar(
            "B", 3, False,
            "Datos que cada empresa publica sobre sus propios servicios o estima con ellos: "
            "fiabilidad B porque son productores serios con método declarado, y credibilidad 3 "
            "porque ninguno es independiente de lo que mide ni se corrobora con otro."),
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": publicables,
            "cobertura": {m["clave"]: cobertura.get(m["clave"], 0) for m in publicables},
            "resumen": {
                "microsoft_archivo": archivo_ms, "microsoft_periodos": periodos_ms,
                "anthropic_entrega": entrega_an, "tabla_nube_revisada": tabla["revisado"],
                "consultado": comun.ahora(),
            },
            "nube_regiones": tabla["empresas"],
        },
    )


if __name__ == "__main__":
    comun.correr(COLECTOR, construir)
