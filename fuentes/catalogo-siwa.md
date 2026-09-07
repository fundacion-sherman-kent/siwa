# Catálogo de fuentes y herramientas — sondeo del 2 de septiembre de 2026

Registro de lo que se salió a buscar para SIWA, con **el resultado de la prueba**,
no con la reputación de la fuente. Cada línea de este catálogo se apoya en una
consulta efectiva: código de respuesta, tipo de contenido, tamaño y —cuando
correspondía— cobertura contada contra el padrón de los 33 Estados.

**Las rechazadas quedan acá con su motivo.** Un catálogo que solo guarda lo que
entró obliga a volver a probar lo mismo dentro de seis meses.

---

## 0 · Advertencia de método, por tres errores de esta misma jornada

En este sondeo **el instrumento falló antes que la fuente, tres veces**:

1. `curl` escribía en `/tmp`, que no existe en este intérprete. Devolvía `000`
   y dejaba leer el archivo de la sonda anterior: **ocho fuentes midieron mal**,
   y dos de ellas parecían responder cuando ni siquiera se las había consultado.
2. El extractor de datos de GitHub buscaba `"stargazers_count":[0-9]` y el
   servicio responde con un espacio después de los dos puntos. Siete
   repositorios figuraron sin estrellas, sin licencia y sin fecha: parecía que
   el servicio estaba caído y estaba mal escrita la expresión.
3. Una consulta compuesta fue rechazada por el intérprete y quedó **sin medir**,
   no fallida. No es lo mismo.

Regla que se desprende y que rige el catálogo: **antes de anotar que una fuente
no responde, hay que probar el instrumento contra una fuente que sí responde.**
Ninguna línea de abajo se escribió sin ese control.

---

## 1 · Entran — probadas, gratuitas, sin credencial

| Fuente | Prueba | Qué aporta | Materia |
|---|---|---|---|
| **OONI** `api.ooni.io` | 200 · JSON · 62.222.952 mediciones en base | Bloqueo y censura de red medidos **por país y por día**, con recuento de anomalías | Desinformación · Ciberseguridad |
| **IODA** (Georgia Tech) | 200 · JSON · 327 KB por país | Cortes de conectividad de un Estado, en crudo y por franja horaria | Ciberseguridad |
| **GDACS** | 200 · JSON · 28 KB | Alertas de desastre con episodio y magnitud, del día | Capa de hoy |
| **Contrataciones abiertas (OCP)** | 200 · JSON · 768 KB | 43 publicadores en ALC, **15 de nuestros 33 Estados** | Contratación pública |
| **FIRST.org** | 200 · JSON | Padrón de equipos de respuesta a incidentes por Estado | Ciberseguridad |
| **CEPALSTAT** `/thematic-tree` | 200 · JSON · 418 KB | Árbol temático de la CEPAL: estadística **nativa de la región** | Varias |
| **GLEIF** | 200 · JSON · 961 entidades solo en Argentina | Identificador de persona jurídica, gratuito y sin credencial | Economías ilícitas |
| **adsb.lol** | 200 · JSON · 92 KB en vivo | Aeronaves militares en vuelo, **sin credencial** | Capa de hoy · Defensa |
| **World Prison Brief** | 200 · HTML · 653 KB | Población carcelaria comparable | Seguridad |
| **OpenSanctions** `/catalog` | 200 · JSON · 1,7 MB | Catálogo de listas de sanciones y personas expuestas | Economías ilícitas |

### Lo que el hallazgo de contratación pública dice de más

De los 33 Estados, **18 no tienen un solo publicador** en el registro de
contrataciones abiertas: Antigua y Barbuda, Bahamas, Barbados, Belice, Cuba,
Dominica, El Salvador, Granada, Guyana, Haití, Jamaica, Nicaragua, San Cristóbal
y Nieves, San Vicente y las Granadinas, Santa Lucía, Surinam, Trinidad y Tobago
y Venezuela.

**La ausencia es el dato.** Esa lista no es un vacío de nuestro registro: es una
medición de opacidad en compras del Estado, y entra al Índice de Opacidad como
materia propia. Se aplica la regla asimétrica ya vigente: la presencia se
acredita con una fuente, la ausencia exige agotar los cuatro pasos antes de
declararse.

---

## 2 · No entran, y por qué

| Descartada | Prueba | Motivo |
|---|---|---|
| **ReliefWeb** | 403 · «You are not using an approved appname» | Exige nombre de aplicación autorizado. **Se pide y se reintenta**: no está descartada, está trabada |
| **GDELT** | Sin conexión (`ECONNREFUSED 104.197.47.124`) por dos rutas de red distintas | La fuente no responde, no es nuestro instrumento. Se reintenta: sería la mejor pieza de la capa de hoy |
| **CEPALSTAT** `/indicator/{id}/data` | 500 · Internal Server Error | El árbol temático responde; **la descarga del dato, no**. Entra el catálogo, no la serie |
| **IOM DTM** | 404 en tres rutas | No se halló el camino público. Queda como pendiente, no como inexistente |
| **OPS / OPS datos abiertos** | 404 | La ruta CKAN publicada no responde |
| **UNODC** `dataunodc.un.org/api` | 200 pero **HTML**, no datos | No hay interfaz de consulta abierta en esa dirección |
| **Transparency International** | 200 · HTML | Sin interfaz de consulta: exige raspado de página. Posible, pero frágil |
| **RSF** | 404 en la ruta en español | A reintentar por la ruta en francés |

---

## 3 · Las herramientas OSINT que llegaron por la Dirección

Se midieron una por una. **Ninguna es una fuente de datos**: son interfaces para
un analista. Es una distinción que conviene sostener, porque SIWA no necesita
más tableros, necesita más series.

| Repositorio | Estrellas | Último empuje | Licencia | Juicio |
|---|---|---|---|---|
| `dev-lu/osint_toolkit` | 938 | 2026-04-28 | **AGPL-3.0** | Herramienta de analista de ciberseguridad. **La licencia obliga**: incorporarla a un servicio en red forzaría a publicar el nuestro bajo AGPL |
| `NoblerWorks-HQ/IRONSIGHT` | 629 | 2026-08-31 | MIT | Vivo y activo. **Lo aprovechable no es el código sino su lista de fuentes** |
| `cipher387/osintmap` | 234 | 2024-02-06 | **sin licencia** | 614 servicios por país: registros de comercio, catastros. Sin licencia declarada significa *todos los derechos reservados*: **sirve de pista, no se puede copiar** |
| `azurejoga/osint-explorer` | 37 | 2026-06-15 | MIT | Directorio de enlaces |
| `doctorfree/osint` | 18 | 2024-02-23 | MIT | Detenido hace dos años |
| `BreaGG/OSINT-MONITOR` | 4 | 2026-01-15 | MIT | Sin adopción. El README no declara una sola fuente |
| `giriaryan694-a11y/ary.osint` | 2 | 2026-07-06 | MIT | Sin adopción |

**De IRONSIGHT se extrajo lo que valía:** declara 17 dominios de fuente. Trece no
sirven acá (dos son sistemas de alerta de Israel y Ucrania, el resto son mapas
base y redes sociales). **Uno vale y ya fue probado: `adsb.lol`**, seguimiento de
aeronaves militares en vivo y sin credencial. FIRMS de la NASA ya lo teníamos.

### Las dos páginas comerciales

- **CrowdStrike, Informe Global de Amenazas 2026** — responde 200, pero es una
  página de captación con formulario. Es **un informe, no una fuente**: no se
  puede recolectar, su licencia no permite redistribuir, y proviene de un
  proveedor cuyo negocio crece cuando la amenaza se percibe mayor. Puede citarse
  en un producto de la Fundación **declarando ese interés**; no entra a SIWA.
- **WSO2, plataforma de integración de eventos** — no es una fuente ni una
  herramienta de análisis: es un bus de integración empresarial. SIWA corre con
  biblioteca estándar de Python y tareas programadas, **a costo cero**.
  Incorporarlo contradice lo único que hace sostenible al registro. No.

---

## 4 · Lo que aportan los tres documentos

Los tres coinciden en algo que SIWA ya practica sin haberlo escrito, y en algo
que no hace.

**Lo que ya se practica.** Balbo ordena el ciclo con una hipótesis previa a la
búsqueda; el ejercicio de Infocenter enseña a restar ruido con términos
negativos y a acotar el dominio. El colector de publicación oficial hace
exactamente eso: acepta un conjunto si el título nombra el hecho delictivo y lo
descarta si nombra una nómina o un presupuesto. La técnica ya está en el código.

