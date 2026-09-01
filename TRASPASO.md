# Traspaso de SIWA

**Fundación Sherman Kent · Oficina de Generación de Inteligencia**
Documento de entrega. Estado al 1 de septiembre de 2026.

---

## 0. Cómo se usa este documento

Tiene **dos lectores** y conviene no confundirlos.

| Lector | Qué le sirve |
|---|---|
| **La persona** que recibe el trabajo | Todo el documento, en orden |
| **La inteligencia artificial** que va a asistirla | El **apartado 3**, que se copia y se pega entero al empezar |

El repositorio es **público**. Cualquier asistente con acceso a internet puede
leer el código y los datos sin credenciales y sin que nadie le mande nada por
archivo adjunto. Eso simplifica el traspaso: en vez de explicar el sistema, se
lo señala.

---

## 1. Qué es SIWA

Un **registro público, libre y gratuito de la situación de América Latina y el
Caribe**: 71 indicadores sobre los 33 Estados del padrón, recolectados de forma
automática de trece fuentes y calificados con doctrina de inteligencia.

Tres cosas lo definen, y las tres son decisiones tomadas, no accidentes:

**1. Publica hechos calificados y no emite juicios.** Cada cifra sale con su
fuente, su fecha de referencia, su calificación de fiabilidad y su estado de
corroboración. Lo que *significa* esa cifra es materia de los informes de la
Fundación, que se firman aparte y llevan confianza y probabilidad declaradas.
**Son dos productos distintos y el registro no debe deslizarse hacia el
segundo.** Si el asistente empieza a escribir «esto indica que» o «la tendencia
sugiere», se salió del registro.

**2. Cuesta cero y tiene que seguir costando cero.** No hay servidor, no hay
base de datos, no hay servicio contratado, no hay una sola dependencia externa
que instalar. Python de biblioteca estándar y una página HTML. Todo corre en el
plan gratuito de GitHub. Cualquier propuesta que introduzca un costo mensual
—una base de datos gestionada, un servicio de mapas con clave, un armazón con
`npm install`— **contradice el diseño** y hay que rechazarla o consultarla.

**3. La calidad es declarada, no supuesta.** El sistema Almirantazgo califica
cada fuente con una **letra** (A a F, fiabilidad de quien publica) y cada dato
con un **número** (1 a 6, credibilidad de la información). Una nota A-1 no se
pone porque el dato parezca bueno: exige corroboración en dos lugares
independientes, y el código lo verifica.

> **Siwa** es el oasis del desierto occidental de Egipto adonde marchó Alejandro
> a consultar al oráculo antes de decidir. El nombre no es decorativo: el
> registro se consulta antes de decidir, y responde con hechos.

---

## 2. Dónde vive todo

| Qué | Dónde |
|---|---|
| **Repositorio (público)** | `https://github.com/fundacion-sherman-kent/siwa` — rama `main` |
| **Sitio publicado** | `https://fundacion-sherman-kent.github.io/siwa/sitio/index.html` |
| **Copia local en la máquina de la Dirección** | `C:\Users\edgar\OneDrive\Documentos\observatorio-fusk` |
| **Bitácora y doctrina** | `C:\Users\edgar\OneDrive\Documentos\ClaudeGral\doctrina\siwa.md` (92 KB) |
| **Catálogo de fuentes probadas y descartadas** | `ClaudeGral\fuentes\catalogo-siwa.md` |
| **Web institucional de la Fundación** | `https://fundacionkent.org` |

La bitácora `doctrina/siwa.md` **no está en el repositorio público**: vive en la
carpeta de trabajo de la Fundación. Es el documento más valioso del proyecto
—registra cada decisión, cada sondeo y cada error— y quien reciba el trabajo
debería recibirla junto con este archivo.

**Cómo se publica un cambio.** No hay compilación ni despliegue: se sube a
`main` y GitHub Pages lo publica solo, en uno o dos minutos. Ojo con una trampa
que ya costó una confusión: **Pages guarda la página diez minutos en el
navegador de quien la visitó** (`Cache-Control: max-age=600`). Después de subir
hay que abrir con **Ctrl + F5**, o se ve la versión vieja y parece que el cambio
no salió.

