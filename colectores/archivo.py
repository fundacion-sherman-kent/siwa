"""La retirada: lo que un Estado publicaba y dejó de publicar, con fecha.

POR QUÉ EXISTE
--------------
El Índice de Opacidad podía decir que un Estado **no publica**. No podía decir
que **dejó de publicar**, que es una afirmación distinta y más grave: no es que
nunca hubo dato, es que lo hubo y se retiró.

El archivo público de la web guarda copias fechadas de los sitios. Preguntándole
cuál fue la última vez que un portal oficial respondió bien, y comparándolo con
lo que ese portal responde hoy, se obtiene la retirada **con fecha y verificable
por cualquiera**.

LA AFIRMACIÓN EXIGE LAS DOS MITADES, Y NINGUNA ALCANZA SOLA
-----------------------------------------------------------
- **Que el archivo no tenga capturas recientes no prueba que el sitio murió.**
  Prueba que el rastreador no pasó. Un sitio puede estar vivo y sin capturar.
- **Que el portal no nos responda hoy no prueba que esté caído.** Puede haber
  rechazado nuestra consulta, o estar caído un rato.

Por eso la retirada solo se afirma cuando **el archivo lo vio vivo en el pasado y
hoy no responde**, y aun así el producto dice las dos fechas por separado para
que el lector pueda rehacer la comprobación.

LO QUE NO HACE
--------------
No guarda ni sirve copias del contenido: publica **la fecha y la dirección de la
copia ajena**, y manda al archivo, que es donde vive. Tampoco interpreta la
causa: un portal puede caerse por presupuesto, por una migración o por decisión.
La caída es el hecho; el motivo es un juicio, y el registro no emite juicios.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import comun
import consulta
import geo

CDX = "http://web.archive.org/cdx/search/cdx"
NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# Mas de esto sin una captura viva ya no es «hace poco».
ANIOS_PARA_SOSPECHAR = 2


def _capturas(dominio: str) -> dict | None:
    """Le pregunta al archivo por todas las capturas de un dominio."""
    p = {
        "url": dominio, "output": "json", "limit": "600",
        "fl": "timestamp,statuscode", "collapse": "timestamp:6",
    }
    url = CDX + "?" + urllib.parse.urlencode(p)
    try:
        peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
        with urllib.request.urlopen(peticion, timeout=60) as respuesta:
            crudo = respuesta.read(2_000_000).decode("utf-8", "replace")
        filas = json.loads(crudo or "[]")
    except Exception:  # noqa: BLE001 — la falla del archivo se declara arriba
        return None
    filas = filas[1:] if filas and filas[0] and filas[0][0] == "timestamp" else filas
    if not filas:
        return {"capturas": 0, "primera": None, "ultima": None, "ultima_viva": None}
    anios = [f[0][:4] for f in filas if f and f[0]]
    vivas = [f[0][:4] for f in filas if len(f) > 1 and f[1] == "200"]
    return {
        "capturas": len(filas),
        "primera": min(anios) if anios else None,
        "ultima": max(anios) if anios else None,
        "ultima_viva": max(vivas) if vivas else None,
    }


def _respondeHoy(dominio: str) -> bool | None:
    """Una sola consulta, y se distingue «no respondió» de «respondió mal»."""
    for esquema in ("https://", "http://"):
        try:
            peticion = urllib.request.Request(
                esquema + dominio, headers={"User-Agent": NAVEGADOR}, method="GET")
            with urllib.request.urlopen(peticion, timeout=35) as respuesta:
                if respuesta.status < 400:
                    return True
        except urllib.error.HTTPError as error:
            # Un 403 o un 404 son RESPUESTA: el servidor esta vivo y contesta.
            if error.code < 500:
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def _mirar(par: tuple) -> tuple:
    iso, dominio = par
    return iso, dominio, _capturas(dominio), _respondeHoy(dominio)


PADRON = __import__("pathlib").Path(__file__).resolve().parent / "archivo.json"


def _delPadron() -> list:
    """Organismos oficiales de los Estados que NO tienen portal de datos.

    Sin esto el colector solo miraba los portales que funcionan —que es como
    conseguimos su dirección— y por eso no podía encontrar una sola retirada:
    estaba buscando donde por definición no la hay.
    """
    d = json.loads(PADRON.read_text(encoding="utf-8"))
    return [(o["iso"], o["dominio"], o.get("organismo", "")) for o in d["organismos"]]


def recolectar():
    dominios = consulta._dominiosProbados()
    # Primero el portal de datos, si lo hay; después los organismos del padrón.
    tareas, organismoDe = [], {}
    for iso, ds in dominios.items():
        if ds:
            tareas.append((iso, ds[0]))
            organismoDe[(iso, ds[0])] = "Portal de datos abiertos"
    for iso, dom, org in _delPadron():
        tareas.append((iso, dom))
        organismoDe[(iso, dom)] = org

    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        vistos = list(ejecutor.map(_mirar, tareas))

    porIso: dict[str, list] = {}
    for iso, dom, arch, vivo in vistos:
        porIso.setdefault(iso, []).append((dom, arch, vivo))

    registros, retirados, vivos, sinArchivo = [], [], 0, 0
    anioHoy = datetime.now(timezone.utc).year
    for pais in geo.padron():
        iso = pais["iso"]
        suyos = porIso.get(iso)
        if not suyos:
            registros.append({
                "iso": iso, "pais": pais["pais"], "bloque": pais["bloque"],
                "estado": "sin_dominio_probado", "sitios": [],
            })
            continue

        sitios = []
        for dominio, arch, respondeHoy in suyos:
            if arch is None:
                estado = "archivo_no_respondio"
                sinArchivo += 1
            elif respondeHoy:
                estado = "vivo"
                vivos += 1
            elif arch["ultima_viva"] and anioHoy - int(arch["ultima_viva"]) >= ANIOS_PARA_SOSPECHAR:
                estado = "retirado"
            elif arch["ultima_viva"]:
                estado = "no_responde_hoy"
            else:
                estado = "sin_rastro_vivo"

            sitios.append({
                "dominio": dominio,
                "organismo": organismoDe.get((iso, dominio), ""),
                "estado": estado,
                "responde_hoy": respondeHoy,
                "archivo": arch,
                "enlace_archivo": f"https://web.archive.org/web/*/{dominio}",
            })
            if estado == "retirado":
                retirados.append(
                    f"{pais['pais']} — {organismoDe.get((iso, dominio), dominio)} "
                    f"({dominio}, visto vivo por última vez en {arch['ultima_viva']})")

        # El estado del ESTADO es el peor de sus sitios: una retirada pesa más
        # que tres portales que andan.
        orden = ["retirado", "no_responde_hoy", "sin_rastro_vivo",
                 "archivo_no_respondio", "vivo"]
        peor = min((s["estado"] for s in sitios), key=lambda e: orden.index(e))
        registros.append({
            "iso": iso, "pais": pais["pais"], "bloque": pais["bloque"],
            "estado": peor, "sitios": sitios,
        })

    vacios = [
        "LA RETIRADA EXIGE LAS DOS MITADES Y NINGUNA ALCANZA SOLA. Que el archivo no "
        "tenga capturas recientes NO prueba que el sitio murio: prueba que el rastreador "
        "no paso. Y que el portal no nos responda hoy NO prueba que este caido: pudo "
        "rechazar nuestra consulta o estar caido un rato. Solo se afirma RETIRADO cuando "
        "el archivo lo vio vivo en el pasado Y hoy no responde, y aun asi se publican "
        "las dos fechas por separado para que cualquiera pueda rehacer la comprobacion.",
        "NO SE INTERPRETA LA CAUSA. Un portal puede caerse por presupuesto, por una "
        "migracion de sistema o por decision. La caida es el hecho; el motivo es un "
        "juicio, y este registro no emite juicios.",
        "LA RETIRADA ES DEL SITIO, NO DEL ESTADO. Un organismo puede haber mudado su "
        "publicacion a otra direccion que este colector no conoce. Por eso se nombra el "
        "organismo y el dominio, y no se dice que el Estado dejo de publicar.",
        "LA IDENTIFICACION DEL ORGANISMO ES DE LA OFICINA. La consulta prueba que el "
        "dominio existe y que el archivo tiene copias fechadas de el; NO prueba que sea "
        "el instituto que decimos. Va declarado como afirmacion nuestra, y se corrige en "
        "el padron si resultara equivocada.",
        f"ALCANZA A {len(tareas)} SITIOS OFICIALES EN "
        f"{len({t[0] for t in tareas})} ESTADOS, todos probados antes de entrar. Los demas "
        "quedan como SIN DOMINIO PROBADO, que no dice nada de ellos: dice que la Oficina "
        "todavia no verifico donde publican.",
        "LA COBERTURA DEL ARCHIVO ES DESPAREJA. Un portal muy visitado se captura seguido "
        "y uno del Caribe oriental puede tener pocas capturas en anios: comparar la "
        "CANTIDAD de capturas entre Estados no dice nada de ellos, dice cuanto los mira "
        "el rastreador.",
    ]

    calificacion = comun.calificar(
        fiabilidad="B",
        credibilidad=2,
        corroborado=True,
        nota=("Archivo publico de la web, consultado por su interfaz abierta. Fiabilidad "
              "B porque es un tercero que guarda copias, no el organismo que publica. "
              "Credibilidad 2 y corroborado porque cada afirmacion de retirada se apoya "
              "en DOS observaciones independientes: la copia fechada del archivo y una "
              "consulta propia al portal en el dia de la corrida."),
    )

    return comun.escribir(
        colector="archivo",
        capa="publico",
        fuente="Archivo público de la web — copias fechadas de los portales oficiales",
        url_fuente="https://web.archive.org/",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "sitios_mirados": len(tareas),
                "estados_mirados": len({t[0] for t in tareas}),
                "portales_vivos": vivos,
                "portales_retirados": len(retirados),
                "archivo_no_respondio": sinArchivo,
                "estados_del_padron": len(registros),
                "anios_para_sospechar": ANIOS_PARA_SOSPECHAR,
                "consultado": comun.ahora(),
            },
            "retirados": retirados,
        },
    )


if __name__ == "__main__":
    comun.correr("archivo", recolectar)
