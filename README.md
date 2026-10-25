# Proyecciones SVG

Skill de Codex para construir un modelo geométrico a partir de una descripción, un croquis o vistas técnicas y generar alzado, planta, perfil y giros SVG. Python estándar y SVG nativo, sin motor 3D ni servicios externos.

Versión estable **1.1.0 para Windows, Linux y macOS**, licencia MIT. La matriz completa de GitHub Actions valida las seis combinaciones de plataforma/Python. Código público: [MauricioPerera/proyecciones-svg](https://github.com/MauricioPerera/proyecciones-svg). El código canónico está en `skills/proyecciones-svg`; la carpeta de skills instalada se obtiene del paquete, no se edita como segunda fuente.

| Plataforma | Python 3.10 | Python 3.14 |
| --- | --- | --- |
| Windows | Validado | Validado |
| Linux | Validado | Validado |
| macOS | Validado | Validado |

La evidencia adjunta a cada release identifica las versiones de Python, sistemas y arquitecturas efectivamente probados. No se han probado todas las versiones o arquitecturas de cada sistema operativo.

## Sitio web

La [landing de Proyecciones SVG](https://mauricioperera.github.io/proyecciones-svg-site/) explica el uso y la instalación, con cuatro ejemplos SVG interactivos y guías para usuarios técnicos y no técnicos. Su fuente está en `docs/`; se sirve como sitio estático de GitHub Pages. La skill y el instalador se pueden descargar sin iniciar sesión. Consulta [el desarrollo de la landing](docs/README.md) para regenerar los ejemplos y comprobarla localmente.

## Descarga directa

- [Skill estable 1.1.0 · ZIP](https://github.com/MauricioPerera/proyecciones-svg/releases/download/v1.1.0/proyecciones-svg-1.1.0.zip)
- [Instalador Python](https://github.com/MauricioPerera/proyecciones-svg/releases/download/v1.1.0/install_skill.py)
- [Sumas SHA-256](https://github.com/MauricioPerera/proyecciones-svg/releases/download/v1.1.0/SHA256SUMS)
- [Evidencia de la matriz completa](https://github.com/MauricioPerera/proyecciones-svg/releases/download/v1.1.0/release-readiness.json)

Guarda los archivos en la misma carpeta. Las instrucciones de la landing explican la instalación asistida con Codex y los comandos para Windows, Linux y macOS.

## Usar

Requiere Python 3.10+. Desde este repositorio:

```sh
python skills/proyecciones-svg/scripts/generar.py skills/proyecciones-svg/assets/cuatro-taladros.json --output-dir build/ejemplo --frames 72 --viewer
```

Abre `build/ejemplo/visor.html`. También se entregan tres SVG independientes, el JSON y un informe de versión, duración, tamaños y sumas. La interpretación de lenguaje/croquis la realiza el agente siguiendo `SKILL.md`; el programa recibe geometría JSON, no interpreta imágenes automáticamente.

Los modelos admitidos y sus límites están en [la skill](skills/proyecciones-svg/SKILL.md), [los contratos](skills/proyecciones-svg/references/modelos.md) y [la ejecución](skills/proyecciones-svg/references/ejecucion.md). Los planos contienen cotas generales y no certifican una pieza para fabricación.

## Exportación opcional a Cota

El código del proyecto añade `--export-cota` al generador. Produce `modelo.cota` junto a las tres vistas y el giro SVG, con la geometría convertida a milímetros y sin dependencias adicionales:

```sh
python skills/proyecciones-svg/scripts/generar.py skills/proyecciones-svg/assets/cuna.json --output-dir build/cuna-cota --viewer --export-cota
python skills/proyecciones-svg/scripts/generar.py skills/proyecciones-svg/assets/cuatro-taladros.json --output-dir build/cuatro-cota --viewer --export-cota
```

Esta opción está incluida en la versión estable 1.1.0. El intercambio es de un solo sentido hacia Cota 1.0.0, esquema 1; las ediciones posteriores en Cota no regeneran los SVG. Para unidades relativas usa `--cota-unit-mm N` con una equivalencia explícita. Consulta [el formato, las unidades y los límites](skills/proyecciones-svg/references/cota.md).

La matriz de CI exige comprobar el ZIP exacto con el motor de Cota 1.0.0 en las seis combinaciones de Windows/Linux/macOS y Python 3.10/3.14. La evidencia queda adjunta a la release; Node y Cota sólo se necesitan para esta validación de desarrollo.

La suite Python comprueba medidas, ejes, unidades, conservación exacta de los SVG, presupuestos y sobrescritura. Opcionalmente, con un checkout de Cota 1.0.0 y sus dependencias de desarrollo ya instaladas, ejecuta `python -B tools/check_cota_interop.py --cota-dir RUTA_A_COTA`. Esta comprobación carga los documentos en el motor real, contrasta las tres vistas y el volumen de la cuña, el volumen bajo la cubierta inclinada y puntos de material/vacío en los cuatro conductos. Usa archivos temporales y no instala dependencias ni altera el código de Cota.

## Comprobar

```sh
python -B tools/verify.py
npm ci
npx playwright install chromium firefox
python -B tools/browser_fixtures.py
npm run test:browser
```

Node/Playwright sólo se usan en pruebas. Se verifican geometría, curvas y cotas al cambiar de escala; piezas esbeltas; instalación limpia; presupuestos de ejecución; controles del visor; 24 ángulos en tres modelos; SMIL, movimiento reducido y pantalla de 320 px. El perfil de publicación predeterminado `all` exige seis informes del mismo commit, ninguna prueba omitida, seis combinaciones de navegador/modelo y ZIP idéntico entre plataformas. La versión 1.1.0 ejecuta 99 pruebas Python y dos pruebas de intercambio Cota por combinación, más 144 comprobaciones de ángulo en Chromium/Firefox sobre Linux.

La validación también puede ejecutarse localmente y por SSH. El perfil histórico `windows-linux` conserva la posibilidad de comprobar cuatro casos, pero no aprueba la matriz completa ni el alcance de 1.1.0. La configuración de CI sigue las guías oficiales de [Actions](https://github.com/actions/setup-python) y [Playwright](https://playwright.dev/docs/ci).

## Empaquetar e instalar

```sh
python -B tools/release.py
python -B tools/install_skill.py dist/proyecciones-svg-1.1.0.zip --skills-dir RUTA_A_CODEX/skills
```

El ZIP usa entradas sin compresión y metadatos fijos para conservar los mismos bytes entre sistemas y versiones de zlib; incluye licencia y manifiesto con SHA-256. El instalador comprueba rutas y sumas antes de escribir. Para actualizar una instalación existente añade `--update`: conserva la versión previa en `skill-backups/`, fuera de la carpeta de descubrimiento de skills. Las sumas detectan alteraciones, pero no autentican por sí solas al distribuidor.

Para volver a una release anterior, instala su ZIP con `--update`; la versión reemplazada también queda respaldada.

Para preparar un borrador desde `main` limpio y sincronizado, espera a que la matriz completa y `Ready for release` aprueben ese mismo commit. Ejecuta:

```sh
python -B tools/prepare_release.py --repo MauricioPerera/proyecciones-svg --create-draft
```

Comprueba la ejecución aprobada, los seis casos, el commit y las sumas antes de adjuntar ZIP, licencia, instalador, notas y evidencia. Requiere GitHub CLI autenticado; no ejecuta Actions. Para evidencia reunida fuera de Actions, usa `--validation-dir RUTA_A_LA_MATRIZ` con el perfil predeterminado `all`. El comando crea un borrador y no lo publica. Las notas están en `releases/1.1.0.md`.

El bloqueo inicial de Actions por presupuesto quedó resuelto tras hacer público el repositorio. La [primera matriz completa aprobada](https://github.com/MauricioPerera/proyecciones-svg/actions/runs/40043435677) reprodujo el ZIP 1.0.0 sin cambiar sus bytes; su [evidencia permanente](reports/1.0.0-full-matrix.json) conserva los seis resultados. La [matriz completa de 1.0.1](reports/1.0.1-stable.md) también está aprobada: incorpora macOS en los metadatos distribuidos y conserva la evidencia del paquete publicado. `--local-only` permite generar archivos pendientes sin aprobarlos ni crear borrador. El [alcance original 1.0.0](reports/1.0.0-stable.md) y el [historial previo de CI](reports/1.0.0-ci.md) se conservan como antecedentes.
