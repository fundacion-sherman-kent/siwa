# SIWA

**Registro de situación de América Latina y el Caribe.**
Fundación Sherman Kent · Oficina de Generación de Inteligencia.

Datos públicos de los 33 Estados del padrón, recolectados de forma automática y
calificados con doctrina de inteligencia: cada cifra sale con su fuente, su
fecha de referencia, su calificación de fiabilidad y su estado de corroboración.

Las materias se ordenan por las tres líneas de trabajo de la Fundación
—**seguridad**, **gobernanza** e **inteligencia estratégica**— y no por la
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

## Estructura

```
colectores/     los programas que traen los datos
  comun.py      funciones compartidas y control de calificación
  geo.py        atribución de una coordenada al padrón de los 33
  focos.py      NASA FIRMS — focos de calor, economías ilícitas
datos/
  publico/      lo que ve cualquier visitante
    estado/     cómo terminó la última corrida de cada colector
```

## Cómo se ejecuta

Cada hora, sin intervención, mediante GitHub Actions. También a mano, desde la
pestaña **Actions** del repositorio, con el botón *Run workflow*.

En una máquina con Python 3.12, sin instalar nada:

```bash
python colectores/focos.py
```

## Fuentes en uso

| Eje | Materia | Fuente | Clave | Estado |
|---|---|---|---|---|
| Seguridad | Violencia organizada | ACLED | Sí | Pendiente |
| Seguridad | Economías ilícitas | NASA FIRMS | Sí | `A-2` en servicio |
| Gobernanza | Contratación pública | Portales OCDS | No | Pendiente |
| Gobernanza | Sanciones e integridad | OpenSanctions, OFAC | No | Pendiente |
| Gobernanza | Estabilidad institucional | Calendarios oficiales, V-Dem | No | Pendiente |
| Inteligencia estratégica | Desplazamiento forzado | ACNUR, IDMC, R4V | No | Pendiente |
| Inteligencia estratégica | Contrabando y subfacturación | UN Comtrade | No | Pendiente |

El colector en servicio califica `2` y no `1` porque es fuente única y la materia
no admite segunda fuente independiente. La circunstancia se declara en el archivo.

## Doctrina

La carta de constitución —capas, calificación automática, cruce multilingüe,
archivo de correcciones y prohibiciones— es interna de la Fundación y rige sobre
cualquier decisión técnica de este repositorio.

---

© Fundación Sherman Kent
