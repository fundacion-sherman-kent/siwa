# -*- coding: utf-8 -*-
"""Genera el PROTOTIPO del anexo de fuentes y método del producto «Trayectorias de
flujos ilícitos»: la tabla de rutas por familia y subtipo, leída de los
`sitio/flujos-rutas-*.json` + `sitio/infra-rutas-*.json` (ilícitas + infraestructura,
menos las `no_publicar`). Hoy son 413 rutas en siete familias.

OJO — este guión NO escribe el anexo publicado. Produce `sitio/proto-anexo-fuentes.html`,
un prototipo con cabecera propia. El anexo publicado, `sitio/flujos-anexo-fuentes.html`,
es una INTEGRACIÓN A MANO de esa salida: lleva la franja oficial de SIWA, la meta de la
página, la nav y una pasada de voz (doctrina/siwa-voz.md). Por eso regenerar acá no pisa
lo publicado; para llevar cambios al anexo publicado hay que reintegrar a mano. Se versiona
para no perder la lógica que arma la tabla desde los datos."""
import json, html, os
from pathlib import Path
SIT = str(Path(__file__).resolve().parents[1] / "sitio")
def L(f):
    pais=json.load(open(os.path.join(SIT,"flujos-rutas-"+f+".json"),encoding="utf-8"))
    rp=[r for r in pais.get("rutas",[]) if not r.get("no_publicar")]
    infp=os.path.join(SIT,"infra-rutas-"+f+".json")
    ri=[r for r in json.load(open(infp,encoding="utf-8")).get("rutas",[]) if not r.get("no_publicar")] if os.path.exists(infp) else []
    return {"rutas":rp+ri, "cobertura_parcial":pais.get("cobertura_parcial")}
e=html.escape

FAM=[
 ("Narcotráfico",["cocaina","opioides","marihuana","sinteticos","precursores"],
  "Narcotráfico: cocaína (el flujo insignia de ALC, con rutas a Asia/Oceanía), opioides (fentanilo y heroína), marihuana, drogas sintéticas y precursores químicos. Fuentes: UNODC, InSight Crime, GI-TOC, Europol, DEA/CRS, aduanas de varios países (actor interesado). El eslabón hidrovía→Australia vía Paraguay está AFIRMADO por prensa, no probado. La capa de cocaína conserva el estándar de la etapa anterior: el peso relativo entre subtipos no es comparable."),
 ("Armas",["armas"],
  "Tráfico de armas de fuego y municiones. ADVERTENCIA: buena parte de lo 'de origen EE.UU.' es dato de TRAZADO del ATF/GAO (origen de fabricación o compra), no una ruta de contrabando medida; en Centroamérica y el Caribe mucho salió por exportación legal y se desvió. También hay desvío de arsenales estatales (Argentina, Perú, Brasil)."),
 ("Migración y desplazamiento",["migracion"],
  "Migración, desplazamiento y retorno, sobre registros de Estado (servicios migratorios, guardias costeras, CBP) y multilaterales (R4V, OIM, ACNUR, IDMC). Muchos tramos son construcción propia: el registro cuenta encuentros o stock, no el trayecto de la misma persona. Incluye deportaciones de 2026 y desplazamiento interno forzado."),
 ("Oro y minerales",["minerales"],
  "Oro, coltán, esmeraldas, estaño/casiterita y cobre. Doble advertencia: mucho oro ilegal se blanquea como producción legal y no deja ruta; y varios pares origen→destino salen de discrepancia de comercio, no de un lote rastreado (van punteados). Casos que NO son contrabando y se rotulan: el oro del BCV venezolano (reserva bajo sanciones) y el oro de Nicaragua (flujo comercial)."),
 ("Especies — vida silvestre y madera",["especies"],
  "Tráfico de fauna y madera. Fuentes: CITES, TRAFFIC, EIA, InSight Crime, GI-TOC, RUSI, Mongabay, Project Seahorse y agencias (actor interesado). El centroide de destino asiático es marcador, no puerto; muchas rutas son pares país-país sin trayecto (construcción propia). Parte del comercio (p. ej. balsa de Ecuador) es legal con ilegalidad parcial."),
 ("Contrabando",["contrabando"],
  "Contrabando de mercancías: cigarrillos, combustible, electrónica, vehículos, medicamentos, licor y textiles. Fuentes: UNODC, Euromonitor, TRACIT, ICIJ, InSight Crime, GI-TOC y fiscos (actor interesado). La dirección de un flujo de frontera puede invertirse según precios; varios corredores de combustible boliviano van como históricos tras el fin del subsidio (dic 2025)."),
 ("Trata de personas",["trata"],
  "Trata de personas con fines de explotación sexual y laboral. Fuentes: OIM, UNODC, OIT, InSight Crime, fiscalías y ONG. Advertencia central: la trata en ALC es mayormente INTERNA o entre vecinos; un mapa de rutas internacionales la sobrerrepresenta. Varias rutas son de 2005-2012 (históricas)."),
]

