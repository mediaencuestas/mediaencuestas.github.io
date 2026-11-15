# Media de encuestas · Generales 29-N

Sistema automático de media de encuestas y proyección de escaños.

- **Tres veces al día** (8:17, 14:17 y 20:17) lee la tabla de encuestas de Wikipedia.
- Si hay encuestas nuevas, **te abre una propuesta** («pull request») para que las revises.
- **Al aprobarla**, recalcula la media ponderada, los escaños y las 10.000 simulaciones, y publica los datos en GitHub Pages para que la web (Lovable) los lea.

## Puesta en marcha (una sola vez)

1. **Crea el repositorio.** En github.com → «New repository». Ponle de nombre `demoscopia` y márcalo como **Public**, porque GitHub Pages es gratis en repositorios públicos. Créalo vacío.
2. **Sube los ficheros.** En el repositorio vacío, pulsa «uploading an existing file» y arrastra **el contenido** de esta carpeta (no la carpeta), incluida la carpeta oculta `.github`. En Mac, pulsa Cmd+Shift+. para ver los ficheros ocultos. Pulsa «Commit changes».
3. **Permisos de las tareas automáticas.** En Settings → Actions → General → «Workflow permissions»:
   - marca **Read and write permissions**;
   - marca **Allow GitHub Actions to create and approve pull requests**;
   - pulsa «Save».
4. **Activa la web de datos.** En Settings → Pages → «Build and deployment» → Source, elige **GitHub Actions**.
5. **Primera publicación.** En la pestaña Actions → «Calcular y publicar» → «Run workflow». Tarda unos 2 minutos. Al terminar, los datos estarán en `https://TU-USUARIO.github.io/demoscopia/`.
6. **Primera lectura de Wikipedia.** En Actions → «Buscar encuestas nuevas» → «Run workflow». Si hay encuestas nuevas, aparecerá una propuesta en la pestaña «Pull requests».
7. **Avisos en el móvil.** Instala la app **GitHub Mobile** y activa las notificaciones. Cada propuesta nueva te llegará como aviso, y puedes aprobarla desde el móvil.

## El día a día

Te llega un aviso: **«3 encuestas nuevas: 40dB, Sigma Dos, SocioMétrica»**.

1. Ábrelo. Verás una tabla con cada encuesta: casa, medio, fechas de campo, muestra y PP, PSOE, Vox, FA, Podemos y SALF. Algunas filas llevan avisos:
   - **casa nueva**: comprueba que es una encuesta de verdad;
   - **cambio grande** frente a su ola anterior: puede ser un error de Wikipedia;
   - **sin muestra**;
   - **no cuenta en la media**: es de una casa excluida, como EM-Analytics.
2. Si todo cuadra, pulsa **«Merge pull request» → «Confirm merge»**. En unos 3 minutos la media, los escaños y la web están actualizados.
3. Si **ninguna** te vale, pulsa **«Close pull request»**. Quedan apuntadas en `datos/descartadas.csv` y no se vuelven a proponer.
4. Si **una sola** está mal:
   - pestaña «Files changed» → tres puntos de `datos/encuestas.csv` → «Edit file»;
   - borra su línea y apúntala en `datos/descartadas.csv` (casa, inicio, fin, motivo);
   - después, «Merge».

Si no apruebas una propuesta y salen más encuestas, se **añaden a la misma propuesta**: nunca se acumulan varias abiertas.

**Corregir una cifra a mano.** Edita `datos/encuestas.csv` en la web de GitHub (icono del lápiz), cambia el número y pulsa «Commit changes». La web se recalcula sola.

**Añadir una encuesta que no está en Wikipedia.** Añade una línea a `datos/encuestas.csv` con el mismo formato que las demás.

## Qué se puede cambiar sin programar (`config.json`)

| Ajuste | Qué hace |
|---|---|
| `excluir_de_la_media` | Casas que se guardan pero no cuentan en la media. Hoy: EM-Analytics. |
| `no_proponer` | Casas que el lector ignora siempre (encuestas de partidos, KeyData). Las reinterpretaciones del CIS se ignoran siempre. |
| `media.vida_media_dias` | Cada cuántos días se reduce a la mitad el peso de una encuesta. Hoy 14; en campaña se podría bajar a 7. |
| `veda` | Fechas en las que no se proponen ni se publican encuestas (LOREG, art. 69.7). Para el 29-N: del 24 al 29 de noviembre. |

## Qué se publica (lo que lee la web)

Todo en `https://TU-USUARIO.github.io/demoscopia/datos/`:

| Fichero | Contenido |
|---|---|
| `hoy.json` | Media ponderada y simple de cada partido en la última fecha, cambio en 28 días y resultado del 23J. |
| `medias.json` | Serie diaria desde agosto de 2023 (ponderada y simple de 28 días). |
| `encuestas.json` | Todas las encuestas, con `en_media` para saber si cuentan. |
| `escanos.json` | Proyección con microdatos (`micro`) y solo con resultados (`resultados`): escaños, horquilla del 90 %, bloques y probabilidad de 176. Incluye el reparto por provincia y las provincias que cambian. |
| `pesos.json` | Peso de cada casa hoy, prueba de quitar cada casa y número efectivo de casas. |
| `partidos.json` | Nombre y color de cada partido. |
| `estado.json` | Cuándo se actualizó, fecha de la media, número de encuestas y si estamos en veda. |

## Microdatos (manual, cada pocas semanas)

El reparto territorial está en `datos/territorial/`. Sale de los microdatos del CIS (preelectoral 3584 y barómetros de enero a septiembre, estos con medio peso), 40dB y More in Common, que no se suben aquí porque son ficheros grandes. Cuando haya un barómetro u oleada nueva, se recalcula con `scripts/microdatos/territorial.py` y se sustituyen esos tres ficheros.

## Fuentes

- Encuestas: Wikipedia, «Opinion polling for the 2026 Spanish general election», cotejada con electoral-lab.
- Resultados del 23J, europeas de 2024 y candidaturas de 2026 por provincia: Ministerio del Interior y BOE, vía el repositorio público spain-vote-ev.
