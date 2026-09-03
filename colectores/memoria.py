"""La memoria del registro: qué cambió, cuándo, y desde cuándo está así.

POR QUÉ EXISTE
--------------
SIWA mide el presente muy bien y **se olvida**. Cada hora el robot sobrescribe.
Las recolecciones quedan en el historial del repositorio, pero como serie son
ilegibles: para saber desde cuándo el instituto de estadística de Venezuela no
responde habría que abrir ciento cuarenta versiones a mano.

Y eso importa por una razón concreta: **la cifra de homicidios de la UNODC va a
seguir existiendo dentro de cinco años; que el sitio de un organismo se apagó en
2024 existe solamente porque alguien lo miró.** Nuestras observaciones son las
únicas del registro que nadie más está guardando.

QUÉ GUARDA, Y POR QUÉ ASÍ
-------------------------
**No guarda fotos diarias: guarda CAMBIOS.** Una foto por día de 33 Estados por
cuatro materias crecería sin freno y repetiría lo mismo miles de veces. Un
registro de transiciones —«Venezuela pasó de vivo a retirado el 2 de septiembre»—
es diminuto, es permanente, y contesta exactamente la pregunta que se le hace:
**desde cuándo**.

Lo único que sí se guarda día a día es el tamaño del registro —fuentes,
indicadores, vacíos—, que son cuatro números y sirven para ver si la casa crece.

LO QUE LA FECHA SIGNIFICA, Y LO QUE NO
--------------------------------------
La fecha es **cuándo la Oficina lo observó**, no cuándo ocurrió. Un portal pudo
caerse el martes y ser visto el jueves. Se declara así en cada línea, porque
confundir las dos fechas convertiría una bitácora de observación en una crónica
de hechos, que es algo que este registro no puede sostener.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import comun

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos" / "publico"
# EL ALMACEN NO ES EL PRODUCTO, y confundirlos costo una corrida: `comun.escribir`
# publica en `datos/publico/memoria.json`, de modo que si la bitacora viviera ahi
# el propio colector se pisaria la memoria en cada vuelta. La bitacora vive
# aparte y completa; lo publicado es una vista de ella.
ARCHIVO = RAIZ / "datos" / "bitacora.json"

# Qué se vigila. Cada materia declara de qué archivo sale, qué campo es «el
# estado» de un Estado, y cómo se lee en castellano.
VIGILADAS = {
    "opacidad": {
        "archivo": "opacidad.json", "campo": "estado",
        "rotulo": "Acceso a la información",
        "significa": {
            "publicado": "publica el consolidado",
            "parcial": "publica de forma parcial",
            "sin_verificar": "sin verificar por la Oficina",
        },
    },
    "archivo": {
        "archivo": "archivo.json", "campo": "estado",
        "rotulo": "Sitio oficial",
        "significa": {
            "vivo": "responde", "retirado": "retirado",
            "no_responde_hoy": "no responde hoy",
            "sin_rastro_vivo": "sin rastro vivo en el archivo",
            "archivo_no_respondio": "el archivo no respondió",
            "sin_dominio_probado": "sin sitio verificado",
        },
    },
    "contratacion": {
        "archivo": "contratacion.json", "campo": "estado",
        "rotulo": "Publicación de compras",
        "significa": {
            "vigente": "publica y su serie está vigente",
            "publica_pero_atrasado": "publica, pero atrasado",
            "sin_publicador": "sin publicador en formato comparable",
        },
    },
    "reciente": {
        "archivo": "reciente_oficial.json", "campo": "estado",
        "rotulo": "Publicación propia de criminalidad",
        "significa": {
            "al_dia": "publicó hace poco", "atrasado": "sin novedad reciente",
            "sin_conjunto": "sin conjunto de criminalidad",
            "sin_portal": "sin portal consultable",
        },
    },
}


def _leer(nombre: str) -> dict | None:
    ruta = DATOS / nombre
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — un archivo ilegible no debe borrar la memoria
        return None


def _observacionDeHoy() -> dict:
    """Lo que el registro ve AHORA, por materia y por Estado."""
    visto = {}
    for materia, cfg in VIGILADAS.items():
        d = _leer(cfg["archivo"])
        if not d:
            continue
        visto[materia] = {
            r["iso"]: r.get(cfg["campo"])
            for r in d.get("registros", []) if r.get("iso") and r.get(cfg["campo"])
        }
    return visto


def _tamanioDelRegistro() -> dict:
    """Cuatro números que dicen si la casa crece."""
    indicadores = vacios = fuentes = 0
    for ruta in sorted(DATOS.glob("*.json")):
        if ruta.name == "memoria.json":
            continue
        d = _leer(ruta.name)
        if not d:
            continue
        fuentes += 1
        indicadores += len(d.get("indicadores") or [])
        vacios += len((d.get("procedencia") or {}).get("vacios_declarados") or [])
    return {"fuentes": fuentes, "indicadores": indicadores, "vacios": vacios}


def _cargar() -> dict:
    if ARCHIVO.exists():
        try:
            return json.loads(ARCHIVO.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"cambios": [], "tamanio": []}


def _rotularEstados(previo: dict) -> dict:
    """El nombre de cada Estado, para no repetirlo en cada transición."""
    nombres = dict(previo.get("estados") or {})
    for cfg in VIGILADAS.values():
        d = _leer(cfg["archivo"])
        for r in (d or {}).get("registros", []):
            if r.get("iso") and r.get("pais"):
                nombres[r["iso"]] = r["pais"]
    return nombres


def _anotar(memoria: dict, visto: dict, fecha: str) -> int:
    """Compara lo visto con el último valor conocido y anota SOLO lo que cambió."""
    ultimo = {}
    for c in memoria["cambios"]:
        ultimo[(c["materia"], c["iso"])] = c["a"]

    nuevos = 0
    for materia in sorted(visto):
        for iso in sorted(visto[materia]):
            valor = visto[materia][iso]
            anterior = ultimo.get((materia, iso))
            if anterior == valor:
                continue
            memoria["cambios"].append({
                "materia": materia, "iso": iso,
                "de": anterior, "a": valor,
                "observado": fecha,
                "primera_vez": anterior is None,
            })
            nuevos += 1
    return nuevos


def _desde(memoria: dict) -> dict:
    """Desde cuándo cada Estado está como está. Es lo que el sitio muestra."""
    hoy = datetime.now(timezone.utc).date()
    salida: dict = {}
    for c in memoria["cambios"]:
        salida.setdefault(c["materia"], {})[c["iso"]] = c
    for materia, porIso in salida.items():
        for iso, c in porIso.items():
            try:
                d = (hoy - datetime.fromisoformat(c["observado"]).date()).days
            except Exception:  # noqa: BLE001
                d = None
            porIso[iso] = {
                "valor": c["a"],
                "significa": VIGILADAS[materia]["significa"].get(c["a"], c["a"]),
                "desde": c["observado"],
                "dias": d,
                # Si es la primera vez que se lo ve, NO se sabe desde cuándo está
                # así: se sabe desde cuándo lo miramos. No es lo mismo y se dice.
                "solo_desde_que_miramos": c["primera_vez"],
                "venia_de": c["de"],
            }
    return salida


def reconstruir() -> int:
    """Siembra la memoria con lo que ya está guardado en el historial.

    Se corre UNA VEZ. Camina los commits de cada archivo vigilado, de más viejo a
    más nuevo, y anota las transiciones que encuentra. El historial es corto
    —varios de estos colectores nacieron hace días— así que rinde poco: el valor
    de la memoria es hacia adelante, no hacia atrás.
    """
    memoria = _cargar()
    sembrados = 0
    for materia, cfg in VIGILADAS.items():
        ruta = f"datos/publico/{cfg['archivo']}"
        try:
            crudo = subprocess.run(
                ["git", "log", "--reverse", "--format=%H %ad", "--date=short", "--", ruta],
                cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", timeout=120)
        except Exception as error:  # noqa: BLE001
            print(f"[memoria] no se pudo leer el historial de {ruta}: {error}", file=sys.stderr)
            continue
        for linea in (crudo.stdout or "").splitlines():
            partes = linea.split()
            if len(partes) < 2:
                continue
            commit, fecha = partes[0], partes[1]
            try:
                contenido = subprocess.run(
                    ["git", "show", f"{commit}:{ruta}"], cwd=RAIZ,
                    capture_output=True, text=True, encoding="utf-8", timeout=60)
                d = json.loads(contenido.stdout)
            except Exception:  # noqa: BLE001 — una versión ilegible se saltea
                continue
            visto = {materia: {
                r["iso"]: r.get(cfg["campo"])
                for r in d.get("registros", []) if r.get("iso") and r.get(cfg["campo"])
            }}
            sembrados += _anotar(memoria, visto, fecha)

    memoria["cambios"].sort(key=lambda c: (c["observado"], c["materia"], c["iso"]))
    ARCHIVO.write_text(json.dumps(memoria, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    print(f"[memoria] reconstrucción: {sembrados} transiciones sembradas del historial")
    return sembrados


def recolectar():
    memoria = _cargar()
    hoy = datetime.now(timezone.utc).date().isoformat()

    nuevos = _anotar(memoria, _observacionDeHoy(), hoy)

    # El tamaño va una vez por día: es una foto chica y sirve como serie.
    tam = _tamanioDelRegistro()
    memoria["tamanio"] = [t for t in memoria.get("tamanio", []) if t.get("fecha") != hoy]
    memoria["tamanio"].append({"fecha": hoy, **tam})
    memoria["tamanio"].sort(key=lambda t: t["fecha"])

    memoria["estados"] = _rotularEstados(memoria)
    memoria["cambios"].sort(key=lambda c: (c["observado"], c["materia"], c["iso"]))

    ARCHIVO.write_text(json.dumps(memoria, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")

    desde = _desde(memoria)
    primeraFecha = memoria["cambios"][0]["observado"] if memoria["cambios"] else hoy

    vacios = [
        "LA FECHA ES CUANDO LA OFICINA LO OBSERVO, NO CUANDO OCURRIO. Un portal pudo "
        "caerse el martes y ser visto el jueves. Confundir las dos fechas convertiria "
        "una bitacora de observacion en una cronica de hechos, y este registro no puede "
        "sostener lo segundo.",
        "LA PRIMERA VEZ QUE SE VE UN ESTADO NO DICE DESDE CUANDO ESTA ASI: dice desde "
        "cuando lo miramos. Esas lineas van marcadas y NO deben leerse como antiguedad "
        "del hecho.",
        f"LA MEMORIA EMPIEZA EL {primeraFecha} y no antes. Lo anterior a esa fecha no se "
        "perdio: nunca se guardo, porque el registro sobrescribia cada hora. Se "
        "reconstruyo lo que el historial del repositorio permitia, que es poco: varios "
        "de los colectores vigilados nacieron hace dias.",
        "SE GUARDAN CAMBIOS, NO FOTOS. Si un Estado no figura con transicion es porque "
        "no cambio desde que se lo mira, no porque no se lo haya mirado.",
        "ESTO NO MIDE AL ESTADO: MIDE LO QUE LA OFICINA PUDO VER DEL ESTADO. Una "
        "transicion a «no responde» puede ser del portal, de la red o de nuestra propia "
        "consulta, y por eso la retirada exige ademas la prueba del archivo publico.",
    ]

    calificacion = comun.calificar(
        fiabilidad="A",
        credibilidad=2,
        corroborado=False,
        nota=("Observacion propia de la Oficina, registrada por su propio robot con fecha "
              "y conservada en un repositorio publico que no admite reescritura hacia "
              "atras. Fiabilidad A porque el productor del dato es quien lo publica. "
              "Credibilidad 2 porque se verifico QUE SE OBSERVO ESO ESE DIA, no que el "
              "hecho haya ocurrido ese dia."),
    )

    total = len(memoria["cambios"])
    return comun.escribir(
        colector="memoria",
        capa="publico",
        fuente="Fundación Sherman Kent — bitácora de observación de SIWA",
        url_fuente="https://fundacion-sherman-kent.github.io/siwa/sitio/index.html#memoria",
        calificacion=calificacion,
        registros=memoria["cambios"][-400:],
        vacios=vacios,
        extra={
            "desde": desde,
            "estados": memoria["estados"],
            "tamanio": memoria["tamanio"],
            "materias": {k: {"rotulo": v["rotulo"], "significa": v["significa"]}
                         for k, v in VIGILADAS.items()},
            "resumen": {
                "transiciones_guardadas": total,
                "transiciones_nuevas_hoy": nuevos,
                "memoria_empieza": primeraFecha,
                "dias_de_memoria": (datetime.now(timezone.utc).date()
                                    - datetime.fromisoformat(primeraFecha).date()).days,
                "consultado": comun.ahora(),
            },
        },
    )


if __name__ == "__main__":
    if "--reconstruir" in sys.argv:
        reconstruir()
    comun.correr("memoria", recolectar)
