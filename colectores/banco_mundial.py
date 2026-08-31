"""Indicadores comparables de los 33 Estados — Banco Mundial.

Cuatro indicadores que sirven a los tres ejes, **homologados por un mismo
organismo con una misma definición**, que es exactamente lo que los catálogos
nacionales no dan.

| Eje | Indicador | Origen |
|---|---|---|
| Seguridad | Homicidios intencionales por 100.000 | UNODC, vía Banco Mundial |
| Gobernanza | Control de la corrupción | Worldwide Governance Indicators |
| Gobernanza | Estado de derecho | Worldwide Governance Indicators |
| Gobernanza | Estabilidad política y ausencia de violencia | Worldwide Governance Indicators |
| Desarrollo | Población urbana y asentamientos precarios | Banco Mundial y ONU-Hábitat |
| Desarrollo | Industria — valor agregado | Cuentas nacionales |
| Desarrollo | Minerales y rentas de recursos naturales | UN Comtrade y Banco Mundial |

Sin clave y sin registro. Los datos del Banco Mundial se publican bajo licencia
abierta con atribución, que **no restringe el uso comercial**: a diferencia de
ACLED, OpenSanctions y el T-Index, estos sí pueden alimentar un producto pago.

Los tres indicadores de gobernanza son **estimaciones de percepción** en una
escala aproximada de -2,5 a 2,5, construidas agregando encuestas y evaluaciones
de expertos. No son recuentos de hechos y no pueden presentarse como tales.
"""

from __future__ import annotations

import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

import comun
import geo

BASE = "https://api.worldbank.org/v2"

# Ventana móvil de diez años: la que la dirección fijó para leer tendencia.
VENTANA = 10
HASTA = datetime.now(timezone.utc).year
DESDE = HASTA - VENTANA