def tags(r):
    t=[]
    if r.get("estado")=="historica": t.append('<span class="tg tg-h">histórica</span>')
    if r.get("no_ilicito"): t.append('<span class="tg tg-n">no ilícito</span>')
    if r.get("inferencia")=="comercio": t.append('<span class="tg tg-c">inferencia de comercio</span>')
    return " ".join(t)
def filas(rutas):
    out=[]
    for r in rutas:
        tray=" → ".join(w[2] for w in r["waypoints"])
        cp = ("<b>Sí</b> — "+e(r.get("base","")) if r.get("base") else "<b>Sí</b>") if r.get("construccion_propia") else "No"
        url=r.get("url",""); fu=e(r.get("fuente",""))
        cita = fu + (f' · <a href="{e(url)}" target="_blank" rel="noopener">enlace</a>' if url else "")
        st=tags(r)
        out.append(f"<tr><td class='id'>{e(r['id'])}</td><td class='st'>{e(r.get('subtipo','—'))}</td>"
                   f"<td><b>{e(r['nombre'])}</b>{(' '+st) if st else ''}<div class='tray'>{e(tray)}</div></td>"
                   f"<td class='cf cf-{e(r.get('confianza','media'))}'>{e(r.get('confianza','media'))}</td>"
                   f"<td class='cp'>{cp}</td><td class='src'>{cita}<div class='desde'>registrada desde {r.get('desde','—')}</div></td></tr>")
    return "\n".join(out)
def seccion(nombre,files,intro):
    rutas=[]; vac=[]
    for f in files:
        d=L(f); rutas+=d["rutas"]
        if d.get("cobertura_parcial"): vac.append(d["cobertura_parcial"])
    subs=sorted(set(r.get("subtipo","—") for r in rutas))
    v="".join(f"<li>{e(x)}</li>" for x in vac) or "<li>Sin vacíos declarados a nivel de familia.</li>"
    return f"""<section><h2>{e(nombre)} <span class="n">{len(rutas)} rutas · {len(subs)} subtipos</span></h2>
    <p class="intro">{e(intro)}</p>
    <p class="subs">Subtipos: {" · ".join("<b>"+e(s)+"</b>" for s in subs)}</p>
    <table><thead><tr><th>ID</th><th>Subtipo</th><th>Ruta y trayectoria (países que atraviesa)</th><th>Confianza</th><th>Construcción propia</th><th>Fuente</th></tr></thead>
    <tbody>{filas(rutas)}</tbody></table>
    <div class="vacios"><h3>Vacíos declarados y cobertura · {e(nombre.lower())}</h3><ul>{v}</ul></div></section>""", len(rutas)

