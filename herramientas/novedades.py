"""El canal de novedades: qué cambió, para quien quiera enterarse sin volver.

POR QUÉ ASÍ Y NO POR CORREO
---------------------------
Un aviso por correo exige una lista, un servicio que la envíe y alguien que la
administre. Este registro **no tiene presupuesto ni administra credenciales**, y
esa es justamente la propiedad que lo mantiene vivo sin que nadie lo cuide.

Un canal de novedades no necesita nada de eso: es un archivo estático que el
robot escribe con el resto, y cualquier lector de noticias lo sigue. Es además
como un periodista vigila fuentes de verdad.

QUÉ ANUNCIA
-----------
Las transiciones que la memoria observó: un portal que volvió, un conjunto que
desapareció del catálogo, un Estado que pasó a publicar. **No anuncia cifras
nuevas** —esas cambian todo el tiempo y no son noticia—: anuncia **cambios de
estado**, que es lo que un periodista puede ir a preguntar.

LO QUE CADA AVISO DECLARA, Y NO ES UN DETALLE
---------------------------------------------
Que la fecha es **cuándo la Oficina lo observó**, no cuándo ocurrió. Un canal de
novedades se lee rápido y se cita rápido; si esa distinción no viaja dentro de
cada aviso, se pierde en el primer reenvío.
"""

from __future__ import annotations

import html
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos" / "publico"
SALIDA = RAIZ / "novedades.xml"
# Un canal por Estado, ademas del general: quien cubre Paraguay no quiere
# sesenta avisos del Caribe oriental para encontrar los dos suyos.
POR_ESTADO = RAIZ / "novedades"
sys.path.insert(0, str(RAIZ / "colectores"))
import comun  # noqa: E402

BASE = comun.BASE

# Cuántos avisos lleva el canal. Más que esto no lo lee nadie y engorda el
# archivo; menos, y quien lo revisa una vez por semana se pierde cosas.
MAXIMO = 60


def esc(t) -> str:
    return html.escape(str(t if t is not None else ""), quote=False)