---

## 3. Bloque para pegarle a la otra inteligencia artificial

Se copia **desde la línea siguiente hasta el cierre**, y se pega como primer
mensaje de la conversación.

```
Vas a asistir en el mantenimiento de SIWA, el registro público de situación de
América Latina y el Caribe de la Fundación Sherman Kent.

QUÉ ES
Una página HTML y trece colectores en Python que publican 71 indicadores sobre
33 Estados, calificados con doctrina de inteligencia. Repositorio público:
https://github.com/fundacion-sherman-kent/siwa
Sitio: https://fundacion-sherman-kent.github.io/siwa/sitio/index.html
Leé el repositorio antes de proponer nada. El archivo sitio/index.html es la
página entera (245 KB, sin dependencias); colectores/comun.py fija las reglas.

REGLAS QUE NO SE NEGOCIAN
1. NUNCA SE FABRICA UN DATO. Si una fuente no responde, no se estima, no se
   completa, no se interpola y no se rellena con lo del año anterior. Se
   declara la falla y se conserva el último dato válido con su fecha. Un número
   inventado en un registro de inteligencia es peor que un vacío.
2. LOS VACÍOS SE DECLARAN. Cada archivo de datos lleva su lista de
   "vacios_declarados": qué NO cubre esa fuente. Un producto sin vacíos
   declarados se rechaza.
3. EL REGISTRO NO EMITE JUICIOS. Publica hechos con su fuente. Nada de "esto
   indica", "la tendencia sugiere", "mejoró", "empeoró". Cuando haya que
   orientar al lector se usa el criterio declarado por la propia fuente, y se
   dice que es de la fuente.
4. TODO DATO LLEVA CALIFICACIÓN ALMIRANTAZGO: una letra A-F para la fiabilidad
   de quien publica y un número 1-6 para la credibilidad del dato. La
   credibilidad 1 exige corroboración en dos lugares independientes y el código
   la verifica: no se pone a mano.
5. DOS FUENTES O DESCIENDE LA CALIFICACIÓN. Sin segunda fuente el dato entra
   marcado y con la credibilidad descendida.
6. COSTO CERO. Python de biblioteca estándar solamente: urllib, json, csv, re,
   zipfile, xml.etree, concurrent.futures. NADA de pip install, npm install,
   CDN, base de datos ni servicio con clave. Si una solución necesita instalar
   algo, es la solución equivocada. Leaflet está copiado dentro del repositorio.
7. SONDEAR, NUNCA AFIRMAR. Antes de incorporar cualquier fuente hay que
   probarla de verdad: pedirla, ver qué código devuelve, ver si trae los 33
   Estados, ver de qué año es el dato. De más de 250 fuentes candidatas entró
   solo lo que respondió, y cada rechazo quedó registrado con su motivo. No
   escribas un colector para una fuente que no probaste.
8. NO SE ELUDE LA PROTECCIÓN CONTRA ROBOTS. Si un portal devuelve 403 o pone
   Cloudflare, se registra como inaccesible y se pide acceso institucional. No
   se disfraza el agente, no se resuelven captchas, no se usa una cuenta con
   sesión iniciada.
9. NUNCA ENTRA UNA CREDENCIAL AL REPOSITORIO. Ni clave de API, ni contraseña,
   ni token, ni siquiera en un comentario o en un ejemplo. Van en GitHub
   Secrets. El repositorio es público.
10. DE UNA INTERFAZ SE COMPRUEBA LO QUE SE VE. Un elemento escondido con
    display:none sigue existiendo, sigue respondiendo al click y sigue
    devolviendo el valor correcto: una prueba por querySelector puede dar verde
    sobre una pantalla rota. Se verifica con captura de pantalla o con
    visibilidad real. Ya pasó.

LENGUA Y VOZ
Español rioplatense, norma de la Real Academia Española, léxico preciso. Los
comentarios del código y los mensajes de commit van en español y explican POR
QUÉ, no qué. El código está escrito para que lo lea alguien que no programa.

IDENTIDAD VISUAL
Azul de la casa #00121E, naranja #FB6500, violeta #8C00E0, tipografía Inter.
Toda pieza —pantalla, papel, planilla— lleva la marca y la cita "SIWA,
Fundación Sherman Kent".

CÓMO SE TRABAJA
- Un colector se corre solo:  python colectores/<nombre>.py
- No hay que instalar nada. Python 3.12.
- Todo colector termina en comun.escribir(), que es el único camino de salida y
  el que impone la calificación, la atribución y los vacíos declarados. No
  escribas un JSON a mano.
- Antes de tocar sitio/index.html, entendé que es una sola página de 245 KB sin
  compilación: se edita el archivo y con eso queda publicado.

QUÉ NO HACER
- No reescribir el proyecto con un armazón de programación.
- No agregar dependencias.
- No cambiar la calificación de una fuente sin evidencia.
- No borrar vacíos declarados para que el informe se vea mejor.
- No publicar nombres de víctimas ni datos personales: el colector de extorsión
  informática trae 1.648 casos y publica solo agregados, a propósito.

Cuando no sepas algo, decilo. No completes con lo que suena razonable: es
exactamente el error que este registro existe para no cometer.
```

