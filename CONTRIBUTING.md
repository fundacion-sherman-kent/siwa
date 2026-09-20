# Cómo contribuir a SIWA

Gracias por el interés. SIWA es el registro público de situación de América
Latina y el Caribe de la Fundación Sherman Kent. Este documento explica cómo
reportar problemas, proponer fuentes y contribuir código.

> **English summary.** SIWA is an open public-interest data platform for Latin
> America and the Caribbean. To contribute: open a GitHub issue for bugs or
> suggestions, propose new data sources with a link to the official open-data
> source, and send code changes as pull requests that keep collectors on the
> Python standard library and pass the checks in `.github/workflows/`. Tests live
> in `tests/` and run with `python -m unittest discover -s tests`.

## Reportar un problema o sugerir algo

Abrí un **issue** en GitHub:
<https://github.com/fundacion-sherman-kent/siwa/issues>

Para un error, contá qué esperabas, qué pasó, y —si podés— el país, la materia y
el enlace de la página donde se ve.

## Proponer una fuente de datos nueva

SIWA busca fuentes de forma permanente. Una propuesta útil incluye:

- el organismo oficial que la publica y el enlace directo al dato (CSV/JSON/API);
- el tema de SIWA al que corresponde y el período que cubre;
- por qué es comparable entre países (o si es de un solo país).

**La calificación y la incorporación son siempre juicio humano** (ver
`doctrina/` y el registro `propuestas/decisiones.md` en la rama
`propuestas-llama`). Una fuente no entra al registro sin estar probada.

## Contribuir código

- Los **colectores** usan solo la **biblioteca estándar de Python** (sin
  dependencias de terceros en tiempo de ejecución) y estadística clásica. No se
  usan modelos de lenguaje en la recolección.
- **No se simulan datos.** Si una fuente falla, el colector termina con error y
  conserva el último dato válido.
- **Los vacíos se declaran** y **cada dato lleva su fuente, fecha y
  calificación**.
- El sitio es **estático** (HTML/CSS/JS), adaptable a teléfono, tableta, monitor
  y papel.

### Tests

Los cambios que agregan funcionalidad deberían venir acompañados de tests. Los
tests viven en `tests/` y se corren, sin instalar nada, con:

```bash
python -m unittest discover -s tests
```

El flujo de calidad (`.github/workflows/calidad.yml`) corre estos tests y un
linter (`ruff`) en cada cambio.

## Conducta

Se espera trato respetuoso y de buena fe. El proyecto no acepta acoso ni
discriminación.
