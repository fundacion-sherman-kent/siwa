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
import time
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
     "rotulo": "Gasto militar sobre el producto", "eje": "Defensa",
     "unidad": "% del producto", "mas_es_peor": False,
     "origen": "SIPRI, compilado por el Banco Mundial",
     "cautela": "Mide lo que el Estado destina a defensa, no su capacidad ni su empleo. "
                "Un valor alto no indica mas seguridad ni menos."},
    # ── Desarrollo científico y tecnológico ──────────────────────────────────
    # La capacidad de un Estado de producir conocimiento propio. No mide calidad
    # ni utilidad: mide esfuerzo y producción.
    {"clave": "id_producto", "codigo": "GB.XPD.RSDV.GD.ZS", "fuente_id": None,
     "rotulo": "Gasto en investigación y desarrollo", "eje": "Defensa",
     "unidad": "% del producto", "mas_es_peor": False,
     "origen": "UNESCO, compilado por el Banco Mundial",
     "cautela": "Menos de la mitad de los Estados lo informan. Mide lo que se gasta, no lo que se "
                "obtiene: un gasto alto mal dirigido no produce capacidad."},
    {"clave": "investigadores", "codigo": "SP.POP.SCIE.RD.P6", "fuente_id": None,
     "rotulo": "Investigadores por millón de habitantes", "eje": "Defensa",
     "unidad": "personas por millón", "mas_es_peor": False,
     "origen": "UNESCO, compilado por el Banco Mundial",
     "cautela": "La cobertura más floja de este bloque: menos de la mitad lo informa. "
                "Cuenta personas dedicadas a investigar, en equivalente a tiempo completo."},
    {"clave": "articulos_cientificos", "codigo": "IP.JRN.ARTC.SC", "fuente_id": None,
     "rotulo": "Artículos científicos y técnicos publicados", "eje": "Defensa",
     "unidad": "artículos por año", "mas_es_peor": False,
     "origen": "National Science Foundation, compilado por el Banco Mundial",
     "cautela": "Los 33. Es un RECUENTO, no una tasa: un Estado grande publica más que "
                "uno chico sin ser por eso más capaz. Se lee junto a la población."},
    {"clave": "patentes_residentes", "codigo": "IP.PAT.RESD", "fuente_id": None,
     "rotulo": "Solicitudes de patente de residentes", "eje": "Defensa",
     "unidad": "solicitudes por año", "mas_es_peor": False,
     "origen": "Organización Mundial de la Propiedad Intelectual, vía el Banco Mundial",
     "cautela": "Tres de cada cuatro Estados. Cuenta solicitudes, no concesiones, y solo de residentes: "
                "es invención propia, no tecnología que entra comprada."},

    # ── Recursos estratégicos ────────────────────────────────────────────────
    # Lo que un Estado tiene bajo su suelo y su territorio, y de qué depende de
    # afuera. La dependencia es tan estratégica como la dotación.
    {"clave": "agua_renovable", "codigo": "ER.H2O.INTR.PC", "fuente_id": None,
     "rotulo": "Agua dulce renovable por habitante", "eje": "Defensa",
     "unidad": "metros cúbicos por persona", "mas_es_peor": False,
     "origen": "FAO AQUASTAT, compilado por el Banco Mundial",
     "cautela": "Los 33. Es el agua que se renueva dentro del propio territorio. Un "
                "promedio nacional alto puede convivir con escasez severa en una región."},
    {"clave": "superficie", "codigo": "AG.SRF.TOTL.K2", "fuente_id": None,
     "rotulo": "Superficie del territorio", "eje": "Defensa",
     "unidad": "kilómetros cuadrados", "mas_es_peor": None,
     "origen": "FAO, compilado por el Banco Mundial",
     "cautela": "Los 33. No es virtud ni defecto: es la extensión que hay que cubrir, "
                "administrar y vigilar. Es el denominador de cualquier medida de densidad "
                "—efectivos, puestos fronterizos, cobertura— y por eso entra acá."},
    {"clave": "tierra_arable", "codigo": "AG.LND.ARBL.ZS", "fuente_id": None,
     "rotulo": "Tierra arable", "eje": "Defensa",
     "unidad": "% de la superficie", "mas_es_peor": False,
     "origen": "FAO, compilado por el Banco Mundial",
     "cautela": "Los 33. Mide superficie cultivable, no producción ni seguridad "
                "alimentaria: un Estado con poca tierra puede alimentarse importando."},
    {"clave": "energia_importada", "codigo": "EG.IMP.CONS.ZS", "fuente_id": None,
     "rotulo": "Energía que se importa", "eje": "Defensa",
     "unidad": "% del uso de energía", "mas_es_peor": True,
     "origen": "Agencia Internacional de Energía, compilado por el Banco Mundial",
     "cautela": "Dos tercios de los Estados. Un valor negativo significa que exporta más energía "
                "de la que usa. Es la medida más directa de dependencia externa."},
    {"clave": "uso_energia", "codigo": "EG.USE.PCAP.KG.OE", "fuente_id": None,
     "rotulo": "Uso de energía por habitante", "eje": "Defensa",
     "unidad": "kg equivalentes de petróleo", "mas_es_peor": False,
     "origen": "Agencia Internacional de Energía, compilado por el Banco Mundial",
     "cautela": "Dos tercios de los Estados. No es virtud ni defecto: es escala de la economía. Se lee junto "
                "a la energía importada, que es la que dice de quién se depende."},

    # ── Infraestructuras críticas ────────────────────────────────────────────
    # Lo que tiene que seguir funcionando para que todo lo demás funcione.
    {"clave": "acceso_electricidad", "codigo": "EG.ELC.ACCS.ZS", "fuente_id": None,
     "rotulo": "Población con acceso a electricidad", "eje": "Defensa",
     "unidad": "% de la población", "mas_es_peor": False,
     "origen": "Banco Mundial, marco de seguimiento de energía sostenible",
     "cautela": "Los 33. Acceso no es continuidad: un hogar conectado a una red que se "
                "corta todos los días cuenta como con acceso."},
    {"clave": "perdidas_electricas", "codigo": "EG.ELC.LOSS.ZS", "fuente_id": None,
     "rotulo": "Electricidad perdida en el traslado", "eje": "Defensa",
     "unidad": "% de la producción", "mas_es_peor": True,
     "origen": "Agencia Internacional de Energía, compilado por el Banco Mundial",
     "cautela": "Dos tercios de los Estados. Mezcla pérdida técnica con robo de energía, y la fuente no las "
                "separa: un valor alto indica una red frágil, sin decir por cuál motivo."},
    {"clave": "puertos_contenedores", "codigo": "IS.SHP.GOOD.TU", "fuente_id": None,
     "rotulo": "Movimiento de contenedores en puertos", "eje": "Defensa",
     "unidad": "contenedores de veinte pies por año", "mas_es_peor": False,
     "origen": "Naciones Unidas, compilado por el Banco Mundial",
     "cautela": "Casi todos. Es un RECUENTO y depende del tamaño de la economía. Los Estados "
                "sin litoral marítimo no tienen este dato, y no es una falla."},
    {"clave": "agua_potable_basica", "codigo": "SH.H2O.BASW.ZS", "fuente_id": None,
     "rotulo": "Población con agua potable básica", "eje": "Defensa",
     "unidad": "% de la población", "mas_es_peor": False,
     "origen": "OMS y UNICEF, programa conjunto de monitoreo, vía el Banco Mundial",
     "cautela": "Casi todos. «Básica» es el escalón mínimo: fuente mejorada a menos de "
                "treinta minutos de ida y vuelta. No dice que el agua sea segura."},
    {"clave": "personal_militar", "codigo": "MS.MIL.TOTL.P1", "fuente_id": None,
     "rotulo": "Efectivos de las fuerzas armadas", "eje": "Defensa",
     "unidad": "personas", "mas_es_peor": False,
     "origen": "Banco Mundial",
     "cautela": "Efectivos declarados. No incluye fuerzas de seguridad interior ni "
                "policiales, que en varios Estados del padron son el grueso del despliegue."},
    {"clave": "voz_rendicion", "codigo": "GOV_WGI_VA.EST", "fuente_id": 3,
     "rotulo": "Voz y rendición de cuentas", "eje": "Gobernanza",
     "unidad": "estimación de -2,5 a 2,5", "mas_es_peor": False,
     "origen": "Worldwide Governance Indicators, Banco Mundial",
     "cautela": "Estimación de percepción sobre libertad de expresión, asociación y "
                "participación. No cuenta hechos."},
    {"clave": "calidad_regulatoria", "codigo": "GOV_WGI_RQ.EST", "fuente_id": 3,
     "rotulo": "Calidad regulatoria", "eje": "Gobernanza",
     "unidad": "estimación de -2,5 a 2,5", "mas_es_peor": False,
     "origen": "Worldwide Governance Indicators, Banco Mundial",
     "cautela": "Estimación de percepción sobre la capacidad del Estado de formular "
                "reglas razonables. No cuenta hechos."},
    {"clave": "recaudacion", "codigo": "GC.TAX.TOTL.GD.ZS", "fuente_id": None,
     "rotulo": "Recaudación tributaria", "eje": "Gobernanza",
     "unidad": "% del producto", "mas_es_peor": False,
     "origen": "FMI y Banco Mundial",
     "cautela": "Entra como capacidad del Estado de recaudar, no como indicador "
                "económico. Una recaudación baja frente a una economía grande señala "
                "evasión o economía no registrada."},
    {"clave": "desempleo_joven", "codigo": "SL.UEM.1524.ZS", "fuente_id": None,
     "rotulo": "Desempleo juvenil", "eje": "Desarrollo",
     "unidad": "% de la población de 15 a 24", "mas_es_peor": True,
     "origen": "OIT, compilado por el Banco Mundial",
     "cautela": "Estimación modelada de la OIT donde el Estado no pública encuesta propia."},
    {"clave": "gini", "codigo": "SI.POV.GINI", "fuente_id": None,
     "rotulo": "Desigualdad — índice de Gini", "eje": "Desarrollo",
     "unidad": "0 igualdad, 100 desigualdad máxima", "mas_es_peor": True,
     "origen": "Banco Mundial, sobre encuestas de hogares",
     "cautela": "Depende de la encuesta de hogares de cada Estado, con años y "
                "metodologías distintos. La comparación entre países es aproximada."},
    {"clave": "pobreza", "codigo": "SI.POV.NAHC", "fuente_id": None,
     "rotulo": "Pobreza según línea nacional", "eje": "Desarrollo",
     "unidad": "% de la población", "mas_es_peor": True,
     "origen": "Banco Mundial, sobre líneas nacionales",
     "cautela": "CADA ESTADO DEFINE SU PROPIA LINEA DE POBREZA. Las cifras NO son "
                "comparables entre países: solo su evolución dentro de cada uno."},
    {"clave": "internet", "codigo": "IT.NET.USER.ZS", "fuente_id": None,
     "rotulo": "Usuarios de internet", "eje": "Desarrollo",
     "unidad": "% de la población", "mas_es_peor": False,
     "origen": "UIT, compilado por el Banco Mundial",
     "cautela": "Es también la base de exposición para la materia de ciberseguridad: "
                "sin población conectada no hay superficie de ataque."},
    {"clave": "bosque", "codigo": "AG.LND.FRST.ZS", "fuente_id": None,
     "rotulo": "Superficie forestal", "eje": "Desarrollo",
     "unidad": "% del territorio", "mas_es_peor": False,
     "origen": "FAO, compilado por el Banco Mundial",
     "cautela": "Superficie total, no su estado de conservación. Una plantación cuenta "
                "igual que un bosque primario."},
    {"clave": "regalo_contrato", "codigo": "IC.FRM.CORR.ZS", "fuente_id": None,
     "rotulo": "Empresas que esperan pagar por un contrato público", "eje": "Gobernanza",
     "unidad": "% de las empresas consultadas", "mas_es_peor": True,
     "origen": "Encuestas de Empresas del Banco Mundial",
     "cautela": "Es la materia de INTEGRIDAD DE LA CONTRATACION PUBLICA. Mide lo que la "
                "empresa declara esperar, no un soborno comprobado. La encuesta no se "
                "levanta todos los años en todos los Estados: el dato de cada país es "
                "de la última ronda disponible y las rondas no coinciden entre si."},
    {"clave": "servidores_seguros", "codigo": "IT.NET.SECR.P6", "fuente_id": None,
     "rotulo": "Servidores de internet cifrados", "eje": "Seguridad",
     "unidad": "por millón de habitantes", "mas_es_peor": False,
     "origen": "Netcraft, compilado por el Banco Mundial",
     "cautela": "Es el único indicador de CIBERSEGURIDAD comparable y gratuito que se "
                "encontro para los 33. Mide infraestructura de cifrado desplegada, no "
                "mide ataques, ni defensa estatal, ni incidentes. Un valor alto indica "
                "una economía digital mas madura, no un Estado mas protegido."},
    {"clave": "banda_ancha", "codigo": "IT.NET.BBND.P2", "fuente_id": None,
     "rotulo": "Suscripciones a banda ancha fija", "eje": "Desarrollo",
     "unidad": "por 100 habitantes", "mas_es_peor": False,
     "origen": "UIT, compilado por el Banco Mundial",
     "cautela": "Junto con los usuarios de internet, delimita la superficie expuesta a "
                "ataque informatico. No mide calidad ni continuidad del servicio."},
    {"clave": "migrantes", "codigo": "SM.POP.TOTL", "fuente_id": None,
     "rotulo": "Población migrante que el país aloja", "eje": "Seguridad",
     "unidad": "personas", "mas_es_peor": False,
     "origen": "Naciones Unidas, compilado por el Banco Mundial",
     "cautela": "Personas nacidas en otro país que residen en este. NO mide flujo ni "
                "irregularidad: es el acervo acumulado. Y no dice nada sobre delito: "
                "asociar migración con inseguridad es un juicio, y el registro no lo hace."},
    {"clave": "migrantes_pct", "codigo": "SM.POP.TOTL.ZS", "fuente_id": None,
     "rotulo": "Peso de la población migrante", "eje": "Seguridad",
     "unidad": "% de la población", "mas_es_peor": False,
     "origen": "Naciones Unidas, compilado por el Banco Mundial",
     "cautela": "El mismo acervo medido contra el tamaño del país. Un Estado chico con "
                "recepción alta aparece arriba sin que el número absoluto sea grande."},
    {"clave": "migracion_neta", "codigo": "SM.POP.NETM", "fuente_id": None,
     "rotulo": "Migración neta", "eje": "Seguridad",
     "unidad": "personas por quinquenio", "mas_es_peor": False,
     "origen": "Naciones Unidas, compilado por el Banco Mundial",
     "cautela": "Entradas menos salidas. NEGATIVO significa que se fue mas gente de la "
                "que llegó: es el indicador de expulsión de población. Se estima por "
                "quinquenios, de modo que no capta una crisis de un solo año."},
    {"clave": "remesas", "codigo": "BX.TRF.PWKR.DT.GD.ZS", "fuente_id": None,
     "rotulo": "Remesas recibidas", "eje": "Seguridad",
     "unidad": "% del producto", "mas_es_peor": False,
     "origen": "Banco Mundial",
     "cautela": "Entra como medida de MIGRACIÓN, no como indicador económico: es cuanto "
                "pesa el dinero que mandan quienes se fueron. Un valor alto señala una "
                "diaspora grande y una economía dependiente de ella. Solo cuenta los "
                "envios por via formal: lo que viaja por fuera del sistema no aparece."},
    {"clave": "gasto_militar_publico", "codigo": "MS.MIL.XPND.ZS", "fuente_id": None,
     "rotulo": "Gasto militar sobre el gasto del Estado", "eje": "Defensa",
     "unidad": "% del gasto público", "mas_es_peor": False,
     "origen": "SIPRI, compilado por el Banco Mundial",
     "cautela": "Cuanto de lo que gasta el Estado va a defensa. Leido junto al gasto "
                "sobre el producto separa dos cosas distintas: un Estado chico que "
                "dedica mucho de lo poco que tiene, de uno grande que dedica poco de "
                "mucho."},
    {"clave": "gasto_militar_dolares", "codigo": "MS.MIL.XPND.CD", "fuente_id": None,
     "rotulo": "Gasto militar en dólares", "eje": "Defensa",
     "unidad": "dólares estadounidenses corrientes", "mas_es_peor": False,
     "origen": "SIPRI, compilado por el Banco Mundial",
     "cautela": "El tamaño absoluto del presupuesto. En dolares corrientes: la "
                "comparación entre años distintos arrastra inflación y tipo de cambio."},
    {"clave": "militares_fuerza_laboral", "codigo": "MS.MIL.TOTL.TF.ZS", "fuente_id": None,
     "rotulo": "Efectivos sobre la fuerza laboral", "eje": "Defensa",
     "unidad": "% de la fuerza laboral", "mas_es_peor": False,
     "origen": "Banco Mundial",
     "cautela": "Que proporción de quienes trabajan esta bajo bandera. Es la medida de "
                "peso relativo del instrumento militar en la sociedad."},
    {"clave": "armas_importadas", "codigo": "MS.MIL.MPRT.KD", "fuente_id": None,
     "rotulo": "Importación de armamento mayor", "eje": "Defensa",
     "unidad": "valor indicativo SIPRI, NO son dólares", "mas_es_peor": False,
     "origen": "SIPRI, compilado por el Banco Mundial",
     "cautela": "Es el indicador de MATERIAL disponible al que se puede llegar sin "
                "pagar: mide la adquisición de armamento mayor —aeronaves, buques, "
                "blindados, misiles— no el inventario. La unidad no es dinero: es un "
                "valor indicativo que SIPRI asigna según capacidad militar, para poder "
                "comparar sistemas de precios distintos. Un año sin compras da cero y "
                "no significa que el país no tenga material."},
    {"clave": "armas_exportadas", "codigo": "MS.MIL.XPRT.KD", "fuente_id": None,
     "rotulo": "Exportación de armamento mayor", "eje": "Defensa",
     "unidad": "valor indicativo SIPRI, NO son dólares", "mas_es_peor": False,
     "origen": "SIPRI, compilado por el Banco Mundial",
     "cautela": "Muy pocos Estados de la región exportan armamento mayor: la mayoria "
                "figura sin dato, y eso es el dato. Misma unidad indicativa que la "
                "importación."},
]