**Lo que no se hace, y es la incorporación que valen los tres documentos.** SIWA
publica el dato pero **no le entrega al lector la manera de ir a buscar el
siguiente**. Los operadores que enseñan Emezeta e Infocenter —`site:`,
`filetype:`, `intitle:`, rango de años, exclusión— combinados con los dominios
oficiales que SIWA **ya tiene cargados** de los 33 Estados, permiten armar la
consulta exacta contra la fuente primaria de cada país, sin que el lector tenga
que saber sintaxis.

Eso es una **caja de consulta dirigida**, y es barata: no necesita colector,
ni credencial, ni recolección. Usa lo que ya está en el registro.

Balbo agrega un segundo aporte que queda anotado y no ejecutado: el seguimiento
por canales de sindicación con alertas booleanas. SIWA ya trae prensa por ese
camino; lo que falta es que la consulta booleana sea **declarada y visible**, no
interna, para que el lector sepa qué se buscó y qué no.

---

## 5 · Gestiones que quedan abiertas

- Pedir nombre de aplicación autorizado a **ReliefWeb**.
- Reintentar **GDELT** hasta que responda.
- Buscar la ruta pública viva de **IOM DTM** y de **OPS**.
- Escribir a **CEPALSTAT** por el error 500 en la descarga de indicadores: el
  catálogo responde y la serie no, y es la única fuente estadística de este
  sondeo que es nativa de la región.

---

# Segundo sondeo — 3 de septiembre de 2026

Nueve enlaces aportados por la Dirección. **Cuatro son proveedores comerciales y
uno es una nota de marketing.** Conviene sostener la distinción que ordena todo
este catálogo: SIWA necesita **fuentes** —series con cobertura, licencia y
dirección estable—; la mesa analítica puede necesitar **herramientas**, que es
otra decisión, otro presupuesto y otro expediente.

## 1 · Entra

### Copernicus Data Space Ecosystem
`catalogue.dataspace.copernicus.eu`

| Prueba | Resultado |
|---|---|
| Catálogo STAC | **200 · JSON · 59 KB** · sin credencial |
| Catálogo OData | **200 · JSON** · sin credencial |

El catálogo es abierto; **la descarga de la imagen exige registro**. Eso no lo
descarta: habilita la misma arquitectura que ya usa el colector de publicación
oficial —**se publica que la imagen existe, de cuándo es y dónde está**, y el
enlace lleva al original—. Es material para minería ilegal, deforestación,
puertos y pasos fronterizos, que son cuatro materias donde hoy no hay serie.

**Advertencia que va con la fuente:** una imagen satelital **no es un hecho
acreditado**. Prueba que había algo el día que pasó el satélite; no prueba qué
era ni de quién. Entra como material de recolección, nunca como cifra.

### OpenSanctions — con una condición que la Fundación tiene que decidir
Ya estaba probada (200 · JSON · 1,7 MB). Lo que faltaba era la licencia, y
**importa**: es **Creative Commons Atribución–NoComercial 4.0**. La descarga
masiva es libre y gratuita.

SIWA es público y gratuito, de modo que **para SIWA la licencia alcanza**. Pero
SIWA **alimenta los productos de la Fundación**, y los productos reservados y a
pedido de cliente se cobran: ese uso **es comercial y esta licencia no lo
cubre**. Antes de que un dato de OpenSanctions viaje a un producto pago hay que
tomar la licencia comercial o dejarlo afuera. **Es una decisión de la Dirección,
no del colector**, y queda anotada acá para que no se resuelva por omisión.

## 2 · Trabadas, no descartadas

### GDELT — la mejor pieza posible, y hoy no se puede construir encima
| Prueba | Resultado |
|---|---|
| Consulta simple, primera hora | **200 · JSON con artículos** |
| 8 intentos seguidos con `curl` | **0 de 8** |
| 6 intentos con `urllib` (la biblioteca de los colectores) | **0 de 6**, agotan el tiempo de espera |
| Repetición de la consulta que sí había andado | **falla también** |

Devuelve exactamente lo que haría falta —noticias del día, multilingües,
acotables por país y por lengua, sin credencial— pero **respondió 2 de unas 20
consultas en una misma jornada**, y la que funcionó hace media hora ya no
funciona. No es formato de consulta: es intermitencia del servicio.

**No se construye un colector sobre esto todavía.** El registro toleraría la
falla —cada colector declara la suya y el dato anterior queda intacto—, pero una
capa de hoy que aparece dos de cada veinte veces no es una capa de hoy. Se mide
durante varios días y se decide con el número, no con la expectativa.

### OCCRP Aleph — **vale la gestión**
`401 · "You are not authorized to do this"` en las dos rutas probadas. Exige
credencial, y **la da gratis a periodistas e investigadores**. Es un archivo de
documentos filtrados y registros societarios con presencia real en la región.
De todo este sondeo, **es la gestión que más rinde por el trabajo que cuesta**.

## 3 · No entran

| Herramienta | Prueba | Motivo |
|---|---|---|
| **Shodan** | 403 de Cloudflare, y exige clave | El nivel gratuito no admite consulta sostenida. Además busca **dispositivos expuestos**: usarlo sobre infraestructura de terceros roza el límite de `doctrina/limites.md`, que manda reconocimiento **estrictamente pasivo** |
| **Sentinel Hub** | La página de precios redirige a Planet | Pasó a un proveedor comercial. **Copernicus da lo mismo gratis** |
| **Maltego** | 200 | Gratuito con **200 consultas por mes** (1.000 con correo institucional); de ahí, **3.000 a 7.500 euros al año**. Es una aplicación de escritorio para analizar vínculos, **no una fuente**: no puede alimentar un registro automático. Puede servirle a la mesa analítica en un caso concreto, y esa es otra decisión |
| **Intel471** | 200 | Proveedor comercial cerrado de inteligencia de amenazas. Sin acceso, sin precio público, sin licencia de redistribución |
| **ShadowDragon** | 200 | El enlace es **una nota explicativa de qué es OSINT**, publicada por un proveedor para captar clientes. No es fuente ni herramienta: es material de difusión |

## 4 · Lo que este segundo sondeo deja para hacer

1. **Decidir la licencia de OpenSanctions** antes de que su dato entre a un
   producto que se cobra. Es lo único de esta lista que puede generar un
   problema si se resuelve por descuido.
2. **Pedir credencial a OCCRP Aleph.** Gratuita, y abre un archivo que ninguna
   de las otras fuentes cubre.
3. **Medir GDELT durante una semana** y decidir con la cifra de disponibilidad.
4. **Escribir el colector de catálogo de Copernicus**, con la advertencia de que
   la imagen no acredita el hecho.

---

# Tercer tramo — 3 de septiembre de 2026 · lo que se construyó

De todo lo probado en los dos sondeos anteriores, esto es lo que dejó de ser
candidato y pasó a ser colector.

| Colector | Fuente | Qué mide | Cadencia |
|---|---|---|---|
| `contratacion` | Registro de contrataciones abiertas | Qué publica cada Estado de sus compras | diaria |
| `ciber` | OONI, IODA y FIRST | Anomalías de red, cortes de conectividad y equipos de respuesta | **cada hora** |
| `archivo` | Archivo público de la web | **Lo que dejó de publicarse**, con fecha | diaria |

## Lo que apareció al construirlos

**Contratación pública.** 15 de los 33 Estados publican en formato comparable y
11 tienen serie vigente. Paraguay actualiza **por hora**; Uruguay y Chile, en
tiempo real. Y 18 Estados no tienen un solo publicador —Venezuela, Cuba,
Nicaragua y Haití entre ellos—, que es la medición de opacidad en compras.

**Ciberseguridad.** 27 de 33 Estados con medición en la ventana de treinta días.
Venezuela tiene **13,06 % de anomalías** cuando el resto ronda el 2 %, diez
cortes de conectividad y **ningún equipo de respuesta declarado** — y cero
bloqueos confirmados, que es exactamente por qué la distinción entre *anomalía* y
*bloqueo* no es un tecnicismo. México, en cambio, registra 939 bloqueos
confirmados.

