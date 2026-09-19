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

---

## 2026-09-19 — Perú y Paraguay · 20 propuestas (corridas 17, 18 y 19/9)

Revisadas una por una. El filtro decisivo, igual que con Panamá: si el tema ya lo
cubre una fuente comparable entre los 33 países, un dato nacional o administrativo
suelto no entra (rompe la comparabilidad o duplica la fuente canónica).

### DESCARTADAS por tema ya cubierto (17)

| País | Conjunto | Tema | Ya lo cubre |
|---|---|---|---|
| PER | Carnet de extranjería | migrantes | Banco Mundial (stock, SM.POP.TOTL) |
| PER | Solicitud de calidad migratoria (visas) | migrantes | Banco Mundial |
| PER | Prórroga de residencia | migrantes | Banco Mundial |
| PER | Consumo eléctrico clientes Electro Puno | uso_energia | Banco Mundial (+ es una sola distribuidora de una región) |
| PRY | Planilla de datos agropecuarios (MAG, 2022) | tierra_arable | Banco Mundial (+ dato de 2022) |
| PRY | Estadísticas Vitales 2024 (INE, PDF) | registro_nacimientos | ONU-ODS (+ PDF, no automatizable) |
| PRY | Pobreza monetaria 2025 (INE) | pobreza | CEPALSTAT / Banco Mundial |
| PRY | Desigualdad de ingresos 2022–2025 (INE, PDF) | gini | Banco Mundial (+ PDF) |
| PRY | Estructura sociodemográfica, Censo 2022 (PDF) | poblacion | Banco Mundial (+ PDF) |
| PER | Empleos declarados en las DJI (Contraloría) | corrupcion_politica | V-Dem vía Our World in Data |
| PER | DJI presentadas ante la Contraloría | corrupcion_politica | V-Dem vía OWID |
| PER | Familiares declarados en las DJI | corrupcion_politica | V-Dem vía OWID |
| PER | Intervenciones de Monitores Ciudadanos (2021) | corrupcion_politica | V-Dem vía OWID |
| PER | Plantaciones forestales por especie (SERFOR) | bosque | Banco Mundial (+ plantación ≠ cobertura de bosque) |
| PER | Videovigilancia, Municipalidad del Callao | victima_delito | CEPAL (+ es una sola ciudad) |
| PER | Feminicidios atendidos por los CEM (MIMP) | femicidios | CEPAL (que **ya toma** del MIMP peruano) |
| PER | Tentativas de feminicidio, CEM (MIMP) | femicidios | CEPAL |

Nota sobre las 4 de corrupción: además del tema ya cubierto, son *declaraciones
juradas presentadas* —un trámite de transparencia—, no una medida de corrupción.

### DESCARTADAS por tema sin fuente, pero el dato no encaja (2)

- **PER · Estrategia Rural frente a la violencia (MIMP)** — tema `situacion_seguridad`.
  Es la carga de casos de **un solo programa social**, serie de apenas dos tramos
  (2024 may-dic, 2025 ene-feb). No mide la situación de seguridad del país: mediría
  el trabajo de un programa. Error de categoría.
- **PRY · Principales resultados EPHC 1.er trim. 2026 (INE)** — tema
  `situacion_desarrollo`. Es un anexo de encuesta de hogares con muchos indicadores
  a la vez, de un solo país; no se puede mapear limpio a una celda de tema ni seguir
  como serie automatizable.

### EN ESPERA de decisión — NO incorporada (1)

- **PER · Registro Nacional de Infractores (SERFOR)** — tema `delitos_flora` (sin
  fuente actual). Tiene lo que haría falta: serie 2011–2026 y desagregación por
  departamento. **Pero cada fila es una persona o empresa sancionada, con nombre y
  número de documento**: es un padrón de datos personales, y SIWA publica indicadores
  agregados, no listas de personas. No se incorpora como está. *Se podría* construir
  una serie agregada (cantidad de sanciones por departamento y año, sin datos
  personales) para la capa subnacional de Perú, pero sería un tema nuevo y de un solo
  país: es una decisión de alcance, no una incorporación automática. Queda a criterio
  de la Dirección.

### Resultado

De 20 propuestas, **0 se incorporan como están**, 19 se descartan y 1 queda a
decisión. El buscador cumplió su papel —traer candidatas—; el filtro humano las
frena porque casi todas son archivos de un solo país que keyword-matchean temas que
SIWA ya cubre con fuentes regionales mejores. Todas figuran ya en `vistos.json`.