---

## 4. La arquitectura, en cinco piezas

```
observatorio-fusk/
├── colectores/            13 colectores + comun.py + geo.py
│   ├── comun.py           ← LAS REGLAS. Único camino de salida.
│   ├── geo.py             atribución de un hecho a un país por coordenadas
│   ├── *.json             padrones a mano: medios, canales, temas, fronteras
│   └── <fuente>.py        un archivo por fuente
├── datos/publico/         la salida: 14 archivos JSON
│   └── estado/            el parte de fallas, uno por colector
├── sitio/
│   ├── index.html         LA PÁGINA ENTERA — 245 KB, sin dependencias
│   ├── geo/               contornos de los 33 Estados
│   ├── marca/             logotipos FUSK
│   └── vendor/            Leaflet 1.9.4, copiado adentro a propósito
└── .github/workflows/
    └── recolectar.yml     el robot
```

**La pieza que hay que entender primero es `colectores/comun.py`.** No es una
biblioteca de utilidades: es donde viven las reglas de la casa, escritas en
código para que no se puedan saltear.

- `calificar(fiabilidad, credibilidad, corroborado, nota)` — **rechaza** una
  credibilidad 1 sin corroboración. La regla no es un comentario: es una
  excepción que detiene la corrida.
- `escribir(...)` — el único camino de salida. Arma el archivo con su
  procedencia, su calificación, sus vacíos declarados y la atribución a la
  Fundación. Un colector que escriba un JSON por su cuenta se saltea todo esto.
- `escribir_estado(...)` — deja el parte de la falla en `datos/publico/estado/`
  **sin pisar el dato anterior**. Que una fuente falle no borra lo que ya se
  sabía: lo deja envejecer a la vista.

**Las seis materias.** La sección `#seis-materias` reúne, por materia, lo que
está repartido entre colectores: violencia organizada, economías ilícitas,
contrabando, ciberseguridad, contratación pública y desinformación. Cada ficha
declara **qué se mide, qué se publica ahora y qué no se mide**. La tercera parte
es la que importa: es la diferencia entre un registro de inteligencia y un
tablero. La lista vive en `MATERIAS_FUSK`, dentro de `index.html`.

**El boletín se enlaza, no se recolecta.** La página es estática y el
repositorio es público: **una dirección de correo no puede pasar por acá**. El
padrón lo administra la Fundación en `fundacionkent.org/newsletter/`, que ya
tiene el alta y la baja. Si alguien propone un formulario en SIWA, esta es la
razón por la que no lo hay.

**La tarjeta para compartir.** `sitio/marca/siwa-compartir.png`, declarada en
`og:image` con dirección **absoluta** —las redes no resuelven rutas relativas—.
Se regenera con `herramientas/tarjeta-compartir.py`, que necesita Pillow y **no
corre en el robot**: es local, a mano, y solo cuando cambian la identidad o las
cifras.

**La segunda pieza es `sitio/index.html`.** Una sola página, 245 KB, sin
compilación y sin una sola petición a un servidor ajeno. Se edita el archivo, se
sube, y queda publicada. Adentro, tres mecanismos vale la pena conocer:

- **Los tres niveles de lectura.** `body[data-nivel]` gobierna qué se ve:
  Ciudadano (3 secciones), Periodista (16) y Analista (46). El contenido lleva
  `data-nivel`; **los botones que eligen el nivel llevan `data-lee`**, y esa
  distinción no es cosmética (ver apartado 9).
- **La memoización por sello de datos.** `capas()` y `valores()` se recalculan
  solo cuando cambia el sello de los datos. Sin eso, el mapa tardaba 3.209 ms en
  pintarse; con eso, 22 ms.
- **`paso(nombre, fn)`.** Cada rutina de pintado corre aislada: si una falla, no
  se lleva puesta la página entera.

---

## 5. Las trece fuentes

| Colector | Fuente | Nota | Qué aporta |
|---|---|---|---|
| `banco_mundial` | Banco Mundial | **A-2** | 31 indicadores: desarrollo, gobernanza, migración, defensa |
| `onu_ods` | Naciones Unidas, ODS | **A-2** | 15 indicadores, 33 Estados |
| `desplazamiento` | ACNUR | **A-2** | Desplazamiento forzado, serie histórica |
| `comercio` | Comtrade (ONU) | **A-2** | Brecha espejo del comercio declarado |
| `fuentes_oficiales` | Catálogos abiertos de los Estados | **A-2** | Qué publica cada Estado |
| `fundacion` | Canal institucional FUSK | **A-1** | Informes propios; cierra el circuito |
| `owd` | V-Dem, GTD, UCDP vía Our World in Data | **B-2** | Democracia, terrorismo, conflicto, entorno informativo, capacidad aeroespacial |
| `bti` | Índice Bertelsmann | **B-3** | 8 indicadores, 22 de 33 Estados |
| `conflictos` | Instituto Javeriana Cali | **B-3** | 460 conflictos, 3.567 polígonos de minería ilegal |
| `ransomware` | ransomware.live | **D-4** | 1.648 víctimas en 31 Estados — **solo agregados** |
| `cobertura` | 153 medios del padrón propio | **F-3** | Qué se está publicando hoy |
| `telegram` | 20 canales públicos verificados | **F-4** | Difusión en mensajería |
| `redes` | Mastodon, 4 instancias | **F-4** | Circulación en red social abierta |

**71 indicadores** repartidos en cuatro ejes: Gobernanza 30, Seguridad 18,
Desarrollo 14, Defensa 9.

**Por qué conviven una fuente A-1 y una F-4.** No es descuido. Una cuenta anual
de la UNODC y una mención de prensa **no son el mismo dato**, y mezclarlos
destruye la serie. La señal reciente —lo que circula hoy, calificado F— se
muestra **al lado** del indicador y dice explícitamente que *no actualiza la
cifra de arriba*. Esa separación es el corazón del diseño y no hay que
«mejorarla» fusionando las dos cosas.

---

## 6. Las reglas de la casa

Las diez del bloque del apartado 3 son las operativas. Estas son las de fondo, y
están en `ClaudeGral/CLAUDE.md` y en `doctrina/`:

1. **Separar información de juicio.** Un hecho lleva fuente. Un juicio lleva
   confianza y probabilidad.
2. **Toda afirmación es trazable.** Sin fuente en el anexo, no entra.
3. **Léxico de probabilidad de Kent.** Nada de «podría» ni «no se descarta».
4. **Los vacíos se declaran.**
5. **Hipótesis alternativa siempre**, y disenso formal antes de publicar.
6. **El método se declara.**
7. **No dejar espacios en blanco.** Sin novedades se dice; no se omite.
8. **Nunca se fabrica.** Si no se encontró, se dice que no se encontró.
9. **Todo juicio sale de una técnica identificable.** No existe el juicio
   emitido «por criterio del analista».
10. **Dos fuentes o desciende la calificación.**

Y una del oficio de escribir, que gobierna hasta los comentarios del código:
**el juicio va en potencial; el hecho acreditado, en indicativo**, y el verbo no
promete más de lo que la evidencia sostiene —*demuestra*, *prueba*, *confirma* y
*revela* exigen lo que su nombre dice.