**El archivo.** Una sola retirada confirmada en los 29 Estados mirados:
**Venezuela — Instituto Nacional de Estadística**, visto vivo por última vez en
2024 y sin responder hoy, con 228 copias fechadas que cualquiera puede revisar.
Nicaragua y Jamaica tienen sitios que hoy no responden pero que el archivo vio
vivos este año: **no se los declara retirados**, y esa distinción es el colector.

De paso, el padrón de sitios oficiales verificados pasó de 13 Estados a **29**.

## Lo que sigue abierto

1. **Licencia de OpenSanctions** — decisión de la Dirección, no técnica.
2. **Credencial de OCCRP Aleph** — gratuita, y abre lo que ninguna otra cubre.
3. **Credencial de ACLED** — es el reemplazo declarado de las dos series de
   terrorismo, detenidas en 2021.
4. **Medir GDELT una semana** y decidir con la cifra de disponibilidad.
5. **Copernicus** — catálogo probado, colector sin escribir.
6. **Los 4 Estados sin sitio verificado** y las cuatro materias que siguen sin
   colector: violencia organizada, economías ilícitas, contrabando y
   desinformación.

---

# ACLED — no entra, y el motivo no es el que parecía

Se gestionó la cuenta (gratuita, ya obtenida). **No se conecta a SIWA**, por dos
razones que aparecieron al leer los términos, no al probar la interfaz.

**1 · La licencia excluye exactamente lo que SIWA es.** Los términos exigen que
todo lo publicado afuera sea *transformativo, de modo que no se pueda
reconstruir el contenido original*, y aclaran que **no basta** con que el
contenido sea «suplementado, adjuntado, extractado, reorganizado **o puesto a
disposición a través del propio tablero del licenciatario**». SIWA es un tablero
público que muestra la cifra por Estado: es el caso excluido con todas las
letras. No es zona gris.

**2 · No hay clave: hay contraseña.** ACLED autentica con correo y contraseña
—testigo de 24 horas, renovación de 14 días—, de modo que automatizarlo exigiría
guardar la contraseña personal en el repositorio. Y SIWA hoy **no usa ni una
sola credencial**: cero secretos en el robot, cero variables de entorno en los 20
colectores. ACLED sería la primera excepción, y con lo peor de las dos formas.

**Para qué sí sirve la cuenta:** consulta de la mesa analítica durante un caso, y
producto **gratuito** de la Fundación que *analice* el fenómeno en lugar de
republicar la tabla. En un producto que se cobra tampoco entra: ahí se suma el
problema de uso comercial.

**UCDP, el reemplazo natural, también pide credencial ahora** (`401 · API token
required`). La diferencia importa: su licencia es de atribución y **sí permite
redistribuir**, y lo que pide es un testigo revocable, no una contraseña
personal. Queda por averiguar si es gratuito.

## Lo que se hizo en su lugar

Las dos series de terrorismo **siguen declaradas como detenidas** —es lo
honesto— y ahora **el aviso de serie detenida trae la señal de prensa**: cuántas
notas se publicaron en las últimas 48 horas sobre esa materia, con titular, medio,
país, fecha y enlace al original.

Con el origen declarado en la primera línea: **es cobertura de prensa, no
estadística.** Cuenta notas publicadas, no hechos ocurridos —un Estado con prensa
libre aparece con más notas que uno donde no se puede publicar—, no reemplaza la
serie ni se suma a ella, y arrastra la cautela del tema. La de terrorismo dice
que la palabra es una calificación disputada y que varios Estados llaman
terrorista a la protesta social; el primer titular que apareció al probarlo era
un decreto sobre «terrorismo medioambiental», que es precisamente el caso.

---

# OpenSanctions entra — decisión de la Dirección, 3 de septiembre de 2026

**Resuelto:** el dato entra a SIWA, que es libre y gratuito, y **no viaja a
ningún producto que la Fundación cobre**. No se toma licencia comercial.

La restricción **no vive en la cabeza de nadie**: viaja pegada al dato. El
colector la declara, el archivo la lleva y el panel de fuentes la muestra.

## Cómo entra, y por qué no por donde parecía

Los archivos masivos son **inviables para un robot gratuito**: 2,5 GB las
entidades, 455 MB el resumen. La vía es la **estadística por país**, 87 KB, que
la fuente publica en cada entrega.

Con un cuidado de método: **la dirección de esa estadística lleva la versión
adentro** y cambia con cada publicación. El colector lee el índice y sigue el
puntero, en lugar de fijar una ruta que se rompe sola.

## La trampa, que decide cómo se publica

La lista de la región la encabeza **Brasil con 132.652 registros**. Venezuela
está **novena, con 1.406**; Nicaragua, decimonovena.

Leerlo como «más listados, peor» llevaría a concluir que Brasil está noventa
veces peor que Venezuela. **Brasil aparece primero porque publica mejor quiénes
son sus funcionarios.** La cifra se mueve por quién sanciona a quién, por cuán
completo es el registro público de cada Estado y por el tamaño del país — tres
cosas ajenas a la conducta del Estado medido.

Por eso entra **como hecho y nunca como orden**, con la misma arquitectura que
Defensa, la medición de red y la contratación pública. Y se declara además que
**persona expuesta no es persona sospechada**: un ministro figura por ser
ministro.

---

# Gestiones — estado al 3 de septiembre de 2026

| Gestión | Estado | Qué falta |
|---|---|---|
| **OpenSanctions** | **Resuelta.** Entra a SIWA; no viaja a producto pago | Nada. La restricción viaja pegada al dato |
| **ACLED** | Credencial cargada por la Dirección | Correr el robot a mano y ver el desenlace |
| **Aleph (OCCRP)** | **Pedido enviado.** Acuse automático el 3 de septiembre: *«our team will be reviewing submissions in the coming weeks»* | Esperar. Es revisión por tandas, no individual |
| **GDELT** | Medición automatizada en curso | Una semana de corridas y se decide con la cifra |

**Ninguna bloquea el registro.** Las cuatro son mejoras; SIWA funciona sin las
cuatro y lo declara cuando falta alguna.

---

# Yale — no entra a SIWA, pero sirve para otra línea

Tres direcciones aportadas por la Dirección el 3 de septiembre de 2026.

| Dirección | Qué es | Prueba |
|---|---|---|
| `geospatial.yale.edu` | **Centro de servicios**, no editor de datos | 200 · HTML |
| `/request-services` | Pedido de consultoría | — |
| Mapa de islas de calor | **Sí es un conjunto real**: 10.000+ aglomeraciones urbanas | Servidor viejo muerto (`000`); vive en NASA Earthdata, 200 |

**El instrumento se validó** antes de anotar el `000`: una fuente de control
respondió 200 en la misma consulta, de modo que el servidor viejo está caído de
verdad.

## Por qué no entra

**1 · Llega detenido.** La serie va de 2003 a **2018**. Entraría el primer día
con ocho años de rezago, y el propio registro lo declararía como serie detenida
—la maquinaria que se construyó esta misma semana—. Sumar un indicador que nace
detenido es sumar trabajo, no información.

**2 · No es de ninguna de las cuatro materias.** Islas de calor urbanas es
clima urbano. Los ejes son seguridad, defensa, gobernanza y desarrollo, y las
seis materias tampoco lo cubren. Meterlo forzaría la arquitectura.

**3 · Rompe la regla de cero credenciales.** Se obtiene por Google Earth Engine
—que exige cuenta y plataforma entera— o por NASA Earthdata, que exige registro.
Todo eso por una serie congelada en 2018.

La licencia, en cambio, es buena: **abierta y sin restricción**. El problema no
es el permiso.

## Para qué sí sirve

**Para la línea EERT** —Evaluación Estratégica de Riesgo Territorial, que es
municipal—. Ahí una medición de isla de calor de la ciudad evaluada es
pertinente, el rezago pesa menos porque describe una condición estructural, y la
descarga se hace una vez a mano en vez de todas las noches.

No es una fuente de SIWA: es material de un producto.

---

# ACLED — resuelto: no es un rechazo, es un embargo de doce meses

La cuenta **funciona**. La consulta **es correcta**. Lo que la cuenta no tiene es
acceso a datos recientes, y la fuente lo declara ella misma:

```
date_recency: 12 Months old · hasta 2025-09-03
```

**Solo entrega datos con más de un año de antigüedad.** Una ventana de treinta
días cae entera adentro del embargo y devuelve cero **con razón**.

## Por qué eso impide la brecha, y no es un detalle

