# -*- coding: utf-8 -*-
"""EL VIGÍA DEL ROBOT — ¿sigue vivo? Dos preguntas que nadie estaba haciendo.

No confundir con el LATIDO (`.github/workflows/latido.yml`), que es otra cosa:
aquel empuja una señal de vida para que GitHub no apague el robot por
inactividad a los sesenta días. Este mira si el robot está corriendo HOY.

POR QUÉ EXISTE
---------------
El 11 de septiembre de 2026 el robot de recolección estuvo **una hora y cuarto
muerto sin que nadie se enterara**. La causa fue un identificador de paso
repetido: GitHub rechaza el archivo entero cuando eso pasa, y deja de correr.

Lo grave no fue el error —se arregla en un minuto— sino que **el silencio se
veía igual que el buen funcionamiento**. El sitio siguió en pie, porque los
datos ya publicados no se caen solos; simplemente dejó de actualizarse. Un
registro que dice ser de hoy y trae lo de ayer engaña sin mentir.

QUÉ PREGUNTA, Y POR QUÉ ESTAS DOS
-----------------------------------
1. **¿Hace cuánto que no llega un dato nuevo?** Se mira la fecha de obtención
   más reciente de todo el registro. Si pasó demasiado, el robot no está
   corriendo, y da igual por qué.
2. **¿Los archivos del robot son válidos para GitHub?** Se revisa lo que el
   lector de YAML no revisa: que ningún paso repita identificador, que todos
   tengan acción y que los avisos de falla apunten a pasos que existen. El YAML
   válido y el flujo válido no son lo mismo, y confundirlos fue justamente lo
   que costó la hora y cuarto.

DÓNDE VIVE, Y POR QUÉ NO EN EL ROBOT
--------------------------------------
**Corre en un flujo distinto del que vigila.** Un vigía que vive adentro de lo
que vigila se muere con ello, y no avisa nada: es el mismo error de diseño que
permitió que esto pasara.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
PUBLICO = RAIZ / "datos" / "publico"
FLUJOS = RAIZ / ".github" / "workflows"
SALIDA = PUBLICO / "estado" / "vigia_robot.json"

# Cuánto puede pasar sin un dato nuevo antes de que esto sea una falla. La
# recolección corre cada hora; tres horas dan margen para una caída pasajera de
# una fuente sin gritar por nada, y no tanto como para que una muerte pase
# inadvertida medio día.
HORAS = 3


def obtenido(d) -> datetime | None:
    t = ((d.get("procedencia") or {}).get("obtenido_en")
         or d.get("corrida") or d.get("consultado"))
    if not isinstance(t, str):
        return None
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        return None


def ultimo_dato() -> tuple:
    """La fecha de obtención más reciente de todo el registro.

    NO SE MIRA A SÍ MISMO, y la advertencia merece quedar escrita porque la
    primera versión de este archivo cometió justamente ese error: leyó su propia
    salida —que por definición se acaba de escribir—, la tomó como el dato más
    fresco del registro y declaró que el robot estaba vivo. Habría dicho lo
    mismo con el robot muerto hacía una semana.

    Tampoco se miran los archivos de `estado/`: los escribe la maquinaria de la
    casa, no las fuentes. Un vigía que se alimenta de sus propias señales no
    vigila nada.
    """
    reciente, quien = None, None
    for ruta in PUBLICO.glob("*.json"):
        if ruta.resolve() == SALIDA.resolve() or ruta.parent.name == "estado":
            continue
        try:
            d = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        t = obtenido(d)
        if t and (reciente is None or t > reciente):
            reciente, quien = t, ruta.name
    return reciente, quien


def revisar_flujos() -> list:
    """Lo que el lector de YAML no revisa y GitHub sí.

    Un archivo puede ser YAML perfecto y aun así ser rechazado entero. Acá se
    buscan las tres formas en que eso pasó o puede pasar.
    """
    try:
        import yaml
    except ImportError:
        return [{"que": "no se pudo revisar los flujos: falta el lector de YAML",
                 "quien": "pyyaml"}]
    fallas = []
    for ruta in sorted(FLUJOS.glob("*.yml")):
        texto = ruta.read_text(encoding="utf-8")
        try:
            y = yaml.safe_load(texto)
        except Exception as e:  # noqa: BLE001
            fallas.append({"que": "el archivo no es YAML válido", "quien": ruta.name,
                           "detalle": str(e)[:120]})
            continue
        todos_los_ids = []
        for nombre, trabajo in ((y or {}).get("jobs") or {}).items():
            pasos = (trabajo or {}).get("steps") or []
            ids = [p.get("id") for p in pasos if isinstance(p, dict) and p.get("id")]
            todos_los_ids += ids
            for k, n in collections.Counter(ids).items():
                if n > 1:
                    fallas.append({
                        "que": "identificador de paso repetido",
                        "quien": f"{ruta.name} · trabajo «{nombre}» · id «{k}»",
                        "porque": "GitHub exige que sean únicos y RECHAZA EL ARCHIVO "
                                  "ENTERO: el robot deja de correr y el silencio se ve "
                                  "igual que el buen funcionamiento"})
            for p in pasos:
                if isinstance(p, dict) and not any(c in p for c in ("run", "uses")):
                    fallas.append({"que": "paso sin acción", "quien":
                                   f"{ruta.name} · {p.get('name', 'sin nombre')}"})
        # Un aviso que nombra un paso inexistente nunca se va a disparar: es una
        # alarma desconectada, que es peor que no tenerla. Se compara contra los
        # identificadores de TODO el archivo y no contra los de cada trabajo:
        # un archivo con dos trabajos daría falsas alarmas de otro modo.
        for citado in set(re.findall(r"steps\.([A-Za-z0-9_\-]+)\.outcome", texto)):
            if citado not in todos_los_ids:
                fallas.append({
                    "que": "el aviso de falla apunta a un paso que no existe",
                    "quien": f"{ruta.name} · «{citado}»",
                    "porque": "esa alarma nunca se va a disparar"})
    return fallas


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ahora = datetime.now(timezone.utc)
    reciente, quien = ultimo_dato()
    fallas = revisar_flujos()

    horas = None
    if reciente is None:
        fallas.append({"que": "no se encontró una sola fecha de obtención",
                       "quien": "datos/publico/"})
    else:
        horas = round((ahora - reciente).total_seconds() / 3600, 1)
        if horas > HORAS:
            fallas.append({
                "que": "el robot no trae datos nuevos",
                "quien": f"el más reciente es {quien}, de hace {horas} horas",
                "porque": "la recolección corre cada hora; si pasaron más de "
                          f"{HORAS}, dejó de correr y hay que mirar por qué"})

    salida = {
        "que_es": "Vigía del robot. Pregunta dos cosas que nadie hacía: hace cuánto que no "
                  "llega un dato nuevo, y si los archivos del robot son válidos para "
                  "GitHub —que no es lo mismo que ser YAML válido—.",
        "corrida": ahora.isoformat(timespec="seconds"),
        "ultimo_dato": reciente.isoformat(timespec="seconds") if reciente else None,
        "de_quien": quien,
        "horas_sin_dato_nuevo": horas,
        "tope_de_horas": HORAS,
        "fallas": fallas,
        "veredicto": "el robot está vivo" if not fallas else f"{len(fallas)} problemas",
        "lo_que_no_dice": "Si los datos son buenos. Dice que llegan y que el robot puede "
                          "correr; la calidad la miden la auditoría y la regla de las dos "
                          "fuentes.",
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2),
                      encoding="utf-8", newline="")

    if horas is not None:
        print(f"[vigia] último dato hace {horas} h ({quien}) · {salida['veredicto']}")
    else:
        print(f"[vigia] {salida['veredicto']}")
    for f in fallas:
        print(f"  FALLA · {f['que']} · {f['quien']}")
    if fallas:
        sys.exit(1)


if __name__ == "__main__":
    main()
