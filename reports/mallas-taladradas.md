# Mallas con cuatro taladros comunicados

25 de octubre de 2026. Ampliación local en desarrollo; la release y la instalación estable 1.1.0 no se modifican.

## Entrega y geometría

`assets/cuatro-taladros.json` conserva el contorno irregular, cubierta inclinada y los cuatro cilindros concurrentes. La pieza mide **80 × 60 × 36 mm**, con diámetros nominales **12, 8, 6 y 4 mm**. Se generan GLB, 3MF y STL junto a las tres vistas, vista oblicua, giro SVG, cortes, visor, JSON y `.cota`.

La representación común contiene **552 vértices y 1128 triángulos**, una única superficie cerrada de género 7 y ocho bocas comunicadas. Su volumen facetado es **112947,08186843421 mm³**. Manifold 3.5.4 calcula cuerpo menos unión de cilindros inscritos; no se conservan paredes enterradas en los otros conductos. El cálculo normalizado evita que las decisiones dependan de la escala física.

Con `--mesh-tolerance-mm 0.02` se usan 40, 32, 32 y 32 segmentos. La flecha radial máxima es **0,019261093311212285 mm** antes de cuantizar el formato. Este límite radial no es una cota de distancia de todas las intersecciones/bocas oblicuas ni una tolerancia de fabricación. Los SVG conservan sus curvas y cotas originales; Cota conserva su árbol CSG y su propia resolución.

La previsualización local carga el GLB real en dos vistas: completa y con recorte visual ajustable. El recorte no añade tapa ni cambia los archivos descargables. Incluye el visor vectorial y descargas individuales y conjuntas. La biblioteca está en `build/cuatro-taladros-mallas/`, con `cuatro-taladros-kit.zip`; se puede servir en `http://127.0.0.1:8781/`.

## Validación realizada

- **Python 3.10.20 y 3.14.6 en Windows AMD64:** 156 pruebas por intérprete, 121 de geometría y 35 de distribución, sin errores, fallos ni omisiones. Se incluyen nueve pruebas específicas de mallas taladradas, integración simultánea de todos los productos e instalación del paquete en una carpeta limpia.
- **Lecturas independientes de GLB/3MF/STL:** aristas compartidas con orientación opuesta, característica de Euler −12, volumen y unidades. Se comprueban todos los siete ejemplos taladrados, puntos de vacío en cada conducto y en el cruce, material retenido, puntos seudoaleatorios contra las ecuaciones originales y ausencia de triángulos enterrados. Se prueba convergencia de volumen y escalas de `1e-8` a `1e6` con tolerancia proporcional, además de cambios cm/mm/m.
- **Conservación:** activar los tres exportadores no cambia los bytes de vistas, ángulo, giro, cortes, JSON, visor ni `.cota` generados con los mismos parámetros. Los errores de geometría, precisión o presupuesto conservan las entregas previas durante el cálculo.
- **glTF-Validator 2.0.0-dev.3.10:** GLB sin errores ni avisos.
- **PrusaSlicer 2.9.6:** importa 3MF y STL con `manifold = yes`, un componente y medidas 80 × 60 × 36 mm. Su volumen informado, 112947,148438 mm³, está dentro del error relativo de `1e-6` exigido al importador. No se laminó ni imprimió físicamente.
- **Navegador:** ambos GLB cargan con dimensiones contrastadas; giro mediante arrastre, control de recorte a 15/20 mm y 24 ángulos del visor SVG comprobados. No hay desbordamiento horizontal en la ventana usada.

Los intérpretes usaron Manifold 3.5.4 con NumPy 2.2.6 (Python 3.10) y 2.5.4 (Python 3.14). GLB y STL resultaron idénticos entre ambos; el 3MF tiene la misma topología y diferencias máximas de coordenadas de `3,552713678800501e-14 mm`, por lo que no se afirma igualdad binaria del 3MF entre intérpretes.

El ZIP fuente de desarrollo es idéntico en ambos: **367749 bytes**, **57 archivos** en el manifiesto y SHA-256 `c7042d5d3714753ee4ad3a21f37ed705dcc6c0d6d75785237b866833045895f3`. Conserva temporalmente el campo 1.1.0 y no debe distribuirse como la release oficial con ese número. El kit de modelos tiene SHA-256 `5c52f1a585118d3943b4e0f53ef3605ef5d9ae13cc13b02e0948bba691b58750`.

La [evidencia archivada](mallas-taladradas-validacion-local.json) contiene informes, dependencias, sumas y validaciones externas. Las pruebas se ejecutaron sobre cambios locales sin commit; `source_base_commit` identifica su base y las sumas identifican el paquete probado.

## Uso y límites

```sh
python -m pip install --only-binary=:all: -r skills/proyecciones-svg/requirements-mesh.txt
python -B tools/verify.py --report-dir build/validacion-mallas-taladradas/repeticion
npm ci
python -B tools/build_bored_asset_example.py
node tools/check_asset_formats.cjs build/cuatro-taladros-mallas
python -B tools/check_print_assets.py --folder build/cuatro-taladros-mallas --slicer RUTA_A_PRUSASLICER_CONSOLE
python -m http.server 8781 --bind 127.0.0.1 --directory build/cuatro-taladros-mallas
```

La dependencia es opcional y sólo se carga para exportar mallas taladradas. Se instaló en entornos virtuales dentro de `build/`, sin modificar el Python global ni la skill estable instalada. SVG, cortes y Cota siguen funcionando sin ella.

Se mantienen las restricciones de los constructores analíticos: hasta cuatro cilindros pasantes, bocas completas dentro de las caras y separadas entre sí, y ejes concurrentes para los cruces. No se añaden agujeros ciegos, salidas laterales ni reparación de mallas CAD arbitrarias. Las mallas taladradas admiten hasta 32768 vértices y 65536 triángulos; cada cilindro usa de 32 a 512 segmentos, y una precisión que requiera más se rechaza explícitamente.

La CI se preparó para instalar la dependencia opcional y validar este GLB; **no se ejecutó remotamente**. Linux/macOS, publicación, perfiles de motor/impresora e impresión física siguen pendientes para esta ampliación. [Contrato completo](../skills/proyecciones-svg/references/assets-mallas.md).