Medir «lo que ocurrió y el Estado no publicó» exige que **las dos observaciones
sean del mismo momento**. Cruzar sucesos de hace un año contra lo que el Estado
publica hoy sería una comparación falsa — la misma clase de error que el
registro ya corrigió en el compuesto con la ventana de comparabilidad.

Así que **la brecha no se calcula**, y el sitio lo dice con esas palabras.

## Hay un camino, y es el tiempo

La bitácora propia empezó el **1 de septiembre de 2026**. Dentro de un año el
registro va a tener su propia memoria de qué publicó cada Estado **en las fechas
que la fuente sí deja ver**, y entonces las dos observaciones vuelven a ser del
mismo momento.

**La memoria que se construyó el primer día del plan es lo que hace posible esto
más adelante.** No estaba previsto así, pero es el resultado.

El colector queda construido y a la espera: el día que la cuenta vea datos
recientes, funciona sin tocar una línea.

---

# CITES entra — 3 de septiembre de 2026

La descarga completa de la base de comercio de especies protegidas pesa
**261 MB**, sin credencial pero imposible de bajar todas las noches. Adivinar
rutas de consulta dio tres 404 seguidos, que es lo que pasa cuando se adivina.

Se abrió el sitio, se apretó su propio botón de búsqueda y **se leyó qué
consulta hace él**. La respuesta era mejor que la buscada:

```
GET https://trade.cites.org/en/cites_trade/exports/download.json?filters[...]
    → {"total": 6886, "csv_limit": 1000000, "web_limit": 50000}
```

Devuelve **el recuento sin descargar los asientos**. La consulta que el sitio
usa para avisarle al usuario el peso de su descarga es, acá, todo el dato.

## Lo que se obtuvo

| | |
|---|---|
| Cobertura | **33 de 33 Estados** — la primera fuente del registro que alcanza el padrón entero |
| Ventana | 2020–2024, cinco años |
| Volumen | 291.463 asientos en la región; 4.078 con origen declarado en decomiso |
| Rezago | Año y medio, y es **del tratado**: los informes anuales vencen el 31 de octubre del año siguiente |
| Credencial | Ninguna |

## Lo que NO se obtuvo, y es lo más importante

**Esta base registra comercio legal.** Cada asiento nace de un permiso o de un
informe que una Parte presentó. El tráfico ilegal no tiene permiso y no entra.
**La materia de contrabando sigue sin fuente propia**, y el sitio lo dice con
esas palabras en vez de dar por cubierto lo que no lo está.

El código de origen `I` —«confiscaciones y decomisos»— se le acerca, pero marca
**especímenes cuyo origen declarado es una incautación**, y el asiento aparece
cuando ese espécimen se mueve después. Más decomiso puede ser más control, más
delito o más movimiento posterior de lo incautado: tres explicaciones, y la
fuente no elige.

Tampoco se puede saber **quién informó**: la consulta no distingue exportador de
importador. Por eso el registro dice «no hay asientos después de tal año» y no
dice «el Estado dejó de informar».

## Dos trampas que costaron dos guardas

**Primera: la fuente ignora en silencio los parámetros que no conoce.** Se probó
mandándole cuatro nombres de filtro inventados: los cuatro devolvieron el total
sin filtrar, sin un solo error. Si mañana renombran el filtro de origen, el
registro publicaría **«todo es decomiso» en los 33 Estados** sin enterarse. El
colector no corre sin comprobar que en Brasil el recuento filtrado sea
**estrictamente menor** que el total.

**Segunda: una proporción sobre tres asientos no es una proporción.** Ordenada
cruda, Granada quedaba **segunda de la región** con 4 asientos sobre 6 y Santa
Lucía tercera con 1 sobre 3, por delante de Bahamas, que tiene 151 sobre 589.
Se fijó un mínimo de 100 asientos: por debajo, el número se publica igual
—esconderlo sería peor— pero **marcado como no comparable**.

## Lo que quedó a la vista una vez ordenado bien

| Estado | Origen en decomiso | Sobre |
|---|---:|---:|
| **Haití** | **98,97 %** | 385 de 389 |
| Bahamas | 25,64 % | 151 de 589 |
| Cuba | 10,06 % | 120 de 1.193 |
| El Salvador | 4,20 % | 87 de 2.073 |
| México | 3,86 % | 2.517 de 65.283 |

Haití no tiene prácticamente comercio legal registrado de especies protegidas:
**lo único que se anota es lo incautado**. El registro publica el hecho y no la
explicación, porque no la tiene.

Y tres Estados sin asientos recientes: **Santa Lucía y Dominica hasta 2022,
Granada hasta 2023**.

---

# Sondeo de cobertura oficial y de bienes culturales — 6 de septiembre de 2026

## 1 · Brasil: el portal central exige identidad brasileña

`dados.gov.br` responde **401** sin clave, y la clave sale de «Minha Conta» tras
entrar con cuenta **gov.br**. El propio portal lo dice: *«Para acessar o novo
Portal de Dados Abertos é preciso ter cadastro no gov.br»*. Para un extranjero
sin CPF eso es un muro, no un trámite.

**La vuelta, probada:** el **IBGE** —el instituto de estadística— sirve sin
credencial en `servicodados.ibge.gov.br`. Devolvía lo que parecía HTML porque
**viene comprimido**, no porque fallara. La API está documentada y es abierta.

El esquema de la clave, para cuando haga falta: encabezado
`chave-api-dados-abertos`, endpoint `GET /dados/api/publico/conjuntos-dados`.

## 2 · Perú: sirve, con una salvedad

`package_list` devuelve **4.684 conjuntos de datos**. Pero `package_search` da
404: ese portal expone unos endpoints de CKAN y no otros. Se puede sumar, leyendo
por la puerta que sí abre.

## 3 · Auditoría de organismos oficiales: 47 de 60 responden

Se probaron tres familias por Estado —**estadística**, **transparencia** y
**acceso a la información**—, 60 organismos en los 33 Estados.

**Sólo tres Estados no tienen ningún organismo que responda:**

| Estado | Qué pasa |
|---|---|
| **Costa Rica** | INEC devuelve 403 y el portal de datos no responde. Es un país de alta transparencia: esto es **bloqueo a máquinas**, no opacidad |
| **Cuba** | ONEI devuelve HTTP 500: el sitio está fallando |
| **Venezuela** | INE no responde, coherente con lo que ya halló el colector de archivo |

**Y el hallazgo de mayor rendimiento:** los **doce Estados chicos del Caribe**
tienen oficina de estadística que responde —Belice, Guyana, Surinam, Antigua,
Bahamas, Barbados, Dominica, Granada, Jamaica, San Cristóbal, Santa Lucía, San
Vicente, Trinidad— y SIWA no tiene **ninguna** fuente oficial de ellos.

**Paraguay era un falso vacío:** responde en las tres familias —estadística,
datos abiertos y acceso a la información—.

### Una categoría nueva para el Índice de Opacidad

Bolivia, Ecuador, Guatemala, Honduras, Costa Rica y República Dominicana
devuelven **403 incluso identificándose como navegador**. Publican para
personas y **le cierran la puerta a las máquinas**. Eso no es lo mismo que no
publicar, y merece su propio estado: **«publica, pero no deja recolectar»**.

## 4 · Bienes culturales: se buscó en cinco idiomas y no hay volúmenes

Rastreado en español, inglés, francés, alemán, italiano y portugués: UNESCO,
UNODC (SHERLOC), UNIDROIT, ICOM, Organización Mundial de Aduanas, INTERPOL,
Carabinieri TPC, Kulturgutschutz Deutschland, POP del Ministerio de Cultura
francés, IBRAM, ARCA y Trafficking Culture.

**No existe fuente libre con volúmenes de tráfico por país.** INTERPOL exige
convenio; la Aduana publica agregados regionales en PDF; SHERLOC da
jurisprudencia y legislación, no cantidades.

**Lo que sí hay, y es comparable en los 33:** el estado de ratificación de los
convenios de **1970 (UNESCO)** y **1995 (UNIDROIT)** —tablas legibles, 124
filas—. No mide tráfico: mide **qué está tipificado y qué no**, que es una
pregunta distinta y contestable.

## 5 · Instituto Igarapé

Cuatro plataformas de alcance regional: **Monitor de Homicidios** (mundial),
**Monitor de Política de Drogas en las Américas**, **Cidades Frágeis** (2.100
ciudades de más de 250.000 habitantes) y **EcoCrime Data** (acaparamiento de
tierras, tala ilegal, minería ilegal y comercio de fauna).

