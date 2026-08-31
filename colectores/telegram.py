"""Difusión en canales públicos de mensajería.

Qué se lee y con qué permiso
----------------------------
La **vista pública** que Telegram sirve en `t.me/s/<canal>`: una página web
abierta, sin cuenta, sin credencial y sin sortear ninguna protección. Es la
misma página que el servicio ofrece a cualquiera para previsualizar un canal
público. El dominio **no publica archivo de exclusión para programas
automáticos** —devuelve 404—, de modo que no hay instrucción que se esté
desatendiendo. No se lee ningún canal privado, ningún grupo y ningún mensaje
que exija iniciar sesión.

La regla que gobierna este colector
-----------------------------------
**Un canal de mensajería de un medio que ya está en el padrón de prensa NO es un
segundo origen: es el mismo medio por otra puerta.** Contarlo como corroboración
independiente inflaría artificialmente la verificación cruzada, que es lo único
que este registro tiene para separar un hecho de un rumor. Por eso este colector
**no alimenta la cobertura noticiosa**: publica su propio registro, y declara
explícitamente qué canales se superponen con el padrón de prensa.

Qué aporta que la prensa no aporta
----------------------------------
1. **Canales oficiales de gobierno**, que son fuente primaria y no intermediada.
2. **Organismos internacionales**, ídem.
3. **Medios de Estados de fuera de la región** —Rusia, Alemania, Francia— que
   cuentan América Latina a su público. Para una fundación que estudia
   resiliencia informativa, **quién narra la región desde afuera es materia de
   estudio en sí misma**, y por eso cada canal declara a quién responde.

Identidad: por qué se verifica y cómo
-------------------------------------
**Un nombre de usuario que coincide con el de un medio no prueba nada**: en
Telegram los nombres se compran, se venden y se transfieren. Durante la prueba
del 31 de agosto de 2026, el canal `@blu_radio` —que por su nombre parecería la
emisora colombiana— resultó ser otro canal, sin relación con ella. Un canal entra
al padrón solo si **enlaza a su propio dominio institucional** o **lleva el sello
de verificado de la plataforma**. De 43 candidatos probados, entraron 20.
"""

from __future__ import annotations

import html as entidades
import json
import re
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import comun
import geo

PADRON = Path(__file__).resolve().parent / "telegram.json"
PADRON_GENTILICIOS = Path(__file__).resolve().parent / "gentilicios.json"
PADRON_MEDIOS = Path(__file__).resolve().parent / "medios.json"
HORAS = 48
TOPE_PALABRAS = 30
MINIMO_CANALES = 2      # un concepto debe salir de dos canales distintos
NAVEGADOR = comun.AGENTE

VACIAS = {
    "para", "como", "pero", "porque", "cuando", "donde", "sobre", "entre", "desde",
    "hasta", "tambien", "todos", "todas", "este", "esta", "estos", "estas", "esto",
    "otro", "otra", "mismo", "hacer", "tiene", "tienen", "puede", "pueden", "sera",
    "the", "and", "for", "with", "that", "this", "from", "have", "will", "they",
    "mais", "pelo", "pela", "isso", "esse", "essa", "muito", "ainda", "apos",
    "seus", "suas", "nao", "por", "dos", "das", "com", "uma", "foi", "sao",
    # Restos del marcado y del propio servicio.
    "html", "quot", "nbsp", "amp", "https", "http", "www", "telegram", "canal",
    "leer", "leia", "read", "mais", "more", "link", "aqui", "video", "foto",
    "noticias", "noticia", "news",
}