---

## 7. Cómo corre solo

El robot está en `.github/workflows/recolectar.yml`.

| Cuándo | Qué |
|---|---|
| **Cada hora**, al minuto 17 | Lo que cambia seguido: prensa, Mastodon, Telegram, informes de la Fundación |
| **Cada día**, 5:40 UTC | Todo, incluidas las series anuales y los catálogos |
| **A mano** | Pestaña *Actions* → *Recolección* → *Run workflow* |

La diferencia la marca la variable `COMPLETA`. Cuidado con un detalle del
lenguaje de GitHub: **sus expresiones no admiten el signo `%`**, así que el
gatillo se compara contra el texto del cron, no contra un módulo.

**Tres cosas que conviene saber antes de tocarlo:**

**La colisión de escrituras está resuelta, y con alcance estricto.** Cuando el
robot y una corrida local reescriben el mismo archivo en la misma hora, git no
puede fusionarlos: no existe «la mitad de un dato». `.gitattributes` resuelve
`datos/**/*.json` con `merge=ours` y la corrida siguiente reconcilia en menos de
una hora. **La regla no alcanza al código ni a la doctrina**, donde descartar en
silencio el cambio ajeno sería grave.

**Una falla no borra el dato.** Si un colector falla, la corrida queda en rojo,
el dato anterior se conserva y la falla queda escrita en
`datos/publico/estado/`. La página lo muestra: dice qué fuente falló y de cuándo
es el último dato válido.

**GitHub apaga las tareas programadas a los 60 días.** El reloj lo mueve la
**actividad en el repositorio** —un commit, un push—, **no las visitas al
sitio**. Como el robot commitea datos casi todos los días, en la práctica no se
apaga solo; pero si el proyecto queda congelado dos meses, hay que volver a
habilitarlo a mano en la pestaña *Actions*.

---

## 8. El método de trabajo: sondear, nunca afirmar

Es lo que más caro sale de reconstruir y lo que más rápido se pierde en un
traspaso.

A lo largo del desarrollo se evaluaron **más de 250 fuentes candidatas**.
Entraron trece. **Ninguna entró porque pareciera buena**: cada una se pidió de
verdad, se miró qué código HTTP devolvía, cuántos de los 33 Estados cubría, de
qué año era el dato y qué decía su licencia. Los rechazos están todos anotados
con su motivo en `fuentes/catalogo-siwa.md` — lo que no responde hoy puede
responder en seis meses, y lo que bloquea al robot puede abrirse con un pedido
institucional.

**La consecuencia práctica para quien siga:** cuando alguien —persona o
asistente— proponga «agregar tal base de datos», la respuesta correcta no es
escribir el colector. Es **probar la fuente primero** y recién después decidir.
Un colector escrito contra una fuente no probada es trabajo perdido en el mejor
caso, y un dato inventado en el peor.

Y un diagnóstico que ordenó buena parte del trabajo, por si ahorra tiempo: **el
retraso de los datos es por fuente, no por país**. Medido sobre los 71
indicadores × 33 Estados, la mediana es de 2 años para todos los países por
igual. Las encuestas llegan con 7 a 10 años de atraso; la evaluación de
expertos, con 1. No tiene sentido buscar «el país que actualiza mal».

---

## 9. Los errores ya cometidos

**Este es el apartado más valioso del documento.** Son errores reales, con su
diagnóstico. Quien reciba el trabajo va a estar tentado de repetir varios.

**1. El índice Bertelsmann con todos los nombres corridos.** Un `.xlsx` es un
zip de XML, y las cadenas van en `sharedStrings.xml`. El código contaba
fragmentos `<t>` en lugar de elementos `<si>` — y el formato parte una cadena en
varios fragmentos. Resultado: **cada nombre y cada rótulo corridos de lugar**.
Cuba aparecía con 8,55 de democracia y Chile con 2,37.

> **Se detectó porque los números eran imposibles, no porque algo fallara.** Es
> la clase de error más peligrosa: cifras verosímiles, en formato correcto,
> completamente equivocadas. Ninguna prueba automática lo hubiera visto.