INDICADORES = [
    {"clave": "homicidios", "codigo": "VC.IHR.PSRC.P5", "fuente_id": None,
     "rotulo": "Homicidios intencionales", "eje": "Seguridad",
     "unidad": "por cada 100.000 habitantes", "mas_es_peor": True,
     "origen": "UNODC, compilado por el Banco Mundial",
     "cautela": "Recuento de hechos registrados por cada Estado y homologado por UNODC. "
                "Un Estado con peor registro puede aparecer con menos homicidios."},
    {"clave": "corrupcion", "codigo": "GOV_WGI_CC.EST", "fuente_id": 3,
     "rotulo": "Control de la corrupción", "eje": "Gobernanza",
     "unidad": "estimación de -2,5 a 2,5", "mas_es_peor": False,
     "origen": "Worldwide Governance Indicators, Banco Mundial",
     "cautela": "Estimación de percepción agregada de encuestas y evaluaciones de "
                "expertos. No cuenta hechos de corrupción: mide cómo se la percibe."},
    {"clave": "estado_derecho", "codigo": "GOV_WGI_RL.EST", "fuente_id": 3,
     "rotulo": "Estado de derecho", "eje": "Gobernanza",
     "unidad": "estimación de -2,5 a 2,5", "mas_es_peor": False,
     "origen": "Worldwide Governance Indicators, Banco Mundial",
     "cautela": "Estimación de percepción, no medición directa del funcionamiento "
                "judicial."},
    {"clave": "estabilidad", "codigo": "GOV_WGI_PV.EST", "fuente_id": 3,
     "rotulo": "Estabilidad política y ausencia de violencia", "eje": "Gobernanza",
     "unidad": "estimación de -2,5 a 2,5", "mas_es_peor": False,
     "origen": "Worldwide Governance Indicators, Banco Mundial",
     "cautela": "Estimación de percepción sobre la probabilidad de inestabilidad o "
                "violencia por motivos políticos. No es un pronóstico."},
    {"clave": "urbanizacion", "codigo": "SP.URB.TOTL.IN.ZS", "fuente_id": None,
     "rotulo": "Población urbana", "eje": "Desarrollo",
     "unidad": "% de la población", "mas_es_peor": False,
     "origen": "Banco Mundial, sobre censos nacionales",
     "cautela": "Mide concentración urbana, no calidad de vida urbana. Un valor alto "
                "no es bueno ni malo por sí mismo."},
    {"clave": "asentamientos", "codigo": "EN.POP.SLUM.UR.ZS", "fuente_id": None,
     "rotulo": "Población en asentamientos precarios", "eje": "Desarrollo",
     "unidad": "% de la población urbana", "mas_es_peor": True,
     "origen": "ONU-Hábitat, compilado por el Banco Mundial",
     "cautela": "Serie con cobertura irregular: varios Estados no la reportan todos los "
                "años y el último dato puede ser viejo."},
    {"clave": "industria", "codigo": "NV.IND.TOTL.ZS", "fuente_id": None,
     "rotulo": "Industria — valor agregado", "eje": "Desarrollo",
     "unidad": "% del producto", "mas_es_peor": False,
     "origen": "Cuentas nacionales, compiladas por el Banco Mundial",
     "cautela": "Peso del sector industrial en el producto. No mide su complejidad ni "
                "su valor agregado tecnológico."},
    {"clave": "minerales", "codigo": "TX.VAL.MMTL.ZS.UN", "fuente_id": None,
     "rotulo": "Exportación de minerales y metales", "eje": "Desarrollo",
     "unidad": "% de las exportaciones", "mas_es_peor": False,
     "origen": "UN Comtrade, compilado por el Banco Mundial",
     "cautela": "Mide dependencia exportadora de materias primas minerales. Un valor "
                "alto señala exposición al precio internacional, no riqueza."},
    {"clave": "rentas_naturales", "codigo": "NY.GDP.TOTL.RT.ZS", "fuente_id": None,
     "rotulo": "Rentas de recursos naturales", "eje": "Desarrollo",
     "unidad": "% del producto", "mas_es_peor": True,
     "origen": "Banco Mundial",
     "cautela": "Proporción del producto que proviene de extraer recursos. Es el "
                "indicador clásico de exposición a la maldición de los recursos."},
{"clave": "gasto_militar", "codigo": "MS.MIL.XPND.GD.ZS", "fuente_id": None,
     "rotulo": "Gasto militar", "eje": "Seguridad",
     "unidad": "% del producto", "mas_es_peor": False,
     "origen": "SIPRI, compilado por el Banco Mundial",
     "cautela": "Mide lo que el Estado destina a defensa, no su capacidad ni su empleo. "
                "Un valor alto no indica mas seguridad ni menos."},
    {"clave": "personal_militar", "codigo": "MS.MIL.TOTL.P1", "fuente_id": None,
     "rotulo": "Personal de las fuerzas armadas", "eje": "Seguridad",
     "unidad": "personas", "mas_es_peor": False,
     "origen": "Banco Mundial",
     "cautela": "Efectivos declarados. No incluye fuerzas de seguridad interior ni "
                "policiales, que en varios Estados del padron son el grueso del despliegue."},
    {"clave": "voz_rendicion", "codigo": "GOV_WGI_VA.EST", "fuente_id": 3,
     "rotulo": "Voz y rendicion de cuentas", "eje": "Gobernanza",
     "unidad": "estimacion de -2,5 a 2,5", "mas_es_peor": False,
     "origen": "Worldwide Governance Indicators, Banco Mundial",
     "cautela": "Estimacion de percepcion sobre libertad de expresion, asociacion y "
                "participacion. No cuenta hechos."},
    {"clave": "calidad_regulatoria", "codigo": "GOV_WGI_RQ.EST", "fuente_id": 3,
     "rotulo": "Calidad regulatoria", "eje": "Gobernanza",
     "unidad": "estimacion de -2,5 a 2,5", "mas_es_peor": False,
     "origen": "Worldwide Governance Indicators, Banco Mundial",
     "cautela": "Estimacion de percepcion sobre la capacidad del Estado de formular "
                "reglas razonables. No cuenta hechos."},
    {"clave": "recaudacion", "codigo": "GC.TAX.TOTL.GD.ZS", "fuente_id": None,
     "rotulo": "Recaudacion tributaria", "eje": "Gobernanza",
     "unidad": "% del producto", "mas_es_peor": False,
     "origen": "FMI y Banco Mundial",
     "cautela": "Entra como capacidad del Estado de recaudar, no como indicador "
                "economico. Una recaudacion baja frente a una economia grande senala "
                "evasion o economia no registrada."},
    {"clave": "desempleo_joven", "codigo": "SL.UEM.1524.ZS", "fuente_id": None,
     "rotulo": "Desempleo juvenil", "eje": "Desarrollo",
     "unidad": "% de la poblacion de 15 a 24", "mas_es_peor": True,
     "origen": "OIT, compilado por el Banco Mundial",
     "cautela": "Estimacion modelada de la OIT donde el Estado no publica encuesta propia."},
    {"clave": "gini", "codigo": "SI.POV.GINI", "fuente_id": None,
     "rotulo": "Desigualdad — indice de Gini", "eje": "Desarrollo",
     "unidad": "0 igualdad, 100 desigualdad maxima", "mas_es_peor": True,
     "origen": "Banco Mundial, sobre encuestas de hogares",
     "cautela": "Depende de la encuesta de hogares de cada Estado, con anios y "
                "metodologias distintos. La comparacion entre paises es aproximada."},
    {"clave": "pobreza", "codigo": "SI.POV.NAHC", "fuente_id": None,
     "rotulo": "Pobreza segun linea nacional", "eje": "Desarrollo",
     "unidad": "% de la poblacion", "mas_es_peor": True,
     "origen": "Banco Mundial, sobre lineas nacionales",
     "cautela": "CADA ESTADO DEFINE SU PROPIA LINEA DE POBREZA. Las cifras NO son "
                "comparables entre paises: solo su evolucion dentro de cada uno."},
    {"clave": "internet", "codigo": "IT.NET.USER.ZS", "fuente_id": None,
     "rotulo": "Usuarios de internet", "eje": "Desarrollo",
     "unidad": "% de la poblacion", "mas_es_peor": False,
     "origen": "UIT, compilado por el Banco Mundial",
     "cautela": "Es tambien la base de exposicion para la materia de ciberseguridad: "
                "sin poblacion conectada no hay superficie de ataque."},
    {"clave": "bosque", "codigo": "AG.LND.FRST.ZS", "fuente_id": None,
     "rotulo": "Superficie forestal", "eje": "Desarrollo",
     "unidad": "% del territorio", "mas_es_peor": False,
     "origen": "FAO, compilado por el Banco Mundial",
     "cautela": "Superficie total, no su estado de conservacion. Una plantacion cuenta "
                "igual que un bosque primario."},
    {"clave": "regalo_contrato", "codigo": "IC.FRM.CORR.ZS", "fuente_id": None,
     "rotulo": "Empresas que esperan pagar por un contrato publico", "eje": "Gobernanza",
     "unidad": "% de las empresas consultadas", "mas_es_peor": True,
     "origen": "Encuestas de Empresas del Banco Mundial",
     "cautela": "Es la materia de INTEGRIDAD DE LA CONTRATACION PUBLICA. Mide lo que la "
                "empresa declara esperar, no un soborno comprobado. La encuesta no se "
                "levanta todos los anios en todos los Estados: el dato de cada pais es "
                "de la ultima ronda disponible y las rondas no coinciden entre si."},
    {"clave": "servidores_seguros", "codigo": "IT.NET.SECR.P6", "fuente_id": None,
     "rotulo": "Servidores de internet cifrados", "eje": "Seguridad",
     "unidad": "por millon de habitantes", "mas_es_peor": False,
     "origen": "Netcraft, compilado por el Banco Mundial",
     "cautela": "Es el unico indicador de CIBERSEGURIDAD comparable y gratuito que se "
                "encontro para los 33. Mide infraestructura de cifrado desplegada, NO "
                "mide ataques, ni defensa estatal, ni incidentes. Un valor alto indica "
                "una economia digital mas madura, no un Estado mas protegido."},
    {"clave": "banda_ancha", "codigo": "IT.NET.BBND.P2", "fuente_id": None,
     "rotulo": "Suscripciones a banda ancha fija", "eje": "Desarrollo",
     "unidad": "por 100 habitantes", "mas_es_peor": False,
     "origen": "UIT, compilado por el Banco Mundial",
     "cautela": "Junto con los usuarios de internet, delimita la superficie expuesta a "
                "ataque informatico. No mide calidad ni continuidad del servicio."},
]