def _sin_marcas(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def _texto_plano(marcado: str) -> str:
    """Texto legible de un mensaje.

    Un enlace se descarta SOLO si lo que muestra es una dirección web. Varios
    canales —Metrópoles, CNN Brasil— publican el titular **dentro** del enlace:
    borrar el enlace entero, como corresponde en otras plataformas, borraba el
    mensaje completo y el canal aparecía mudo teniendo veinte publicaciones.

    Se limpia dos veces porque parte del marcado viaja escapado dentro del propio
    mensaje: al traducir las entidades reaparecen etiquetas cuando la limpieza ya
    pasó.
    """
    def _enlace(m):
        dentro = re.sub(r"<[^>]+>", "", m.group(1) or "")
        dentro = entidades.unescape(dentro).strip()
        # Si el enlace muestra una dirección, no aporta texto: se va.
        if not dentro or re.fullmatch(r"(https?://)?[\w.\-]+\.[a-z]{2,}(/\S*)?", dentro, re.I):
            return " "
        return " " + dentro + " "

    texto = marcado or ""
    for _ in range(2):
        texto = re.sub(r"<a\b[^>]*>(.*?)</a>", _enlace, texto, flags=re.S | re.I)
        texto = re.sub(r"<br\s*/?>", " ", texto, flags=re.I)
        texto = re.sub(r"<[^>]+>", " ", texto)
        texto = entidades.unescape(texto)
    texto = re.sub(r"https?://\S+|www\.\S+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _palabras(texto: str) -> list:
    limpio = re.sub(r"[#@]\s*\w+", " ", texto)
    limpio = re.sub(r"\S*\.(com|net|org|ly|co|io|gl|me|br|ar|mx|cu|ec|cr|do|hn)\b\S*",
                    " ", limpio, flags=re.I)
    return re.findall(r"[a-z0-9]{4,}", _sin_marcas(limpio).lower())


def _traer(canal: dict) -> tuple:
    """Lee la vista pública de un canal. Devuelve (canal, mensajes, falla)."""
    url = f"https://t.me/s/{canal['canal']}"
    try:
        peticion = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR})
        with urllib.request.urlopen(peticion, timeout=45) as respuesta:
            pagina = respuesta.read(1_200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return canal, [], f"HTTP {error.code}"
    except Exception as error:  # noqa: BLE001 — la falla se declara, no se oculta
        return canal, [], type(error).__name__

    # Cada mensaje viene en su propio bloque. El corte se hace por el COMIENZO de
    # cada bloque y no por sus cierres: los mensajes con imagen anidan un nivel
    # mas, de modo que contar etiquetas de cierre corta el bloque antes del texto
    # y el canal aparece vacio teniendo mensajes. Le paso a Metropoles, que
    # publicaba ese mismo dia y figuraba en cero.
    bloques = re.split(r'(?=<div class="tgme_widget_message_wrap)', pagina)
    mensajes = []
    for bloque in bloques:
        cuerpo = re.search(
            r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', bloque, re.S)
        if not cuerpo:
            continue
        texto = _texto_plano(cuerpo.group(1))
        if len(texto) < 20:
            continue
        fecha = re.search(r'<time[^>]+datetime="([^"]+)"', bloque)
        enlace = re.search(r'href="(https://t\.me/[^"/]+/\d+)"', bloque)
        vistas = re.search(r'class="tgme_widget_message_views">([^<]+)<', bloque)
        momento = None
        if fecha:
            try:
                momento = datetime.fromisoformat(fecha.group(1).replace("Z", "+00:00"))
            except ValueError:
                momento = None
        mensajes.append({
            "texto": texto,
            "momento": momento,
            "publicado": momento.isoformat() if momento else None,
            "enlace": enlace.group(1) if enlace else url,
            "vistas": vistas.group(1).strip() if vistas else None,
        })
    mensajes.sort(key=lambda m: m["publicado"] or "")
    return canal, mensajes, None


def _paises(texto: str, mapa: dict) -> list:
    plano = " " + " ".join(_palabras(texto)) + " "
    return sorted({iso for iso, formas in mapa.items()
                   if any(f" {f} " in plano for f in formas)})


def recolectar():
    padron = json.loads(PADRON.read_text(encoding="utf-8"))["canales"]
    gentilicios = json.loads(PADRON_GENTILICIOS.read_text(encoding="utf-8"))["paises"]
    gentilicios = {iso: [" ".join(_palabras(f)) for f in formas]
                   for iso, formas in gentilicios.items()}
    medios = json.loads(PADRON_MEDIOS.read_text(encoding="utf-8"))["medios"]
    dominios_prensa = {m["dominio"].lower() for m in medios}

    lugares = geo.padron()
    nombres = {p["iso"]: p["pais"] for p in lugares}
    bloques = {p["iso"]: p["bloque"] for p in lugares}

    with ThreadPoolExecutor(max_workers=6) as ejecutor:
        crudo = list(ejecutor.map(_traer, padron))

    caidos = [f"{c['nombre']} (@{c['canal']}): {f}" for c, _, f in crudo if f]
    corte = datetime.now(timezone.utc) - timedelta(hours=HORAS)

    registros, todos = [], []
    for canal, mensajes, falla in crudo:
        if falla:
            continue
        ultimo = next((m["publicado"] for m in reversed(mensajes) if m["publicado"]), None)
        recientes = [m for m in mensajes
                     if m["momento"] is None or m["momento"] >= corte]
        for m in recientes:
            m.pop("momento", None)
            m["canal"] = canal["canal"]
            m["_isos"] = _paises(m["texto"], gentilicios)
        todos.extend(recientes)
        menciones = Counter(i for m in recientes for i in m["_isos"])
        registros.append({
            "canal": canal["canal"],
            "nombre": canal["nombre"],
            "pais": canal["pais"],
            "idioma": canal["idioma"],
            "tipo": canal["tipo"],
            "responde_a": canal.get("responde_a", ""),
            "identidad": canal["identidad"],
            "tambien_en_prensa": canal.get("dominio", "").lower() in dominios_prensa,
            "mensajes": len(recientes),
            "mensajes_visibles": len(mensajes),
            "ultimo_mensaje": ultimo,
            "estados_mencionados": [
                {"iso": i, "pais": nombres.get(i, i), "menciones": n}
                for i, n in menciones.most_common()],
            "ultimos": [{k: m[k] for k in ("texto", "publicado", "enlace", "vistas")}
                        for m in recientes[:4]],
        })

    # --- Atención por Estado y nube de conceptos, por ámbito ---
    def nube(msgs):
        cont, canales_de = Counter(), {}
        for m in msgs:
            for palabra in set(_palabras(m["texto"])):
                if palabra in VACIAS or palabra.isdigit():
                    continue
                cont[palabra] += 1
                canales_de.setdefault(palabra, set()).add(m["canal"])
        return [{"palabra": t, "mensajes": n, "canales": len(canales_de[t])}
                for t, n in cont.most_common(TOPE_PALABRAS * 5)
                if n >= 2 and len(canales_de[t]) >= MINIMO_CANALES][:TOPE_PALABRAS]

    por_iso, por_bloque = {}, {}
    for m in todos:
        for iso in m["_isos"]:
            por_iso.setdefault(iso, []).append(m)
            if iso in bloques:
                por_bloque.setdefault(bloques[iso], []).append(m)

    estados = [{
        "iso": iso, "pais": nombres.get(iso, iso), "bloque": bloques.get(iso, "—"),
        "mensajes": len(msgs),
        "canales_distintos": len({m["canal"] for m in msgs}),
        "palabras": nube(msgs),
    } for iso, msgs in sorted(por_iso.items(), key=lambda x: -len(x[1]))]

    superpuestos = [r["nombre"] for r in registros if r["tambien_en_prensa"]]
    # Un canal institucional abandonado es un hallazgo, no una falla: dice que ese
    # emisor dejo de usar la via. Se declara con la fecha de su ultimo mensaje.
    hoy = datetime.now(timezone.utc)
    dormidos = sorted(
        ((r["nombre"], r["ultimo_mensaje"][:10]) for r in registros
         if r["ultimo_mensaje"]
         and (hoy - datetime.fromisoformat(r["ultimo_mensaje"])).days > 90),
        key=lambda x: x[1])
    sin_mencion = sorted(p["pais"] for p in lugares if p["iso"] not in por_iso)

    vacios = [
        "ESTE REGISTRO NO CORROBORA NADA DE LA COBERTURA NOTICIOSA, Y NO SE MEZCLA "
        "CON ELLA. Un canal de mensajeria de un medio que ya esta en el padron de "
        "prensa es EL MISMO MEDIO POR OTRA PUERTA, no un segundo origen. Contarlo "
        "como corroboracion independiente inflaria la verificacion cruzada, que es lo "
        "unico que separa un hecho de un rumor. Canales que se superponen con el "
        "padron de prensa: " + (", ".join(superpuestos) if superpuestos else "ninguno") + ".",
        "Solo se lee la VISTA PUBLICA que el propio servicio ofrece sin cuenta. No se "
        "lee ningun canal privado, ningun grupo, ninguna conversacion y ningun mensaje "
        "que exija iniciar sesion. No se sortea proteccion alguna.",
        "UN NOMBRE DE USUARIO NO PRUEBA IDENTIDAD: en esta plataforma los nombres se "
        "compran, se venden y se transfieren. Durante la prueba, el canal «@blu_radio» "
        "—que por su nombre pareceria la emisora colombiana— resulto ser otro canal sin "
        "relacion con ella. Solo entran canales que enlazan a su propio dominio "
        "institucional o llevan el sello de verificado de la plataforma. De 43 "
        "candidatos probados entraron 20.",
        "Canales del padron SIN PUBLICAR HACE MAS DE NOVENTA DIAS, con la fecha de su "
        "ultimo mensaje: "
        + ("; ".join(f"{n} ({f})" for n, f in dormidos) if dormidos else "ninguno")
        + ". No es una falla de lectura: el canal responde y su contenido esta a la "
          "vista. Es que ese emisor dejo de usar esta via, y conviene saberlo antes de "
          "buscar ahi lo que ya no se publica.",
        "El padron cubre 8 jurisdicciones de las 33 del registro. La mayoria de los "
        "Estados de la region no tiene medios ni organismos con canal publico "
        "verificable en esta plataforma. NO es que no se hable de ellos: es que no hay "
        "canal propio que leer.",
        "Los medios de Estados de fuera de la region —Rusia, Alemania, Francia— entran "
        "a proposito y con su atribucion declarada: quien narra America Latina desde "
        "afuera es materia de estudio, no ruido. Su presencia en este registro NO "
        "implica que la Fundacion avale lo que publican.",
        f"Sin una sola mencion en la ventana de {HORAS} h: "
        + (", ".join(sin_mencion) if sin_mencion else "ninguno")
        + ". Ausencia de mencion no es ausencia de hechos.",
        "El recuento de vistas lo publica la propia plataforma y NO es verificable de "
        "forma independiente. Se transcribe tal como viene, sin tratarlo como medida.",
    ]
    if caidos:
        vacios.append("Canales que no respondieron: " + "; ".join(caidos))

    calificacion = comun.calificar(
        fiabilidad="F",
        credibilidad=4,
        corroborado=False,
        nota=("Difusion declarada por el propio emisor en su canal. Se registra QUE "
              "se publico y CON QUE palabras, que se observa directamente; no que lo "
              "publicado sea cierto. La identidad del canal esta verificada; el "
              "contenido no."),
    )

    return comun.escribir(
        colector="telegram",
        capa="publico",
        fuente="Canales publicos de Telegram, vista sin cuenta",
        url_fuente="colectores/telegram.json",
        calificacion=calificacion,
        registros=registros,
        vacios=vacios,
        extra={
            "resumen": {
                "canales_del_padron": len(padron),
                "canales_que_respondieron": len(padron) - len(caidos),
                "mensajes_en_ventana": len(todos),
                "estados_mencionados": len(estados),
                "estados_del_padron": len(lugares),
                "jurisdicciones_con_canal": len({c["pais"] for c in padron}),
                "canales_superpuestos_con_prensa": len(superpuestos),
                "ventana_horas": HORAS,
            },
            "estados": estados,
            "nube_conceptos": {
                "region": nube(todos),
                "bloques": {b: nube(l) for b, l in sorted(por_bloque.items())},
                "mensajes_region": len(todos),
                "mensajes_por_bloque": {b: len(l) for b, l in sorted(por_bloque.items())},
            },
            "metodo": (
                "Se lee la vista publica de cada canal y se toman los mensajes de la "
                "ventana vigente. La atribucion por Estado usa el diccionario de "
                "gentilicios del registro. Un concepto figura en la nube solo si "
                "aparece en dos mensajes de DOS CANALES distintos: lo que dice un solo "
                "canal es su linea editorial, no circulacion."
            ),
        },
    )


if __name__ == "__main__":
    comun.correr("telegram", recolectar)
