"""Funciones compartidas por los colectores del SIWA.

Sin dependencias externas: solo biblioteca estándar de Python.

Reglas de la casa que este módulo hace cumplir por código
(`doctrina/siwa.md`):

- Si una fuente falla, el colector termina con error, deja intacto el dato
  anterior y registra la falla en `datos/publico/estado/`. Nunca escribe un
  valor de ejemplo (§8.1).
- Ningún dato puede calificar credibilidad `1` sin corroboración por dos
  orígenes independientes (§3). El intento levanta excepción.
- Todo archivo sale con fuente, dirección de la fuente, momento de obtención y
  vacíos declarados (§1).
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
AGENTE = "SIWA/0.1 (Fundacion Sherman Kent; +https://fundacionkent.org)"
ESPERA = 30

FIABILIDAD = ("A", "B", "C", "D", "E", "F")

# La atribucion viaja DENTRO de cada archivo, no solo en la pantalla. Quien se
# lleve el dato crudo se lleva tambien de quien es el trabajo: es la unica forma
# de que el credito sobreviva a una descarga.
ATRIBUCION = {
    "obra": "SIWA — Reporte de situación de América Latina y el Caribe",
    "autor": "Fundación Sherman Kent — Oficina de Generación de Inteligencia",
    "sitio": "https://fundacion-sherman-kent.github.io/siwa/sitio/index.html",
    "uso": ("Acceso libre y gratuito. Se permite reproducir, redistribuir y "
            "derivar esta información CITANDO LA FUENTE de este modo: «SIWA, "
            "Fundación Sherman Kent». La recolección, la calificación de fuentes "
            "y la declaración de vacíos son trabajo de la Fundación; los datos "
            "de base pertenecen a los productores citados en cada indicador."),
    "no_implica": ("La cita no implica aval de la Fundación sobre el uso que se "
                   "haga de estos datos, ni sobre las conclusiones ajenas."),
}


def ahora() -> str:
    """Momento actual en ISO 8601, UTC, sin fracciones de segundo."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def pedir(url: str) -> dict:
    """Trae un JSON. Levanta excepción ante cualquier respuesta que no sea 200."""
    peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(peticion, timeout=ESPERA) as respuesta:
        if respuesta.status != 200:
            raise RuntimeError(f"HTTP {respuesta.status} al pedir {url}")
        return json.loads(respuesta.read().decode("utf-8"))


def calificar(fiabilidad: str, credibilidad: int, corroborado: bool, nota: str) -> dict:
    """Arma la calificación de Almirantazgo y verifica los techos del §3."""
    if fiabilidad not in FIABILIDAD:
        raise ValueError(f"Fiabilidad fuera de escala: {fiabilidad}")
    if credibilidad not in range(1, 7):
        raise ValueError(f"Credibilidad fuera de escala: {credibilidad}")
    if credibilidad == 1 and not corroborado:
        raise ValueError(
            "Credibilidad 1 exige corroboración por dos orígenes independientes "
            "(doctrina/fuentes.md §2 ter). El colector intentó asignarla sin ella."
        )
    return {
        "fiabilidad": fiabilidad,
        "credibilidad": credibilidad,
        "corroborado": corroborado,
        "nota": nota,
    }


def escribir(
    colector: str,
    capa: str,
    fuente: str,
    url_fuente: str,
    calificacion: dict,
    registros: list,
    vacios: list | None = None,
    extra: dict | None = None,
) -> Path:
    """Escribe el archivo de datos con su bloque de procedencia.

    `extra` permite sumar bloques propios de un colector —por ejemplo una muestra
    acotada para el mapa— sin alterar la estructura común.
    """
    destino = DATOS / capa / f"{colector}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)

    contenido = {
        "procedencia": {
            "colector": colector,
            "capa": capa,
            "obtenido_en": ahora(),
            "fuente": {"nombre": fuente, "url": url_fuente},
            "calificacion": calificacion,
            "vacios_declarados": vacios or [],
            "cantidad": len(registros),
            "atribucion": ATRIBUCION,
        },
        "registros": registros,
    }
    if extra:
        contenido.update(extra)

    # allow_nan=False es deliberado: NaN e Infinity NO son JSON valido y el
    # navegador rechaza el archivo entero, no solo el valor. Si un colector
    # produce uno, la corrida falla aca y se ve, en lugar de escribir un
    # archivo que nadie puede leer.
    try:
        texto = json.dumps(contenido, ensure_ascii=False, indent=2, allow_nan=False)
    except ValueError as error:
        raise ValueError(
            f"El colector «{colector}» produjo un valor no representable en JSON "
            f"(NaN o infinito): {error}. Un dato ausente se omite, no se escribe."
        ) from error

    destino.write_text(texto + "\n", encoding="utf-8")
    return destino


def escribir_estado(colector: str, estado: str, mensaje: str) -> None:
    """Deja constancia de cómo terminó la corrida, para mostrarla en el sitio."""
    destino = DATOS / "publico" / "estado" / f"{colector}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(
            {"colector": colector, "estado": estado, "mensaje": mensaje, "momento": ahora()},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def correr(colector: str, tarea) -> None:
    """Ejecuta un colector, registra el resultado y propaga la falla al sistema."""
    try:
        destino = tarea()
    except Exception as error:  # noqa: BLE001 — cualquier falla se declara igual
        escribir_estado(colector, "error", f"{type(error).__name__}: {error}")
        print(f"[{colector}] FALLA: {error}", file=sys.stderr)
        print(f"[{colector}] no se escribió ningún dato. El anterior queda intacto.", file=sys.stderr)
        sys.exit(1)
    escribir_estado(colector, "correcto", "Recolección completa.")
    print(f"[{colector}] escrito: {destino.relative_to(RAIZ)}")