CSS="""
:root{--navy:#00121E;--naranja:#FB6500;--tinta:#07131E;--tenue:#667B89;--crema:#F9F9F7;--linea:#e2e0d8;--caja:#fff;--violeta:#460070;}
*{box-sizing:border-box;} body{margin:0;background:var(--crema);color:var(--tinta);font-family:'Inter',system-ui,'Segoe UI',sans-serif;line-height:1.55;}
.wrap{max-width:1040px;margin:0 auto;padding:28px 24px 60px;}
.filete{height:4px;width:80px;background:var(--naranja);border-radius:2px;margin-bottom:14px;}
.rotulo{font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--tenue);}
h1{font-size:28px;margin:4px 0 6px;letter-spacing:-.4px;} h1 b{color:var(--naranja);}
.bajada{color:var(--tenue);font-size:14.5px;max-width:820px;margin:0 0 16px;}
h2{font-size:19px;margin:34px 0 6px;border-top:2px solid var(--navy);padding-top:18px;} h2 .n{font-size:12px;color:var(--tenue);font-weight:600;}
.intro{font-size:13.5px;color:#33434f;max-width:900px;margin:2px 0 6px;}
.subs{font-size:12px;color:var(--tenue);margin:0 0 12px;}
table{width:100%;border-collapse:collapse;font-size:12px;margin:6px 0;}
th{text-align:left;background:var(--navy);color:#fff;padding:7px 9px;font-size:10.5px;letter-spacing:.03em;text-transform:uppercase;vertical-align:top;}
td{padding:7px 9px;border-bottom:1px solid var(--linea);vertical-align:top;}
td.id{font-weight:700;color:var(--tenue);white-space:nowrap;} td.st{color:var(--violeta);font-weight:600;white-space:nowrap;font-size:11px;}
.tray{color:var(--tenue);font-size:11px;margin-top:3px;}
.cf{font-weight:700;text-transform:uppercase;font-size:10px;white-space:nowrap;}
.cf-alta{color:#1f7a3d;} .cf-media{color:#a86a00;} .cf-baja{color:var(--tenue);}
td.cp{font-size:11px;max-width:200px;}
td.src{font-size:11px;} td.src a{color:var(--naranja);} .desde{color:var(--tenue);font-size:10px;margin-top:3px;}
.tg{display:inline-block;font-size:9.5px;font-weight:700;text-transform:uppercase;border-radius:10px;padding:1px 6px;margin-left:4px;vertical-align:middle;}
.tg-h{background:#fdeede;color:#a8630a;} .tg-n{background:#eef1f4;color:#556;} .tg-c{background:#efeaf6;color:var(--violeta);}
.metodo,.vacios{background:var(--caja);border:1px solid var(--linea);border-radius:10px;padding:14px 16px;margin:14px 0;}
.vacios h3,.metodo h3{font-size:14px;margin:0 0 8px;color:var(--violeta);}
.metodo ul,.vacios ul{margin:0;padding-left:18px;} .metodo li,.vacios li{font-size:12.5px;margin-bottom:5px;}
.lex{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0 2px;}
.lex span{font-size:11.5px;border:1px solid var(--linea);border-radius:16px;padding:4px 10px;background:var(--caja);}
.pie{margin-top:30px;border-top:1px solid var(--linea);padding-top:14px;color:var(--tenue);font-size:12px;}
@media print{body{background:#fff;} .metodo,.vacios,table{break-inside:avoid;}}
"""
HEAD=f"""<!DOCTYPE html><html lang="es-AR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Anexo de fuentes y método · Trayectorias de flujos ilícitos</title><link rel="stylesheet" href="_comun/paleta-fusk.css"><style>{CSS}</style></head><body><div class="wrap">
<div class="filete"></div><div class="rotulo">SIWA · Fundación Sherman Kent · Anexo del producto</div>
<h1>Anexo de fuentes y método — <b>Trayectorias de flujos ilícitos</b></h1>
<p class="bajada">Acompaña al mapa de trayectorias de los flujos ilícitos de América Latina y el Caribe, organizado en siete familias con sus subtipos. Toda afirmación del producto es trazable a este anexo; sin fuente acá, no entra al producto.</p>
<div class="metodo"><h3>Nota de método</h3><ul>
<li><b>Qué es y qué no.</b> El producto muestra <b>rutas registradas por terceros, no flujos medidos</b>. Cada ruta es una <b>trayectoria de países de tránsito</b>, no un trazado geográfico exacto ni un volumen.</li>
<li><b>La honestidad de la ficha no basta: manda también el dibujo.</b> La regla de dos fuentes opera en el píxel, no sólo en el texto. La confianza baja cuando el último tramo se apoya en una sola fuente interesada o un solo caso.</li>
<li><b>Recolección.</b> OSINT sobre fuentes públicas y legales (recolección pasiva, doctrina/limites.md). No se saltearon controles de acceso.</li>
<li><b>Confianza por ruta.</b> <b>alta</b> (primaria o varias independientes), <b>media</b> (una fuente analítica o casos), <b>baja</b> (caso puntual o país de tránsito incierto).</li>
<li><b>Construcción propia.</b> Donde un tramo no lo afirma una fuente se declara «construcción propia en base a [fuente]» y va punteado; no se presenta como hecho.</li>
<li><b>Etiquetas.</b> «histórica» (dato viejo, atenuado), «no ilícito» (flujo soberano bajo sanción o comercial, en gris), «inferencia de comercio» (discrepancia de comercio espejo, no trayecto físico).</li>
<li><b>Fuentes interesadas.</b> Las de gobiernos (EE.UU. sobre todo), fiscos, aduanas y policías se usan pero se rotulan como actor interesado.</li>
<li><b>Cómo se lee el trazo, y la línea de tiempo.</b> El color marca la familia; la <b>opacidad</b>, la confianza (no el volumen); la <b>línea punteada</b>, lo inferido, histórico o difuso; y la <b>línea más fina</b>, el vínculo difuso. El año es el de REGISTRO, no el de vigencia.</li>
<li><b>Disenso.</b> El producto pasó por el décimo hombre en dos rondas; sus objeciones se aplicaron sobre estos datos.</li>
</ul>
<div class="lex"><span><b>alta</b>: primaria o varias independientes</span><span><b>media</b>: analítica o casos</span><span><b>baja</b>: puntual o incierto</span></div></div>
"""
FOOT="""<div class="pie"><b>SIWA — Fundación Sherman Kent.</b> Registro público de situación de América Latina y el Caribe.
Datos de base bajo la licencia de cada fuente citada; el anexo, uso libre con atribución.
La Oficina agradece a los especialistas y funcionarios cuyas publicaciones hacen posible este registro, sin mencionar nombres.
Prototipo — no publicado. Pendiente: el visto bueno de la Dirección para reincorporarlo a SIWA.</div></div></body></html>"""

cuerpo=""; tot=0
for nombre,files,intro in FAM:
    html_sec,n=seccion(nombre,files,intro); cuerpo+=html_sec; tot+=n
open(os.path.join(SIT,"proto-anexo-fuentes.html"),"w",encoding="utf-8").write(HEAD+cuerpo+FOOT)
print("anexo generado:",tot,"rutas en",len(FAM),"familias")