def _traer(indicador: dict, isos: list) -> dict:
    """Serie anual por país de un indicador. Devuelve {iso: [(anio, valor)]}."""
    partes = [
        f"{BASE}/country/{';'.join(isos)}/indicator/{indicador['codigo']}",
        f"?format=json&per_page=20000&date={DESDE}:{HASTA}",
    ]
    if indicador["fuente_id"]:
        partes.append(f"&source={indicador['fuente_id']}")
    peticion = urllib.request.Request("".join(partes), headers={"User-Agent": comun.AGENTE})
    with urllib.request.urlopen(peticion, timeout=120) as respuesta:
        crudo = json.loads(respuesta.read().decode("utf-8", "replace"))

    if not isinstance(crudo, list) or len(crudo) < 2 or crudo[1] is None:
        mensaje = crudo[0] if isinstance(crudo, list) and crudo else crudo
        raise RuntimeError(f"El Banco Mundial no devolvió serie para {indicador['codigo']}: {mensaje}")

    series = defaultdict(list)
    for fila in crudo[1]:
        if fila.get("value") is None:
            continue
        iso = (fila.get("countryiso3code") or "").upper()
        if iso:
            series[iso].append((int(fila["date"]), round(float(fila["value"]), 4)))
    for iso in series:
        series[iso].sort()
    return series


