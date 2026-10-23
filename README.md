# Proyecciones SVG

Skill de Codex para construir un modelo geométrico a partir de una descripción, un croquis o vistas técnicas y generar alzado, planta, perfil y giros SVG. Python estándar y SVG nativo, sin motor 3D ni servicios externos.

Versión estable **1.0.0 para Windows y Linux**, licencia MIT. **macOS pendiente de validación**. Repositorio privado: [MauricioPerera/proyecciones-svg](https://github.com/MauricioPerera/proyecciones-svg). El código canónico está en `skills/proyecciones-svg`; la carpeta de skills instalada se obtiene del paquete, no se edita como segunda fuente.

| Plataforma | Python 3.10 | Python 3.14 |
| --- | --- | --- |
| Windows | Validado | Validado |
| Linux | Validado en Ubuntu 24.04 por SSH | Validado en Ubuntu 24.04 por SSH |
| macOS | Pendiente | Pendiente |

## Sitio web

La [landing de Proyecciones SVG](https://mauricioperera.github.io/proyecciones-svg/) explica el uso y la instalación, con cuatro ejemplos SVG interactivos y guías para usuarios técnicos y no técnicos. Su fuente está en `docs/`; se sirve como sitio estático de GitHub Pages. La descarga de la skill sigue requiriendo acceso al repositorio privado. Consulta [el desarrollo de la landing](docs/README.md) para regenerar los ejemplos y comprobarla localmente.

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

Node/Playwright sólo se usan en pruebas. Se verifican geometría, curvas y cotas al cambiar de escala; piezas esbeltas; instalación limpia; presupuestos de ejecución; controles del visor; 24 ángulos en tres modelos; SMIL, movimiento reducido y pantalla de 320 px. El perfil de publicación `windows-linux` exige cuatro informes del mismo commit, ninguna prueba omitida, seis combinaciones de navegador/modelo y ZIP idéntico entre plataformas.

La validación puede ejecutarse localmente y por SSH sin GitHub Actions. El perfil completo `all` conserva las seis combinaciones, incluidas las dos de macOS; sigue siendo el predeterminado del validador y del workflow de CI, y no se considera aprobado por una validación de cuatro casos. La configuración opcional de CI sigue las guías oficiales de [Actions](https://github.com/actions/setup-python) y [Playwright](https://playwright.dev/docs/ci).

## Empaquetar e instalar

```sh
python -B tools/release.py
python -B tools/install_skill.py dist/proyecciones-svg-1.0.0.zip --skills-dir RUTA_A_CODEX/skills
```

El ZIP usa entradas sin compresión y metadatos fijos para conservar los mismos bytes entre sistemas y versiones de zlib; incluye licencia y manifiesto con SHA-256. El instalador comprueba rutas y sumas antes de escribir. Para actualizar una instalación existente añade `--update`: conserva la versión previa en `skill-backups/`, fuera de la carpeta de descubrimiento de skills. Las sumas detectan alteraciones, pero no autentican por sí solas al distribuidor.

Para volver a una release anterior, instala su ZIP con `--update`; la versión reemplazada también queda respaldada.

Para preparar un borrador del alcance Windows/Linux desde `main` limpio y sincronizado, reúne los cuatro informes y sus ZIP en carpetas `python-*/`, y el informe Linux de navegadores en `browser-evidence/report.json`. Ejecuta:

```sh
python -B tools/prepare_release.py --repo MauricioPerera/proyecciones-svg --validation-dir RUTA_A_LA_MATRIZ --profile windows-linux --create-draft
```

Comprueba los cuatro casos, el commit y las sumas antes de adjuntar ZIP, licencia, instalador, notas y evidencia. Requiere GitHub CLI autenticado para crear el borrador; no ejecuta Actions. Sin `--validation-dir`, permanece disponible la ruta de CI con la matriz completa. El comando crea un borrador y no lo publica. Las notas están en `releases/1.0.0.md`.

El primer intento de Actions fue rechazado por presupuesto y quedó aplazado. Esa limitación no impide publicar el alcance Windows/Linux con evidencia local y por SSH. `--local-only` sigue disponible para generar archivos pendientes sin aprobarlos ni crear borrador. Consulta [el alcance de la estable](reports/1.0.0-stable.md) y [el historial de CI](reports/1.0.0-ci.md).
