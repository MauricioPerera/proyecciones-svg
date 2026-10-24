# Landing de Proyecciones SVG

> Registro de la publicación inicial. Posteriormente se hizo pública la skill y se añadieron descargas directas; consulta [la actualización de distribución pública](public-distribution.md).

Publicada el 23 de octubre de 2026 en https://mauricioperera.github.io/proyecciones-svg-site/.

- Fuente canónica: `docs/` de este repositorio privado.
- Copia pública para Pages: https://github.com/MauricioPerera/proyecciones-svg-site, `main`, carpeta `/docs`.
- GitHub rechazó Pages en el repositorio privado con HTTP 422: el plan actual no admite Pages para ese repositorio. No se cambió su visibilidad ni se publicó el paquete privado.
- El despliegue automático de Pages del repositorio público finalizó con éxito: ejecución `40041201648`, commit `0d9362d77f73b2036fdd4b2b9d4bb9b2d142bef8`.
- La release estable de la skill conserva el tag y paquete originales; no se reanudó su CI geométrica pendiente.

## Contenido

Explicación de la skill y de las tres vistas; cuatro modelos vectoriales seleccionables; giro de 24 ángulos; planos y JSON descargables; ejemplos de peticiones; instalación asistida y por terminal con Windows/Linux; comandos de comprobación; formatos de salida; límites y preguntas frecuentes. La página indica que la descarga de la skill requiere acceso al repositorio privado y que macOS no está validado.

## Comprobaciones

- `python -B tools/check_site.py`: 32 IDs únicos, 33 referencias, cuatro ejemplos y escala consistente entre proyecciones.
- `node --check docs/app.js`: correcto.
- `git diff --check`: correcto.
- Navegador local: los cuatro modelos cargan 24 ángulos; se muestra un solo fotograma; los enlaces de descarga cambian con el modelo; instalación alterna correctamente los comandos Windows/Linux; navegación móvil operativa.
- URL pública: carga de la landing y del giro irregular; selección y control de ángulo; vistas; pantalla estrecha y escritorio sin desbordamiento horizontal observado; registros del navegador sin errores.
- Movimiento reducido emulado: el botón avanza un ángulo y conserva `aria-pressed=false`; no inicia reproducción continua. Se restableció la preferencia tras comprobarla.

Los SVG se generan con la skill estable instalada 1.0.0. Las variantes para la presentación conservan la geometría, ajustan estilos y eliminan rótulos internos; la página no calcula una geometría alternativa ni usa un motor 3D.
