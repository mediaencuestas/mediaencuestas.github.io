# Instrucciones para Lovable

Copia el texto de abajo en Lovable como primer mensaje. Antes, sustituye `TU-USUARIO` por tu usuario de GitHub.

---

Crea una web en español, «Media de encuestas · Generales 29-N». Debe ser sobria y periodística, con fondo claro, tipografía serif para titulares y sans para el texto, y pensada primero para móvil.

**No inventes datos ni uses una base de datos.** Todo se lee de estos JSON públicos. Vuelve a pedirlos cada vez que se cargue la página, sin caché:

- `https://TU-USUARIO.github.io/demoscopia/datos/hoy.json`: lista de `{party, nombre, fecha, hoy, simple, cambio28, r23j, vs23j}`. `hoy` es la media ponderada en %.
- `https://TU-USUARIO.github.io/demoscopia/datos/medias.json`: serie diaria `{date, PP, PP_simple, PSOE, PSOE_simple, …}`. Los códigos son PP, PSOE, VOX, FA, PODEMOS, SALF, ERC, JUNTS, BILDU, PNV, BNG, CC y ADELANTE.
- `https://TU-USUARIO.github.io/demoscopia/datos/encuestas.json`: `{firm, media, start, end, n, PP, PSOE, VOX, FA, PODEMOS, SALF, …, en_media}`.
- `https://TU-USUARIO.github.io/demoscopia/datos/escanos.json`:
  - `{fecha_media, micro: {partidos, bloques}, resultados: {partidos, bloques}, provincias}`;
  - `partidos` = `{party, nombre, voto, escanos, p05, p50, p95}`;
  - `bloques` = `{bloque, partidos, escanos, p05, p95, prob176}`;
  - `provincias` = `{provincia, escanos, micro, resultados, cambios}`.
- `https://TU-USUARIO.github.io/demoscopia/datos/pesos.json`: `{casas: [{firm, pond, simple}], robustez: [{firm, peso, olas, dias, dPP, dPSOE, dVOX, dFA}], casas_efectivas}`.
- `https://TU-USUARIO.github.io/demoscopia/datos/partidos.json`: `{party, nombre, color}`. Usa siempre estos colores.
- `https://TU-USUARIO.github.io/demoscopia/datos/estado.json`: `{actualizado, fecha_media, encuestas_en_media, casas, en_veda}`.

Secciones, en este orden:

1. **Cabecera.** Título, la frase «Media ponderada a [fecha_media]: [partido 1] encabeza con X %, Y puntos por delante de [partido 2]», y «Actualizado: [actualizado]».
2. **Tarjetas** de PP, PSOE, Vox y FA + aliados (Frente Amplio, Front Valencià, UPC y Ara Més-Front Ampli): media en grande, cambio en 28 días y diferencia frente al 23J.
3. **Evolución desde el 23J.** Gráfico de líneas (Recharts) con la media de cada partido, más los puntos de las encuestas individuales (solo las de `en_media`) en el color del partido y con transparencia. Tres controles:
   - interruptor «Ponderada / Simple 28 días» (usa las columnas `_simple`);
   - periodo: Todo, 1 año, 6 meses, 3 meses;
   - leyenda en la que se pulsa un partido para mostrarlo u ocultarlo.

   Tooltip con los valores del día.
4. **Proyección de escaños.**
   - Selector «Con microdatos» (`micro`, por defecto) / «Solo resultados 23J» (`resultados`).
   - Barras horizontales por partido con su horquilla del 90 % (`p05`–`p95`) como línea fina.
   - Tabla de bloques con la probabilidad de llegar a 176.
   - Debajo, la lista de provincias en las que cambia el reparto (`cambios` no vacío).
5. **Resto de partidos.** Tabla con media ponderada, simple, cambio en 28 días y resultado del 23J.
6. **Cuánto pesa cada encuestadora.** Barras dobles de peso en la media ponderada frente a peso en la simple, la tabla de robustez y la frase «la media equivale a promediar N casas con el mismo peso».
7. **Todas las encuestas.** Tabla ordenada por fecha, con buscador por casa. Las que no cuentan en la media van en gris y con la nota «no cuenta en la media».
8. **Metodología.** Desplegable. Pega aquí el texto de metodología que te daré.

Si `estado.json` tiene `en_veda: true`, muestra arriba un aviso: «Periodo de veda electoral (art. 69.7 LOREG): no se publican encuestas nuevas hasta el cierre de los colegios».

Formato español en todo: coma decimal, fechas «13 nov 2026». Cada cifra que muestres debe salir de los JSON.
