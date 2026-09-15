# -*- coding: utf-8 -*-
"""Reloj de actualidad: ¿SIWA tiene el último dato que publica cada fuente?

POR QUÉ EXISTE
--------------
Dos analistas señalaron que SIWA mostraba homicidios de 2023 cuando Argentina ya
publicaba 2025 (15/9/2026). Un colector puede andar sin fallas y aun así quedarse
atrás: porque la fuente sacó una edición nueva con otra dirección, o porque la
fuente misma está atrasada y hay otra más nueva. Nada de eso se ve en rojo.

Este control compara, fuente por fuente y país por país, el período más nuevo que
tiene SIWA con el período más nuevo que la fuente publica HOY, y dice cuál de las
tres cosas pasa:

  · AL DÍA — SIWA tiene lo último que publica la fuente.
  · SIWA ATRASADO — la fuente tiene algo más nuevo y el colector no lo tomó.
    Se corrige en el colector.
  · FUENTE SIN NOVEDAD — la fuente no tiene nada más nuevo. Si hay otra fuente
    más fresca, se anota aparte en «fuentes más nuevas fuera de SIWA».

EL RELOJ
--------
Antes de medir nada se comprueba la hora: se lee la hora que informan varios
servidores públicos (encabezado `Date` de HTTP) y se la compara con la del
equipo. Si la diferencia pasa de dos minutos, el control lo dice. Todas las
fechas del resultado van en hora UTC y en hora de Buenos Aires.

LO QUE NO HACE
--------------
No cambia ningún dato de SIWA ni publica nada: escribe su resultado en el
archivo que se le indique.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "colectores"))
import comun  # noqa: E402
import geo  # noqa: E402

DATOS = RAIZ / "datos" / "publico"
BUENOS_AIRES = timezone(timedelta(hours=-3))
NAVEGADOR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
RELOJES = ["https://api.worldbank.org", "https://ghoapi.azureedge.net", "https://www.google.com",
           "https://github.com", "https://www.cloudflare.com"]
TOLERANCIA_RELOJ = 120  # segundos


def pedir(url: str, metodo: str = "GET", agente: str = NAVEGADOR, tope: int | None = None):
    for intento in range(3):
        try:
            p = urllib.request.Request(url, headers={"User-Agent": agente}, method=metodo)
            with urllib.request.urlopen(p, timeout=60) as r:
                cuerpo = b"" if metodo == "HEAD" else (r.read(tope) if tope else r.read())
                return r.status, dict(r.headers), cuerpo
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404, 410):
                return e.code, dict(e.headers or {}), b""
        except Exception:  # noqa: BLE001
            pass
        time.sleep(3 * (intento + 1))
    return None, {}, b""


def ahora_txt(momento: datetime) -> dict:
    return {"utc": momento.astimezone(timezone.utc).isoformat(timespec="seconds"),
            "buenos_aires": momento.astimezone(BUENOS_AIRES).strftime("%d/%m/%Y %H:%M:%S")}


# ── EL RELOJ ────────────────────────────────────────────────────────────────
def reloj() -> dict:
    lecturas = []
    for url in RELOJES:
        antes = datetime.now(timezone.utc)
        estado, cab, _ = pedir(url, "HEAD")
        despues = datetime.now(timezone.utc)
        fecha = cab.get("Date") or cab.get("date")
        if not fecha:
            continue
        servidor = parsedate_to_datetime(fecha)
        local = antes + (despues - antes) / 2
        lecturas.append({"servidor": url, "desfase_segundos": round((local - servidor).total_seconds(), 1)})
    if not lecturas:
        return {"estado": "sin_referencia", "lecturas": []}
    desfases = sorted(x["desfase_segundos"] for x in lecturas)
    mediana = desfases[len(desfases) // 2]
    return {"estado": "sincronizado" if abs(mediana) <= TOLERANCIA_RELOJ else "desfasado",
            "desfase_mediano_segundos": mediana, "tolerancia_segundos": TOLERANCIA_RELOJ,
            "lecturas": lecturas}


# ── LO QUE TIENE SIWA ────────────────────────────────────────────────────────
def siwa(archivo: str) -> dict:
    """{clave: {iso: año}} del archivo publicado."""
    ruta = DATOS / archivo
    if not ruta.exists():
        return {}
    d = json.loads(ruta.read_text(encoding="utf-8"))
    salida: dict = {}
    for r in d.get("registros", []):
        for k, v in (r.get("indicadores") or {}).items():
            if isinstance(v, dict) and v.get("anio"):
                salida.setdefault(k, {})[r["iso"]] = int(str(v["anio"])[:4])
    return salida


def comparar(clave, rotulo, fuente, en_siwa: dict, en_fuente: dict, donde: str) -> dict:
    atrasados, sin_novedad, al_dia, faltan = [], [], [], []
    for iso, anio_f in sorted(en_fuente.items()):
        anio_s = en_siwa.get(iso)
        if anio_s is None:
            faltan.append({"iso": iso, "fuente": anio_f})
        elif anio_f > anio_s:
            atrasados.append({"iso": iso, "siwa": anio_s, "fuente": anio_f})
        else:
            al_dia.append(iso)
    mas_nuevo_siwa = max(en_siwa.values()) if en_siwa else None
    mas_nuevo_fuente = max(en_fuente.values()) if en_fuente else None
    if atrasados:
        estado = "siwa_atrasado"
    elif en_fuente:
        estado = "al_dia"
    else:
        estado = "no_comprobado"
    return {"clave": clave, "rotulo": rotulo, "fuente": fuente, "donde_se_comprobo": donde,
            "estado": estado, "anio_siwa": mas_nuevo_siwa, "anio_fuente": mas_nuevo_fuente,
            "paises_al_dia": len(al_dia), "paises_atrasados": atrasados,
            "paises_con_dato_en_fuente_y_no_en_siwa": faltan}


# ── BANCO MUNDIAL ────────────────────────────────────────────────────────────
def banco_mundial(isos: list) -> list:
    import banco_mundial as bm
    publicado = siwa("banco-mundial.json")
    medidas = [m for m in bm.INDICADORES if m.get("codigo") and m["clave"] in publicado]

    def uno(m):
        url = (f"https://api.worldbank.org/v2/country/{';'.join(isos)}/indicator/{m['codigo']}"
               f"?format=json&mrnev=1&per_page=200"
               + (f"&source={m['fuente_id']}" if m.get("fuente_id") else ""))
        estado, _, cuerpo = pedir(url, agente=comun.AGENTE)
        try:
            filas = json.loads(cuerpo)[1] or []
        except Exception:  # noqa: BLE001
            return comparar(m["clave"], m["rotulo"], "Banco Mundial", publicado.get(m["clave"], {}), {},
                            url) | {"estado": "no_comprobado", "motivo": f"respuesta {estado}"}
        fuente = {f["countryiso3code"]: int(f["date"][:4]) for f in filas
                  if f.get("value") is not None and f.get("countryiso3code")}
        return comparar(m["clave"], m["rotulo"], "Banco Mundial", publicado.get(m["clave"], {}), fuente, url)

    with ThreadPoolExecutor(6) as ex:
        return list(ex.map(uno, medidas))


# ── OMS ──────────────────────────────────────────────────────────────────────
def oms(isos: list) -> list:
    import oms as o
    publicado = siwa("oms.json")
    salida = []
    for m in o.MEDIDAS:
        # Un filtro con los 33 países es demasiado largo para la API: se pide la región
        # de las Américas y se queda con los del padrón.
        region = urllib.parse.quote("ParentLocationCode eq 'AMR'")
        url = f"{o.BASE}/{m['codigo']}?$filter={region}"
        estado, _, cuerpo = pedir(url, agente=comun.AGENTE)
        try:
            filas = json.loads(cuerpo)["value"]
        except Exception:  # noqa: BLE001
            salida.append(comparar(m["clave"], m["rotulo"], "OMS", publicado.get(m["clave"], {}), {}, url)
                          | {"motivo": f"respuesta {estado}"})
            continue
        fuente: dict = {}
        for f in filas:
            if f.get("SpatialDim") not in isos:
                continue
            if m["sexo"] and f.get("Dim1") != m["sexo"]:
                continue
            if f.get("NumericValue") is None:
                continue
            fuente[f["SpatialDim"]] = max(fuente.get(f["SpatialDim"], 0), int(f["TimeDim"]))
        salida.append(comparar(m["clave"], m["rotulo"], "OMS", publicado.get(m["clave"], {}), fuente,
                               f"{o.BASE}/{m['codigo']}"))
    return salida


# ── EDICIONES QUE SALEN DE A UNA ────────────────────────────────────────────
def ediciones() -> list:
    salida = []
    import bti
    for anio in (bti.EDICION + 4, bti.EDICION + 2):
        url = f"https://bti-project.org/content/en/downloads/data/BTI_{anio}_Scores.xlsx"
        estado, cab, _ = pedir(url, "HEAD")
        if estado == 200:
            salida.append({"clave": "bti (6 indicadores)", "rotulo": "Índice de Transformación Bertelsmann",
                           "fuente": "BTI", "estado": "siwa_atrasado", "anio_siwa": bti.EDICION,
                           "anio_fuente": anio, "donde_se_comprobo": url})
            break
    else:
        salida.append({"clave": "bti (6 indicadores)", "rotulo": "Índice de Transformación Bertelsmann",
                       "fuente": "BTI", "estado": "al_dia", "anio_siwa": bti.EDICION,
                       "anio_fuente": bti.EDICION, "donde_se_comprobo": "bti-project.org/downloads"})

    import recursos
    edicion = int(re.search(r"mcs(\d{4})", str(recursos.COPIA_USGS).lower()).group(1))
    siguiente = edicion + 1
    url = ("https://www.sciencebase.gov/catalog/items?format=json&max=5&q="
           + urllib.parse.quote(f"Mineral Commodity Summaries {siguiente} Data Release"))
    estado, _, cuerpo = pedir(url, agente=comun.AGENTE)
    try:
        titulos = [i.get("title", "") for i in json.loads(cuerpo).get("items", [])]
    except Exception:  # noqa: BLE001
        titulos = []
    hay = any(f"Mineral Commodity Summaries {siguiente}" in t for t in titulos)
    salida.append({"clave": "cuota_mineral_mundial, minerales_escala_mundial", "rotulo": "Minerales (USGS)",
                   "fuente": "USGS Mineral Commodity Summaries",
                   "estado": "siwa_atrasado" if hay else ("al_dia" if estado == 200 else "no_comprobado"),
                   "anio_siwa": edicion - 1, "anio_fuente": (siguiente - 1) if hay else edicion - 1,
                   "donde_se_comprobo": "sciencebase.gov"})

    import percepcion_corrupcion as pc
    actual = int(re.search(r"CPI(\d{4})", pc.URL).group(1))
    # La página de Transparency International responde 403 a programas, pero sus
    # planillas no: se prueban los dos nombres que usó (2024 y 2025).
    siguiente = actual + 1
    candidatas = [f"https://images.transparencycdn.org/images/CPI{siguiente}_Results.xlsx",
                  f"https://images.transparencycdn.org/images/CPI{siguiente}-Results-and-trends.xlsx"]
    hallada = next((u for u in candidatas if pedir(u, "HEAD", agente=comun.AGENTE)[0] == 200), None)
    salida.append({"clave": "percepcion_corrupcion", "rotulo": "Índice de Percepción de la Corrupción",
                   "fuente": "Transparency International",
                   "estado": "siwa_atrasado" if hallada else "al_dia",
                   "anio_siwa": actual, "anio_fuente": siguiente if hallada else actual,
                   "donde_se_comprobo": hallada or candidatas[0]})
    return salida


# ── FUENTES NACIONALES MÁS NUEVAS FUERA DE SIWA ─────────────────────────────
def nacionales(publicado_bm: dict) -> list:
    salida = []
    estado, _, cuerpo = pedir("https://cloud-snic.minseg.gob.ar/Bases/SNIC/snic-pais.csv")
    if estado == 200:
        filas = [l.split(";") for l in cuerpo.decode("utf-8", "replace").splitlines()[1:]]
        hom = [f for f in filas if len(f) > 9 and "Homicidios dolosos" == f[2].strip('"')]
        ultimo = max(hom, key=lambda f: int(f[0]))
        salida.append({"iso": "ARG", "materia": "homicidios dolosos", "organismo": "Ministerio de Seguridad — SNIC",
                       "ultimo_periodo": int(ultimo[0]), "valor": float(ultimo[9].replace(",", ".")),
                       "unidad": "víctimas por cada 100.000 habitantes",
                       "siwa": publicado_bm.get("homicidios", {}).get("ARG"),
                       "url": "https://cloud-snic.minseg.gob.ar/Bases/SNIC/snic-pais.csv"})
    estado, _, cuerpo = pedir("https://www.datos.gov.co/api/views/m8fd-ahd9.json")
    if estado == 200:
        j = json.loads(cuerpo)
        filas_al = datetime.fromtimestamp(j.get("rowsUpdatedAt", 0), timezone.utc)
        salida.append({"iso": "COL", "materia": "homicidios", "organismo": "Ministerio de Defensa — datos.gov.co",
                       "ultima_actualizacion": filas_al.date().isoformat(),
                       "siwa": publicado_bm.get("homicidios", {}).get("COL"),
                       "url": "https://www.datos.gov.co/d/m8fd-ahd9"})
    return salida


# ── LOS COLECTORES ESTÁN CORRIENDO ──────────────────────────────────────────
def corridas(momento: datetime) -> list:
    salida = []
    for f in sorted((DATOS / "estado").glob("*.json")):
        try:
            e = json.loads(f.read_text(encoding="utf-8"))
            cuando = datetime.fromisoformat(e["momento"])
        except Exception:  # noqa: BLE001
            continue
        salida.append({"colector": e.get("colector", f.stem), "estado": e.get("estado"),
                       "horas_desde_la_ultima_corrida": round((momento - cuando).total_seconds() / 3600, 1)})
    return salida


def main() -> None:
    # --avisar: termina en error si SIWA quedó atrás de alguna fuente. En el robot eso
    # pone la corrida en rojo, y GitHub manda el correo solo, sin credenciales.
    avisar = "--avisar" in sys.argv
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    destino = Path(argumentos[0]) if argumentos else RAIZ / "reloj-actualidad.json"
    inicio = datetime.now(timezone.utc)
    isos = [p["iso"] for p in geo.padron()]
    r = reloj()
    comprobaciones = banco_mundial(isos) + oms(isos) + ediciones()
    publicado_bm = siwa("banco-mundial.json")
    resultado = {
        "que_es": "Compara el período más nuevo que tiene SIWA con el que publica cada fuente hoy.",
        "controlado": ahora_txt(inicio),
        "reloj": r,
        "resumen": {
            "comprobados": sum(1 for c in comprobaciones if c["estado"] != "no_comprobado"),
            "al_dia": sum(1 for c in comprobaciones if c["estado"] == "al_dia"),
            "siwa_atrasado": sum(1 for c in comprobaciones if c["estado"] == "siwa_atrasado"),
            "no_comprobado": sum(1 for c in comprobaciones if c["estado"] == "no_comprobado"),
        },
        "comprobaciones": comprobaciones,
        "fuentes_nacionales_mas_nuevas_fuera_de_siwa": nacionales(publicado_bm),
        "corridas_de_los_colectores": corridas(inicio),
        "duracion_segundos": round((datetime.now(timezone.utc) - inicio).total_seconds()),
    }
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    s = resultado["resumen"]
    print(f"[reloj] {resultado['controlado']['buenos_aires']} (Buenos Aires) · reloj {r['estado']}"
          f" (desfase {r.get('desfase_mediano_segundos')} s)")
    print(f"[reloj] {s['comprobados']} comprobados · {s['al_dia']} al día · {s['siwa_atrasado']} con SIWA atrasado"
          f" · {s['no_comprobado']} sin comprobar")
    for c in comprobaciones:
        if c["estado"] == "siwa_atrasado":
            detalle = c.get("paises_atrasados")
            print(f"   ATRASADO · {c['rotulo']} · SIWA {c['anio_siwa']} · fuente {c['anio_fuente']}"
                  + (f" · {len(detalle)} países" if detalle else ""))
        elif c["estado"] == "no_comprobado":
            print(f"   SIN COMPROBAR · {c['rotulo']} · {c.get('motivo')}")
    for n in resultado["fuentes_nacionales_mas_nuevas_fuera_de_siwa"]:
        print(f"   FUENTE NACIONAL · {n['iso']} {n['materia']} · SIWA {n['siwa']} · {n['organismo']}"
              f" {n.get('ultimo_periodo') or n.get('ultima_actualizacion')}")


    if avisar and (s["siwa_atrasado"] or r.get("estado") == "desfasado"):
        print("[reloj] AVISO: SIWA quedó atrás de su fuente o el reloj del robot está desfasado.")
        sys.exit(1)


if __name__ == "__main__":
    main()
