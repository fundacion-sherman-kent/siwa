# Entrada manual (file-drop)

Acá van los archivos que **se bajan a mano** de fuentes que no tienen API abierta o
que exigen descargar un archivo. El robot tiene un **lector por archivo**: procesa lo
que encuentre acá en cada corrida. **No borres los archivos**: si el archivo no está,
el lector se degrada y lo declara (no rompe el robot).

## Cómo dejar un archivo
Desde la web de GitHub: entrá a esta carpeta → botón **"Add file" → "Upload files"** →
arrastrá el archivo → **"Commit changes"**. Guía paso a paso en
`direccion/instructivos/file-drops-siwa.md`.

## Archivos esperados (nombre exacto que espera el lector)
| Archivo | Fuente | Flujo |
|---|---|---|
| `cites_trade_full.csv` | CITES Trade Database (descarga completa) | Especies |
| `unodc_glotip.xlsx` | UNODC — Global Report on Trafficking in Persons (dataset) | Trata |
| `gfi_iff.xlsx` | Global Financial Integrity — trade misinvoicing | Financiero |
| `undesa_migrant_stock.xlsx` | UN DESA — International Migrant Stock (origen×destino) | Migrantes (todos los países) — sólo si el robot no puede bajarlo solo |

El nombre importa: el lector busca ese archivo por su nombre. Si bajás una versión con
otro nombre, **renombralo** al de la tabla antes de subirlo.
