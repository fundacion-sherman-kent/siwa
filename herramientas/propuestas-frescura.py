# -*- coding: utf-8 -*-
"""El proponedor de frescura: clasifica cada indicador atrasado y PROPONE, no aplica.

POR QUÉ EXISTE
---------------
`frescura.py` dice QUÉ está viejo. Esta herramienta contesta la pregunta
siguiente —¿y ahora qué se hace con eso?— pero la contesta clasificando, nunca
resolviendo sola: la doctrina de la casa es «se automatiza el PROCESO, nunca el
JUICIO», y decidir qué dato mostrar es juicio. Que dos fuentes midan lo mismo y
cuál de las dos es más comparable con el resto del registro es una decisión que
toma una persona, con el mismo cuidado con que se decidió promover CEPAL sobre
la OMS en esperanza de vida.

CADA INDICADOR ATRASADO SE CLASIFICA EN UNO DE CUATRO CAMINOS, Y NINGUNO SE
APLICA SOLO
--------------------------------------------------------------------------
  (a) PROMOVER HERMANA FRESCA. Ya hay una segunda fuente EN SIWA, del mismo
      asunto (`segunda-fuente.ASUNTOS`), con año más nuevo. Se propone mostrar
      esa en vez de —o además de— la vieja. NO se aplica: la comparabilidad
      entre dos productores es juicio (por eso el registro sostiene además
      `retrocesos` en `segunda-fuente.py`). Antes de proponer, se pasa por
      tres filtros para no repetir el ruido que ya se midió (22/9/2026: 9
      propuestas, 0 accionables tras revisión humana):
        1. NO se propone si la candidata ya se exhibe ANTES que la clave vieja
           en el mismo `tarjetasBanco([...])` de `sitio/index.html` — la
           tarjeta ya está resuelta y proponerlo de nuevo es ruido.
        2. NO se propone si la candidata NO aparece en ningún `tarjetasBanco`
           de `sitio/index.html` — si se sacó de la vista es porque una
           persona ya decidió que no correspondía (p. ej. `gasto_militar`,
           retirado en la deduplicación de SIPRI), y este clasificador no
           puede saber por qué sin leer el sitio.
        3. NO se propone si el rótulo de la candidata no es, en su forma de
           comparación, EL MISMO que el de la vieja (ver `_misma_medida`):
           mismo asunto + misma unidad no alcanza — «confiar en el
           municipio» y «confiar en la policía» comparten asunto y unidad y
           no son la misma medida.
  (b) RE-PULL. El propio `reloj-actualidad.json` (si corrió en esta pasada) ya
      demostró EN VIVO que la fuente que SIWA ya usa tiene una edición más
      nueva —normalmente una de las tres ediciones anuales que no se
      reconsultan cada hora (BTI, USGS, CPI)—. Se propone actualizar la
      constante de edición en el colector.
  (c) REZAGO DE FUENTE, YA INVESTIGADO. `colectores/comun.SERIES_DETENIDAS`
      (confirmado contra la fuente) o `fuentes/fuentes-intentadas.json`
      (investigación de una fuente candidata) ya explican por qué no hay nada
      más nuevo que mostrar. Se informa el motivo — no es una tarea pendiente,
      es un vacío YA declarado.
  (d) SIN ARREGLO INTERNO. Nada de lo anterior aplica: no hay hermana fresca,
      el reloj no lo marcó y no hay investigación previa. Se deriva a la cola
      del buscador externo (`buscador_llama.py`) o a investigación manual —
      ESTO ES LO ÚNICO QUE ESTA HERRAMIENTA AGREGA A UNA COLA DE TRABAJO; no
      dispara ninguna búsqueda por sí misma.

LO QUE NO HACE
---------------
No escribe en ningún dato publicado, no crea colectores, no cambia ninguna
constante de edición y no le pide nada a ningún servicio de internet: todo lo
que usa ya está escrito en el repositorio.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
PUBLICO = RAIZ / "datos" / "publico"
FRESCURA = PUBLICO / "frescura.json"
RELOJ = PUBLICO / "reloj-actualidad.json"
MEMORIA = RAIZ / "fuentes" / "fuentes-intentadas.json"
SITIO = RAIZ / "sitio" / "index.html"
SALIDA = PUBLICO / "propuestas-frescura.json"

# Sólo se clasifican los que ya salieron de "al día" en el propio termómetro:
# los mismos dos cortes que usa `frescura.py`, para no duplicar el criterio.
DESDE_ANIOS = 2


def _cargar(ruta: Path, defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — sin el archivo, se degrada y se declara
        return defecto


def _modulo(ruta: Path, nombre: str):
    """Carga un .py del propio repositorio como módulo, con o sin guion en el
    nombre de archivo (mismo recurso que ya usa `tarjeta-compartir.py` con
    `geo.py`). Devuelve None si no se pudo — nunca tumba la corrida."""
    try:
        esp = importlib.util.spec_from_file_location(nombre, ruta)
        mod = importlib.util.module_from_spec(esp)
        esp.loader.exec_module(mod)
        return mod
    except Exception as e:  # noqa: BLE001
        print(f"  AVISO: no se pudo cargar {ruta.name}: {type(e).__name__} {e}", file=sys.stderr)
        return None


def _asuntos() -> dict:
    """{clave: asunto}, tomado de `segunda-fuente.ASUNTOS` — no se copia la
    lista acá: en un solo lugar no se desincroniza."""
    mod = _modulo(AQUI / "segunda-fuente.py", "segunda_fuente_mod")
    if not mod:
        return {}
    return {clave: asunto for asunto, claves in getattr(mod, "ASUNTOS", {}).items() for clave in claves}, \
        getattr(mod, "ASUNTOS", {})


def _series_detenidas() -> dict:
    """`colectores/comun.SERIES_DETENIDAS`, la memoria de rezagos YA
    confirmados contra la fuente (no supuestos)."""
    sys.path.insert(0, str(RAIZ / "colectores"))
    try:
        import comun
        return dict(getattr(comun, "SERIES_DETENIDAS", {}))
    except Exception as e:  # noqa: BLE001
        print(f"  AVISO: no se pudo leer comun.SERIES_DETENIDAS: {type(e).__name__} {e}", file=sys.stderr)
        return {}


_PARENTESIS = re.compile(r"\s*\([^)]*\)")


def _reloj_por_clave(reloj: dict) -> dict:
    """El reloj compara por texto libre («bti (6 indicadores)», «cuota_mineral_mundial,
    minerales_escala_mundial»), no por clave única: se parte por coma y se saca el
    paréntesis, y lo que no coincide con ninguna clave real de SIWA se descarta sin
    ruido — es un cruce best-effort, declarado como tal en los vacíos."""
    salida = {}
    for c in reloj.get("comprobaciones") or []:
        if c.get("estado") != "siwa_atrasado":
            continue
        for pedazo in str(c.get("clave", "")).split(","):
            clave = _PARENTESIS.sub("", pedazo).strip()
            if clave:
                salida[clave] = c
    return salida


# ── ORDEN DE EXHIBICIÓN (filtros 1 y 2) ─────────────────────────────────────
# `sitio/index.html` decide, tarjeta por tarjeta, con qué claves y en qué
# orden se llama a `tarjetasBanco([...], destino)` — esa función acepta tanto
# un arreglo como una clave suelta (`claves = [].concat(claves)` en el propio
# JS), así que las dos formas se leen igual acá.
_TARJETAS_BANCO = re.compile(r"tarjetasBanco\(\s*(\[[^\]]*\]|'[^']+'|\"[^\"]+\")\s*,")
_CLAVE_EN_LISTA = re.compile(r"['\"]([a-z_][a-z_0-9]*)['\"]")


def _orden_de_exhibicion(texto: str) -> list[list[str]]:
    """Una lista por cada llamado a `tarjetasBanco`, con las claves en el
    orden exacto en que se exhiben. Vacía si no se pudo leer o parsear."""
    llamados = []
    for m in _TARJETAS_BANCO.finditer(texto):
        claves = _CLAVE_EN_LISTA.findall(m.group(1))
        if claves:
            llamados.append(claves)
    return llamados


def _candidata_se_exhibe(llamados: list[list[str]], candidata: str) -> bool:
    """FILTRO 2 — si la candidata no aparece en ningún `tarjetasBanco`, se
    sacó a propósito (p. ej. `gasto_militar`, retirado el 21/9/2026 en la
    deduplicación de SIPRI): no se propone revivirla."""
    return any(candidata in claves for claves in llamados)


def _candidata_ya_exhibida_antes(llamados: list[list[str]], vieja: str, candidata: str) -> bool:
    """FILTRO 1 — si, en la MISMA tarjeta, la candidata fresca ya aparece
    ANTES que la clave vieja, la tarjeta ya está resuelta y proponer de nuevo
    es ruido (casos reales: `gasto_seguridad_cepal`, `desempleo_cepal`,
    `gini_cepal`, `esperanza_vida`)."""
    for claves in llamados:
        if vieja in claves and candidata in claves:
            if claves.index(candidata) < claves.index(vieja):
                return True
    return False


# ── MISMA MEDIDA, NO SÓLO MISMO ASUNTO + UNIDAD (filtro 3) ──────────────────
# La casa ya marca, en el propio rótulo que declaran los colectores, cuándo
# dos claves son la MISMA medida contada por dos productores: el sufijo
# «· segunda fuente» (`colectores/cepal.py`, `colectores/eia.py`,
# `colectores/owd.py`, `colectores/infraestructura.py`...) o, en CEPALSTAT,
# el nombre del productor entre paréntesis al final («... (CEPALSTAT)»).
# No es una tabla explícita de pares — no existe una en el repositorio, y
# armar una a mano se desincroniza igual que copiar `ASUNTOS` se
# desincronizaría — pero es la única declaración de la casa sobre qué rótulo
# es «el mismo dato, otra fuente», y separa bien los casos reales medidos el
# 22/9/2026 (ver vacío declarado más abajo).
_SEPARADOR_ROTULO = re.compile(r"[·—–]")
_PARENTESIS_FINAL = re.compile(r"\s*\([^)]*\)\s*$")


def _base_rotulo(rotulo: str) -> str:
    sin_fuente_entre_parentesis = _PARENTESIS_FINAL.sub("", rotulo or "")
    tramos = [t.strip() for t in _SEPARADOR_ROTULO.sub("|", sin_fuente_entre_parentesis).split("|") if t.strip()]
    if tramos and tramos[-1].lower() == "segunda fuente":
        tramos = tramos[:-1]
    return " ".join(tramos).strip().lower()


def _misma_medida(rotulo_vieja: str, rotulo_candidata: str) -> bool:
    base = _base_rotulo(rotulo_vieja)
    return bool(base) and base == _base_rotulo(rotulo_candidata)


def clasificar() -> dict:
    frescura = _cargar(FRESCURA, None)
    if frescura is None:
        # Sin `frescura.json` no hay nada que clasificar: se degrada con una
        # salida vacía y declarada, no con una excepción que tumbe el paso.
        return {
            "que_es": "Clasificador de indicadores atrasados de SIWA — no encontró "
                      "datos/publico/frescura.json en esta corrida.",
            "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "propuestas": [], "resumen": {"clasificados": 0},
            "vacios_declarados": ["Corrió sin `frescura.json`: ejecutar `frescura.py` antes."],
        }

    por_clave = {x["clave"]: x for x in frescura.get("indicadores", [])}
    clave_a_asunto, asuntos_completos = _asuntos()
    detenidas = _series_detenidas()
    memoria = _cargar(MEMORIA, {}).get("intentos", [])
    memoria_por_clave: dict[str, list] = {}
    for it in memoria:
        for clave in it.get("claves_relacionadas") or []:
            memoria_por_clave.setdefault(clave, []).append(it)

    reloj = _cargar(RELOJ, None)
    reloj_por_clave = _reloj_por_clave(reloj) if reloj else {}
    reloj_disponible = reloj is not None

    sitio_html = None
    try:
        sitio_html = SITIO.read_text(encoding="utf-8")
    except Exception as e:  # noqa: BLE001 — sin el sitio, el camino (a) se apaga entero
        print(f"  AVISO: no se pudo leer {SITIO.name}: {type(e).__name__} {e}", file=sys.stderr)
    llamados = _orden_de_exhibicion(sitio_html) if sitio_html is not None else []
    orden_disponible = bool(llamados)

    propuestas = []
    for clave, ind in por_clave.items():
        if ind["antiguedad_anios"] < DESDE_ANIOS:
            continue

        base = {"clave": clave, "rotulo": ind["rotulo"], "eje": ind["eje"],
                "fuente_actual": ind["fuente"], "anio_actual": ind["anio_mas_reciente"],
                "antiguedad_anios": ind["antiguedad_anios"],
                "aplicable_automaticamente": False}

        # (a) HERMANA FRESCA — dentro del mismo asunto de corroboración
        # (`segunda-fuente.ASUNTOS`) Y con la MISMA UNIDAD declarada. El asunto
        # solo no alcanza: agrupa por «qué corrobora qué» para la regla de las
        # dos fuentes, y junta cosas que NO son sustitutas —«fuerza militar»
        # mezcla personas, % de la fuerza laboral y valor SIPRI de armas—.
        # Exigir la misma unidad es lo que evita proponer, por ejemplo,
        # promover los efectivos militares (personas) con el valor de
        # importación de armas (SIPRI): dos magnitudes del mismo asunto que no
        # se pueden mostrar una en lugar de la otra. Entre las candidatas que
        # pasan asunto+unidad, sólo se propone la primera que además pasa los
        # tres filtros de exhibición y de misma medida (ver arriba); si
        # ninguna pasa, no se propone nada por esta vía y el indicador cae al
        # próximo camino aplicable.
        asunto = clave_a_asunto.get(clave)
        unidad = (ind.get("unidad") or "").strip().lower()
        hermanas = [h for h in (asuntos_completos.get(asunto, []) if asunto else [])
                    if h != clave and h in por_clave]
        mejores = sorted((h for h in hermanas if por_clave[h]["anio_mas_reciente"] > ind["anio_mas_reciente"]
                          and unidad and (por_clave[h].get("unidad") or "").strip().lower() == unidad),
                         key=lambda h: -por_clave[h]["anio_mas_reciente"])

        candidata_valida = None
        for h in mejores:
            candidata = por_clave[h]
            if orden_disponible:
                if not _candidata_se_exhibe(llamados, h):
                    continue  # FILTRO 2: se sacó del sitio a propósito
                if _candidata_ya_exhibida_antes(llamados, clave, h):
                    continue  # FILTRO 1: la tarjeta ya está resuelta
            if not _misma_medida(ind["rotulo"], candidata["rotulo"]):
                continue  # FILTRO 3: mismo asunto+unidad no es la misma medida
            candidata_valida = candidata
            break

        if candidata_valida:
            propuestas.append({**base, "camino": "promover_hermana_fresca",
                               "asunto": asunto,
                               "candidata": {"clave": candidata_valida["clave"], "rotulo": candidata_valida["rotulo"],
                                            "fuente": candidata_valida["fuente"],
                                            "anio": candidata_valida["anio_mas_reciente"]},
                               "motivo": f"«{asunto}» ya tiene, dentro de SIWA, «{candidata_valida['rotulo']}» "
                                         f"({candidata_valida['fuente']}) con dato de "
                                         f"{candidata_valida['anio_mas_reciente']}, más nuevo que "
                                         f"{ind['anio_mas_reciente']}, y todavía no está exhibida antes que la "
                                         "vieja en su tarjeta.",
                               "que_falta": "Una persona decide si son comparables (metodología, cobertura) "
                                            "antes de promoverla a vista principal — mismo criterio que la "
                                            "promoción de esperanza de vida (CEPAL sobre OMS)."})
            continue

        # (b) RE-PULL — el reloj, EN VIVO, ya encontró una edición más nueva de
        # la MISMA fuente que SIWA usa.
        r = reloj_por_clave.get(clave)
        if r:
            propuestas.append({**base, "camino": "re_pull_misma_fuente",
                               "anio_en_la_fuente": r.get("anio_fuente"),
                               "donde_se_comprobo": r.get("donde_se_comprobo"),
                               "comprobado_en": reloj.get("controlado", {}).get("utc"),
                               "motivo": f"El reloj de actualidad comprobó en vivo que {r.get('fuente')} ya "
                                         f"publica {r.get('anio_fuente')} y SIWA tiene {r.get('anio_siwa')}.",
                               "que_falta": "No se marca auto-aplicable: en este registro los colectores de "
                                            "API (Banco Mundial, OMS) ya piden la edición más reciente en "
                                            "cada corrida horaria, así que un atraso persistente es de "
                                            "investigar (filtro, ventana, código), no de republicar a ciegas. "
                                            "Las tres ediciones anuales (BTI, USGS, CPI) sí se resuelven "
                                            "actualizando a mano la constante de edición en el colector."})
            continue

        # (c) REZAGO YA INVESTIGADO — comun.SERIES_DETENIDAS o la memoria de
        # fuentes intentadas ya explican por qué no hay nada más nuevo.
        d = detenidas.get(clave)
        m = memoria_por_clave.get(clave)
        if d or m:
            propuestas.append({**base, "camino": "rezago_de_fuente_ya_investigado",
                               "serie_detenida": d,
                               "fuentes_intentadas": m,
                               "motivo": (f"Se consultó a la fuente el {d.get('consultado')} y su dato más "
                                          f"nuevo es {d.get('ultimo_en_la_fuente')}."
                                          if d else
                                          f"{len(m)} intento(s) ya registrados en fuentes-intentadas.json.")
                                         + (f" Reemplazo: {d.get('reemplazo')}." if d and d.get("reemplazo") else ""),
                               "que_falta": "Nada pendiente de esta herramienta: es un vacío ya declarado. "
                                            "Reabrir sólo si cambia la licencia o aparece una fuente nueva."})
            continue

        # (d) SIN ARREGLO INTERNO — a la cola del buscador externo.
        propuestas.append({**base, "camino": "derivar_a_buscador_externo",
                           "motivo": "No hay hermana fresca en SIWA, el reloj no lo marcó esta corrida (o no "
                                     "corrió) y no hay investigación previa registrada.",
                           "que_falta": "Candidata para que el buscador de fuentes (Llama) o una investigación "
                                        "manual busquen un reemplazo o una segunda fuente. No se dispara "
                                        "ninguna búsqueda automáticamente desde acá."})

    por_camino = {}
    for p in propuestas:
        por_camino.setdefault(p["camino"], []).append(p)
    propuestas.sort(key=lambda p: -p["antiguedad_anios"])

    salida = {
        "que_es": "Clasifica cada indicador atrasado de SIWA (frescura.json) en cuatro caminos posibles. "
                  "PROPONE: ninguna fila de este archivo se aplicó sola. Incorporar una fuente, promover una "
                  "sobre otra o tocar comparabilidad es juicio, y el juicio no se automatiza.",
        "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reloj_disponible_esta_corrida": reloj_disponible,
        "orden_de_exhibicion_disponible_esta_corrida": orden_disponible,
        "resumen": {
            "clasificados": len(propuestas),
            "promover_hermana_fresca": len(por_camino.get("promover_hermana_fresca", [])),
            "re_pull_misma_fuente": len(por_camino.get("re_pull_misma_fuente", [])),
            "rezago_de_fuente_ya_investigado": len(por_camino.get("rezago_de_fuente_ya_investigado", [])),
            "derivar_a_buscador_externo": len(por_camino.get("derivar_a_buscador_externo", [])),
        },
        "propuestas": propuestas,
        "vacios_declarados": [
            "El cruce contra `reloj-actualidad.json` es por texto (el reloj compara por rótulo libre, no por "
            "clave única) y sólo está disponible en la corrida diaria completa, no en las horarias.",
            "Ninguna fila lleva `aplicable_automaticamente: true`. Se evaluó la opción de marcar el re-pull "
            "de una misma API como automático y se descartó: en este registro esos colectores ya corren "
            "cada hora con el filtro de \"más reciente\", así que no hay una acción mecánica separada que "
            "aplicar sin investigar primero por qué no llegó sola.",
            "«derivar_a_buscador_externo» es sólo una cola: esta herramienta no ejecuta "
            "`colectores/buscador_llama.py` ni ninguna búsqueda por su cuenta.",
            "«promover_hermana_fresca» exige mismo asunto de `segunda-fuente.ASUNTOS`, misma unidad "
            "declarada, que la candidata ya se exhiba en algún `tarjetasBanco` de `sitio/index.html` sin "
            "estar ya antes que la vieja en esa misma tarjeta, y que el rótulo de las dos sea, en su forma "
            "de comparación, LA MISMA medida (filtro 3, ver `_misma_medida`). Este último filtro no lee una "
            "tabla explícita de pares «misma medida, dos productores»: no existe una en el repositorio. Se "
            "apoya en la convención de rótulo que ya usan los colectores («· segunda fuente» en "
            "`cepal.py`/`eia.py`/`owd.py`/`infraestructura.py`, o el productor entre paréntesis al final "
            "en CEPALSTAT) para reconocer cuándo dos claves son el mismo dato contado por dos fuentes. Es "
            "un indicio de texto, no un metadato limpio: separó bien los nueve casos medidos el 22/9/2026 "
            "(los cuatro reales — `gasto_seguridad_cepal`, `esperanza_vida`, `desempleo_cepal`, `gini_cepal` "
            "— quedaron fuera por el filtro 1, ya exhibidos; y descartó los cuatro falsos positivos de "
            "concepto — `confianza_municipio`→`confianza_policia`, `seguridad_barrio` y `victima_delito`→"
            "`temor_delito`, `recaudacion`→`industria` — porque sus rótulos no son el mismo texto base) pero "
            "puede, en el futuro, descartar por error un par real que la casa nombre sin esa convención. "
            "Sigue faltando una tabla explícita y mantenida (como `segunda-fuente.ASUNTOS`) de qué pares son "
            "literalmente la misma medida de dos productores distintos — hasta que exista, esta es una "
            "propuesta y una persona la confirma antes de promover, igual que antes.",
            "Los filtros 1 y 2 leen `sitio/index.html` con una expresión regular sobre el texto de las "
            "llamadas a `tarjetasBanco(...)`, no con un parser de HTML/JS: si esa función cambia de firma o "
            "de nombre, los dos filtros dejan de encontrar nada y se apagan solos (`orden_de_exhibicion_"
            "disponible_esta_corrida: false`), degradando SIN filtrar en vez de fallar en silencio con un "
            "resultado equivocado — declarado para que se note en la salida, no para que se ignore.",
        ],
    }
    return salida


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    salida = clasificar()
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8", newline="")
    r = salida["resumen"]
    print(f"[propuestas-frescura] {r.get('clasificados', 0)} indicadores clasificados · "
          f"{r.get('promover_hermana_fresca', 0)} con hermana fresca · "
          f"{r.get('re_pull_misma_fuente', 0)} re-pull · "
          f"{r.get('rezago_de_fuente_ya_investigado', 0)} rezago ya investigado · "
          f"{r.get('derivar_a_buscador_externo', 0)} a derivar")
    for p in salida["propuestas"][:10]:
        print(f"   {p['camino']:<28} · {p['rotulo']} ({p['clave']}) · {p['antiguedad_anios']} años")


if __name__ == "__main__":
    main()