**2. El mapa se congelaba.** `estiloPais` corre una vez por país y cada llamada
reconstruía el catálogo de 57 capas con sus cuartiles. 3.209 ms → 22 ms
memoizando. Arreglándolo aparecieron tres más: una coalescencia que *descartaba*
repintados encolados (la última fuente nunca se dibujaba);
`requestAnimationFrame` no dispara en una pestaña oculta (página en blanco); y
`fitBounds` sobre un contenedor de altura cero lanzaba `Invalid LatLng` y mataba
el script entero.

**3. El mapa entero naranja para terrorismo.** 22 de 32 Estados en cero daban
cuartiles `[0, 0, 76]`: todo el mundo en la categoría más alta. **El cero es una
categoría propia** con tono neutro, y los cortes se calculan solo entre los
Estados con casos: `[2, 5, 21]`.

**4. Los tres botones se escondían a sí mismos.** Los botones que eligen el
nivel de lectura se escribieron con `data-nivel="1|2|3"` — que es exactamente el
atributo con el que la página oculta lo que no corresponde al nivel elegido. En
Ciudadano quedaba visible un solo botón y no había forma de volver.

> **Y la comprobación falló por el método.** La prueba recorría los niveles con
> `querySelector` y `click()`. Un elemento con `display:none` sigue existiendo,
> sigue respondiendo al click y sigue devolviendo el nivel correcto: dio verde
> sobre una pantalla rota. **De una interfaz se comprueba lo que se ve.**

**5. Doble conteo en el comercio.** Comtrade repite filas por modo de
transporte. Sumarlas daba una brecha Argentina–Brasil del +109 %. Filtrando
`motCode = 0`: +4,7 %, exactamente lo que explica la diferencia entre valor FOB
y CIF.

**6. Telegram: ceros que parecían datos.** Dos errores a la vez —cortar los
bloques por la etiqueta de cierre, y quitar los elementos `<a>` enteros cuando
el titular vive adentro del enlace— hacían que un canal que había publicado ese
mismo día figurara en cero. 97 → 125 mensajes.

**7. Porcentajes imposibles.** −331 % sobre un índice que va de −2,5 a 2,5;
−133 % sobre una migración neta que cruza el cero; y «−1.000.000 pts» cuando la
regla nueva agarró valores del SIPRI en millones. La regla final: **puntos**
para índices de rango corto, **diferencia** para cantidades que cruzan el cero,
**porcentaje** para el resto.

**8. La ficha para el ciudadano emitía juicios.** Decía «Mejoró» ante una suba
del 542 % en exportación de minerales. Se reemplazó por el criterio declarado
por la propia fuente, y diciendo que es de la fuente.

**9. Dos mapeos de léxico equivocados.** «Contrabando» apuntaba al indicador de
soborno y «minería ilegal» a las rentas de la minería legal: un titular sobre un
decomiso aparecía bajo «empresas que esperan pagar por un contrato». Ninguno de
los dos temas tiene indicador, y ahora se declara así.

**10. El PDF impreso salía sin identidad ni cita**, porque la barra superior y
el pie están ocultos en impresión. Y **el informe descargable traía 22 de los 65
indicadores**: 43 faltaban en lo que la gente se llevaba.

---

## 10. Lo que quedó pendiente

**Gestiones que dependen de una persona, no del código:**

- **Instituto de Estudios Interculturales (Javeriana Cali)** — pedir permiso
  escrito de uso. Hoy se publican solo agregados por prudencia.
- **World Economic Forum** — bloquea las tres direcciones probadas. Hace falta
  acceso institucional.
- **Lloyd's Register Foundation World Risk Poll** — mide *percepción* de
  seguridad, que es el último vacío declarado de importancia. Requiere registro.
- **UNODC** — `dataportal.unodc.org` no resuelve desde la máquina de la
  Dirección. Vale reintentarlo desde otra red: habilitaría la medición en kilos.
- **Brasil** — claves gratuitas de sus API.

**Trabajo técnico anotado y no hecho:**

- Exportación a planilla `.xlsx` con logotipo. Hoy el descargable es CSV con
  cabecera de atribución, y el PDF sí lleva membrete y colofón.
