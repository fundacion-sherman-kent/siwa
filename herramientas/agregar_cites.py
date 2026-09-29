# -*- coding: utf-8 -*-
"""Agrega la descarga completa de CITES a los flujos que tocan ALC.

Lee los 59 CSV del zip en streaming, se queda con las filas donde el importador O el
exportador es uno de los 33 Estados, y suma por (exportador, importador, grupo, año):
cantidad de registros y cuántos son incautaciones (Source='I'). Escribe un CSV chico.
No carga todo en memoria: cuenta al vuelo.
"""
import zipfile, io, csv, sys, collections, time

ZIP = r"C:\Users\edgar\Downloads\cites_trade_full.zip"
SALIDA = r"C:\Users\edgar\AppData\Local\Temp\claude\C--Users-edgar-OneDrive-Documentos-ClaudeGral\2b0eb76c-8ec7-4359-95b4-da98ae031f65\scratchpad\siwa-repo\fuentes\entrada-manual\cites_alc.csv"

ALC = {"AR","BO","BR","CL","CO","CR","CU","DO","EC","SV","GT","HN","MX","NI","PA",
       "PY","PE","UY","VE","HT","JM","TT","GY","SR","BZ","BS","BB","AG","DM","GD",
       "KN","LC","VC"}

conteo = collections.defaultdict(lambda: [0, 0])  # clave -> [registros, incautaciones]
z = zipfile.ZipFile(ZIP)
csvs = sorted([n for n in z.namelist() if n.endswith(".csv")],
              key=lambda n: int(''.join(c for c in n if c.isdigit()) or 0))
t0 = time.time(); leidas = 0; guardadas = 0
for i, name in enumerate(csvs, 1):
    with z.open(name) as f:
        r = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        for row in r:
            leidas += 1
            imp, exp = row.get("Importer", ""), row.get("Exporter", "")
            if imp not in ALC and exp not in ALC:
                continue
            grupo = "fauna" if (row.get("Class") or "").strip() else "flora"
            anio = (row.get("Year") or "").strip()
            src = (row.get("Source") or "").strip()
            clave = (exp, imp, grupo, anio)
            c = conteo[clave]
            c[0] += 1
            if src == "I":
                c[1] += 1
            guardadas += 1
    print(f"[{i}/{len(csvs)}] {name} · leidas {leidas:,} · pares ALC {guardadas:,} · "
          f"claves {len(conteo):,} · {time.time()-t0:.0f}s", flush=True)

with open(SALIDA, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["exportador", "importador", "grupo", "anio", "registros", "incautaciones"])
    for (exp, imp, grupo, anio), (n, inc) in sorted(conteo.items()):
        w.writerow([exp, imp, grupo, anio, n, inc])
print(f"LISTO. {len(conteo):,} claves. Leidas {leidas:,} filas totales, "
      f"{guardadas:,} tocan ALC. Salida: {SALIDA} · {time.time()-t0:.0f}s", flush=True)