**El problema es técnico, no de permiso:** son aplicaciones que arman el
contenido en el navegador y sirven una cáscara de 0 a 10 KB. El robot no tiene
navegador. Habría que hallar el archivo de datos que cada una consume, o pedirlo
—y siendo la Fundación una casa de la región, pedirlo es razonable—.

---

# Igarapé: la técnica, y por qué el dato no está donde parecía

La Dirección pidió investigar la técnica y buscar los datos, «deben ser
públicos». Lo son. El problema es otro.

## Cómo sirven los datos

Sus plataformas son aplicaciones que arman todo en el navegador y traen los
datos como **archivos estáticos**, sin credencial. Se los halla mirando qué pide
la propia página —la misma técnica que abrió CITES y el índice de crimen
organizado—:

```
/resources/datasets.json                          el catálogo
/resources/data/<conjunto>/metadata/<...>.json    las columnas
/resources/data/<conjunto>/data/t20/...           los datos, en mosaicos
```

## Qué se encontró, plataforma por plataforma

| Plataforma | Estado | Datos |
|---|---|---|
| **Monitor de Homicidios** | **muerta** | cáscara de 836 bytes con sólo el medidor de visitas |
| **EcoCrime Data** | cáscara de 1,1 KB | ninguno |
| **Cidades Frágeis** | viva | 33.601 registros, 2.100 ciudades, 23 columnas… en **formato binario propietario** de su visor, y la serie **termina en 2015** |
| **urbanradar** (GitHub) | vivo | pilotos municipales de Brasil y Tanzania: no es regional |
| **armsglobe** (GitHub) | archivo abierto | **81.638 registros de comercio bilateral de armas, 31 de 33 Estados** |

## El hallazgo que cambia la decisión

El conjunto de armas trae una categoría llamada **`930330`**. Eso es un **código
arancelario de Naciones Unidas**. Igarapé no produjo ese dato: **lo derivó de UN
Comtrade**, y su copia va de **1992 a 2010**.

**SIWA ya le habla a Comtrade.** El colector de comercio consulta
`comtradeapi.un.org` para la brecha espejo. Se probó pedirle el capítulo 93
—armas y municiones— para Argentina en 2023: **102 socios comerciales con su
valor**.

> **Conclusión: no hay que importar el archivo de Igarapé.** Hay que pedirle a la
> fuente original lo mismo, trece años más nuevo, con un colector que ya existe y
> una consulta que ya funciona. Copiar la copia vieja habría sido el error.

## Lo que sí valdría pedirles

**Cidades Frágeis** es un trabajo real y su formato es el único obstáculo. Siendo
la Fundación una casa de la región, pedir el archivo de origen es razonable. Pero
conviene saber antes de pedir que **la serie termina en 2015**.

---

# SIPRI — sondeo del 6 de septiembre de 2026

## Lo primero: buena parte ya está adentro

El gasto militar que SIWA publica **viene del Banco Mundial, que lo toma de
SIPRI**. Ya está en el registro y llega a **2024**: gasto sobre el producto,
sobre el gasto del Estado, en dólares, y —lo que importa— **importación y
exportación de armamento mayor**, que es justamente lo que el capítulo aduanero
del colector de armas NO cubre.

## Qué agrega ir a la fuente directa

El archivo se descarga **sin credencial**: `SIPRI-Milex-data-1949-2025_v1.2.xlsx`,
901 KB, diez hojas.

| Agrega | Ya lo teníamos |
|---|---|
| **2025** (un año más que el Banco Mundial) | gasto sobre el producto |
| **Gasto militar por habitante** | gasto en dólares |
| Dólares constantes de 2024 | gasto sobre el gasto del Estado |
| Totales regionales | armamento mayor importado y exportado |

## La licencia, que es una condición cuantitativa

> *Fair use = non-commercial **AND** the reproduction of less than 10 per cent
> of a published data set. **Both** the above conditions must apply.*

SIWA cumple lo primero. Lo segundo se cumple **si se publica una foto reciente y
no la serie entera**: el conjunto cubre unos 170 países desde 1949, de modo que
33 Estados en un año son el 0,3 %, y una serie de cinco años, el 1,3 %. Publicar
todos los años de los 33 rondaría el 19 % y **quedaría fuera**.

## El premio mayor está en otra base, y resistió

La **base de transferencias de armas** —armamento mayor, bilateral: quién le
vendió qué a quién— es la que llenaría el hueco que el colector de armas declara.
Su interfaz no respondió a la automatización: el formulario exige selección de
una lista y no acepta texto libre. Habría que insistir con la interfaz o pedirle
a SIPRI el archivo.

## Recomendación

Ir a SIPRI directo por MILEX **rinde poco**: un año más y el gasto por habitante,
a cambio de asumir una restricción de licencia donde hoy no hay ninguna —el
Banco Mundial redistribuye con licencia abierta—. **Lo que sí vale la pena es la
base de transferencias**, que no tenemos por ningún lado.

---

# Las 33 oficinas de estadística entran — 7 de septiembre de 2026

Estaba propuesto desde el sondeo del 6 y no se había sumado. Por el método de la
casa —lo propuesto se verifica y se suma—, se verificó y se sumó.

## El problema que resolvía

SIWA tenía **9 de 33 Estados** con fuente oficial: los nueve con catálogo de
datos abiertos consultable por máquina. Los otros veinticuatro figuraban sin
ninguna, y una ficha vacía se lee como un Estado que no publica. **Publican
todos**: los 33 tienen oficina nacional de estadística. Lo que veinticuatro no
tienen es interfaz para programas, que es una afirmación distinta.

**Cobertura después: 28 de 33.**

## Tres correcciones que sólo aparecieron probando

| Estado | Lo que se creía | Lo que hay |
|---|---|---|
| **El Salvador** | sin oficina que responda | la **ONEC** responde en `onec.bcr.gob.sv`. Reemplazó a la DIGESTYC y vive dentro del Banco Central de Reserva. La dirección que se había supuesto no existe |
| **Cuba** | HTTP 500, oficina caída | la **ONEI** responde en `onei.gob.cu`. Es el prefijo `www.` el que devuelve 500. Un prefijo de más decidía lo que el registro afirmaba |
| **Bahamas** | `bahamas.gov.bs`, portal general | la oficina es el **BNSI**, en `stats.gov.bs`. El portal de gobierno no es la oficina de estadística |

Y una precisión sobre **Venezuela**: el dominio del INE no resuelve, pero los
resolutores de Google y de Cloudflare devuelven **SERVFAIL**, no «nombre
inexistente». Fallan los servidores de nombres del dominio estatal; la dirección
no está mal escrita. Se consultó fuera de esta casa antes de afirmarlo.

## Y dos fallas del instrumento, antes que de las fuentes

**La primera firma de «verificación anti-robot» buscaba la palabra «captcha» en
el cuerpo de la página.** Esa palabra aparece en cualquier formulario de
contacto: marcó como bloqueadas a seis oficinas que sirven su sitio entero,
Chile entre ellas. Un rótulo falso de bloqueo es peor que no tener rótulo. La
firma ahora exige que el viaje **termine** en un servicio de desafío o que el
título de la página sea el del desafío. Con eso queda **una sola**: Guatemala.

**Tres oficinas quedaron como «sin respuesta» y en realidad contestan**: su
certificado no valida. Uruguay y Antigua sirven contenido; Cuba falla aun sin
validar. «Certificado que no valida» tiene ahora su propio estado y no se lee
como silencio.

## Los seis estados de respuesta, que no significan lo mismo

`responde` · `certificado_invalido` · `cierra_a_maquinas` (401/403: publica para
personas) · `verificacion_anti_robot` (un 200 que miente) · `falla_el_servidor`
· `no_resuelve`. **Ninguno de los cinco últimos prueba opacidad**, y el registro
lo dice en cada ficha.

## Control

El INDEC responde. Si no responde, el que falló es el sondeo y el mapa de
silencio se declara no confiable en vez de publicarse.

---

# Bienes culturales entran — 7 de septiembre de 2026

Estaba propuesto desde el sondeo del 6 y no se había sumado.

## Lo que se pudo, y lo que no

**Entra el Convenio de UNIDROIT de 1995** sobre bienes culturales robados o
exportados ilícitamente. La tabla del depositario abre sin credencial: 65 Estados
en el mundo, **13 de los 33 del padrón**. Uruguay ratificó en julio de 2024 y el
convenio le rige desde enero de 2025, lo que confirma que la fuente está al día.

