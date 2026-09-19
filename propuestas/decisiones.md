# Registro de decisiones sobre propuestas de fuentes

El buscador (`buscador_llama.py`) **propone**; la incorporación y el descarte son
juicio humano. Este archivo deja la traza de qué se decidió y por qué. No lo lee
ningún robot: es memoria de la casa.

Formato: fecha de la decisión · país · conjunto · veredicto · motivo.

---

## 2026-09-19 — Panamá · ONPAR (Ministerio de Gobierno) · **DESCARTADAS (4)**

Propuestas en la corrida del 18/9, tema asignado por el clasificador
«migrantes / Población migrante que el país aloja».

| Conjunto | Veredicto |
|---|---|
| Solicitudes de carné de residencia temporal (ago 2026) | Descartada |
| Solicitudes de carné de residencia permanente (ago 2026) | Descartada |
| Solicitudes de permiso de trabajo definido (ago 2026) | Descartada |
| Solicitudes de pasaporte para estatus de refugiados (ago 2026) | Descartada |

**Motivo.** Se abrieron los archivos, no los títulos:

1. **El tema ya está cubierto, y mejor.** «Población migrante que el país aloja»
   lo alimenta el Banco Mundial (SM.POP.TOTL, *stock* de migrantes, comparable en
   los 33 países, serie anual). La recepción de refugiados en particular la cubre
   ACNUR (`desplazamiento.py`), que además advierte contra fundir fenómenos
   distintos bajo «migración».
2. **No es lo que mide el tema.** El tema es el *stock* de población migrante; esto
   es un *trámite mensual*: 40 solicitudes en el carné temporal, 3 en el pasaporte
   de refugiados (agosto 2026). Poner «solicitudes del mes» donde va «población que
   aloja» es un error de categoría.
3. **Rompe la comparabilidad regional**, que es el valor de SIWA: Panamá con un
   conteo suelto de un mes junto a 32 países con stock anual del Banco Mundial.
4. **No se puede automatizar.** El portal publica un archivo distinto por mes, con
   dirección nueva cada vez; el robot no puede seguir esa serie sin recableado
   humano mensual, contra el diseño de actualización continua.

Las cuatro ya figuran en `vistos.json`, de modo que el buscador no las volverá a
proponer.
