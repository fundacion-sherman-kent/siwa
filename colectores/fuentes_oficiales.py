"""Padrón de fuentes oficiales — catálogos de datos abiertos de los Estados.

**Esto no publica datos: publica dónde están los datos.** Es un índice
verificado de qué conjuntos oficiales existen en cada país para cada materia del
registro, con su nombre y su dirección, para que el analista vaya al original.

Se hace así, y no descargando las cifras, por una razón de método: **el dato de
seguridad existe país por país pero no está homologado.** Cada Estado define el
homicidio a su manera, lo publica con su cadencia y lo cuenta desde su año. Una
serie regional armada sumando esas cifras sería una serie falsa. El índice
manda al analista al original, donde la definición está escrita.

Consulta portales CKAN y Socrata, que son interfaces estándar. El padrón vive en
`colectores/oficiales.json` y lo mantiene el equipo analítico.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import comun
import geo

PADRON = Path(__file__).resolve().parent / "oficiales.json"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
EJEMPLOS = 4

# HAY PORTALES QUE HABLAN MEDIO DIALECTO. Paraguay y Perú publican catálogo
# —434 y 4.684 conjuntos— pero NO tienen buscador: `package_search` devuelve 404
# en Perú y algo que no es JSON en Paraguay. Sumarlos sin más habría dado cero en
# las seis materias, y el registro habría dicho que no publican nada.
#
# Con esos se lee la LISTA COMPLETA de nombres una sola vez y se filtra acá.
# Es una busqueda POR NOMBRE, no por texto completo, y por eso NO es comparable
# con la de los portales que sí buscan: un conjunto llamado «serie 3.4.1» sobre
# homicidios no aparece. Se declara.
_LISTAS: dict = {}


def _lista(base: str) -> list:
    """La lista completa de nombres de un portal, pedida una sola vez."""
    if base in _LISTAS:
        return _LISTAS[base]
    try:
        peticion = urllib.request.Request(
            f"{base}/api/3/action/package_list",
            headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
        with urllib.request.urlopen(peticion, timeout=60) as respuesta:
            d = json.loads(respuesta.read(8_000_000).decode("utf-8", "replace"))
        _LISTAS[base] = d.get("result") or []
    except Exception:  # noqa: BLE001 — la falla se declara arriba
        _LISTAS[base] = []
    return _LISTAS[base]


def _consultar(portal: dict, consulta: str) -> tuple:
    """Devuelve (cantidad, ejemplos, falla) para una materia en un portal."""
    base = portal["base"].rstrip("/")
    termino = urllib.parse.quote(consulta)

    if portal["tipo"] == "CKAN-lista":
        nombres = _lista(base)
        if not nombres:
            return (0, [], "no se pudo leer la lista de conjuntos")
        # Se compara sin tildes: los nombres vienen normalizados y la consulta no.
        import unicodedata
        def pelar(t):
            t = unicodedata.normalize("NFKD", t.lower())
            return "".join(c for c in t if not unicodedata.combining(c))
        aguja = pelar(consulta)
        hallados = [n for n in nombres if aguja in pelar(n)]
        ejemplos = [{"titulo": n.replace("-", " ").strip(),
                     "organismo": "",
                     "enlace": f"{base}/dataset/{n}"} for n in hallados[:EJEMPLOS]]
        return (len(hallados), ejemplos, None)

    if portal["tipo"] == "CKAN":
        url = f"{base}/api/3/action/package_search?q={termino}&rows={EJEMPLOS}"
    else:
        url = f"{base}/api/catalog/v1?q={termino}&limit={EJEMPLOS}"
    try:
        peticion = urllib.request.Request(
            url, headers={"User-Agent": NAVEGADOR, "Accept": "application/json"})
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            crudo = json.loads(respuesta.read(400_000).decode("utf-8", "replace"))
    except Exception as error:  # noqa: BLE001 — la falla del portal se declara
        return (0, [], f"{type(error).__name__}")

    ejemplos = []
    if portal["tipo"] == "CKAN":
        if not crudo.get("success"):
            return (0, [], "respuesta sin exito")
        resultado = crudo["result"]
        cantidad = resultado.get("count", 0)
        for conjunto in resultado.get("results", [])[:EJEMPLOS]:
            ejemplos.append({
                "titulo": (conjunto.get("title") or conjunto.get("name") or "").strip(),
                "organismo": (conjunto.get("organization") or {}).get("title", ""),
                "enlace": f"{base}/dataset/{conjunto.get('name','')}",
            })
    else:
        cantidad = crudo.get("resultSetSize", 0)
        for conjunto in crudo.get("results", [])[:EJEMPLOS]:
            recurso = conjunto.get("resource", {})
            ejemplos.append({
                "titulo": (recurso.get("name") or "").strip(),
                "organismo": (conjunto.get("owner") or {}).get("display_name", ""),
                "enlace": conjunto.get("permalink", base),
            })
    return (cantidad, ejemplos, None)


# ---- Oficinas nacionales de estadistica ---------------------------------
# Nueve Estados tienen catalogo de datos abiertos consultable por maquina. Los
# otros VEINTICUATRO figuraban en el registro sin NINGUNA fuente oficial, y eso
# se leia como si no publicaran. Publican: tienen oficina de estadistica y la
# oficina contesta. Lo que no tienen es interfaz para programas.
#
# Aca se toca cada una y se dice que contesto. NO se cuentan conjuntos —no hay
# de donde— y por eso estas fichas no son comparables con las de los portales.
CONTROL_OFICINA = "ARG"     # el INDEC responde; si no, el que fallo es el robot
ESPERA_OFICINA = 35

# La firma del desafio anti-robot tiene que ser ESTRECHA. La primera version
# buscaba la palabra «captcha» en el cuerpo, y esa palabra aparece en cualquier
# formulario de contacto: marco como bloqueadas a seis oficinas que sirven su
# sitio entero, Chile entre ellas. Ahora se exige que el viaje TERMINE en un
# servicio de desafio, o que el titulo de la pagina sea el del desafio. Un
# rotulo falso de bloqueo es peor que no tener rotulo.
DESTINOS_DESAFIO = ("perfdrive.com", "validate.perfdrive.com", "ddos-guard.net",
                    "incapsula.com", "imperva.com", "challenges.cloudflare.com")
TITULOS_DESAFIO = ("captcha", "just a moment", "checking your browser",
                   "attention required", "verificacion de seguridad",
                   "verificación de seguridad", "access denied")


def _titulo(cuerpo: bytes) -> str:
    texto = cuerpo[:120_000].decode("utf-8", "replace")
    ini = texto.lower().find("<title")
    if ini == -1:
        return ""
    ini = texto.find(">", ini)
    fin = texto.lower().find("</title>", ini)
    if ini == -1 or fin == -1:
        return ""
    return " ".join(texto[ini + 1:fin].split()).strip()


def _pedir(url: str, verificar: bool):
    contexto = None
    if not verificar:
        contexto = ssl.create_default_context()
        contexto.check_hostname = False
        contexto.verify_mode = ssl.CERT_NONE
    peticion = urllib.request.Request(url, headers={
        "User-Agent": NAVEGADOR,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "es,en;q=0.8"})
    with urllib.request.urlopen(peticion, timeout=ESPERA_OFICINA, context=contexto) as r:
        return r.read(400_000), r.status, r.geturl()


def _tocar_oficina(oficina: dict) -> dict:
    """Toca una oficina y dice QUE contesto, que no es lo mismo que si publica."""
    url = oficina["url"]
    ficha = {k: oficina[k] for k in ("iso", "sigla", "organismo", "url") if k in oficina}
    if oficina.get("nota"):
        ficha["nota"] = oficina["nota"]
    certificado = "valido"
    try:
        cuerpo, codigo, destino = _pedir(url, True)
    except urllib.error.HTTPError as e:
        # Un 401 o un 403 NO dicen que el Estado no publique: dicen que publica
        # para personas y le cierra la puerta a los programas. Son dos cosas
        # distintas y el registro no debe confundirlas.
        ficha["estado"] = ("cierra_a_maquinas" if e.code in (401, 403, 429)
                           else "falla_el_servidor" if e.code >= 500 else "responde_con_error")
        ficha["codigo"] = e.code
        return ficha
    except ssl.SSLError as e:
        # El servidor CONTESTA; lo que no valida es su certificado. Llamar a eso
        # «sin respuesta» seria decir que el Estado no publica cuando lo que pasa
        # es que su certificado esta vencido o mal encadenado. Se reintenta sin
        # validar solo para saber si hay sitio detras, y se declaran las dos cosas.
        certificado = "no valida: " + str(e)[:110]
        try:
            cuerpo, codigo, destino = _pedir(url, False)
        except Exception as e2:  # noqa: BLE001
            ficha["estado"] = "sin_respuesta"
            ficha["detalle"] = f"{type(e2).__name__}: {e2}"[:160]
            ficha["certificado"] = certificado
            return ficha
    except Exception as e:  # noqa: BLE001 — se declara la falla, no se la disfraza
        falla = f"{type(e).__name__}: {e}"
        if "CERTIFICATE_VERIFY_FAILED" in falla or "SSL" in falla:
            certificado = "no valida: " + falla[:110]
            try:
                cuerpo, codigo, destino = _pedir(url, False)
            except Exception as e2:  # noqa: BLE001
                ficha["estado"] = "sin_respuesta"
                ficha["detalle"] = f"{type(e2).__name__}: {e2}"[:160]
                ficha["certificado"] = certificado
                return ficha
        else:
            ficha["estado"] = "no_resuelve" if "getaddrinfo" in falla else "sin_respuesta"
            ficha["detalle"] = falla[:160]
            return ficha

    titulo = _titulo(cuerpo).lower()
    if (any(d in destino.lower() for d in DESTINOS_DESAFIO)
            or any(t in titulo for t in TITULOS_DESAFIO)):
        ficha["estado"] = "verificacion_anti_robot"
    elif certificado != "valido":
        ficha["estado"] = "certificado_invalido"
    else:
        ficha["estado"] = "responde"
    ficha["codigo"] = codigo
    if certificado != "valido":
        ficha["certificado"] = certificado
    return ficha


def _oficinas(padron: dict) -> tuple:
    bloque = padron.get("oficinas_estadistica") or {}
    lista = bloque.get("oficinas") or []
    if not lista:
        return [], "el padron no trae oficinas de estadistica"
    with ThreadPoolExecutor(max_workers=10) as ejecutor:
        fichas = list(ejecutor.map(_tocar_oficina, lista))
    control = next((f for f in fichas if f["iso"] == CONTROL_OFICINA), None)
    if control is None or control["estado"] != "responde":
        # PROBAR ANTES DE AFIRMAR: si la oficina que se sabe que contesta no
        # contesta, lo que fallo es el sondeo. No se publica un mapa de silencio
        # dibujado por una falla propia.
        return fichas, (
            f"El control ({CONTROL_OFICINA}) no respondio en esta corrida: "
            f"{(control or {}).get('estado', 'ausente')}. El estado de las demas "
            "oficinas de este sondeo NO es confiable y no debe leerse como "
            "opacidad de ningun Estado.")
    return fichas, None


def recolectar():
    padron = json.loads(PADRON.read_text(encoding="utf-8"))
    portales, materias = padron["portales"], padron["materias"]
    nombres = {p["iso"]: p for p in geo.padron()}

    tareas = [(p, m) for p in portales for m in materias]
    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        crudos = list(ejecutor.map(lambda t: (t[0], t[1]) + _consultar(t[0], t[1]["consulta"]), tareas))

    por_pais, caidos = {}, []
    for portal, materia, cantidad, ejemplos, falla in crudos:
        iso = portal["iso"]
        ficha = por_pais.setdefault(iso, {
            **nombres.get(iso, {"iso": iso, "pais": iso, "bloque": "—"}),
            "organismo": portal["organismo"],
            "tipo": portal["tipo"],
            "portal": portal["base"],
            "materias": [],
            "conjuntos_hallados": 0,
        })
        if falla:
            caidos.append(f"{iso}/{materia['materia']}: {falla}")
            continue
        ficha["materias"].append({
            "materia": materia["materia"],
            "eje": materia["eje"],
            "consulta": materia["consulta"],
            "cantidad": cantidad,
            "ejemplos": ejemplos,
        })
        ficha["conjuntos_hallados"] += cantidad

    registros = sorted(por_pais.values(), key=lambda r: r["conjuntos_hallados"], reverse=True)
    for ficha in registros:
        ficha["materias"].sort(key=lambda m: m["cantidad"], reverse=True)

    oficinas, aviso_control = _oficinas(padron)
    por_estado = {}
    for o in oficinas:
        por_estado[o["estado"]] = por_estado.get(o["estado"], 0) + 1

    con_portal = {r["iso"] for r in registros}
    sin_portal = [p["pais"] for p in geo.padron() if p["iso"] not in con_portal]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=(
            "Catálogos oficiales de los propios Estados: registro primario. Lo que se "
            "consigna es la existencia del conjunto de datos y su dirección, no su "
            "contenido. Fuente única por naturaleza: solo el Estado publica su catálogo."
        ),
    )

    vacios = [

        "Dos portales se leen de otra manera, y sus cifras no son comparables con las "

        "demás. Perú y Paraguay publican catálogo —4.684 y 434 conjuntos— pero no "

        "tienen buscador: package_search devuelve 404 en uno y algo que no es JSON en "

        "el otro. Con ellos se lee la lista completa de nombres y se filtra por nombre, "

        "no por texto completo. Un conjunto llamado «serie 3.4.1» sobre homicidios no "

        "aparece, de modo que sus cantidades salen más bajas por como se los consulta y "

        "no por lo que publican. Se los suma igual: tenerlos mal contados es mejor que "

        "no tenerlos, siempre que se diga.",
        "Esto no publica datos, publica dónde están. Es un índice de conjuntos "
        "oficiales con su dirección, para que el analista vaya al original.",
        "**Las cifras de estos catálogos no son comparables entre países.** Cada Estado "
        "define el delito a su manera, lo publica con su cadencia y lo cuenta desde su "
        "año. Sumarlas para armar una serie regional produciría una serie falsa.",
        (
            f"Solo {len(con_portal)} de los 33 Estados tienen portal oficial con interfaz "
            f"de consulta verificada. Sin portal verificado: {', '.join(sin_portal)}."
        ),
        "Que un Estado no tenga portal NO significa que no publique. Las 33 oficinas nacionales de estadistica estan en el padron con su direccion "
        "verificada, y en esta corrida respondieron " + str(por_estado.get("responde", 0)) + " de 33. Un Estado sin portal de datos abiertos es un Estado sin interfaz para programas, no un Estado callado.",
        "Las fichas de oficina de estadistica NO son comparables con las de portal: de la oficina se registra que existe, donde esta y que contesto, no cuantos conjuntos publica. No hay de donde contarlos.",
        "Cuatro respuestas distintas que no deben leerse como una sola: «cierra a maquinas» es un 401 o un 403 —el Estado publica para personas y rechaza a los programas—; «verificacion anti-robot» es una pagina de desafio devuelta con codigo 200, que finge normalidad; «falla el servidor» es un 500, que es una averia; y «no resuelve» es que el nombre de dominio no llega a ninguna maquina. Ninguna de las cuatro prueba opacidad.",
        "Que un Estado no figure no prueba que carezca de portal. De los que no figuran: "
        "Brasil exige clave gratuita con registro; Guatemala, Costa Rica, Bolivia y Ecuador "
        "interponen protección contra acceso automatizado, que no se esquiva por decisión "
        "de doctrina (límites.md) y se gestiona por vía oficial; Perú y Jamaica tienen "
        "portal cuya plataforma no se identificó. El resto no expuso dirección alguna.",
        "La búsqueda es por palabra en el título y la descripción del conjunto. Un "
        "conjunto rotulado con otro vocabulario no aparece, y uno que menciona la "
        "palabra al pasar aparece sin corresponder.",
        "El recuento es de conjuntos publicados, no de calidad ni de vigencia: un "
        "catálogo puede listar un conjunto abandonado hace años.",
    ]
    if aviso_control:
        vacios.append(aviso_control)
    if caidos:
        vacios.append(f"{len(caidos)} consultas fallaron en esta corrida: {'; '.join(caidos)}.")

    return comun.escribir(
        colector="oficiales",
        capa="publico",
        fuente="Catálogos oficiales de datos abiertos de los Estados del padrón",
        url_fuente="colectores/oficiales.json",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "estados_con_portal": len(con_portal),
                "estados_del_padron": 33,
                "conjuntos_hallados": sum(r["conjuntos_hallados"] for r in registros),
                "materias_consultadas": len(materias),
                "oficinas_que_responden": por_estado.get("responde", 0),
                "estados_con_alguna_fuente_oficial": len(
                    con_portal | {o["iso"] for o in oficinas
                                  if o["estado"] == "responde"}),
            },
            "oficinas_estadistica": oficinas,
            "oficinas_por_estado": por_estado,
            "sectoriales_verificados": padron.get("sectoriales_verificados", []),
            "sin_acceso_automatizado": padron.get("_bloqueados", {}),
        },
    )


if __name__ == "__main__":
    comun.correr("oficiales", recolectar)