def _traer(indicador: dict, isos: list) -> dict:
    """Serie anual por país de un indicador. Devuelve {iso: [(año, valor)]}."""
    partes = [
        f"{BASE}/country/{';'.join(isos)}/indicator/{indicador['codigo']}",
        f"?format=json&per_page=20000&date={DESDE}:{HASTA}",
    ]
    if indicador["fuente_id"]:
        partes.append(f"&source={indicador['fuente_id']}")
    # SE REINTENTA ANTES DE DAR UN INDICADOR POR CAIDO. La fuente contesta a
    # unos indicadores y a otros no, y cambia en cada vuelta: son treinta y
    # cuatro pedidos seguidos y corta unos cuantos. La mayoria de esos cortes se
    # resuelven en el segundo intento.
    peticion = urllib.request.Request("".join(partes), headers={"User-Agent": comun.AGENTE})
    crudo, ultimo = None, None
    for intento in range(3):
        if intento:
            time.sleep(2 * intento)
        try:
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                crudo = json.loads(respuesta.read().decode("utf-8", "replace"))
        except Exception as error:  # noqa: BLE001 — se reintenta y, si no, se declara
            ultimo, crudo = error, None
            continue
        if isinstance(crudo, list) and len(crudo) >= 2 and crudo[1]:
            break
        ultimo, crudo = crudo, None

    if not isinstance(crudo, list) or len(crudo) < 2 or crudo[1] is None:
        raise RuntimeError(f"El Banco Mundial no devolvió serie para {indicador['codigo']}: {ultimo}")

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

    # UN INDICADOR CON CERO ESTADOS NO ES UN RESULTADO: ES UNA FALLA.
    #
    # Pasó, y pasó con homicidios, que es la única cifra de seguridad comparable
    # entre los 33. La API respondió sin excepción y devolvió vacío; el
    # indicador se publicó igual, declarado en el catálogo y sin un solo valor.
    # Río abajo el mapa pintaba los treinta y tres Estados del color de fondo,
    # la leyenda inventaba cortes de reserva —«hasta 1 · 1 a 2 · 2 a 3» sobre
    # una serie que llega a 64— y el selector seguía ofreciendo el tema.
    #
    # Se lo saca de todo: del catálogo, de la cobertura y de los registros. El
    # sitio no puede ofrecer lo que no existe, y la falla queda declarada donde
    # se declaran las demás.

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

    # UN INDICADOR CON CERO ESTADOS NO ES UN RESULTADO: ES UNA FALLA.
    #
    # Paso, y paso con homicidios, que es la unica cifra de seguridad comparable
    # entre los 33. La fuente respondio sin excepcion y no dejo un solo valor en
    # el padron; el indicador se publico igual, declarado en el catalogo y
    # vacio. Rio abajo el mapa pintaba los treinta y tres Estados del color de
    # fondo, la leyenda inventaba cortes de reserva y el selector seguia
    # ofreciendo el tema.
    #
    # El filtro va DESPUES de contar la cobertura y no antes: que la API
    # devuelva algo no significa que ese algo caiga en los Estados del padron, y
    # mirar lo que devolvio en vez de lo que quedo fue justamente el error de la
    # primera version de este control.
    # LO QUE NO VINO ESTA VUELTA SE CONSERVA DE LA ANTERIOR, Y SE DICE.
    #
    # El valor viejo no es una invencion: es el ultimo dato que la fuente
    # publico, y viaja con su anio como todos los demas. Perder un indicador
    # porque la fuente tosio es peor que mostrarlo con la fecha que tiene,
    # siempre que la fecha este dicha. Lo que sigue prohibido es publicar un
    # indicador VACIO como si existiera: eso es lo que dejaba el mapa en blanco.
    heredados = []
    previo = comun.DATOS / "publico" / "banco-mundial.json"
    if previo.exists():
        try:
            anterior = json.loads(previo.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — sin archivo previo no hay nada que heredar
            anterior = {}
        antes = {r["iso"]: r.get("indicadores", {}) for r in anterior.get("registros", [])}
        porIso = {r["iso"]: r for r in registros}
        for i in INDICADORES:
            clave = i["clave"]
            if cobertura.get(clave, 0):
                continue
            recuperados = 0
            for iso, viejos in antes.items():
                dato = viejos.get(clave)
                if not dato:
                    continue
                ficha = porIso.get(iso)
                if ficha is None:
                    continue
                ficha["indicadores"][clave] = dato
                recuperados += 1
            if recuperados:
                cobertura[clave] = recuperados
                heredados.append(f"{i['rotulo']}: no se pudo actualizar en esta vuelta; "
                                 f"se conserva el dato anterior en {recuperados} Estados")

    publicables = [i for i in INDICADORES if cobertura.get(i["clave"], 0) > 0]
    for i in INDICADORES:
        if cobertura.get(i["clave"], 0):
            continue
        if not any(f.startswith(i["rotulo"] + ":") for f in fallidos):
            fallidos.append(f"{i['rotulo']}: la fuente no dejo un solo Estado del padron")
    fallidos.extend(heredados)
    fuera = {i["clave"] for i in INDICADORES} - {i["clave"] for i in publicables}
    for ficha in registros:
        for clave in fuera:
            ficha["indicadores"].pop(clave, None)
    registros = [r for r in registros if r["indicadores"]]

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
        "entre el primer y el último año disponibles dentro de esa ventana, que pueden "
        "no ser los extremos de la ventana misma.",
        "Serie anual con rezago: el último año disponible suele ir dos o tres años "
        "atrás del corriente. No es un dato en vivo.",
        "Los tres indicadores de gobernanza son estimaciones de percepción en escala "
        "de -2,5 a 2,5, construidas agregando encuestas y evaluaciones de expertos. No "
        "cuentan hechos y no pueden presentarse como recuentos.",
        "El homicidio sí es recuento de hechos, pero depende de la capacidad de "
        "registro de cada Estado: uno que registra peor aparece con menos homicidios. "
        "La cifra baja puede indicar buena seguridad o mal registro.",
        "Sin desglose subnacional: la cifra es nacional.",
        (
            "Cobertura por indicador: "
            + ", ".join(f"{i['rotulo']} en {cobertura.get(i['clave'], 0)} de 33" for i in publicables)
            + "."
        ),
    ]
    if faltan:
        vacios.append(f"Sin ningún indicador: {', '.join(faltan)}.")
    if fallidos:
        vacios.append(f"Indicadores que no respondieron en esta corrida: {'; '.join(fallidos)}.")
    vacios.append(
        "Licencia abierta con atribución obligatoria al Banco Mundial. A diferencia de "
        "otras fuentes del catálogo, no restringe el uso comercial."
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
                for i in publicables
            ],
            "cobertura": cobertura,
            "serie_desde": DESDE,
            "ventana_anios": VENTANA,
        },
    )


if __name__ == "__main__":
    comun.correr("banco-mundial", recolectar)
