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
    cuerpo = json.dumps({
        "username": usuario, "password": clave,
        "grant_type": "password", "client_id": "acled", "scope": "authenticated",
    }).encode()
    peticion = urllib.request.Request(
        TESTIGO, data=cuerpo, method="POST",
        headers={"User-Agent": NAVEGADOR, "Content-Type": "application/json",
                 "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=45) as respuesta:
        d = json.loads(respuesta.read(200_000).decode("utf-8", "replace"))
    t = d.get("access_token")
    if not t:
        raise RuntimeError(
            "La fuente respondió sin entregar testigo. NO se continúa a ciegas: "
            "seguir sin testigo daría cero eventos en todos los Estados, y eso se "
            "leería como «no pasa nada» cuando en realidad es «no pudimos mirar».")
    return t


def _hayRegistro(testigo: str, pais: str, desde: str) -> bool | None:
    """¿La fuente registra actividad en este Estado dentro de la ventana?

    Devuelve un SÍ o un NO, nunca un número. El recuento se usa acá y se tira:
    no vuelve de esta función y por lo tanto no puede llegar al archivo.
    """
    p = {"country": pais, "event_date": desde, "event_date_where": ">=",
         "limit": "1", "_format": "json"}
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
    datos = d.get("data")
    if datos is None:
        return None
    return len(datos) > 0


def recolectar():
    usuario = os.environ.get("ACLED_USUARIO", "").strip()
    clave = os.environ.get("ACLED_CLAVE", "").strip()

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
    if conCredencial:
        testigo = _pedirTestigo(usuario, clave)

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
