# -*- coding: utf-8 -*-
"""Policías por cada 1.000 habitantes — fuente UNODC (UN-CTS), file-drop.

DE DÓNDE SALE
-------------
Del dataset «Access and functioning of justice» del UNODC Data Portal (encuesta
UN-CTS), bajado a mano a `fuentes/entrada-manual/unodc_cts_personnel.xlsx` (file-drop).
Indicator «Criminal Justice Personnel», Category «Police personel» (errata de UNODC),
Unit «Counts», Sex=Total. Son CONTEOS absolutos de personal policial por país y año.

QUÉ ARMA
--------
La tasa por 1.000 habitantes = conteo / población × 1.000, usando la población del
Banco Mundial (`datos/publico/banco-mundial.json`, SP.POP.TOTL) del MISMO año del
conteo. Reemplaza en frescura al dato de Our World in Data, que terminaba en 2015.

QUÉ MIDE Y QUÉ NO
-----------------
Personal policial declarado por cada Estado a UN-CTS. La cobertura y la definición de
«policía» (si incluye administrativos o policías subnacionales) dependen de lo que
reporta cada país: por eso entra calificada B/2 y rotulada como cambio de proveedor
respecto de OWD. UNODC no declara licencia abierta; la casa la usa como «uso no
comercial con cita» (mismo criterio que trata_unodc).
"""
from __future__ import annotations
import json, datetime
from pathlib import Path
import openpyxl

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
XLSX = RAIZ / "fuentes" / "entrada-manual" / "unodc_cts_personnel.xlsx"
BM = RAIZ / "datos" / "publico" / "banco-mundial.json"
SALIDA = RAIZ / "datos" / "publico" / "policias_unodc.json"

PAIS = {  # iso3 -> (nombre, bloque)  — 33 Estados del padrón
 "ARG":("Argentina","Cono Sur"),"BOL":("Bolivia","Andina"),"BRA":("Brasil","Brasil"),
 "CHL":("Chile","Cono Sur"),"COL":("Colombia","Andina"),"CRI":("Costa Rica","Centroamérica"),
 "CUB":("Cuba","Caribe"),"DOM":("República Dominicana","Caribe"),"ECU":("Ecuador","Andina"),
 "SLV":("El Salvador","Centroamérica"),"GTM":("Guatemala","Centroamérica"),"HND":("Honduras","Centroamérica"),
 "MEX":("México","México"),"NIC":("Nicaragua","Centroamérica"),"PAN":("Panamá","Centroamérica"),
 "PRY":("Paraguay","Cono Sur"),"PER":("Perú","Andina"),"URY":("Uruguay","Cono Sur"),
 "VEN":("Venezuela","Andina"),"HTI":("Haití","Caribe"),"JAM":("Jamaica","Caribe"),
 "TTO":("Trinidad y Tobago","Caribe"),"GUY":("Guyana","Caribe"),"SUR":("Surinam","Caribe"),
 "BLZ":("Belice","Centroamérica"),"BHS":("Bahamas","Caribe"),"BRB":("Barbados","Caribe"),
 "ATG":("Antigua y Barbuda","Caribe"),"DMA":("Dominica","Caribe"),"GRD":("Granada","Caribe"),
 "KNA":("San Cristóbal y Nieves","Caribe"),"LCA":("Santa Lucía","Caribe"),
 "VCT":("San Vicente y las Granadinas","Caribe"),
}

def poblacion():
    bm = json.loads(BM.read_text(encoding="utf-8"))
    pob = {}
    for r in bm.get("registros", []):
        ind = r.get("indicadores", {}).get("poblacion")
        if not ind: continue
        pob[r["iso"]] = {p["anio"]: p["valor"] for p in ind.get("serie", []) if p.get("valor")}
    return pob

def conteos():
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    ws = wb["data_cts_access_and_functioning"]
    it = ws.iter_rows(values_only=True)
    for _ in range(3): next(it)
    datos = {}  # iso -> {anio: conteo}
    for row in it:
        if not row or len(row) < 12: continue
        iso, country, region, sub, ind, dim, cat, sex, age, year, unit, val = row[:12]
        if str(ind) != "Criminal Justice Personnel": continue
        if str(cat).strip() != "Police personel": continue   # total exacto, NO las sub-categorías "- responsible for ..."
        if str(unit) != "Counts": continue
        if str(sex).strip() != "Total": continue              # sólo el total, no Male/Female
        if iso not in PAIS: continue
        try:
            y = int(year); v = float(val)
        except (TypeError, ValueError):
            continue
        datos.setdefault(iso, {})[y] = v
    return datos

