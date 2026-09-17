# Metodología del Índice de Opacidad de SIWA — base estadística

**Qué mide.** La **ausencia** de datos públicos de un Estado: cuán difícil es, para
cualquiera, obtener del Estado la información que debería ser pública. **0 = el más
transparente; 100 = el más opaco.** Mide **actos observables**, no percepciones: por eso
cualquiera puede reproducir cada componente repitiendo la consulta. Por eso NO se compara
con el Índice de Percepción de la Corrupción (que promedia opiniones de expertos): contestan
preguntas distintas.

## 1. Es un indicador compuesto (composite indicator)
Se construye siguiendo el marco estándar de indicadores compuestos (OCDE–JRC, *Handbook on
Constructing Composite Indicators*), con sus cuatro decisiones declaradas:

| Decisión | Qué se hizo | Por qué |
|---|---|---|
| **Selección de componentes** | 6 actos observables (ver §2) | cada uno se mide en este mismo registro, con fecha y rastro; ninguno es estimación |
| **Normalización** | todos en escala 0–100, misma dirección (más alto = más opaco) | hace comparables actos de naturaleza distinta |
| **Ponderación** | **pesos iguales** | cualquier reparto de pesos es un juicio escondido; pesos iguales es la única elección que no oculta una preferencia (se declara) |
| **Agregación** | **media aritmética** de los actos MEDIDOS | lineal y transparente; el lector puede rehacerla a mano |

## 2. Los seis actos y su función de puntaje
Cada acto puntúa 0 (el Estado lo cumple) a 100 (no lo cumple), con valores intermedios donde
la realidad es intermedia —y cada intermedio se justifica—:

| # | Acto | 0 | intermedio | 100 |
|---|---|---|---|---|
| 1 | **Puerta a los datos** | portal legible por máquina | 60: responde a una persona pero no se deja recolectar | sin portal |
| 2 | **Sitio oficial en pie** | vivo | 60: no responde hoy | retirado |
| 3 | **Compras públicas comparables** | publica en formato abierto | — | no publica |
| 4 | **Declara su comercio de armas (ONU)** | declaró | — | sin declarar |
| 5 | **Informa al tratado de especies (CITES)** | al día | 50: un año atrás | más atrás |
| 6 | **Publica lo que importa** | las 6 materias en su portal | proporción faltante | ninguna |

## 3. El tratamiento estadístico de los faltantes — el núcleo del método
- **Un acto sin evidencia NO puntúa:** no suma ni resta. El índice es la media de los actos
  **efectivamente medidos**, no de los seis siempre. Así, *no se castiga lo que no se miró.*
- **Fallo de un tercero ≠ opacidad del Estado:** si el archivo público que verifica un sitio no
  respondió, el que falló es el archivo; ese acto se descarta, no se cuenta en contra.
- **Umbral de validez:** con **menos de 3 actos medidos**, el Estado queda **SIN MEDIR** —que no
  es lo mismo que opaco—. Es el piso de datos por debajo del cual una media no es confiable.

## 4. Fiabilidad de cada puntaje (propuesta de mejora estadística)
Como la media se calcula sobre distinto número de actos según el país, se declara junto al número
una **fiabilidad** derivada de cuántos actos lo sostienen: 6/6 = plena, 3/6 = mínima. Es el
equivalente honesto de un intervalo: un 40 medido con 6 actos pesa más que un 40 con 3. **El
número se muestra siempre junto a cuántos actos lo miden.**

## 5. Sensibilidad — por qué el orden es robusto
El ranking no depende de un solo acto: como los pesos son iguales y hay hasta seis componentes,
mover un acto cambia el puntaje en a lo sumo `100/n`. Los extremos (los muy transparentes y los
muy opacos) son estables ante cualquier reparto de pesos alternativo; el movimiento posible está
en la zona media, y por eso el ranking se lee con esa cautela declarada.

## 6. Control de calidad
En cada corrida se comprueba un **Estado de control** (Uruguay, que abre portal, tiene sitio en
pie, publica compras, declara armas, informa especies y publica las seis materias): si su puntaje
supera 35, el que falló es el cálculo, no el Estado, y el índice **no se publica**.

## 7. Qué se publica
Por país: el **puntaje 0–100**, **cuántos actos lo miden**, el **puesto en el ranking** (de 33) y
el **desglose acto por acto**. Y la **serie histórica** del puntaje, que permite ver cómo se mueve
en el ranking. Todo con su fecha. La escala y los pesos se dicen en pantalla, no se esconden en la
fórmula.
