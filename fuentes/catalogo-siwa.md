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