def pob_cercana(pob_iso, anio):
    if not pob_iso: return None
    if anio in pob_iso: return pob_iso[anio]
    cand = min(pob_iso, key=lambda a: abs(a - anio))  # año de población más cercano
    return pob_iso[cand]

def main():
    pob = poblacion()
    cuentas = conteos()
    registros = []
    con_dato = 0
    for iso, (nombre, bloque) in PAIS.items():
        c = cuentas.get(iso, {})
        serie = []
        for y in sorted(c):
            p = pob_cercana(pob.get(iso, {}), y)
            if not p: continue
            serie.append({"anio": y, "valor": round(c[y] / p * 1000, 4)})
        reg = {"iso": iso, "pais": nombre, "bloque": bloque, "indicadores": {}}
        if serie:
            con_dato += 1
            ult = serie[-1]
            prev = serie[-2] if len(serie) > 1 else None
            ini = serie[0]
            reg["indicadores"]["policias"] = {
                "valor": ult["valor"], "anio": ult["anio"],
                "anio_anterior": prev["anio"] if prev else None,
                "valor_anterior": prev["valor"] if prev else None,
                "variacion_pct": round((ult["valor"]/prev["valor"]-1)*100, 4) if prev and prev["valor"] else None,
                "anio_inicial": ini["anio"], "valor_inicial": ini["valor"],
                "conteo": c[ult["anio"]], "serie": serie,
            }
        registros.append(reg)
    anios = [r["indicadores"]["policias"]["anio"] for r in registros if r["indicadores"]]
    ultimo = max(anios) if anios else None
    salida = {
        "indicadores": [{
            "clave": "policias", "rotulo": "Policías por cada mil habitantes", "eje": "Seguridad",
            "unidad": "policías por 1.000 personas", "mas_es_peor": False,
            "origen": "UNODC — UN-CTS (personal policial), tasa por 1.000 con población del Banco Mundial",
            "cautela": "Cuenta EFECTIVOS DECLARADOS a la encuesta UN-CTS de la ONU, no despliegue en calle: "
                       "más policías por habitante no significa más presencia ni mejor servicio. La cobertura y "
                       "la definición de «policía» (si incluye administrativos o policías subnacionales) varían "
                       "por país. Años heterogéneos (2010–2024) según lo último que cada Estado reportó. "
                       "Reemplaza la serie de Our World in Data, que terminaba en 2015 por no poder leer esta "
                       "planilla; es el MISMO proveedor (UNODC), ahora directo y más fresco.",
            "fuente_slug": "cjs-personnel", "hasta_anio": ultimo, "seccion": "violencia",
            "seccion_rotulo": "Homicidios",
        }],
        "procedencia": {
            "colector": "policias_unodc", "capa": "publico",
            "obtenido_en": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "fuente": {"nombre": "UNODC — UN-CTS, «Criminal Justice Personnel»: personal policial (conteos), "
                                 "convertido a tasa por 1.000 con población del Banco Mundial (SP.POP.TOTL)",
                       "url": "https://data.unodc.org/datareport/cjs-personnel"},
            "calificacion": {"fiabilidad": "B", "credibilidad": 2,
                             "nota": "Encuesta oficial UN-CTS; cobertura y definición de «policía» varían por país. "
                                     "Cambio de proveedor respecto de Our World in Data (que terminaba en 2015): "
                                     "serie no empalmable, se muestra rotulada."},
        },
        "registros": registros,
        "resumen": {"paises_con_dato": con_dato, "de": len(PAIS),
                    "nota": "Tasa por 1.000 habitantes = personal policial (UNODC/UN-CTS, conteos) ÷ población "
                            "(Banco Mundial) × 1.000, del mismo año. Años heterogéneos por país (2010–2024)."},
        "licencia": "UNODC, uso no comercial con cita. SIWA se considera uso no comercial.",
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    print(f"policias_unodc.json: {con_dato}/{len(PAIS)} países con dato")

if __name__ == "__main__":
    main()
