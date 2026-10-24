# Distribución pública de la skill

El usuario autorizó hacer público `MauricioPerera/proyecciones-svg` y añadir descargas directas desde la landing. El repositorio y la release estable 1.0.0 se pueden consultar y descargar sin autenticación.

La landing conserva su dirección: https://mauricioperera.github.io/proyecciones-svg-site/. Ofrece acceso directo al ZIP desde la portada y la instalación, además de enlaces al instalador Python, `SHA256SUMS` y las notas. Las instrucciones y preguntas frecuentes ya no requieren acceso a un repositorio privado.

## Integridad y alcance

- ZIP: `proyecciones-svg-1.0.0.zip`, 240680 bytes; SHA-256 `221efe5c1bad18d5df9e5316c7c154bdf8c93e0b388257a3aeeceb85c4e5968a`.
- Instalador: 3944 bytes; SHA-256 `28321ad8649255e90d779b5a7c71ce74599dd688f6ccb3e4e8afec8172bfbcab`.
- El ZIP, el instalador, la licencia, el manifiesto y la evidencia geométrica no se modificaron. Se actualizaron las notas de distribución y sus sumas.
- La release permanece estable, asociada al commit `88c384b7dbadba64425ac2579a22b83e6500c98e`.
- Windows/Linux validados; macOS continúa pendiente. El cambio no añade validación de plataformas ni modifica la geometría.

## Comprobaciones

- Lectura anónima de la API del repositorio: `private=false`.
- Descarga HTTP anónima de los siete archivos de la release, sin cabeceras Authorization ni Cookie; verificación completa de `SHA256SUMS`.
- Instalación aislada usando el instalador y el ZIP recién descargados: versión 1.0.0 y 41 archivos verificados contra el manifiesto.
- Suite de distribución/publicación: 17 pruebas correctas. Incluye aceptar el repositorio público manteniendo el rechazo de un destino distinto.
- Landing: comprobador estático correcto; enlaces directos ligados a la versión estable y eliminación del requisito de acceso privado.
- GitHub Pages: despliegue `40042840215` aprobado, commit `1077376b09438e90c30553b6c0174451d369b7cc`. Lectura HTTP anónima con estado 200; el HTML servido coincide exactamente con la fuente y contiene los cuatro enlaces directos esperados.

Las descargas se sirven desde los assets de la release oficial; la landing no conserva una segunda copia del paquete.
