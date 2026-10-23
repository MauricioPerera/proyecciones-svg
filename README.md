# Proyecciones SVG

Skill de Codex para construir un modelo geométrico a partir de una descripción, un croquis o vistas técnicas y generar alzado, planta, perfil y giros SVG. Python estándar y SVG nativo, sin motor 3D ni servicios externos.

Versión preparada: **1.0.0**, licencia MIT. Repositorio privado: [MauricioPerera/proyecciones-svg](https://github.com/MauricioPerera/proyecciones-svg). La publicación se prepara como borrador tras aprobar CI. El código canónico está en `skills/proyecciones-svg`; la carpeta de skills instalada se obtiene del paquete, no se edita como segunda fuente.

## Usar

Requiere Python 3.10+. Desde este repositorio:

```sh
python skills/proyecciones-svg/scripts/generar.py skills/proyecciones-svg/assets/cuatro-taladros.json --output-dir build/ejemplo --frames 72 --viewer
```

Abre `build/ejemplo/visor.html`. También se entregan tres SVG independientes, el JSON y un informe de versión, duración, tamaños y sumas. La interpretación de lenguaje/croquis la realiza el agente siguiendo `SKILL.md`; el programa recibe geometría JSON, no interpreta imágenes automáticamente.

Los modelos admitidos y sus límites están en [la skill](skills/proyecciones-svg/SKILL.md), [los contratos](skills/proyecciones-svg/references/modelos.md) y [la ejecución](skills/proyecciones-svg/references/ejecucion.md). Los planos contienen cotas generales y no certifican una pieza para fabricación.

## Comprobar

```sh
python -B tools/verify.py
npm ci
npx playwright install chromium firefox
python -B tools/browser_fixtures.py
npm run test:browser
```

Node/Playwright sólo se usan en pruebas. Se verifican geometría, curvas y cotas al cambiar de escala; piezas esbeltas; instalación limpia; presupuestos de ejecución; controles del visor; 24 ángulos en tres modelos; SMIL, movimiento reducido y pantalla de 320 px. La matriz CI ejecuta Python 3.10/3.14 en Windows, Linux y macOS, y Chromium/Firefox en Linux. `Ready for release` exige seis informes del mismo commit, ninguna prueba omitida, las seis combinaciones de navegador/modelo y ZIP idéntico entre plataformas. Los resultados se conservan como artefactos. La configuración sigue las guías oficiales de [Actions](https://github.com/actions/setup-python) y [Playwright](https://playwright.dev/docs/ci).

## Empaquetar e instalar

```sh
python -B tools/release.py
python -B tools/install_skill.py dist/proyecciones-svg-1.0.0.zip --skills-dir RUTA_A_CODEX/skills
```

El ZIP usa entradas sin compresión y metadatos fijos para conservar los mismos bytes entre sistemas y versiones de zlib; incluye licencia y manifiesto con SHA-256. El instalador comprueba rutas y sumas antes de escribir. Para actualizar una instalación existente añade `--update`: conserva la versión previa en `skill-backups/`, fuera de la carpeta de descubrimiento de skills. Las sumas detectan alteraciones, pero no autentican por sí solas al distribuidor.

Para volver a una release anterior, instala su ZIP con `--update`; la versión reemplazada también queda respaldada.

Para preparar el borrador estable desde el commit aprobado de `main`, usa `python -B tools/prepare_release.py --repo MauricioPerera/proyecciones-svg --create-draft`. Comprueba CI y descarga su evidencia, compara el paquete local con el de las seis plataformas y adjunta ZIP, sumas, instalador, notas y evidencia. Requiere GitHub CLI autenticado. Este comando crea un borrador y no lo publica. Las notas están en `releases/1.0.0.md`.

Si CI sigue pendiente, `python -B tools/prepare_release.py --repo MauricioPerera/proyecciones-svg --local-only` prepara los archivos con estado `pending_ci` y no crea borrador. El primer intento remoto fue rechazado antes de ejecutar pruebas por el presupuesto de Actions; el usuario decidió aplazarlo. Detalles y reanudación en [el informe](reports/1.0.0-ci.md).
