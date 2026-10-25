# Prototipo genérico: módulos para videojuegos e impresión

25 de octubre de 2026. Prototipo local en desarrollo, con formatos abiertos y sin motor de juego ni impresora asignados. La release publicada y la instalación estable 1.1.0 no se modificaron.

Este informe conserva el primer hito, sin mallas taladradas. La ampliación posterior y sus nuevas pruebas están en [mallas con taladros comunicados](mallas-taladradas.md).

## Entrega

| Módulo | Envolvente | Volumen geométrico | Triángulos |
| --- | --- | --- | --- |
| Rampa | 40 × 40 × 20 mm | 16000 mm³ | 8 |
| Bloque | 40 × 40 × 20 mm | 32000 mm³ | 12 |
| Escalera de cuatro peldaños | 40 × 40 × 20 mm | 20000 mm³ | 36 |

Cada módulo incluye GLB, 3MF, STL, las tres vistas SVG, una vista oblicua, el giro SVG, el visor HTML, el JSON fuente, el informe y el archivo `.cota`. La galería abre los GLB reales y construye un recorrido con instancias de los mismos módulos. `kit-modular.zip` incluye modelos, fuentes, SVG/Cota y la previsualización local; conserva las licencias del proyecto y de Three.js.

La fuente está en `skills/proyecciones-svg/assets/modulos/`. Los exportadores están en `scripts/exportar_mallas.py` de la skill y se activan mediante `--export-glb`, `--export-3mf` y `--export-stl`. GLB usa metros con Y arriba y 3MF/STL se generan en milímetros con Z arriba. Se conserva el origen fuente. `--unit-mm` define una equivalencia común para mallas y Cota cuando hace falta.

El módulo común de mallas está separado de sus escritores de formato; admite futuros conversores sin depender de un motor de juego o un modelo de impresora. Los SVG continúan calculándose por su método vectorial original.

## Validación

- **Python 3.14.6 y 3.10.20 en Windows:** 146 pruebas por intérprete, sin fallos ni omisiones: 112 de geometría y 34 de distribución. Incluyen 13 pruebas nuevas de mallas y cuatro de integración; también se amplió la instalación limpia para comprobar los formatos nuevos.
- **glTF-Validator oficial, versión 2.0.0-dev.3.10:** los tres GLB pasan sin errores, avisos, informaciones ni sugerencias. Se añadió esta comprobación al flujo de CI; no se ejecutó CI remota en este hito.
- **PrusaSlicer 2.9.6:** seis importaciones con `--info` (3MF y STL de cada módulo), todas con `manifold = yes`, un componente, dimensiones 40 × 40 × 20 mm y el volumen esperado. Se usó una carpeta de configuración de prueba dentro de `build/`, sin cambiar preferencias del usuario.
- **Navegador:** carga de los tres GLB, cuatro lienzos 3D, medidas cargadas contrastadas con el catálogo y recorrido de 0,12 m de ancho. Se comprobó el giro interactivo mediante arrastre. La galería conserva enlaces a las tres vistas y al giro SVG.
- **Conservación:** activar las mallas no cambia los bytes de las tres vistas, la vista oblicua, el giro, el JSON, el visor SVG ni el `.cota` obtenidos con los mismos parámetros. Un corte convexo puede combinarse con todos los exportadores.
- **Precisión:** lecturas independientes de GLB/3MF/STL comprueban escala, volumen, orientación y estructura. Se prueban equivalencias mm/cm/m, escalas de `1e-8` a `1e6`, rechazo de colapsos float32 y volúmenes físicos no representables.

El ZIP de desarrollo de la skill resultó idéntico entre los dos intérpretes: 347530 bytes, 54 archivos en el manifiesto, SHA-256 `691040a6d9864f34f33e54ab2570eaca15e52b8ff5022a4831694734c85f655d`. Conserva temporalmente el campo de versión 1.1.0; es distinto de la release publicada y no debe distribuirse como ella.

El archivo de la biblioteca `kit-modular.zip` tiene SHA-256 `3d3a64ef54d83bf6590d6a6d58b2d81d70cc76f4e15cb3011a6ba44f0843a001`. El ZIP oficial de PrusaSlicer usado para validar tiene SHA-256 `5aaf22e42f95accecfa122d23a835911f289ecc2ff606db3e83d637ddcc0a209`, contrastado con el digest de su release de origen.

La [evidencia archivada](assets-validacion-local.json) conserva informes, sumas y resultados de importación. Las ejecuciones se hicieron sobre cambios locales sin commit; el campo `commit` de los informes identifica el HEAD base y se complementa con las sumas del paquete probado.

## Alcance y pendientes

El exportador inicial admite extrusiones simples, incluidos perfiles cóncavos como la escalera, y mallas convexas compatibles. Exige una sola superficie cerrada de género cero, hasta 256 vértices y 2048 triángulos. No es un reparador ni un detector universal de autointersecciones de mallas arbitrarias.

Se rechazan los taladros en estos tres exportadores: falta construir su frontera de vaciado como una malla cerrada, sin rellenar los agujeros. Las capacidades existentes de taladros SVG y Cota se conservan.

La biblioteca no incluye UV, texturas, colisiones, esqueletos ni animación de personajes. Tampoco incluye perfil de impresora, parámetros de laminado ni G-code. La comprobación en PrusaSlicer fue de importación y geometría: no se laminó ni se imprimió físicamente. Antes de fabricar hay que elegir equipo/material, revisar el laminado y comprobar la pieza real.

La validación multiplataforma del código nuevo, el versionado y la publicación siguen pendientes. El [contrato de mallas](../skills/proyecciones-svg/references/assets-mallas.md) mantiene las unidades, restricciones y comandos de uso.

## Reproducir

Desde la raíz del proyecto:

```sh
python -B tools/verify.py --report-dir build/validacion-assets/repeticion
npm ci
python -B tools/build_asset_examples.py
node tools/check_asset_formats.cjs
python -B tools/check_print_assets.py --slicer RUTA_A_PRUSASLICER_CONSOLE
python -m http.server 8780 --bind 127.0.0.1 --directory build/prototipo-assets
```

Abrir `http://127.0.0.1:8780/` para la galería. El generador de mallas necesita sólo Python; las dependencias Node y el laminador se usan para la previsualización y la validación externa.