def recolectar():
    padron = geo.padron()
    isos = [p["iso"] for p in padron]

    datos, fallidos = {}, []
    for indicador in INDICADORES:
        try:
            datos[indicador["clave"]] = _traer(indicador, isos)
        except Exception as error:  # noqa: BLE001 — el indicador caído se declara
            fallidos.append(f"{indicador['rotulo']}: {type(error).__name__}")
            datos[indicador["clave"]] = {}

    if all(not v for v in datos.values()):
        raise RuntimeError("Ningún indicador devolvió serie. No se escribe nada.")

    registros, cobertura = [], {}
    for pais in padron:
        ficha = {**pais, "indicadores": {}}
        for indicador in INDICADORES:
            serie = datos[indicador["clave"]].get(pais["iso"], [])
            if not serie:
                continue
            anio, valor = serie[-1]
            variacion = None
            if len(serie) >= 2 and serie[-2][1] not in (0, None):
                variacion = round((valor - serie[-2][1]) / abs(serie[-2][1]) * 100, 1)
            # Tendencia de la ventana: primer año disponible contra el último.
            # Es más robusta que la variación interanual, que es puro ruido.
            decada = None
            if len(serie) >= 3 and serie[0][1] not in (0, None):
                decada = round((valor - serie[0][1]) / abs(serie[0][1]) * 100, 1)
            ficha["indicadores"][indicador["clave"]] = {
                "valor": valor,
                "anio": anio,
                "anio_anterior": serie[-2][0] if len(serie) >= 2 else None,
                "valor_anterior": serie[-2][1] if len(serie) >= 2 else None,
                "variacion_pct": variacion,
                "anio_inicial": serie[0][0],
                "valor_inicial": serie[0][1],
                "tendencia_ventana_pct": decada,
                "serie": [{"anio": a, "valor": v} for a, v in serie],
            }
        if ficha["indicadores"]:
            registros.append(ficha)
        for clave in ficha["indicadores"]:
            cobertura[clave] = cobertura.get(clave, 0) + 1

    registros.sort(key=lambda r: r["pais"])

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=(
            "Compilación de un organismo multilateral sobre registros estatales y "
            "encuestas. Fuente única: la segunda fuente independiente sería el registro "
            "nacional de cada Estado, que no es comparable entre sí. Declarado conforme "
            "a doctrina/fuentes.md §2 ter."
        ),
    )

    faltan = [p["pais"] for p in padron if p["iso"] not in {r["iso"] for r in registros}]
    vacios = [
        f"Ventana móvil de {VENTANA} años ({DESDE}-{HASTA}). La tendencia se calcula "
        "entre el primer y el último año DISPONIBLES dentro de esa ventana, que pueden "
        "no ser los extremos de la ventana misma.",
        "Serie ANUAL con rezago: el último año disponible suele ir dos o tres años "
        "atrás del corriente. No es un dato en vivo.",
        "Los tres indicadores de gobernanza son ESTIMACIONES DE PERCEPCIÓN en escala "
        "de -2,5 a 2,5, construidas agregando encuestas y evaluaciones de expertos. No "
        "cuentan hechos y no pueden presentarse como recuentos.",
        "El homicidio sí es recuento de hechos, pero depende de la capacidad de "
        "registro de cada Estado: uno que registra peor aparece con menos homicidios. "
        "La cifra baja puede indicar buena seguridad o mal registro.",
        "Sin desglose subnacional: la cifra es nacional.",
        (
            "Cobertura por indicador: "
            + ", ".join(f"{i['rotulo']} en {cobertura.get(i['clave'], 0)} de 33" for i in INDICADORES)
            + "."
        ),
    ]
    if faltan:
        vacios.append(f"Sin ningún indicador: {', '.join(faltan)}.")
    if fallidos:
        vacios.append(f"Indicadores que no respondieron en esta corrida: {'; '.join(fallidos)}.")
    vacios.append(
        "Licencia abierta con atribución obligatoria al Banco Mundial. A diferencia de "
        "otras fuentes del catálogo, NO restringe el uso comercial."
    )

    return comun.escribir(
        colector="banco-mundial",
        capa="publico",
        fuente="Banco Mundial — indicadores de desarrollo y gobernanza",
        url_fuente="https://data.worldbank.org",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "indicadores": [
                {k: i[k] for k in ("clave", "codigo", "rotulo", "eje", "unidad",
                                   "mas_es_peor", "origen", "cautela")}
                for i in INDICADORES
            ],
            "cobertura": cobertura,
            "serie_desde": DESDE,
            "ventana_anios": VENTANA,
        },
    )


if __name__ == "__main__":
    comun.correr("banco-mundial", recolectar)