**No entra el Convenio de la UNESCO de 1970**, que es el principal. No por
licencia ni por reserva: **UNESCO interpone una verificación anti-robot**
(F5/TrafficShield) en las cuatro direcciones probadas —la página del convenio, la
vía antigua `eri/la/convention.asp`, el portal heredado y los subdominios de
datos—. El dato es público; el sitio del organismo rechaza a los programas. Queda
declarado en el registro con la dirección exacta, para que cualquiera repita la
prueba, y se gestiona por vía oficial.

Se probaron además, sin resultado para esta materia: la colección de tratados de
Naciones Unidas (el 1970 se deposita en UNESCO, no ahí), SHERLOC (da
jurisprudencia y legislación, no ratificaciones) y los subdominios de datos de
UNESCO.

## Lo que el registro dice, y lo que se cuidó de no decir

Mide **qué está tipificado**, no cuánto se trafica. Un Estado que no figura
**puede tener ley interna**: la ficha lo dice con esas palabras, porque convertir
una ausencia de ratificación en una acusación es exactamente el error que este
registro existe para no cometer.

## Dos guardas del colector

**La tabla se reconoce por su encabezado, no por su lugar.** La página trae nueve
tablas y varias son declaraciones territoriales: tomar «la primera» sin mirar qué
dice haría publicar las provincias del Canadá como Estados soberanos el día que
UNIDROIT rediseñe la página.

**Control: Perú.** Es parte desde 1998. Si no aparece en la lectura, lo que falló
es el lector y no la ratificación de nadie: no se publica.

## Sigue pendiente de gestión

**SIPRI — base de transferencias de armamento mayor.** Su interfaz no responde a
la automatización: el formulario exige selección de una lista y no acepta texto
libre. Hay que insistir con la interfaz o pedirle el archivo a SIPRI. El gasto
militar ya está en el registro por vía del Banco Mundial, que lo toma de SIPRI y
lo redistribuye con licencia abierta.

---

# Sondeo de diez direcciones propuestas — 7 de septiembre de 2026

La Dirección propuso diez direcciones. Se probaron todas. **Entran dos, una ya
estaba, cinco no sirven como fuente de datos y dos cierran la puerta.**

## Entran

**Departamento de Estado — Informe sobre la Trata de Personas.** Clasifica cada
Estado en Nivel 1, 2, 2 con lista de vigilancia, 3 o caso especial. **30 de los
33** del padrón; Dominica, Granada y San Cristóbal y Nieves **no están en el
informe** —verificado contra la lista de 186 fichas del propio informe, no
supuesto—. Haití es «caso especial» por segundo año. Obra del gobierno de los
Estados Unidos: sin restricción de licencia. Se califica **B-2**, no A: es un
Estado evaluando a otros Estados, con consecuencias legales propias, y eso lo
hace parte y no observador.

**V-Dem — «Regímenes del Mundo».** Cuatro casillas: autocracia cerrada,
autocracia electoral, democracia electoral, democracia liberal. **25 de 33**; los
ocho del Caribe chico quedan fuera del proyecto. Es la pregunta previa a todas
las del eje de gobernanza y el registro no la tenía. Va al nivel Ciudadano.

## Ya estaba

**V-Dem.** El registro publica **trece indicadores** suyos desde antes, por medio
de Our World in Data. Ir al productor directo **exige registro** y su libro de
códigos reserva los derechos; Our World in Data redistribuye con licencia
abierta. Se sigue por la puerta que está abierta.

## Cierran la puerta

**INTERPOL.** Su propia página declara el servicio público
`ws-public.interpol.int/notices/v1/red`, y el borde (Akamai) devuelve **403
Access Denied** a este llamador. Es el caso «publica y no deja recolectar». **No
se esquiva**: se declara y se gestiona la vía oficial.

**OEA.** Los tres caminos probados —Estados miembros, base de misiones
electorales y la raíz del sitio— devuelven **403 en todo el dominio**. La base de
observación electoral sería valiosa y queda como gestión.

## No son fuente de datos

**El PAcCTO (FIIAPP y Comisión Europea).** Es un programa de cooperación:
publica noticias y documentos, no series por país. Sirve como referencia
institucional y como posible contraparte, no como capa del registro.

**USA.gov y su ficha del Departamento de Estado.** Es un directorio de
organismos. La fuente útil está detrás: los informes anuales del Departamento,
que es de donde se tomó la trata de personas.

**Datosmacro (Expansión).** Republica cifras del Banco Mundial y del Fondo
Monetario que el registro **ya toma del original**. Doctrina de la casa: una
copia debe mandarte al original. Y el contenido es de un editor privado con
derechos reservados. **No entra.**

## Un hallazgo de método

`state.gov` devuelve **403 a quien no antepone «Mozilla/5.0»**. No es un desafío
anti-robot: es una convención heredada. Se la respeta **sin mentir**, con la
forma `Mozilla/5.0 (compatible; SIWA/0.1; +fundacionkent.org)`, que el estándar
prevé justamente para esto. Disfrazarse de Chrome habría funcionado igual y
habría sido una mentira innecesaria. **Dos colectores viejos —el padrón oficial
y el explorador— todavía se identifican como Chrome y convendría pasarlos a esta
forma.**

---

# UCDP entra — 7 de septiembre de 2026

Llegó la credencial que se venía gestionando. **Cierra el vacío que el registro
declaraba desde el principio**: la interfaz de UCDP devuelve 401 sin token, y las
muertes en conflicto entraban sólo por Our World in Data, con la serie detenida
donde ese intermediario la corta.

## Qué tabla, y por qué esa

De las siete que la interfaz expone se usa **`organizedviolencecy`** —país-año
sobre violencia organizada dentro de fronteras—. No es la más grande: es la
**comparable**. Una fila por Estado y año con la presencia de los tres tipos que
UCDP distingue —estatal (interna e interestatal), no estatal y unilateral—.

El conjunto georreferenciado `gedevents` tiene **417.968 filas** y obliga a
paginar. Traerlo entero para contar muertes por país gastaría cientos de las
5.000 peticiones diarias por un resultado que esta tabla ya entrega agregado.

## La advertencia que manda

**UCDP exige 25 muertes relacionadas en un año para registrar un conflicto.** Un
cero no dice «no hay violencia»: dice «no alcanzó el umbral». Buena parte de la
violencia de la región —homicidio común, extorsión, violencia intrafamiliar— no
entra acá porque no es conflicto armado organizado. La ficha lo dice arriba de
todo y la vista muestra a los Estados sin marca como **«bajo el umbral»**, nunca
como Estados en paz.

## Guardas

**Control: Colombia**, con violencia estatal registrada desde hace décadas. Si la
lectura no la encuentra, lo que falló es la lectura —la tabla, el rótulo o el
campo— y no la historia de Colombia: se detiene y no publica.

**Mínimo de 25 Estados con correspondencia de nombre.** La correspondencia se
hace por nombre porque el código numérico de UCDP es el de Gleditsch y Ward, que
no es el ISO y no se adivina. Un Estado sin correspondencia aparece declarado
como tal, no en cero.

**El 401 no se reintenta**: reintentar una credencial rechazada gasta peticiones
del tope diario sin ninguna posibilidad de éxito. El 429 —tope agotado— tampoco:
se espera a la corrida siguiente y el dato anterior queda intacto.

**Sin credencial el colector falla a propósito** en vez de publicar una tabla de
ceros. Treinta y tres Estados sin mirar no son treinta y tres Estados en paz.

## El token

Va como secreto del repositorio, con el nombre `UCDP_TOKEN`. **Es el segundo
secreto del registro**, después de la clave de NASA FIRMS. El valor lo carga la
Dirección y no se escribe en ningún archivo, registro de corrida ni mensaje de
error.

---

# Dos capas que faltaban enteras — 7 de septiembre de 2026

El registro no tenía **ninguna** capa de desastres ni de sismicidad. En esta
región eso es un hueco grande: inundación, ciclón, sequía, terremoto y erupción
condicionan la situación de un Estado tanto como la violencia o la economía.

## Desastres y emergencias — IFRC GO

El sistema operativo de la Federación Internacional de la Cruz Roja y la Media
Luna Roja. Abierto, sin credencial. **438 emergencias en cinco años, 32 de los
33 Estados** —sólo Dominica sin registro—. Tipo, fecha, gravedad operativa y
Estados alcanzados.