def sello(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()


# Cómo se anuncia cada transición. El verbo importa: «dejó de figurar» no es
# «cerró», y el registro no puede afirmar lo segundo.
COMO_SE_DICE = {
    ("archivo", "vivo"): "su sitio oficial volvió a responder",
    ("archivo", "retirado"): "su sitio oficial figura retirado",
    ("archivo", "no_responde_hoy"): "su sitio oficial no respondió",
    ("archivo", "sin_rastro_vivo"): "su sitio oficial no tiene rastro vivo en el archivo",
    ("reciente", "al_dia"): "volvió a publicar datos de criminalidad",
    ("reciente", "atrasado"): "no publica datos de criminalidad desde hace tiempo",
    ("reciente", "sin_conjunto"): "su conjunto de criminalidad dejó de figurar en el catálogo",
    ("reciente", "sin_portal"): "quedó sin portal de datos consultable",
    ("contratacion", "vigente"): "publica sus compras con la serie vigente",
    ("contratacion", "publica_pero_atrasado"): "publica sus compras, pero atrasadas",
    ("contratacion", "sin_publicador"): "quedó sin publicador de compras en formato comparable",
    ("opacidad", "publicado"): "pasó a publicar el consolidado de acceso a la información",
    ("opacidad", "parcial"): "publica de forma parcial el acceso a la información",
    ("opacidad", "sin_verificar"): "volvió a quedar sin verificar por la Oficina",
}


def _canal(titulo: str, descripcion: str, self_url: str, enlace: str, avisos: list) -> str:
    """El XML del canal. Es el mismo para el general y para los de cada Estado:
    lo unico que cambia es el rotulo y que avisos entran."""
    ahora = format_datetime(datetime.now(timezone.utc))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!--
  Canal de novedades de SIWA. Se GENERA con herramientas/novedades.py; no se
  escribe a mano. Anuncia CAMBIOS DE ESTADO observados por la Oficina, no cifras
  nuevas: una cifra cambia todo el tiempo y no es noticia; que un portal deje de
  responder, si.
-->
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{esc(titulo)}</title>
    <link>{enlace}</link>
    <atom:link href="{self_url}" rel="self" type="application/rss+xml"/>
    <description>{esc(descripcion)}</description>
    <language>es-AR</language>
    <lastBuildDate>{ahora}</lastBuildDate>
    <copyright>Acceso libre y gratuito. Citar como «SIWA, Fundación Sherman Kent».</copyright>
    <generator>SIWA · herramientas/novedades.py</generator>
{chr(10).join(avisos)}
  </channel>
</rss>
"""


def construir() -> int:
    ruta = DATOS / "memoria.json"
    if not ruta.exists():
        print("[novedades] todavía no hay memoria: no se escribe el canal", file=sys.stderr)
        return 0
    d = json.loads(ruta.read_text(encoding="utf-8"))
    nombres = d.get("estados", {})
    materias = d.get("materias", {})

    # Solo transiciones REALES. La primera vez que se ve a un Estado no es una
    # novedad: es que empezamos a mirarlo, y anunciarlo seria dar por noticia el
    # arranque del propio registro.
    todos_los_cambios = [c for c in d.get("registros", []) if not c.get("primera_vez")]
    todos_los_cambios = list(reversed(todos_los_cambios))
    # El canal GENERAL se corta en los mas recientes; cada canal por Estado se
    # arma despues de la memoria COMPLETA de ese Estado, con su propio tope. Un
    # Estado con tres cambios en dos anios los lleva a los tres, aunque el
    # general ya no los muestre. Repartir el recorte del general dejaba sin
    # archivo al Estado cuyo ultimo cambio quedaba en el aviso sesenta y uno.
    cambios = todos_los_cambios

    avisos = []
    for c in cambios:
        iso, materia = c["iso"], c["materia"]
        pais = nombres.get(iso, iso)
        rot = (materias.get(materia) or {}).get("rotulo", materia)
        sig = (materias.get(materia) or {}).get("significa") or {}
        frase = COMO_SE_DICE.get((materia, c["a"]))
        titulo = f"{pais}: {frase}" if frase else \
            f"{pais}: {rot} pasó a «{sig.get(c['a'], c['a'])}»"

        cuerpo = (
            f"<p><b>{esc(pais)}</b> · {esc(rot)}<br>"
            f"Antes: {esc(sig.get(c.get('de'), c.get('de') or 'sin observación previa'))}<br>"
            f"Ahora: {esc(sig.get(c['a'], c['a']))}</p>"
            f"<p><b>La fecha es cuándo la Oficina lo observó, no cuándo ocurrió.</b> "
            f"Observado el {esc(c['observado'])}. El cambio pudo producirse antes: "
            f"el registro declara lo que vio y el día que lo vio.</p>"
            f"<p>Este aviso no es una nota: es una observación de un registro público "
            f"y gratuito. Para citarlo: «SIWA, Fundación Sherman Kent».</p>"
        )

        enlace = f"{BASE}/sitio/pais/{sello(pais)}.html"
        try:
            fecha = datetime.fromisoformat(c["observado"]).replace(tzinfo=timezone.utc)
        except Exception:  # noqa: BLE001
            fecha = datetime.now(timezone.utc)

        avisos.append((iso,
            "    <item>\n"
            f"      <title>{esc(titulo)}</title>\n"
            f"      <link>{enlace}</link>\n"
            f"      <guid isPermaLink=\"false\">siwa-{materia}-{iso}-{c['observado']}-{sello(c['a'])}</guid>\n"
            f"      <pubDate>{format_datetime(fecha)}</pubDate>\n"
            f"      <category>{esc(rot)}</category>\n"
            f"      <description><![CDATA[{cuerpo}]]></description>\n"
            "    </item>"
        ))

    todos = [x for _, x in avisos][:MAXIMO]
    SALIDA.write_text(_canal(
        "SIWA — lo que cambió",
        "Cambios de estado observados en los 33 Estados de América Latina y el Caribe: "
        "portales que dejan de responder, conjuntos que desaparecen de un catálogo, Estados "
        "que pasan a publicar. Cada aviso declara que la fecha es la de la observación, no la "
        "del hecho. Registro público y gratuito de la Fundación Sherman Kent.",
        f"{BASE}/novedades.xml", f"{BASE}/sitio/index.html", todos), encoding="utf-8")

    # Un canal por Estado que TENGA algo que anunciar. Publicar uno vacio seria
    # una promesa que no se cumple: quien lo sigue espera avisos que no van a
    # llegar porque todavia no hay nada que contar.
    POR_ESTADO.mkdir(parents=True, exist_ok=True)
    porIso = {}
    for iso, x in avisos:
        porIso.setdefault(iso, []).append(x)
    for iso, suyos in porIso.items():
        suyos = suyos[:MAXIMO]
        pais = nombres.get(iso, iso)
        arch = f"{sello(pais)}.xml"
        (POR_ESTADO / arch).write_text(_canal(
            f"SIWA — lo que cambió en {pais}",
            f"Cambios de estado observados por la Oficina en {pais}: su portal oficial, su "
            f"catálogo de datos, sus compras públicas y su acceso a la información. Cada aviso "
            f"declara que la fecha es la de la observación, no la del hecho. Registro público y "
            f"gratuito de la Fundación Sherman Kent.",
            f"{BASE}/novedades/{arch}", f"{BASE}/sitio/pais/{sello(pais)}.html", suyos),
            encoding="utf-8")

    print(f"[novedades] canal general con {len(todos)} aviso"
          f"{'' if len(todos) == 1 else 's'} de cambio observado de {len(avisos)} · "
          f"{len(porIso)} canales por Estado")
    return len(avisos)


if __name__ == "__main__":
    construir()
