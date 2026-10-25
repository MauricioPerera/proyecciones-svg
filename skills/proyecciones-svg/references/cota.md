# Exportación opcional a Cota

Usa esta salida cuando el usuario pida editar el volumen en Cota. El generador entrega `modelo.cota` además de los SVG seleccionados, `modelo.json`, `informe.json` y el visor si se solicita. El cálculo SVG sigue usando únicamente Python estándar. No instala ni abre Cota automáticamente.

```sh
python <skill>/scripts/generar.py modelo.json --output-dir salida --viewer --export-cota
```

La cuña y la pieza de cuatro taladros se generan así:

```sh
python <skill>/scripts/generar.py <skill>/assets/cuna.json --output-dir salida-cuna --frames 24 --viewer --export-cota
python <skill>/scripts/generar.py <skill>/assets/cuatro-taladros.json --output-dir salida-cuatro --frames 24 --viewer --export-cota
```

## Unidades y orientación

- El documento Cota usa milímetros. Se reconocen `mm`, `cm`, `m`, `km`, `um`, `µm`, `μm`, `nm`, `in` y `ft`, sin distinguir mayúsculas.
- Para `u` u otra unidad personalizada, pide la equivalencia si no está dada. Ejemplo: `--export-cota --cota-unit-mm 10` significa que una unidad del JSON equivale a 10 mm. La opción también permite sustituir explícitamente una equivalencia conocida.
- Se mantienen `x=ancho`, `y=profundidad` y `z=altura`; el frente está en `y<0`. Se registra primer o tercer diedro según `--system`.
- La conversión afecta sólo al documento Cota. El JSON y las cotas SVG conservan sus unidades originales. Cambiar la escala de una lámina o el zoom no cambia las medidas físicas del modelo.

## Representación y compatibilidad

El destino comprobado es Cota 1.0.0, esquema JSON 1. La matriz de la versión 1.1.0 instala el ZIP de entrega y comprueba la cuña y los cuatro taladros con el motor Cota en Windows, Linux y macOS, con Python 3.10 y 3.14. Su implementación de referencia está en [mxchristian17/cota](https://github.com/mxchristian17/cota/tree/e43e37de4017e6b87f72180b0f4e6162943f4880). Es un formato de intercambio ligado a esa versión, no una API CAD estable.

- `extrusion` se convierte en un sólido `EXTRUDE`, con el perfil en XZ y extrusión en +Y.
- `mesh` se convierte en `MESH3D`: las caras cóncavas se triangulan y se orientan hacia afuera. No se obtiene un historial paramétrico de esa malla.
- Los bloques taladrados usan `BOX`; los cuerpos con cubierta inclinada se construyen con una extrusión recortada por una caja orientada bajo el plano de cubierta. Se evita `LOFT` en Cota 1.0.0 porque su orientación de tapas y laterales produce resultados incorrectos al perforar estas piezas. Los taladros se representan con `SUBTRACT` y cilindros orientados según sus ejes, extendidos más allá del cuerpo para atravesarlo completamente.

El archivo incluye metadatos de versión, unidades, factor de conversión y SHA-256 del JSON fuente serializado de forma canónica. `informe.json` registra también el tamaño y SHA-256 del `.cota`. La exportación participa en los presupuestos de tiempo y tamaño y en las comprobaciones de sobrescritura; si falla, no se publican los nuevos productos.

## Abrir y revisar

En Cota usa `OPEN` o Archivo → Abrir y selecciona `modelo.cota`. Revisa una vista isométrica y las vistas frontal, superior y lateral. Para verificar las medidas de la cuña del ejemplo, deben ser 60 × 40 × 30 mm; en la pieza irregular, los diámetros son 12, 8, 6 y 4 mm.

La exportación es de un solo sentido. Al editar el archivo en Cota, no se actualizan `modelo.json`, sus metadatos de origen ni los SVG existentes. Para regenerar los SVG, modifica el JSON fuente y vuelve a ejecutar la skill.

Cota evalúa los sólidos curvos mediante mallas; los cilindros exportados usan 64 segmentos radiales. Sus proyecciones, redondeos y cotas posteriores deben revisarse en esa aplicación y no heredan las garantías de las curvas SVG. Tampoco se transfieren al archivo Cota la lámina acotada ni la animación: se entregan por separado como SVG. No presentes esta exportación como un plano de fabricación ni como un intercambio CAD exacto y bidireccional. Las dimensiones o desplazamientos extremos pueden superar la precisión de malla de Cota incluso cuando el SVG original es válido.
