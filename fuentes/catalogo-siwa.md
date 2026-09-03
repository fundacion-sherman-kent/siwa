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
