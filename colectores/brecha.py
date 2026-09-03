"""La brecha: lo que ocurre y el Estado no publica.

QUÉ MIDE, Y POR QUÉ NO ES LO QUE PARECE
---------------------------------------
No mide conflicto. Mide **transparencia**: si en un Estado hay actividad
registrada por un observatorio independiente **y ese Estado no publica nada de
sí mismo**, esa distancia es un hecho sobre su publicación, no sobre su
violencia.

Es una variable **de la Oficina**, no de la fuente que la alimenta.

LA REGLA QUE GOBIERNA ESTE COLECTOR, Y NO ES NEGOCIABLE
-------------------------------------------------------
`NO SE PUBLICA NI UN SOLO NUMERO DE LA FUENTE.` Ni eventos, ni recuentos, ni
fechas, ni actores. Lo único que sale es **una clasificación de tres estados**
—hay registro y publica, hay registro y no publica, no hay registro— que nadie
puede revertir para reconstruir nada del conjunto original.

Esa es la condición que la licencia de la fuente exige para el material
derivado, y acá se cumple **por construcción, no por promesa**: el recuento
entra al cálculo y se descarta; no llega al archivo publicado.

Y aun así queda dicho lo que corresponde: **esta es nuestra lectura de un
contrato ajeno.** Se le consultó a la fuente; mientras no haya respuesta, el
colector puede correr porque no publica su contenido, pero la interpretación es
nuestra y se declara como tal.

LA CREDENCIAL
-------------
La fuente autentica con **correo y contraseña**, no con clave revocable. Este es
el único colector del registro que necesita un secreto, y por eso:

- se lee del entorno, nunca del código ni de un archivo del repositorio;
- **si no está, el colector no falla: se declara sin credencial** y el registro
  sigue funcionando exactamente igual;
- el testigo dura 24 horas y **no se guarda en ningún lado**: se pide en cada
  corrida y muere con ella.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

import comun
import geo

TESTIGO = "https://acleddata.com/oauth/token"
DATOS = "https://acleddata.com/api/acled/read"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DIAS = 30   # la ventana de observación

# Lo ultimo que contesto la fuente, para poder decir POR QUE fallo el control.
ULTIMA_RESPUESTA: dict = {}

# El nombre con que la fuente conoce a cada Estado. Se declara a mano porque
# adivinarlo por parecido de cadena confunde «Dominica» con «Dominican Republic».
NOMBRE_EN_LA_FUENTE = {
    "ARG": "Argentina", "BOL": "Bolivia", "BRA": "Brazil", "CHL": "Chile",
    "COL": "Colombia", "CRI": "Costa Rica", "CUB": "Cuba",
    "DOM": "Dominican Republic", "ECU": "Ecuador", "SLV": "El Salvador",
    "GTM": "Guatemala", "HTI": "Haiti", "HND": "Honduras", "MEX": "Mexico",
    "NIC": "Nicaragua", "PAN": "Panama", "PRY": "Paraguay", "PER": "Peru",
    "URY": "Uruguay", "VEN": "Venezuela", "BLZ": "Belize", "GUY": "Guyana",
    "SUR": "Suriname", "JAM": "Jamaica", "TTO": "Trinidad and Tobago",
    "BRB": "Barbados", "BHS": "Bahamas", "ATG": "Antigua and Barbuda",
    "DMA": "Dominica", "GRD": "Grenada", "LCA": "Saint Lucia",
    "KNA": "Saint Kitts and Nevis", "VCT": "Saint Vincent and the Grenadines",
}


def _pedirTestigo(usuario: str, clave: str) -> str:
    """Pide el testigo. Prueba las dos formas y declara lo que la fuente contesta.

    La primera version mandaba JSON y la fuente devolvia 400. El estandar OAuth
    para pedir un testigo es FORMULARIO CODIFICADO, no JSON: se prueba esa
    primero. La otra queda como respaldo porque no todas las implementaciones
    siguen el estandar, y probar las dos cuesta una consulta.
    """
    campos = {"username": usuario, "password": clave,
              "grant_type": "password", "client_id": "acled",
              "scope": "authenticated"}
    intentos = [
        ("formulario", urllib.parse.urlencode(campos).encode(),
         "application/x-www-form-urlencoded"),
        ("JSON", json.dumps(campos).encode(), "application/json"),
    ]

    dichos = []
    for comoSeLlama, cuerpo, tipo in intentos:
        peticion = urllib.request.Request(
            TESTIGO, data=cuerpo, method="POST",
            headers={"User-Agent": NAVEGADOR, "Content-Type": tipo,
                     "Accept": "application/json"})
        try:
            with urllib.request.urlopen(peticion, timeout=45) as respuesta:
                d = json.loads(respuesta.read(200_000).decode("utf-8", "replace"))
        except urllib.error.HTTPError as error:
            # LO QUE LA FUENTE DICE, no lo que uno supone. Un 400 puede ser la
            # forma de la peticion o la credencial, y la unica manera de saberlo
            # es leer su respuesta. NUNCA se registra el usuario ni la clave.
            crudo = error.read(2_000).decode("utf-8", "replace")
            detalle = " ".join(crudo.split())[:300]
            dichos.append(f"{comoSeLlama}: HTTP {error.code} · {detalle}")
            continue
        except Exception as error:  # noqa: BLE001
            dichos.append(f"{comoSeLlama}: {type(error).__name__}")
            continue

        t = d.get("access_token")
        if t:
            return t
        dichos.append(f"{comoSeLlama}: respondió 200 sin entregar testigo")

    raise RuntimeError(
        "No se obtuvo testigo de la fuente. NO se continúa a ciegas: seguir sin "
        "testigo daría cero en los 33 Estados, y eso se leería como «no pasa nada» "
        "cuando en realidad es «no pudimos mirar». Lo que contestó la fuente, "
        "textual y sin credenciales: " + " | ".join(dichos))


def _hayRegistro(testigo: str, pais: str, desde: str) -> bool | None:
    """¿La fuente registra actividad en este Estado dentro de la ventana?

    Devuelve un SÍ o un NO, nunca un número. El recuento se usa acá y se tira:
    no vuelve de esta función y por lo tanto no puede llegar al archivo.
    """
    p = {"country": pais, "event_date": f"{desde}|{date.today().isoformat()}",
         "event_date_where": "BETWEEN", "limit": "1", "_format": "json"}
    url = DATOS + "?" + urllib.parse.urlencode(p)
    peticion = urllib.request.Request(
        url, headers={"User-Agent": NAVEGADOR, "Accept": "application/json",
                      "Authorization": f"Bearer {testigo}"})
    try:
        with urllib.request.urlopen(peticion, timeout=60) as respuesta:
            d = json.loads(respuesta.read(400_000).decode("utf-8", "replace"))
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise RuntimeError(
                f"La fuente rechazó la consulta ({error.code}). Puede ser el testigo "
                "vencido o un permiso que la cuenta no tiene. NO se anota «sin "
                "registro»: no saber no es saber que no.") from error
        return None
    except Exception:  # noqa: BLE001 — la falla de un Estado no tumba la corrida
        return None
    # Se guarda lo que la fuente contesta para el control, sin cifras ni contenido:
    # solo las CLAVES que devolvio y su estado. Es lo que permite distinguir «no
    # hay nada» de «pregunte mal» de «la cuenta no ve datos».
    global ULTIMA_RESPUESTA
    ULTIMA_RESPUESTA = {
        "claves": sorted(d.keys())[:12],
        "status": d.get("status"),
        "success": d.get("success"),
        "error": d.get("error") or d.get("message"),
        "count": d.get("count"),
        "total_count": d.get("total_count"),
        # LOS DOS CAMPOS QUE EXPLICAN EL CERO. La fuente respondio 200 con
        # success true y cero filas: no entendio mal la consulta, decidio no
        # entregar. Estos dos campos son donde lo dice.
        "restricciones": str(d.get("data_query_restrictions"))[:400],
        "mensajes": str(d.get("messages"))[:400],
        "filas": len(d.get("data") or []) if isinstance(d.get("data"), list) else None,
    }
    datos = d.get("data")
    if datos is None:
        return None
    return len(datos) > 0


def _conEmbargo(padron, publica, desde, restriccion):
    """La cuenta funciona, pero solo ve el pasado. Se dice, y no se falla.

    Fallar cada noche por una condicion que no va a cambiar convierte el parte de
    fallas en ruido, y entonces deja de mirarse. Un limite conocido se declara.
    """
    registros = [{
        "iso": p["iso"], "pais": p["pais"], "bloque": p["bloque"],
        "estado": "fuente_con_embargo",
        "el_estado_publica_lo_suyo": publica.get(p["iso"]) in ("al_dia",),
    } for p in padron]

    vacios = [
        "LA CUENTA TIENE UN EMBARGO DE DOCE MESES Y NO ES UNA FALLA: la fuente solo "
        "entrega datos con mas de un anio de antiguedad. Lo declara ella misma en su "
        "respuesta, y por eso una ventana de treinta dias devuelve cero CON RAZON.",
        "POR ESO LA BRECHA NO SE PUEDE CALCULAR TODAVIA, y no se calcula. Medir «lo que "
        "ocurrio y el Estado no publico» exige que las dos observaciones sean del MISMO "
        "MOMENTO. Cruzar sucesos de hace un anio contra lo que el Estado publica hoy "
        "seria una comparacion falsa, que es exactamente lo que este registro no hace.",
        "EL COLECTOR QUEDA CONSTRUIDO Y A LA ESPERA. El dia que la cuenta vea datos "
        "recientes, funciona sin tocar una linea. Mientras tanto los 33 Estados figuran "
        "con la fuente en embargo, que NO es lo mismo que en cero.",
        "HAY UN CAMINO, Y ES EL TIEMPO. La bitacora propia empezo el 1 de septiembre de "
        "2026: dentro de un anio el registro va a tener su propia memoria de que publico "
        "cada Estado en las fechas que la fuente SI deja ver, y entonces las dos "
        "observaciones vuelven a ser del mismo momento.",
        "LO QUE LA FUENTE DECLARA sobre esta cuenta, textual: " + restriccion[:300],
    ]

    return comun.escribir(
        colector="brecha",
        capa="publico",
        fuente="Fundación Sherman Kent — brecha entre lo registrado y lo publicado",
        url_fuente="https://fundacion-sherman-kent.github.io/siwa/sitio/index.html#brecha",
        calificacion=comun.calificar(
            fiabilidad="B", credibilidad=2, corroborado=False,
            nota=("La credencial funciona y la consulta es correcta; lo que la cuenta no "
                  "tiene es acceso a datos recientes. Se declara la condicion en lugar "
                  "de publicar un cero o de fallar todas las noches.")),
        registros=registros,
        vacios=vacios,
        extra={"resumen": {
            "con_credencial": True,
            "variables_que_faltan": [],
            "instrumento_probado": False,
            "embargo_de_la_fuente": True,
            "ventana_dias": DIAS,
            "desde": desde,
            "estados_con_brecha": 0,
            "estados_que_publican_y_hay_registro": 0,
            "estados_sin_registro_en_la_ventana": 0,
            "estados_sin_mirar": len(registros),
            "estados_del_padron": len(registros),
            "consultado": comun.ahora(),
        }},
    )


def recolectar():
    usuario = os.environ.get("ACLED_USUARIO", "").strip()
    clave = os.environ.get("ACLED_CLAVE", "").strip()

    # QUE FALTA, SIN DECIR QUE VALE. Decir «sin credencial» a secas obliga a
    # adivinar si el problema es el nombre del secreto, uno de los dos o los dos.
    # Se declara la AUSENCIA de cada variable, nunca su contenido.
    falta = [n for n, v in (("ACLED_USUARIO", usuario), ("ACLED_CLAVE", clave)) if not v]
    if falta:
        print(f"[brecha] sin credencial. Variables vacias o no definidas: "
              f"{', '.join(falta)}. Si el secreto se cargo con OTRO NOMBRE, el robot no "
              f"lo ve: el nombre tiene que coincidir exactamente.", file=sys.stderr)

    padron = geo.padron()
    publica = {}
    try:
        rec = json.loads((comun.DATOS / "publico" / "reciente_oficial.json")
                         .read_text(encoding="utf-8"))
        publica = {r["iso"]: r.get("estado") for r in rec.get("registros", [])}
    except Exception:  # noqa: BLE001
        pass

    desde = (date.today() - timedelta(days=DIAS)).isoformat()
    conCredencial = bool(usuario and clave)
    testigo = None
    instrumentoSano = None
    if conCredencial:
        testigo = _pedirTestigo(usuario, clave)
        # SE PRUEBA EL INSTRUMENTO CONTRA UN CASO QUE TIENE QUE DAR ALGO, antes
        # de creerle un cero a nadie. La primera version dio CERO EN LOS 33
        # ESTADOS —imposible— porque el filtro de fecha estaba mal escrito, y sin
        # este control eso se habria publicado como «no pasa nada en la region».
        instrumentoSano = _hayRegistro(testigo, "Colombia", desde)
        # EL EMBARGO NO ES UNA FALLA: ES UNA CONDICION DE LA CUENTA, y se declara
        # en vez de repetirse como error todas las noches. La fuente lo dice en
        # `data_query_restrictions`: esta cuenta solo ve datos con mas de doce
        # meses de antiguedad, de modo que una ventana de treinta dias cae
        # entera adentro del embargo y devuelve cero CON RAZON.
        r = (ULTIMA_RESPUESTA.get("restricciones") or "")
        if instrumentoSano is not True and "date_recency" in r and "Months" in r:
            return _conEmbargo(padron, publica, desde, r)
        if instrumentoSano is not True:
            raise RuntimeError(
                "La prueba del instrumento falló: la consulta de control sobre Colombia "
                "—que en cualquier ventana de treinta días tiene registros— no devolvió "
                "ninguno. Eso NO significa que no haya pasado nada: significa que la "
                "consulta está mal armada o que la cuenta no ve datos. NO se publica un "
                "cero que no se puede sostener. Lo que contestó la fuente, sin contenido: "
                + json.dumps(ULTIMA_RESPUESTA, ensure_ascii=False))

    registros, cuenta = [], {"brecha": 0, "publica_y_hay": 0, "sin_registro": 0,
                             "sin_mirar": 0}
    for p in padron:
        iso = p["iso"]
        nombre = NOMBRE_EN_LA_FUENTE.get(iso)
        publicaEste = publica.get(iso) in ("al_dia",)

        if not conCredencial or not nombre:
            estado = "sin_credencial" if not conCredencial else "sin_nombre_en_la_fuente"
            cuenta["sin_mirar"] += 1
        else:
            hay = _hayRegistro(testigo, nombre, desde)
            if hay is None:
                estado = "no_se_pudo_mirar"
                cuenta["sin_mirar"] += 1
            elif hay and not publicaEste:
                estado = "hay_registro_y_no_publica"
                cuenta["brecha"] += 1
            elif hay:
                estado = "hay_registro_y_publica"
                cuenta["publica_y_hay"] += 1
            else:
                estado = "sin_registro_en_la_ventana"
                cuenta["sin_registro"] += 1

        registros.append({
            "iso": iso, "pais": p["pais"], "bloque": p["bloque"],
            "estado": estado,
            "el_estado_publica_lo_suyo": publicaEste,
        })

    vacios = [
        "NO SE PUBLICA NI UN SOLO NUMERO DE LA FUENTE: ni eventos, ni recuentos, ni "
        "fechas, ni actores. Sale UNA CLASIFICACION DE TRES ESTADOS, que nadie puede "
        "revertir para reconstruir el conjunto original. El recuento entra al calculo y "
        "se descarta antes de escribir el archivo.",
        "ESTO NO MIDE VIOLENCIA: MIDE TRANSPARENCIA. Que un Estado figure en «hay "
        "registro y no publica» dice que un observatorio independiente anoto actividad y "
        "el Estado no publico nada de si mismo en su propio catalogo. NO dice cuanta "
        "actividad hubo, ni que sea grave, ni que el Estado la oculte a proposito.",
        "«SIN REGISTRO EN LA VENTANA» NO ES «NO PASO NADA». Es que la fuente no anoto "
        "nada, y la cobertura de cualquier observatorio es despareja: los Estados chicos "
        "del Caribe se miran menos que los grandes.",
        "LA INTERPRETACION DE LA LICENCIA ES NUESTRA. La fuente permite material derivado "
        "que sea transformativo y no reconstruible; la Oficina sostiene que una "
        "clasificacion de tres estados lo es, y se lo consulto. Mientras no haya "
        "respuesta, esta lectura queda declarada COMO LECTURA PROPIA de un contrato "
        "ajeno, no como permiso obtenido.",
        "ANTES DE CREERLE UN CERO A NADIE SE PRUEBA EL INSTRUMENTO. Se consulta un caso "
        "que tiene que dar algo —Colombia, que en cualquier ventana de treinta dias tiene "
        "registros— y si ESE da cero, la corrida se detiene entera. La primera version "
        "devolvio cero en los 33 Estados porque el filtro de fecha estaba mal escrito, y "
        "sin este control se habria publicado como «no pasa nada en la region».",
        "SIN CREDENCIAL NO SE MIRA, Y SE DICE. Este es el unico colector del registro que "
        "necesita un secreto. Si no esta, los 33 Estados quedan en «sin credencial»: NO "
        "en cero, porque no saber no es saber que no.",
    ]

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=2,
        corroborado=True,
        nota=("Variable propia de la Oficina construida cruzando DOS observaciones "
              "independientes: un observatorio externo de eventos y el propio catalogo "
              "del Estado. Fiabilidad B porque ninguno de los dos es el organismo "
              "responsable de declarar transparencia. Credibilidad 2 y corroborado "
              "porque la clasificacion exige que las dos observaciones coincidan en el "
              "mismo Estado y la misma ventana."),
    )

    return comun.escribir(
        colector="brecha",
        capa="publico",
        fuente="Fundación Sherman Kent — brecha entre lo registrado y lo publicado",
        url_fuente="https://fundacion-sherman-kent.github.io/siwa/sitio/index.html#brecha",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "con_credencial": conCredencial,
                "variables_que_faltan": falta,
                "instrumento_probado": instrumentoSano,
                "ventana_dias": DIAS,
                "desde": desde,
                "estados_con_brecha": cuenta["brecha"],
                "estados_que_publican_y_hay_registro": cuenta["publica_y_hay"],
                "estados_sin_registro_en_la_ventana": cuenta["sin_registro"],
                "estados_sin_mirar": cuenta["sin_mirar"],
                "estados_del_padron": len(registros),
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    comun.correr("brecha", recolectar)
