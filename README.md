# Proyecciones SVG

Skill de Codex para construir un modelo geométrico a partir de una descripción, un croquis o vistas técnicas y generar alzado, planta, perfil y giros SVG. Python estándar y SVG nativo, sin motor 3D ni servicios externos.

Estado: **1.0.0-rc.1**, candidata local. El código canónico está en `skills/proyecciones-svg`; la carpeta de skills instalada se obtiene del paquete, no se edita como segunda fuente.

## Usar

Requiere Python 3.10+. Desde este repositorio:

```sh
python skills/proyecciones-svg/scripts/generar.py skills/proyecciones-svg/assets/cuatro-taladros.json --output-dir build/ejemplo --frames 72 --viewer
```

Abre `build/ejemplo/visor.html`. También se entregan tres SVG independientes, el JSON y un informe de versión, duración, tamaños y sumas. La interpretación de lenguaje/croquis la realiza el agente siguiendo `SKILL.md`; el programa recibe geometría JSON, no interpreta imágenes automáticamente.

Los modelos admitidos y sus límites están en [la skill](skills/proyecciones-svg/SKILL.md), [los contratos](skills/proyecciones-svg/references/modelos.md) y [la ejecución](skills/proyecciones-svg/references/ejecucion.md). Los planos contienen cotas generales y no certifican una pieza para fabricación.

## Comprobar

```sh
python -B -m unittest discover -s skills/proyecciones-svg/scripts -p "test_*.py"
python -B -m unittest discover -s tests -p "test_*.py"
npm ci
npx playwright install chromium firefox
python -B tools/browser_fixtures.py
npm run test:browser
```

Node/Playwright sólo se usan en pruebas. Se verifican geometría, curvas y cotas al cambiar de escala; piezas esbeltas; instalación limpia; presupuestos de ejecución; controles del visor; 24 ángulos en tres modelos; SMIL, movimiento reducido y pantalla de 320 px. La matriz CI configura Python 3.10/3.14 en Windows, Linux y macOS, y Chromium/Firefox en Linux. Su configuración sigue las guías oficiales de [Actions](https://github.com/actions/setup-python) y [Playwright](https://playwright.dev/docs/ci); configurar la matriz no significa haberla ejecutado.

## Empaquetar e instalar

```sh
python -B tools/release.py
python -B tools/install_skill.py dist/proyecciones-svg-1.0.0-rc.1.zip --skills-dir RUTA_A_CODEX/skills
```

El ZIP es reproducible e incluye un manifiesto con SHA-256. El instalador comprueba rutas y sumas antes de escribir. Para actualizar una instalación existente añade `--update`: conserva la versión previa en `skill-backups/`, fuera de la carpeta de descubrimiento de skills. Las sumas detectan alteraciones, pero no autentican por sí solas al distribuidor.

Para volver a una release anterior, instala su ZIP con `--update`; la versión reemplazada también queda respaldada.

Antes de una publicación estable: ejecutar la matriz remota completa, revisar la evidencia de aceptación, elegir licencia y canal de distribución. Esta preparación no crea un repositorio remoto ni publica una release.
