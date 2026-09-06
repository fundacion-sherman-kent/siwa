# SIWA

**Registro de situación de América Latina y el Caribe.**
Fundación Sherman Kent · Oficina de Generación de Inteligencia.

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

## Qué es y qué no es

Este registro **no emite juicios**. Publica hechos calificados. El análisis, con
su confianza y su probabilidad, sale por otro camino y con firma.

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

**28 fuentes en servicio.** Esta tabla no se escribe: la calcula `herramientas/sellar-portada.py` desde los archivos de datos, después de cada recolección. Un colector que no dejó dato no aparece acá.

| Colector | Fuente | Calificación | Estados | Vacíos declarados |
|---|---|:---:|---:|---:|
| `archivo` | Archivo público de la web — copias fechadas de los portales oficiales | `B-2` | 33 | 6 |
| `banco-mundial` | Banco Mundial — indicadores de desarrollo y gobernanza | `A-2` | 33 | 8 |
| `brecha` | Fundación Sherman Kent — brecha entre lo registrado y lo publicado | `B-2` | 33 | 5 |
| `bti` | Índice de Transformación Bertelsmann (BTI), edición 2024 | `B-3` | 22 | 7 |
| `ciber` | OONI, IODA y FIRST — medición técnica de red y capacidad de respuesta | `B-2` | 33 | 6 |
| `cites` | CITES — base de datos de comercio de especies protegidas (secretaría CITES / UNEP-WCMC) | `A-3` | 33 | 8 |
| `cobertura` | Padrón de medios de la Fundación Sherman Kent | `F-3` | — | 11 |
| `comercio` | Comtrade de Naciones Unidas — vista pública | `A-2` | 19 | 9 |
| `conflictos` | Instituto de Estudios Interculturales, Pontificia Universidad Javeriana Cali — visor de conflictos de America Latina | `B-3` | 11 | 7 |
| `consulta` | Fundación Sherman Kent — consulta dirigida a la fuente primaria | `A-2` | 33 | 6 |
| `contratacion` | Registro de publicadores de contrataciones abiertas | `B-2` | 33 | 5 |
| `copernicus` | Copernicus — catálogo de observación de la Tierra de la Unión Europea | `A-2` | 33 | 6 |
| `desplazamiento-serie` | ACNUR — Refugee Data Finder | `A-2` | 33 | 7 |
| `desplazamiento` | ACNUR — Refugee Data Finder | `A-2` | 33 | 7 |
| `focos` | NASA FIRMS — focos de calor detectados por satélite | `A-2` | 33 | 6 |
| `fundacion` | Fundación Sherman Kent — canal institucional | `A-1` | — | 4 |
| `memoria` | Fundación Sherman Kent — bitácora de observación de SIWA | `A-2` | 33 | 5 |
| `oficiales` | Catálogos oficiales de datos abiertos de los Estados del padrón | `A-2` | 7 | 6 |
| `onu-ods` | Naciones Unidas — base global de indicadores de los ODS | `A-2` | 33 | 7 |
| `opacidad` | Fundación Sherman Kent — Índice de Opacidad, edición cero | `A-3` | 33 | 8 |
| `owd` | V-Dem, Base Global de Terrorismo y UCDP, vía Our World in Data | `B-2` | 33 | 9 |
| `prensa_libre` | Reporteros Sin Fronteras — clasificación mundial de la libertad de prensa | `B-3` | 33 | 5 |
| `ransomware` | ransomware.live — recopilación de sitios de extorsión informática | `D-4` | 31 | 6 |
| `reciente_oficial` | Catalogos oficiales de los Estados — lo mas reciente publicado | `A-2` | 33 | 5 |
| `redes` | Mastodon — instancias mastodon.social, mstdn.social, masto.ai, mas.to | `F-4` | 33 | 7 |
| `sanciones` | OpenSanctions — registros de sanciones y personas expuestas | `B-2` | 33 | 5 |
| `sondeo` | Fundación Sherman Kent — banco de pruebas de fuentes candidatas | `A-1` | — | 5 |
| `telegram` | Canales públicos de Telegram, vista sin cuenta | `F-4` | — | 8 |

La calificación es la del Almirantazgo: la letra mide **de quién viene** y el número, **qué tan verificado está lo que dice**. Ninguna fuente única puede calificar `1`; la circunstancia viaja declarada dentro de cada archivo.

<!-- fuentes:fin -->

## Doctrina

La carta de constitución —capas, calificación automática, cruce multilingüe,
archivo de correcciones y prohibiciones— es interna de la Fundación y rige sobre
cualquier decisión técnica de este repositorio.

---

© Fundación Sherman Kent