**La advertencia que manda:** registra las emergencias ante las que la red
responde o sobre las que informa, **no todos los desastres que ocurren**. Un
Estado con sociedad nacional grande deja más asientos que uno con sociedad
chica. **Más emergencias registradas puede significar más capacidad de
respuesta.**

### El filtro que no filtra

`countries__iso3` **se ignora en silencio**: pedirle los eventos de Colombia
devuelve los 6.065 del mundo, exactamente igual que pedirle un parámetro
inventado. Se probó con valores cuyo resultado se conoce de antemano:

| Consulta | Devuelve | Veredicto |
|---|---|---|
| sin filtro | 6.065 | — |
| `regions__in=1` (Américas) | 1.300 | **filtra** |
| `regions__in=3` (Europa) | 857 | **filtra** |
| `regions__in=99` (inexistente) | 0 | **filtra** |
| `countries__iso3=COL` | 6.065 | **NO filtra** |
| `countries__iso3=ZZZ` | 6.065 | **NO filtra** |
| `parametro_inventado=1` | 6.065 | — |

Un colector que le hubiera creído al filtro por país habría publicado los
desastres del planeta como si fueran de un solo Estado. **Se filtra por región y
el país se cruza acá**, y la comprobación de que el filtro filtra corre en cada
corrida: las Américas tienen que ser menos que el total y una región inexistente
tiene que dar cero.

## Sismicidad — Servicio Geológico de los Estados Unidos

Servicio FDSN, abierto, sin credencial. **299 sismos de magnitud 4,5 o mayor en
noventa días.**

### La decisión de diseño que se justificó sola

**195 de los 299 ocurrieron en el mar** —incluidos los dos mayores: magnitud 7,5
frente a Venezuela y 7,3 frente a México—. Un colector que asignara cada sismo a
un Estado y descartara lo que cae fuera de tierra firme **habría borrado
justamente los más grandes**, que son además los que pueden generar tsunami. El
mar es una categoría declarada, no un descarte. Y se aclara que el rótulo del
lugar nombra la **costa más cercana**, no el Estado donde ocurrió.

**No mide riesgo ni daño: mide energía liberada.** Un sismo de magnitud 6 a diez
kilómetros bajo una ciudad hace más daño que uno de 7 a doscientos kilómetros
mar adentro. **No entra a ningún índice compuesto.**

## Probadas y descartadas, con su motivo

**ReliefWeb (OCHA).** Su interfaz v1 fue dada de baja —410— y la v2 **exige un
nombre de aplicación aprobado**, que se pide por formulario. Queda como gestión.

**WFP HungerMap**, **EM-DAT** y **datos de la OPS**: no se halló dirección
pública que responda. La OPS devuelve 502.

**OMS — indicadores globales (`ghoapi`).** Abierta y funciona. Queda como
candidata: falta decidir qué indicadores de salud son comparables en los 33 sin
repetir lo que ya entra por el Banco Mundial.

---

# Percepción de corrupción entra — 7 de septiembre de 2026

El registro medía corrupción de dos maneras —control de la corrupción del Banco
Mundial y corrupción política de V-Dem— y le faltaba **la más citada del mundo**:
el Índice de Percepción de la Corrupción de Transparency International. **30 de
los 33 Estados**; quedan afuera Antigua y Barbuda, Belice y San Cristóbal y
Nieves, que no alcanzan el mínimo de fuentes independientes que el método exige.

## Lo que aporta y no teníamos

La planilla trae **ISO3** —de modo que no hay que emparejar nombres— y, sobre
todo, **el error estándar, el intervalo de confianza y la cantidad de fuentes**
de cada puntaje. Eso permite mostrar algo que casi ninguna publicación muestra:
**cuándo un puesto no significa nada.** Las Bahamas figuran 28.ª con un intervalo
de 54,8 a 75,2 construido sobre tres fuentes; la ficha lo dice con esas palabras
—«muy ancho, el puesto dice poco»— en vez de presentar el puesto como un hecho.

## La licencia fija una regla

Transparency International publica bajo **CC BY-ND 4.0**: permite reproducir y
redistribuir, **no derivar**. Por eso los valores van **tal cual**, con su
atribución, y **este índice NO entra a ningún cálculo compuesto** del registro.

## Tres medidas de lo mismo, y no se promedian

Están las tres por separado, a propósito. Se construyen distinto y a veces
ordenan distinto a los mismos Estados. **Cuando coinciden, el juicio se apoya
mejor; cuando discrepan, el analista tiene que ir a ver por qué.** Promediarlas
borraría exactamente la información útil.

---

# UCDP resuelto — 7 de septiembre de 2026

## Qué pasó

La credencial llegó y **funciona**: el colector entró, leyó y falló en **la guarda
de control** —Colombia no aparecía con violencia estatal—. La guarda hizo lo que
tenía que hacer: frenó en vez de publicar treinta y tres ceros.

Pero el diagnóstico era imposible desde acá: **la credencial vive en el
repositorio y no se ve**, así que no había forma de consultar la fuente para
averiguar qué fallaba. Antes de armar un ida y vuelta de corridas a ciegas, se
probó otra puerta.

## La puerta que estaba abierta

**El mismo conjunto se descarga como archivo, sin credencial**:
`organizedviolencecy-261-csv.zip`. Y es mejor por cuatro razones:

1. No depende de un secreto.
2. No gasta la cuota de 5.000 consultas diarias.
3. **Se puede verificar antes de publicar** —que es la razón de fondo—.
4. **Trae mucho más**: 7.132 filas desde 1989, y no sólo la presencia de
   violencia sino **las muertes con su estimación baja, mejor y alta**, y **los
   nombres de las partes en conflicto**.

Nunca se estableció por qué falló la interfaz con credencial. **No se inventa una
causa**: se cambió de puerta y se dejó constancia.

## Qué publica ahora

**32 de 33 Estados** —Antigua y Barbuda no está en el conjunto—. En 2025: dos
Estados con violencia estatal, ocho con violencia no estatal y siete con
violencia unilateral; **12.627 muertes contabilizadas en la región**, encabezadas
por México (7.904), Haití (2.448) y Colombia (986).

Las muertes van **con su rango**: quedarse con la cifra del medio escondería lo
que el propio productor declara no saber.

## Dos errores propios, corregidos

**El separador de las partes.** Se partía por coma, y los nombres de los grupos
llevan comas adentro: cortaba un nombre al medio y pegaba dos grupos en uno. Es
punto y coma.

**El corte silencioso de páginas.** La versión con credencial leía hasta un tope
y seguía como si nada si la tabla tenía más. Una lectura cortada sin aviso deja
Estados en cero, y un cero por lectura corta no se distingue de un cero real.

## El token no se descarta

Queda cargado y sirve para lo que el archivo no da: **consultas filtradas del
conjunto georreferenciado de eventos**, evento por evento, con 417.968 registros
y filtros de fecha, país y tipo de violencia. Ese es su lugar.

---

# Las tres direcciones de Brasil — 7 de septiembre de 2026

Brasil era uno de los huecos del padrón: su portal federal exige cuenta gov.br
—inalcanzable para un extranjero sin CPF— y sólo teníamos el IBGE. La Dirección
propuso tres direcciones. Se probaron todas.

## Entra

**Fórum Brasileiro de Segurança Pública.** El **Anuário Brasileiro de Segurança
Pública** se descarga directo, sin credencial: **1,4 MB, 134 hojas**, y la
primera es «Mortes violentas intencionais». Es la referencia de hecho para la
seguridad en el Brasil.

**Y se consigna lo que es: una asociación civil, no un organismo del Estado.** La
ficha lo dice con esas palabras. Se lo incluye por su calidad y su uso
establecido, no por un carácter oficial que no tiene.

**Ministerio de Justicia y Seguridad Pública.** Sus datos nacionales de seguridad
responden, pero la página arma el contenido en el navegador: queda como dirección
verificada, no como archivo recolectable.

## Cierran la puerta, y se declara con la prueba

**Central de Paneles de la CGU.** Redirige a `/signin`: **exige cuenta**. Mismo
muro que el portal federal.

**Portal da Transparência.** Este es el caso más engañoso y el más útil de
declarar: **la página lista decenas de conjuntos abiertos** —empresas
inhabilitadas, funcionarios expulsados, acuerdos de lenidad— **y se lee sin
problema, pero las descargas devuelven 403** a quien no es un navegador. Y su
interfaz de consulta exige credencial (401). **Publica para personas y cierra a
los programas.** Quien mire sólo la página concluiría que Brasil publica todo eso
en abierto; quien intente tomarlo, no puede.

