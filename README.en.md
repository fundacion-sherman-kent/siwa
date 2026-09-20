# SIWA (English)

**A situation register for Latin America and the Caribbean.**
Fundación Sherman Kent · Office for Intelligence Generation.

*(This is an English overview. The full documentation is in Spanish in
[`README.md`](README.md).)*

Public data for the 33 states of the region, collected automatically and
qualified with intelligence tradecraft: every figure carries its **source**, its
**reference date**, its **reliability rating** and its **corroboration status**.
Topics are organised along four axes — **security, defence, governance and
development**.

## Goal

**To be the first data-consultation platform for Latin America and the
Caribbean** — not the largest, but the one people turn to when they need to know
how the region is doing and where a figure comes from.

## What it is, and what it isn't

This register **does not issue judgements**. It publishes qualified facts.
Analysis — with confidence and probability — is published separately and signed.

## Rules the code enforces

1. **No simulated data.** If a source fails, the collector stops with an error,
   keeps the previous value, and records the failure in `datos/publico/estado/`.
2. **Corroboration is not self-declared.** No figure can reach the highest
   credibility without two independent sources.
3. **Gaps are declared.** Every file lists what its source does not cover.
4. **No language models in collection.** Only the Python standard library and
   classical statistics.
5. **Everything is public.** There is no reserved layer and no login: the state,
   the historical series, the spreadsheet export and the downloadable report are
   open to anyone, without registration.

## Data and licensing

- **Data** (`datos/publico/`): **Creative Commons Attribution 4.0 (CC BY 4.0)** —
  see [`LICENSE-DATOS.md`](LICENSE-DATOS.md).
- **Code** (collectors, site, tools): **MIT** — see [`LICENSE`](LICENSE).
- Base data belongs to the cited producers and keeps its own source terms,
  declared per datum in the `restriccion_de_uso` field.
- How to cite: “SIWA — Fundación Sherman Kent”, linking to
  <https://siwa.fundacionkent.org>.

The data catalogue, with each dataset's source, rating and date, is at
<https://siwa.fundacionkent.org/datos/>.

## How it runs

Every hour, unattended, via GitHub Actions. Also by hand from the repository's
**Actions** tab. On a machine with Python 3.12, with nothing installed:

```bash
python colectores/focos.py
```

## Contributing, security and tests

- Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security policy: [`SECURITY.md`](SECURITY.md)
- Tests live in `tests/` and run with `python -m unittest discover -s tests`.