- **Contratación pública** es la brecha más grande y la más remontable de las
  seis materias: el expediente de cada licitación existe en los portales de
  compras de cada Estado, pero en 33 formatos distintos. Hoy solo se mide
  percepción y experiencia declarada.
- La tarjeta para compartir se dibuja con **Segoe UI** porque Inter, la
  tipografía de la casa, no está instalada en la máquina de la Dirección.
  Instalarla y volver a correr `herramientas/tarjeta-compartir.py` la deja
  con la tipografía correcta.

---

## 11. Seguridad, credenciales y límites legales

**Léase antes de tocar nada.**

**Credenciales que hay que rotar.** Durante el desarrollo se pegaron en una
conversación de chat una **clave de API de NASA FIRMS** y la **contraseña
institucional de ACLED** de la casilla `direjecutiva@fundacionkent.org`. **Las
dos deben darse de baja y volver a emitirse.** No figuran en este documento ni
en el repositorio, y así tiene que seguir: el repositorio es público y una
credencial subida ahí queda en el historial de git aunque después se borre. Van
en **GitHub Secrets**, nunca en el código.

**Lo que no se hace, y por qué.**

- **No se elude la protección contra robots.** Varios portales devuelven 403 o
  ponen Cloudflare —el WEF, la CICAD de la OEA, algunos portales nacionales—. Se
  registran como inaccesibles y se pide acceso institucional. Está en
  `doctrina/limites.md`.
- **No se raspa X/Twitter, foros ni mensajería con una cuenta con sesión
  iniciada** sin revisión legal previa. Telegram se incorporó **únicamente** por
  la vista pública `t.me/s/<canal>`, después de confirmar que el dominio no la
  excluye por `robots.txt`. La vía MTProto con cuenta de usuario queda excluida
  hasta que haya dictamen.
- **ACLED** no permite republicar datos de evento en crudo. Su licencia se
  respeta.
- **No se publican nombres de víctimas.** El colector de extorsión informática
  trae 1.648 casos y publica **solo agregados**, deliberadamente.

**La Fundación es una fundación privada de análisis.** No es, ni simula ser, un
organismo estatal. «Clasificado» es una categoría **interna de la Fundación** y
nunca una clasificación estatal.

---

## 12. Lo que no hay que hacer

Ordenado por daño probable.

1. **No reescribir el proyecto con un armazón de programación.** La ausencia de
   dependencias no es pobreza: es lo que hace que esto siga corriendo gratis y
   sin mantenimiento dentro de tres años.
2. **No completar un dato faltante.** Ni estimarlo, ni interpolarlo, ni
   arrastrar el del año anterior. Se declara la falla.
3. **No borrar vacíos declarados** para que el informe se vea más completo.
4. **No subir la calificación de una fuente** sin evidencia de corroboración.
5. **No fusionar la señal reciente con el indicador.** Una mención de prensa no
   actualiza una cuenta anual.
6. **No dar por verificada una interfaz sin verla.**
7. **No subir una credencial**, ni siquiera de ejemplo, ni siquiera comentada.
8. **No mover la línea entre el registro y el análisis.** El registro publica
   hechos calificados. El juicio es de los informes de la Fundación, y va
   firmado.

---

## 13. Nota final para quien recibe

El valor de este proyecto no está en las 245 KB de la página ni en los trece
colectores: está en **las decisiones registradas**. Por qué una fuente entró y
otra no. Por qué el cero es una categoría propia. Por qué la señal reciente va
al lado y no adentro. Por qué un error de cifras verosímiles es peor que una
caída.

Todo eso está en `doctrina/siwa.md` y en `fuentes/catalogo-siwa.md`. Si sólo se
transfiere el código, se transfiere la parte fácil.

---

*SIWA — Reporte de situación de América Latina y el Caribe.
Fundación Sherman Kent, Oficina de Generación de Inteligencia.
Acceso libre y gratuito, citando la fuente: «SIWA, Fundación Sherman Kent».
La Fundación agradece a los especialistas y funcionarios que contribuyeron con
su tiempo y criterio.*