## No entra

**Contas Abertas.** Es una agencia de noticias y una asociación civil de
seguimiento del gasto: publica análisis, no conjuntos de datos. No hay archivo
que recolectar.

## Y algo que estaba mal desde antes

Las **fuentes sectoriales verificadas** —el Banco Central argentino, SECOP de
Colombia, el IBGE— **estaban en el archivo de datos y la página no las
mostraba**. Direcciones verificadas una por una que ningún lector podía ver.
Ahora aparecen en la ficha de cada país, con dos cosas que importan: **si el
organismo es del Estado o de la sociedad civil**, y **la prueba de que se lo
tocó**.

---

# Lo que el robot tenía anotado — 7 de septiembre de 2026

Revisión del banco de pruebas de fuentes candidatas. **Tres de las once trabas
declaradas ya no existían.**

## CEPALSTAT entra, y la lección es dura

Figuraba como «nunca respondió», con un error 500. **La interfaz estaba sana: lo
que estaba roto era el indicador con el que se la probaba** —el 2246—. Probada
con otro, contesta perfecto.

**Probar una fuente con un solo indicador y concluir que la fuente está muerta es
el mismo error que probar un país y concluir que no publica.** Quedó escrito en el
propio archivo del banco de pruebas.

De ahí sale un colector nuevo: **pobreza por ingresos**, en los tres umbrales de
la CEPAL —3,0, 4,1 y 8,3 dólares de paridad por día—, para **27 de los 33
Estados**. Es la primera vez que el registro mide pobreza, y lo hace con **la
única fuente estadística nativa de la región**: la comisión de las Naciones
Unidas para América Latina y el Caribe, que no mira desde afuera.

### El peligro de esta capa, y cómo se resolvió

Los años **no coinciden**: Haití es de 2012 y Honduras de 2024. Ordenados por
pobreza quedan uno al lado del otro, y eso no es una comparación. **El año va en
el título de cada ficha**, y las que tienen más de cinco años quedan marcadas con
la advertencia expresa de que no se las puede comparar con las recientes.

## UCDP sale de la lista

Pedía un testigo. Se gestionó y se obtuvo —y funciona—, pero **el mismo conjunto
se descarga como archivo sin credencial**. La puerta con llave no era la única.
**Antes de gestionar un permiso conviene mirar si hay otra puerta.**

## Cuba tenía mal la dirección

Se la probaba en `www.onei.gob.cu`, que devuelve 500. **Sin el prefijo `www`
responde.** Su oficina ya está en el padrón; lo que sigue faltando es que
publique algo consultable por máquina, y así queda anotado.

## Las que siguen abiertas

Ocho candidatas, con su traba verificada de nuevo hoy: **GDELT** —intermitente,
respondió ayer y hoy devolvió 429—, **ReliefWeb** —exige nombre de aplicación
autorizado—, **OPS** —su ruta publicada no responde; la interfaz de indicadores
de la OMS sí, y queda como reemplazo posible—, **OIM DTM** —404 en todas las
rutas probadas— y los portales de **Ecuador, Guatemala, Bolivia y Costa Rica**,
que bloquean incluso a quien se identifica como navegador.

---

# Narcotráfico — 7 de septiembre de 2026

La Dirección observó que el registro no tenía datos de narcotráfico. **Los tenía,
y no se podían ver.**

## Lo que estaba pasando

El Índice Global de Crimen Organizado, que el registro recolecta desde hace
semanas, puntúa **cuatro mercados de drogas** —cocaína, heroína, cannabis y
drogas sintéticas— de 1 a 10 en los 33 Estados. Pero:

1. Los treinta y seis rótulos del índice **estaban en inglés**. Un lector de la
   región veía «Cocaine trade 9,5» y **la palabra narcotráfico no aparecía en
   ninguna parte del sitio**.
2. Las medidas se mostraban **sólo al elegir un país**. Mirando la región, nadie
   podía ver quién encabeza el mercado de cocaína.

**Un dato que no se puede encontrar es, para el lector, un dato que no existe.**

## Lo que se hizo

**Los 36 rótulos, en castellano**, con traducción literal y el nombre original al
lado en cada ficha para contrastar. Y **las cuatro definiciones de los mercados
de drogas traducidas** —sólo esas cuatro: son las que aparecen en una sección de
nivel Ciudadano, donde una definición en inglés no sirve. Las otras treinta y dos
quedan como las publica la fuente, porque traducir sin necesidad agrega una capa
de interpretación que nadie pidió.

**Sección propia en el eje Seguridad**, que en la vista regional muestra cada
mercado con los Estados que lo encabezan y el promedio del ámbito, y en la ficha
de un país sus cuatro puntajes.

Así queda a la vista lo que antes estaba enterrado: en cocaína, **Colombia 9,5;
Venezuela, Perú, México, Ecuador y Brasil, 9**.

## Lo que NO se agregó, y por qué

**Cantidades.** No hay toneladas incautadas, hectáreas cultivadas ni precios. Se
buscó en la Oficina de Naciones Unidas contra la Droga y el Delito: su **informe
mundial sale en PDF**, su portal de datos **devuelve la misma cáscara para
cualquier ruta** —arma todo en el navegador— y la dirección que su propia página
declara, `dataportal.unodc.org`, **ni siquiera resuelve**. La CICAD de la OEA
devuelve 403, como todo ese dominio.

Queda declarado en la ficha con esas palabras, y se gestiona por vía oficial.

**Y se dice qué mide y qué no:** es la evaluación de un panel de especialistas
sobre cuán extendido y estructurado está cada mercado, **no un volumen**. Dos
países con el mismo puntaje no mueven la misma cantidad. Tampoco distingue
producción de tránsito ni de consumo: mide el mercado, no el eslabón.

---

# Buscar por delito, no por rótulo — 7 de septiembre de 2026

La Dirección escribió «narcotráfico» en el buscador y no salió nada. **Dos fallas
distintas, y las dos de fondo.**

## 1 · La búsqueda exigía las tildes

Escribir «cocaina» o «narcotrafico» sin tilde no encontraba nada. **En un sitio en
castellano eso es una falla de base: nadie pone las tildes al buscar.** Ahora se
comparan las dos puntas sin ellas.

## 2 · Se podía buscar por rótulo, no por delito

Y es peor que un problema de palabras. Los **veinte mercados y actores** del
Índice Global de Crimen Organizado estaban enterrados dentro de una sola capa:
**no se los podía buscar, ni cruzar, ni poner en el mapa**, aunque el registro
tuviera el dato para los 33 Estados desde hacía semanas.

Ahora cada uno es una **materia propia**, con su capa de mapa y su lugar en el
cruce de temas. El registro pasó de **75 a 91 materias**, y se volvió consultable
por tipo de delito: extorsión, lavado, contrabando, tráfico de migrantes, minería
ilegal, tala ilegal, tráfico de fauna, falsificación, ciberdelito, trata,
mafias, redes criminales, actores incrustados en el Estado.

Se arman **del catálogo que publica la fuente**: si el índice agrega un mercado,
aparece solo.

## 3 · Un mapa de palabras por actividad

Nadie escribe «Control de la corrupción»: escribe **coima**, **soborno** o
**cohecho**. Nadie escribe «Homicidios intencionales»: escribe **asesinato** o
**muerte violenta**. Se agregaron las palabras con que la gente pregunta a
cincuenta materias, además de las veinte nuevas.

| Se escribe | Encuentra |
|---|---|
| narcotráfico · droga · coca | los cuatro mercados de drogas |
| extorsión · vacuna · cobro de piso | Extorsión y cobro de protección |
| lavado · lavado de activos · fraude | Delitos financieros |
| minería ilegal · oro | Delitos contra recursos no renovables |
| coima · soborno · cohecho | las cinco medidas de corrupción |
| asesinato · muerte violenta | Homicidios intencionales |
| villas · favelas | Población en asentamientos precarios |
| refugiados · exilio · asilo | Desplazamiento forzado |
| ciberdelito · hackeo | Delitos informáticos |
| maras · carteles · pandillas | Grupos de tipo mafioso |

**Nada de esto suma una fuente.** Hace encontrable lo que el registro ya tenía y
nadie podía hallar. Un dato que no se puede buscar es, para el lector, un dato
que no existe.
