# Landing de Proyecciones SVG

Sitio estático en español: presentación, cuatro modelos interactivos, instalación asistida y por terminal, ejemplos de peticiones, archivos de salida, límites y preguntas frecuentes. Ofrece enlaces directos al ZIP, al instalador y a las sumas SHA-256 de la release pública.

Se publica en [GitHub Pages](https://mauricioperera.github.io/proyecciones-svg-site/) mediante el repositorio público `MauricioPerera/proyecciones-svg-site`, que contiene únicamente el sitio y sus ejemplos. El repositorio de la skill también es público. `.nojekyll` evita transformar los archivos estáticos. No necesita dependencias ni un proceso de compilación en el servidor.

## Desarrollo local

```sh
python -m http.server 8770 --bind 127.0.0.1 --directory docs
```

Abre `http://127.0.0.1:8770/`. Las rutas de los ejemplos son relativas para admitir un sitio de proyecto de GitHub Pages.

## Regenerar los ejemplos

```sh
python -B tools/build_site_examples.py
```

La regeneración y las comprobaciones con `tools/` se ejecutan en el repositorio de la skill; esos programas no se incluyen en la copia del sitio. También acepta `--skill-dir RUTA_A_LA_SKILL_ESTABLE`. Los modelos sencillos proceden de los recursos de la skill; la pieza irregular usa `docs/assets/models/irregular/modelo.json`. Los SVG de descarga conservan la geometría del generador. Las versiones de presentación eliminan rótulos internos, añaden estilos propios y usan curvas y fotogramas calculados por la misma skill; no recalculan la geometría en JavaScript.

## Verificación

```sh
python -B tools/check_site.py
node --check docs/app.js
```

Revisar además en navegador: selección de las cuatro piezas; giro y un único fotograma visible; planos; descarga de ejemplos; instalación en ambos sistemas; navegación móvil; pantalla estrecha; movimiento reducido y ausencia de errores. Comprobar sin autenticación las descargas de la release. macOS permanece pendiente de validación.

La geometría y el alcance de la skill estable no se modifican al actualizar esta landing.
