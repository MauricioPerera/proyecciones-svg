# Proyecciones SVG

Skill de Codex para construir un modelo geométrico a partir de una descripción, un croquis o vistas técnicas y generar alzado, planta, perfil y giros SVG. Python estándar y SVG nativo, sin motor 3D ni servicios externos.

Versión estable **1.2.0 para Windows, Linux y macOS**, licencia MIT. La matriz completa de GitHub Actions valida las seis combinaciones de plataforma/Python. Código público: [MauricioPerera/proyecciones-svg](https://github.com/MauricioPerera/proyecciones-svg). El código canónico está en `skills/proyecciones-svg`; la carpeta de skills instalada se obtiene del paquete, no se edita como segunda fuente.

El [estado formal del proyecto](ESTADO.md) distingue la release publicada, la instalación local y los cortes y las mallas incluidos en 1.2.0, con su validación, límites y pendientes de publicación.

| Plataforma | Python 3.10 | Python 3.14 |
| --- | --- | --- |
| Windows | Validado | Validado |
| Linux | Validado | Validado |
| macOS | Validado | Validado |

La evidencia adjunta a cada release identifica las versiones de Python, sistemas y arquitecturas efectivamente probados. No se han probado todas las versiones o arquitecturas de cada sistema operativo.

## Sitio web

La [landing de Proyecciones SVG](https://mauricioperera.github.io/proyecciones-svg-site/) explica el uso y la instalación, con cuatro ejemplos SVG interactivos y guías para usuarios técnicos y no técnicos. Su fuente está en `docs/`; se sirve como sitio estático de GitHub Pages. La skill y el instalador se pueden descargar sin iniciar sesión. Consulta [el desarrollo de la landing](docs/README.md) para regenerar los ejemplos y comprobarla localmente.

## Descarga directa

- [Skill estable 1.2.0 · ZIP](https://github.com/MauricioPerera/proyecciones-svg/releases/download/v1.2.0/proyecciones-svg-1.2.0.zip)
- [Instalador Python](https://github.com/MauricioPerera/proyecciones-svg/releases/download/v1.2.0/install_skill.py)
- [Sumas SHA-256](https://github.com/MauricioPerera/proyecciones-svg/releases/download/v1.2.0/SHA256SUMS)
- [Evidencia de la matriz completa](https://github.com/MauricioPerera/proyecciones-svg/releases/download/v1.2.0/release-readiness.json)

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

Esta opción está incluida en la versión estable 1.2.0. El intercambio es de un solo sentido hacia Cota 1.0.0, esquema 1; las ediciones posteriores en Cota no regeneran los SVG. Para unidades relativas usa `--cota-unit-mm N` con una equivalencia explícita. Consulta [el formato, las unidades y los límites](skills/proyecciones-svg/references/cota.md).

La matriz de CI exige comprobar el ZIP exacto con el motor de Cota 1.0.0 en las seis combinaciones de Windows/Linux/macOS y Python 3.10/3.14. La evidencia queda adjunta a la release; Node y Cota sólo se necesitan para esta validación de desarrollo.

La suite Python comprueba medidas, ejes, unidades, conservación exacta de los SVG, presupuestos y sobrescritura. Opcionalmente, con un checkout de Cota 1.0.0 y sus dependencias de desarrollo ya instaladas, ejecuta `python -B tools/check_cota_interop.py --cota-dir RUTA_A_COTA`. Esta comprobación carga los documentos en el motor real, contrasta las tres vistas y el volumen de la cuña, el volumen bajo la cubierta inclinada y puntos de material/vacío en los cuatro conductos. Usa archivos temporales y no instala dependencias ni altera el código de Cota.

## Cortes opcionales

El código del proyecto añade `--sections` para obtener secciones SVG analíticas de cuerpos convexos, con o sin taladros. Esta opción está incluida desde 1.2.0:

```sh
python skills/proyecciones-svg/scripts/generar.py skills/proyecciones-svg/assets/cuatro-taladros.json --output-dir build/cuatro-cortes --sections --viewer --export-cota
```

Añade `cortes.svg` y los controles de guías al visor, conservando las tres vistas, el giro y el volumen completo `.cota`. La cuña también admite cortes. Los planos automáticos de los cuatro taladros pasan por el cruce de sus ejes; se pueden especificar de uno a cuatro planos en el JSON. Se mantienen las unidades del modelo y se prueban factores de escala de `1e-8` a `1e6`, además de conversiones de unidades y conservación de los demás productos. [Contrato, interpretación y límites de los cortes](skills/proyecciones-svg/references/cortes.md).

## Prototipo genérico para videojuegos e impresión

La versión 1.2.0 añade `--export-glb`, `--export-3mf` y `--export-stl`, conservando SVG y Cota. Los poliedros sin vaciados usan Python estándar y una malla común; los constructores taladrados requieren Manifold como dependencia opcional. GLB emplea metros con Y arriba, y 3MF/STL se generan en milímetros con Z arriba. Para unidades relativas usa `--unit-mm N`, también aplicado a Cota. Se admiten extrusiones simples (incluidos perfiles cóncavos como una escalera), mallas convexas y hasta cuatro taladros pasantes comunicados.

```sh
python -B skills/proyecciones-svg/scripts/generar.py skills/proyecciones-svg/assets/modulos/rampa.json --output-dir build/rampa-mallas --viewer --export-glb --export-3mf --export-stl --export-cota
```

La biblioteca inicial contiene rampa, bloque y escalera de 40 × 40 mm y altura máxima de 20 mm. Los formatos se mantienen independientes del motor y de la impresora. No incluyen colisiones, animación de personaje, perfil de laminado ni G-code. [Contrato de mallas y unidades](skills/proyecciones-svg/references/assets-mallas.md).

La galería local abre los GLB y compone una escena con esos mismos módulos. Para construirla y comprobar formatos con las dependencias de desarrollo instaladas:

```sh
npm ci
python -B tools/build_asset_examples.py
node tools/check_asset_formats.cjs
python -m http.server 8780 --bind 127.0.0.1 --directory build/prototipo-assets
```

Abre `http://127.0.0.1:8780/`. Incluye descargas individuales, la biblioteca ZIP, las tres vistas y el giro SVG. Opcionalmente, `python -B tools/check_print_assets.py --slicer RUTA_A_PRUSASLICER_CONSOLE` comprueba con un laminador real las seis mallas 3MF/STL: cierre, medidas, volumen y un único componente. Esa comprobación no lamina ni imprime el objeto.

Para añadir taladros a las mallas y construir la demostración de cuatro conductos:

```sh
python -m pip install --only-binary=:all: -r skills/proyecciones-svg/requirements-mesh.txt
python -B tools/build_bored_asset_example.py
python -m http.server 8781 --bind 127.0.0.1 --directory build/cuatro-taladros-mallas
```

La opción `--mesh-tolerance-mm` controla la flecha radial de los cilindros facetados; no es una tolerancia de fabricación ni modifica las curvas SVG o el archivo Cota. El [contrato de mallas](skills/proyecciones-svg/references/assets-mallas.md) describe las unidades, topología y límites. La suite completa de desarrollo requiere la dependencia opcional.

## Comprobar

```sh
python -m pip install --only-binary=:all: -r skills/proyecciones-svg/requirements-mesh.txt
python -B tools/verify.py
npm ci
npx playwright install chromium firefox
python -B tools/browser_fixtures.py
npm run test:browser
```

Node/Playwright sólo se usan en pruebas. Se verifican geometría, curvas y cotas al cambiar de escala; piezas esbeltas; instalación limpia; presupuestos de ejecución; controles del visor; 24 ángulos en tres modelos; SMIL, movimiento reducido y pantalla de 320 px. El perfil de publicación predeterminado `all` exige seis informes del mismo commit, ninguna prueba omitida, seis combinaciones de navegador/modelo y ZIP idéntico entre plataformas. La versión 1.2.0 ejecuta 159 pruebas Python y dos pruebas de intercambio Cota por combinación, más 144 comprobaciones de ángulo en Chromium/Firefox sobre Linux.

La batería adversarial también entra en `tools/verify.py`. Para ejecutarla por separado con semilla reproducible y guardar su informe:

```sh
python -B tools/adversarial.py --seed 20261025 --output build/adversarial/report.json
```

Incluye 18 pruebas y 230 subcasos con la semilla predeterminada: planos aleatorios contrastados con ecuaciones independientes, cambios de escala, normales entre `1e-300` y `1.7e308`, orígenes alejados dentro del mismo plano, cortes muy finos, tangencias, permutaciones de taladros, entradas inválidas, textos con marcas HTML y fallos de presupuesto/E/S. El informe registra semilla, intérprete y sumas del código. No certifica CAD ni sustituye las pruebas de navegador. La publicación continúa siendo atómica por archivo: una falla de E/S durante la sustitución puede dejar archivos de dos entregas; la batería comprueba y documenta este límite.

La validación también puede ejecutarse localmente y por SSH. El perfil histórico `windows-linux` conserva la posibilidad de comprobar cuatro casos, pero no aprueba la matriz completa ni el alcance de 1.2.0. La configuración de CI sigue las guías oficiales de [Actions](https://github.com/actions/setup-python) y [Playwright](https://playwright.dev/docs/ci).

## Empaquetar e instalar

```sh
python -B tools/release.py
python -B tools/install_skill.py dist/proyecciones-svg-1.2.0.zip --skills-dir RUTA_A_CODEX/skills
```

El ZIP usa entradas sin compresión y metadatos fijos para conservar los mismos bytes entre sistemas y versiones de zlib; incluye licencia y manifiesto con SHA-256. El instalador comprueba rutas y sumas antes de escribir. Para actualizar una instalación existente añade `--update`: conserva la versión previa en `skill-backups/`, fuera de la carpeta de descubrimiento de skills. Las sumas detectan alteraciones, pero no autentican por sí solas al distribuidor.

Para volver a una release anterior, instala su ZIP con `--update`; la versión reemplazada también queda respaldada.

Para preparar un borrador desde `main` limpio y sincronizado, espera a que la matriz completa y `Ready for release` aprueben ese mismo commit. Ejecuta:

```sh
python -B tools/prepare_release.py --repo MauricioPerera/proyecciones-svg --create-draft
```

Comprueba la ejecución aprobada, los seis casos, el commit y las sumas antes de adjuntar ZIP, licencia, instalador, notas y evidencia. Requiere GitHub CLI autenticado; no ejecuta Actions. Para evidencia reunida fuera de Actions, usa `--validation-dir RUTA_A_LA_MATRIZ` con el perfil predeterminado `all`. El comando crea un borrador y no lo publica. Las notas están en `releases/1.2.0.md`.

El bloqueo inicial de Actions por presupuesto quedó resuelto tras hacer público el repositorio. La [primera matriz completa aprobada](https://github.com/MauricioPerera/proyecciones-svg/actions/runs/40043435677) reprodujo el ZIP 1.0.0 sin cambiar sus bytes; su [evidencia permanente](reports/1.0.0-full-matrix.json) conserva los seis resultados. La [matriz completa de 1.0.1](reports/1.0.1-stable.md) también está aprobada: incorpora macOS en los metadatos distribuidos y conserva la evidencia del paquete publicado. `--local-only` permite generar archivos pendientes sin aprobarlos ni crear borrador. El [alcance original 1.0.0](reports/1.0.0-stable.md) y el [historial previo de CI](reports/1.0.0-ci.md) se conservan como antecedentes.

La [versión estable 1.1.0](reports/1.1.0-stable.md) añade la exportación Cota y aprueba las seis combinaciones con el ZIP instalado y el motor Cota fijado. Sus informes y la verificación de las descargas públicas se conservan junto al repositorio y en los archivos de la release.

La [versión estable 1.2.0](reports/1.2.0-stable.md) publica cortes y mallas GLB/3MF/STL, incluidos los taladros comunicados. Sus seis entornos ejecutan 159 pruebas Python, intercambio Cota y lectura independiente de los tres formatos desde el ZIP instalado. La evidencia de CI, las descargas anónimas y la landing desplegada quedan archivadas en `reports/1.2.0-*.json`.
