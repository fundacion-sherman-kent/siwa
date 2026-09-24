# SIWA

**Registro de situación de América Latina y el Caribe.**
Fundación Sherman Kent · Oficina de Generación de Inteligencia.

[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/14737/badge)](https://www.bestpractices.dev/projects/14737)
[![ODI Open Data Certificate](https://img.shields.io/badge/ODI%20Open%20Data%20Certificate-Silver-9e9e9e)](https://certificates.theodi.org/datasets/6ab05790309dbc520e929c91/certificates/6ab057cc309dbc520e929ca1)
[![Código: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-green)](LICENSE)
[![Datos: CC BY 4.0](https://img.shields.io/badge/datos-CC%20BY%204.0-blue)](LICENSE-DATOS.md)

*English: [`README.en.md`](README.en.md).*

Datos públicos de los 33 Estados del padrón, recolectados de forma automática y
calificados con doctrina de inteligencia: cada cifra sale con su fuente, su
fecha de referencia, su calificación de fiabilidad y su estado de corroboración.

Las materias se ordenan por los cuatro ejes de trabajo de la Fundación
—**seguridad**, **defensa**, **gobernanza** y **desarrollo**— y no por la
disponibilidad de las fuentes.

> **Siwa** es el oasis del desierto occidental de Egipto adonde Alejandro marchó
> en el 331 a.C. antes de decidir su campaña. El nombre alude a eso —el lugar que
> se consulta antes de decidir— y no a la adivinación: este registro no predice
> nada, registra.

## El objetivo

**Ser la primera plataforma de consulta de datos de América Latina y el Caribe.**
No la más grande: la primera a la que se recurre cuando hay que averiguar cómo
está la región y de dónde sale ese dato. De ahí, tres compromisos que obligan al
desarrollo:

1. **Vanguardia en la obtención.** Se buscan fuentes nuevas de forma permanente
   y ninguna entra sin una disponibilidad medida por el mismo robot que después
   la va a usar.
2. **Vanguardia en el procesamiento y en la visualización.** Todo tema tiene que
   poder mirarse en el tiempo y compararse; una cifra sin historia ni contexto es
   un dato incompleto, no un tablero.
3. **Diseño adaptable, siempre.** Teléfono, tableta, monitor y papel. **Un
   desarrollo que no entra en una pantalla chica está incompleto**, por bien que
   se vea en la grande.

**El objetivo no se declara: se mide**, y la medición se publica junto con la
declaración. Los cinco controles que lo hacen cumplir, y que corren solos, están
en la tabla de «Mejora continua» más abajo. La regla que los ordena a todos:
**toda disciplina que dependa de que alguien se acuerde se convierte en máquina;
lo que no falla solo en rojo, no se sostiene.**

## Qué es y qué no es

Este registro **no emite juicios**. Publica hechos calificados. El análisis, con
su confianza y su probabilidad, sale por otro camino y con firma.

## Licencia

- **Datos** (`datos/publico/`): **Creative Commons Atribución 4.0 (CC BY 4.0)** —
  cubre el aporte de la Fundación (recolección, calificación, vacíos). Ver
  [`LICENSE-DATOS.md`](LICENSE-DATOS.md).
- **Código** (colectores, sitio, herramientas): **MIT**. Ver [`LICENSE`](LICENSE).
- Los **datos de base** conservan la licencia de su fuente; cuando hay condiciones
  adicionales, se declaran por dato en el campo `restriccion_de_uso`.
- Cómo citar: «SIWA — Fundación Sherman Kent», enlazando a https://siwa.fundacionkent.org.

## Reglas que el código hace cumplir

1. **No se simulan datos.** Si una fuente falla, el colector termina con error,
   deja intacto el dato anterior y anota la falla en `datos/publico/estado/`.
   Nunca escribe un valor de ejemplo.
2. **La corroboración no se declara sola.** Ningún dato puede calificar
   credibilidad `1` sin dos orígenes independientes. El intento levanta
   excepción y detiene la corrida.
3. **Los vacíos se declaran.** Cada archivo lleva la lista de lo que su fuente
   no cubre.
4. **Sin modelos de lenguaje en la recolección.** Solo biblioteca estándar de
   Python y estadística clásica.
5. **Todo el registro es público.** No hay capa reservada ni cuenta de acceso:
   el estado, la serie histórica, la exportación en planilla y el informe
   descargable están abiertos para cualquiera, sin registro.
6. **Nada se cambia si pone en riesgo el sitio o los datos.** Ante la duda entre
   una función nueva y la integridad de lo publicado, gana lo publicado. Ningún
   cambio se sube sin sus controles en verde; ningún colector nuevo puede tumbar
   a los que ya andan; lo que no se pudo probar entra al robot pero no a la
   pantalla; y ninguna función vistosa justifica publicar una cifra sin fuente,
   sin año o sin su vacío declarado.

   No es una excusa para no avanzar: frena lo riesgoso, no lo nuevo. La medida
   de si una mejora vale la pena no es cuánto impresiona, sino **si el lector
   puede seguir sabiendo de dónde sale cada cifra, de cuándo es y qué no cubre**.

## Estructura

```
colectores/     los programas que traen los datos
  comun.py      funciones compartidas y control de calificación
  geo.py        atribución de una coordenada al padrón de los 33
  cites.py      CITES — comercio de especies protegidas
  focos.py      NASA FIRMS — focos de calor
  ...           un archivo por fuente; la lista completa, en la tabla de abajo
datos/
  publico/      todo el registro; no hay capa reservada
    estado/     cómo terminó la última corrida de cada colector
sitio/
  index.html    registro, mapa e informe descargable
```

## Cómo se ejecuta

Cada hora, sin intervención, mediante GitHub Actions. También a mano, desde la
pestaña **Actions** del repositorio, con el botón *Run workflow*.

En una máquina con Python 3.12, sin instalar nada:

```bash
python colectores/focos.py
```

## Fuentes en uso

<!-- fuentes:calculado -->

**88 fuentes en servicio**, en 90 archivos de datos: hay fuentes que dejan más de un archivo. Esta tabla no se escribe: la calcula `herramientas/sellar-portada.py` desde los archivos de datos, después de cada recolección. Un colector que no dejó dato no aparece acá.

| Colector | Fuente | Calificación | Estados | Vacíos declarados |
|---|---|:---:|---:|---:|
| `archivo` | Archivo público de la web — copias fechadas de los portales oficiales | `B-2` | 33 | 6 |
| `armas` | Comtrade de Naciones Unidas — capítulo 93: armas, municiones y sus partes | `A-2` | 33 | 8 |
| `banco-mundial` | Banco Mundial — indicadores de desarrollo y gobernanza | `A-2` | 33 | 8 |
| `bce_ecuador` | Banco Central del Ecuador (BCE) — Información Estadística Mensual (IEM-121, reservas) | `A-2` | 1 | 2 |
| `bienes_culturales` | UNIDROIT — Convenio de 1995 sobre bienes culturales robados o exportados ilícitamente | `A-2` | 33 | 5 |
| `brecha` | Fundación Sherman Kent — brecha entre lo registrado y lo publicado | `B-2` | 33 | 5 |
| `bti` | Índice de Transformación Bertelsmann (BTI), edición 2026 | `B-3` | 22 | 6 |
| `censo_subnacional` | Censo propio de disponibilidad subnacional — Fundación Sherman Kent, sobre la base georreferenciada de Upsala y la interfaz humanitaria de Naciones Unidas | `B-3` | 33 | 12 |
| `cepal` | CEPALSTAT — Comisión Económica para América Latina y el Caribe (CEPAL): Observatorio de Igualdad de Género y estadísticas de seguridad ciudadana | `A-2` | 33 | 8 |
| `chile_ine_seguridad` | Instituto Nacional de Estadísticas de Chile (INE) — Estadísticas Policiales, cuadro de víctimas | `A-2` | 1 | 4 |
| `ciber` | OONI, IODA y FIRST — medición técnica de red y capacidad de respuesta | `B-2` | 33 | 6 |
| `cites` | CITES — base de datos de comercio de especies protegidas (secretaría CITES / UNEP-WCMC) | `A-3` | 33 | 8 |
| `cobertura` | Padrón de medios de la Fundación Sherman Kent | `F-3` | — | 11 |
| `comercio` | Comtrade de Naciones Unidas — vista pública | `A-2` | 19 | 9 |
| `conflictos` | Instituto de Estudios Interculturales, Pontificia Universidad Javeriana Cali — visor de conflictos de America Latina | `B-3` | 11 | 7 |
| `consulta` | Fundación Sherman Kent — consulta dirigida a la fuente primaria | `A-2` | 33 | 6 |
| `contratacion` | Registro de publicadores de contrataciones abiertas | `B-2` | 33 | 5 |
| `contrataciones_abiertas` | Registro de publicadores del Estándar de Datos de Contrataciones Abiertas — Open Contracting Partnership | `A-2` | 33 | 4 |
| `copernicus` | Copernicus — catálogo de observación de la Tierra de la Unión Europea | `A-2` | 33 | 6 |
| `crimen_organizado` | Índice Global de Crimen Organizado — Global Initiative Against Transnational Organized Crime | `B-3` | 33 | 7 |
| `desastres` | IFRC GO — Federación Internacional de Sociedades de la Cruz Roja y de la Media Luna Roja, registro de emergencias | `A-2` | 33 | 8 |
| `designados` | Consejo de Seguridad de las Naciones Unidas — lista consolidada de sanciones | `A-2` | 33 | 6 |
| `desplazamiento-serie` | ACNUR — Refugee Data Finder | `A-2` | 33 | 8 |
| `desplazamiento` | ACNUR — Refugee Data Finder | `A-2` | 33 | 8 |
| `drogas` | Informe Mundial sobre las Drogas 2025, anexo estadístico — Oficina de las Naciones Unidas contra la Droga y el Delito (UNODC) | `B-2` | 33 | 4 |
| `eia` | Administración de Información Energética de los Estados Unidos (EIA) — estadística energética internacional | `A-2` | 33 | 3 |
| `estado_reciente` | Estadística oficial de homicidios de cada Estado, leída en la fuente primaria de cada país: Argentina, Colombia, Ecuador, México, Panamá, Perú, Trinidad y Tobago | `A-2` | 33 | 4 |
| `explorador` | Fundación Sherman Kent — exploración de puertas de datos oficiales | `A-1` | 33 | 6 |
| `fmi_mensual` | Fondo Monetario Internacional — datos estadísticos (SDMX 3.0): liquidez internacional (IL) e índice de precios al consumidor (CPI) | `A-2` | 33 | 4 |
| `focos` | NASA FIRMS — focos de calor detectados por satélite | `A-2` | 33 | 6 |
| `fundacion` | Fundación Sherman Kent — canal institucional | `A-1` | — | 4 |
| `gasto_publico` | Estadísticas de Finanzas Públicas del Fondo Monetario Internacional, clasificación del gasto por función (COFOG), vía DBnomics | `B-2` | 22 | 8 |
| `gti` | Institute for Economics & Peace (IEP) — Global Terrorism Index 2026: Measuring the Impact of Terrorism | `B-3` | 33 | 7 |
| `ia` | Microsoft AI Economy Institute; OpenAI Signals; Anthropic Economic Index; documentación oficial de siete empresas de nube | `B-3` | 33 | 7 |
| `ia_apps` | Apple App Store — rankings de apps gratuitas y disponibilidad por país; padrón de asistentes de IA con origen verificado por la Fundación | `B-3` | 33 | 6 |
| `indice_opacidad` | Fundación Sherman Kent — Índice de Opacidad, edición uno | `A-1` | 33 | 10 |
| `inflacion` | CEPALSTAT — Índice de precios al consumidor mensual (indicador 365), Comisión Económica para América Latina y el Caribe | `A-2` | 33 | 4 |
| `influencia` | Google — boletín trimestral de operaciones de influencia coordinada (TAG Bulletin); TikTok — informes de operaciones de influencia encubiertas | `B-3` | 33 | 8 |
| `inform` | INFORM Risk — Centro Común de Investigación de la Comisión Europea y OCHA | `A-3` | 33 | 4 |
| `infraestructura` | Mapa de cables submarinos — TeleGeography, interfaz pública; OurAirports — censo abierto y colaborativo de aeródromos del mundo; Energy Institute y Ember, via Our World in Data; GCAT — catálogo general de objetos espaciales de Jonathan McDowell, CC BY 4.0 | `B-3` | 33 | 10 |
| `memoria` | Fundación Sherman Kent — bitácora de observación de SIWA | `A-2` | 30 | 5 |
| `oficiales` | Catálogos oficiales de datos abiertos de los Estados del padrón | `A-2` | 9 | 11 |
| `oit` | Organización Internacional del Trabajo — ILOSTAT, armonización de las encuestas de hogares de cada Estado | `B-2` | 33 | 6 |
| `oms` | Observatorio Mundial de la Salud — Organización Mundial de la Salud (OMS) | `B-2` | 33 | 5 |
| `oms_homicidios` | Observatorio Mundial de la Salud — Organización Mundial de la Salud (OMS) | `A-2` | 33 | 6 |
| `onu-ods` | Naciones Unidas — base global de indicadores de los ODS | `A-2` | 33 | 7 |
| `opacidad` | Fundación Sherman Kent — Índice de Opacidad, edición cero | `A-3` | 33 | 8 |
| `opacidad_historia` | Fundación Sherman Kent — archivo del Índice de Opacidad | `A-2` | 33 | 1 |
| `owd` | V-Dem y UCDP, vía Our World in Data (la Base Global de Terrorismo se retiró de esta capa el 21/9/2026: ver vacíos declarados) | `B-2` | 33 | 10 |
| `pdh_guatemala_subnacional` | Procuraduría de los Derechos Humanos de Guatemala (PDH) — panel «PDH en cifras», denuncias por departamento | `B-3` | 1 | 4 |
| `percepcion_corrupcion` | Transparency International — Índice de Percepción de la Corrupción | `B-2` | 33 | 7 |
| `pobreza` | Banco Mundial, Plataforma sobre Pobreza y Desigualdad — redistribuido por CEPALSTAT (Comisión Económica para América Latina y el Caribe) | `A-2` | 33 | 5 |
| `prensa_libre` | Reporteros Sin Fronteras — clasificación mundial de la libertad de prensa | `B-3` | 33 | 5 |
| `radar` | Cloudflare Radar — mediciones sobre tráfico real de internet | `B-2` | 33 | 4 |
| `ransomware` | ransomware.live — recopilación de sitios de extorsión informática | `D-4` | 31 | 6 |
| `reciente_oficial` | Catalogos oficiales de los Estados — lo mas reciente publicado | `A-2` | 33 | 5 |
| `recursos` | Servicio Geológico de los Estados Unidos — Mineral Commodity Summaries, base mundial de producción y reservas; Energy Institute y Servicio Geológico de los Estados Unidos, via Our World in Data | `A-2` | 33 | 9 |
| `redes` | Mastodon — instancias mastodon.social, mstdn.social, masto.ai, mas.to | `F-4` | 33 | 7 |
| `regimen_politico` | V-Dem, Universidad de Gotemburgo — «Regímenes del Mundo», vía Our World in Data | `B-2` | 33 | 5 |
| `reliefweb` | ReliefWeb — Oficina de Coordinación de Asuntos Humanitarios de las Naciones Unidas (OCHA) | `A-2` | 33 | 3 |
| `sanciones` | OpenSanctions — registros de sanciones y personas expuestas | `B-2` | 33 | 5 |
| `sanciones_primarias` | Listas primarias de sanciones: OFAC (EE. UU.) y UK Sanctions List (Reino Unido) | `A-2` | 33 | 4 |
| `sipri` | SIPRI — Stockholm International Peace Research Institute: base de gasto militar | `A-2` | 33 | 3 |
| `sipri_transferencias` | SIPRI — Stockholm International Peace Research Institute: base de transferencias de armas mayores (valores TIV) | `A-2` | 33 | 2 |
| `sismos` | Servicio Geológico de los Estados Unidos (USGS) — catálogo de sismos, servicio FDSN | `A-1` | 33 | 6 |
| `sondeo` | Fundación Sherman Kent — banco de pruebas de fuentes candidatas | `A-1` | — | 5 |
| `subnacional` | Censo propio de fuentes subnacionales — Fundación Sherman Kent, sobre los catálogos que publica cada jurisdicción | `A-2` | — | 3 |
| `subnacional_acled` | ACLED — Armed Conflict Location & Event Data Project: eventos de violencia política por unidad de primer orden (admin1) de cada Estado | `B-2` | 30 | 3 |
| `subnacional_colombia_extorsion` | Extorsión — Ministerio de Defensa Nacional / Policía Nacional de Colombia, vía datos.gov.co (Socrata) | `A-2` | 1 | 4 |
| `subnacional_colombia_incautacion_base_coca` | Incautación de base de coca — Ministerio de Defensa Nacional / Policía Nacional de Colombia, vía datos.gov.co (Socrata) | `A-2` | 1 | 5 |
| `subnacional_colombia_incautacion_basuco` | Incautación de basuco — Ministerio de Defensa Nacional / Policía Nacional de Colombia, vía datos.gov.co (Socrata) | `A-2` | 1 | 4 |
| `subnacional_colombia_incautacion_cocaina` | Incautación de cocaína — Ministerio de Defensa Nacional / Policía Nacional de Colombia, vía datos.gov.co (Socrata) | `A-2` | 1 | 5 |
| `subnacional_colombia_incautacion_insumos_liquidos` | Incautación de insumos líquidos — Ministerio de Defensa Nacional / Policía Nacional de Colombia, vía datos.gov.co (Socrata) | `A-2` | 1 | 5 |
| `subnacional_colombia_incautacion_marihuana` | Incautación de marihuana — Ministerio de Defensa Nacional / Policía Nacional de Colombia, vía datos.gov.co (Socrata) | `A-2` | 1 | 5 |
| `subnacional_colombia_secuestro` | Secuestro — Ministerio de Defensa Nacional / Policía Nacional de Colombia, vía datos.gov.co (Socrata) | `A-2` | 1 | 5 |
| `subnacional_colombia_terrorismo` | Terrorismo / acciones subversivas — Ministerio de Defensa Nacional / Policía Nacional de Colombia, vía datos.gov.co (Socrata) | `A-2` | 1 | 5 |
| `subnacional_datos` | Fuentes oficiales nacionales que publican por unidad de primer orden: Policía Nacional de Colombia; Sistema Nacional de Información Criminal (SNIC); Ministerio del Interior del Uruguay | `A-2` | 3 | 6 |
| `subnacional_focos` | Focos de calor por unidad de primer orden — NASA FIRMS agregado sobre geoBoundaries ADM1 | `A-2` | 21 | 3 |
| `subnacional_homicidios` | Homicidios por unidad de primer orden, de la fuente nacional de cada Estado (Argentina SNIC, Colombia MinDefensa, Ecuador INEC, Perú CEIC, México SESNSP) | `A-2` | 10 | 3 |
| `subnacional_robos` | Robos/hurtos por unidad de primer orden, de la fuente nacional de cada Estado (Argentina SNIC, Colombia Policía Nacional, Bolivia INE, Trinidad TTPS, República Dominicana — Policía Nacional vía datos.gob.do) | `A-2` | 8 | 3 |
| `subnacional_santafe` | Observatorio de Seguridad Pública de Santa Fe — infografía mensual de homicidios dolosos | `A-2` | 1 | 3 |
| `subnacional_viales` | Muertes en accidentes viales por provincia — Ministerio de Seguridad, SNIC (Argentina) | `A-2` | 1 | 4 |
| `subnacional_vigia` | Vigía subnacional de SIWA — reintento sostenido de fuentes por unidad de primer orden | `A-2` | — | 2 |
| `telegram` | Canales públicos de Telegram, vista sin cuenta | `F-4` | — | 8 |
| `trata_personas` | Departamento de Estado de los Estados Unidos — Informe sobre la Trata de Personas, edición 2025 | `B-2` | 33 | 6 |
| `ucdp` | UCDP — Programa de Datos de Conflicto de Upsala, Universidad de Upsala. Conjunto de país-año sobre violencia organizada dentro de las fronteras | `A-2` | 33 | 8 |
| `unesco` | Instituto de Estadística de la UNESCO (UIS), interfaz abierta | `B-2` | 33 | 5 |
| `unidades` | CEPAL — Proyecto MEGA nivel 2 (con UN-GGIM Américas) y geoBoundaries (gbHumanitarian, con gbOpen como red de seguridad) | `A-2` | 33 | 4 |
| `unodc_armas` | UNODC — Oficina de las Naciones Unidas contra la Droga y el Delito: base de tráfico de armas de fuego (incautaciones y detenciones) | `A-2` | 33 | 2 |
| `wjp` | World Justice Project — WJP Rule of Law Index (índice general de estado de derecho) | `A-2` | 33 | 2 |

La calificación es la del Almirantazgo: la letra mide **de quién viene** y el número, **qué tan verificado está lo que dice**. Ninguna fuente única puede calificar `1`; la circunstancia viaja declarada dentro de cada archivo.

<!-- fuentes:fin -->

## Mejora continua

El objetivo declarado arriba no se sostiene con buena voluntad. Se sostiene
porque **cada regla de calidad es un programa que corre solo y termina en rojo
cuando algo se rompe**. Ninguno depende de que una persona se acuerde de
revisar.

| Control | Qué hace cumplir | Qué publica | Cuándo corre |
|---|---|---|---|
| `herramientas/auditoria.py` | Procedencia completa, padrón cerrado de 33, series sin agujeros, y que exista todo lo que la pantalla carga | `datos/publico/auditoria.json` | cada recolección |
| `herramientas/pantallas.py` | Que la página entre en 360, 390, 768, 1024 y 1440 px, con los dos fondos y los tres niveles de lectura | `datos/publico/pantallas.json` | cada cambio de código |
| `colectores/sondeo.py` | Que las fuentes candidatas se reintenten solas y lleven disponibilidad medida antes de entrar | `datos/publico/sondeo.json` | cada recolección |
| `colectores/explorador.py` | Que se toquen puertas de datos oficiales nuevas, sin publicar nada sin decisión humana | `datos/publico/explorador.json` | corrida diaria |
| `colectores/memoria.py` | Que los cambios de estado queden registrados y anunciados, en la región y por Estado | `novedades.xml`, `novedades/*.xml` | cada recolección |
| `herramientas/indice-datos.py` | Que el catálogo público no pueda quedar viejo: se regenera del recorrido de archivos | `datos/publico/indice.json` | cada recolección |
| `.github/workflows/latido.yml` | Que GitHub no apague el robot por inactividad a los 60 días | `latido.txt` | dos veces por mes |

Las **fallas** tumban la corrida y avisan solas. Las **brechas** no tumban nada:
son la distancia que falta, se calculan igual y se publican, porque un objetivo
sin medición es una intención.

Para correr el control de pantallas hace falta un navegador de prueba, que no es
dependencia del sitio sino de la verificación:

```bash
pip install playwright && python -m playwright install chromium
python -m http.server 8000 &
python herramientas/pantallas.py http://localhost:8000
```

## Doctrina

La carta de constitución —el objetivo, las capas, la calificación automática, el
cruce multilingüe, el archivo de correcciones y las prohibiciones— es interna de
la Fundación y rige sobre cualquier decisión técnica de este repositorio.

---

© Fundación Sherman Kent
