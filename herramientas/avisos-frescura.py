# -*- coding: utf-8 -*-
"""El aviso: pone el termómetro de frescura y la cola de propuestas donde una
persona las vea, sin que nadie tenga que abrir dos archivos JSON para saberlo.

POR QUÉ VIVE ACÁ Y NO EN LA RECOLECCIÓN
-----------------------------------------
`frescura.py` y `propuestas-frescura.py` ya imprimen su resumen en su propio
paso de `recolectar.yml`, pero ese registro se pierde entre ochenta pasos de
log. Este script corre en el Vigía —que ya se revisa cada hora y es «contents:
read», solo lectura— y deja el mismo resumen en el Resumen de la corrida de
GitHub (`$GITHUB_STEP_SUMMARY`), que es lo primero que se ve al abrir la
pestaña de Actions.

QUÉ NO HACE
------------
No falla nunca por sí mismo: la frescura y las propuestas son información, no
una falla del robot. Si `frescura.json` o `propuestas-frescura.json` todavía
no existen (por ejemplo, la primera vez que se hace un `checkout` sin haber
corrido nunca la recolección completa), lo dice y sigue.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
PUBLICO = RAIZ / "datos" / "publico"


def _cargar(nombre: str):
    ruta = PUBLICO / nombre
    if not ruta.exists():
        return None, f"no existe todavía {ruta.relative_to(RAIZ)}"
    try:
        return json.loads(ruta.read_text(encoding="utf-8")), None
    except Exception as e:  # noqa: BLE001
        return None, f"{ruta.name} no se pudo leer: {type(e).__name__}"


def armar() -> str:
    f, f_err = _cargar("frescura.json")
    p, p_err = _cargar("propuestas-frescura.json")
    renglones = ["## Termómetro de frescura de SIWA", ""]

    if f:
        r = f["resumen"]
        renglones += [
            f"**{r['indicadores_medidos']} indicadores** · mediana **{r['mediana_antiguedad_anios']} años** · "
            f"{r['al_dia_1_anio_o_menos']} al día · {r['tibio_2_a_3_anios']} tibios · "
            f"**{r['atrasado_4_anios_o_mas']} atrasados** ({f['corrida'][:16].replace('T', ' ')} UTC)",
            "",
            "Los 5 más atrasados:",
            "",
        ]
        for x in f["ranking_mas_atrasados"][:5]:
            renglones.append(f"- **{x['antiguedad_anios']} años** · {x['rotulo']} (`{x['clave']}`) · "
                             f"hasta {x['anio_mas_reciente']} · {x['fuente']}")
        renglones.append("")
    else:
        renglones += [f"_Sin termómetro esta vez: {f_err}._", ""]

    if p:
        r = p["resumen"]
        renglones += [
            "### Propuestas pendientes (ninguna se aplicó sola)",
            "",
            f"{r.get('clasificados', 0)} indicadores clasificados · "
            f"**{r.get('promover_hermana_fresca', 0)}** con hermana fresca en SIWA · "
            f"**{r.get('re_pull_misma_fuente', 0)}** re-pull de la misma fuente · "
            f"{r.get('rezago_de_fuente_ya_investigado', 0)} con rezago ya investigado · "
            f"**{r.get('derivar_a_buscador_externo', 0)}** a la cola del buscador externo.",
            "",
        ]
        destacadas = [x for x in p["propuestas"] if x["camino"] in
                      ("promover_hermana_fresca", "re_pull_misma_fuente")][:5]
        if destacadas:
            renglones.append("Para decidir primero:")
            renglones.append("")
            for x in destacadas:
                renglones.append(f"- **{x['camino']}** · {x['rotulo']} (`{x['clave']}`) — {x['motivo']}")
            renglones.append("")
    else:
        renglones += [f"_Sin propuestas esta vez: {p_err}._", ""]

    return "\n".join(renglones)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    texto = armar()
    print(texto)
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a", encoding="utf-8") as fh:
            fh.write(texto + "\n")
    # NUNCA falla: es información, no un control. Si algo de arriba lanzó una
    # excepción real, eso sí se ve como falla del paso — no hace falta forzarla.


if __name__ == "__main__":
    main()
