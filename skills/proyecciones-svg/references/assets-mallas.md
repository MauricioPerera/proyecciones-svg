# Assets genéricos y modelos para impresión

Opción incluida desde la distribución 1.2.0. SVG, cortes y Cota conservan su cálculo independiente de las mallas.

```sh
python <skill>/scripts/generar.py <skill>/assets/modulos/rampa.json --output-dir salida --viewer --export-glb --export-3mf --export-stl --export-cota
```

La fuente sigue siendo el JSON. `scripts/exportar_mallas.py` genera una representación común de vértices, triángulos, unidades y origen; los escritores de formatos trabajan sobre ella. No se reconstruye el volumen a partir de los SVG. Los poliedros sin vaciados usan Python estándar. Sólo las mallas taladradas requieren una dependencia opcional; las otras salidas se conservan.

## Formatos y coordenadas

| Salida | Unidades | Orientación | Contenido |
| --- | --- | --- | --- |
| `modelo.glb` | Metros | Y arriba, coordenadas `(x,z,-y)` | GLB 2.0 autónomo, normales planas y material de color |
| `modelo.3mf` | Milímetros declarados | Z arriba, como el JSON | 3MF Core con una malla indexada y un objeto de construcción |
| `modelo.stl` | Coordenadas exportadas en mm | Z arriba | STL binario con normales exteriores; el estándar no declara unidades |

La transformación a GLB conserva la orientación del sólido y convierte de mm a metros. El origen del modelo se conserva: el visor puede centrar la cámara, pero no desplaza los vértices del archivo. Los conversores para motores específicos pueden añadir después sus convenciones, colisiones o jerarquías.

Las medidas originales del JSON siguen en los SVG y en `modelo.json`. Se reconocen las mismas unidades físicas que Cota. Para unidades relativas o una equivalencia explícita, usa `--unit-mm N`: milímetros por unidad de origen, aplicado tanto a las mallas como a Cota si se exporta. `--cota-unit-mm` conserva su compatibilidad; si se proporcionan ambos factores deben coincidir. No uses una equivalencia distinta para cada formato de la misma pieza.

`informe.json` registra tamaños y SHA-256, límites, volumen en mm³, cantidad de vértices/triángulos, unidades y orientación. Los formatos nuevos participan en los presupuestos de tiempo, tamaño y sobrescritura. Un fallo durante el cálculo mantiene la entrega anterior; la publicación final conserva su garantía por archivo.

## Alcance inicial

Se admiten perfiles extruidos simples, incluidos perfiles cóncavos como una escalera, y `type=mesh` con cuerpo convexo. Sin taladros, la salida requiere una única superficie cerrada y conectada de género cero, orientación exterior, sin triángulos degenerados y con un ciclo válido alrededor de cada vértice. Se permiten hasta 256 vértices y 2048 triángulos, además de los límites existentes del constructor.

Se rechazan mallas cóncavas generales, geometrías que no conserven una triangulación cerrada y componentes separados. El método no es un reparador ni un detector general de autointersecciones de mallas arbitrarias.

## Taladros y vaciados comunicados

Se admiten `block_with_bore`, `sloped_prism_with_bore`, `crossed_bores`, `unequal_crossed_bores`, `triple_crossed_bores` y `quadruple_crossed_bores`, con las mismas restricciones analíticas de sus vistas: bocas completas separadas y dentro de la base/cubierta, y ejes concurrentes para los cruces. No se añaden agujeros ciegos, salidas laterales ni entradas de mallas CAD arbitrarias.

En el intérprete que ejecutará el generador, preferentemente dentro de un entorno virtual:

```sh
python -m pip install --only-binary=:all: -r <skill>/requirements-mesh.txt
python <skill>/scripts/generar.py <skill>/assets/cuatro-taladros.json --output-dir salida --frames 24 --viewer --sections --export-cota --export-glb --export-3mf --export-stl --mesh-tolerance-mm 0.02
```

La dependencia fijada es [Manifold 3.5.4](https://pypi.org/project/manifold3d/3.5.4/) con su dependencia NumPy. No se instala automáticamente. Si falta, el generador emite un error y conserva los archivos anteriores. SVG, cortes y Cota funcionan sin ella cuando no se solicitan mallas taladradas. El paquete de la skill contiene fuentes e instrucciones; no redistribuye esos binarios.

`mallas_taladradas.py` reutiliza el constructor analítico, normaliza las coordenadas y calcula **cuerpo menos unión de cilindros poligonales inscritos**. Se eliminan las paredes enterradas dentro de otro conducto. La frontera resultante debe ser única, orientada y manifold; se comprueban aristas, conectividad y ciclos de vértices. Para N conductos comunicados con 2N bocas separadas, el género esperado es `2N−1`: 1, 3, 5 o 7. Se permiten hasta 32768 vértices y 65536 triángulos en estas salidas, manteniendo los límites del cuerpo fuente y los presupuestos de tiempo/tamaño.

`--mesh-tolerance-mm` es un valor físico positivo, por defecto 0,02 mm. Determina los segmentos por cilindro mediante la flecha radial `r·(1−cos(π/n))`, con un mínimo de 32 y máximo de 512, en múltiplos de cuatro. Se rechaza una tolerancia que requiera superar el máximo; no se reduce silenciosamente la precisión. El informe registra segmentos, flecha y versión del backend. Al escalar una pieza y querer igual resolución relativa, escala también esta tolerancia.

Esta cota limita la distancia radial entre el círculo y el polígono antes de cuantizar el formato. No limita por sí sola la distancia de todas las bocas oblicuas o curvas de intersección; tampoco es una tolerancia de fabricación. El vaciado inscrito deja algo más de material que el cilindro ideal. Una mayor resolución hace converger volúmenes y superficies. Los SVG conservan sus curvas y cotas originales; el `.cota` conserva su propio árbol CSG y resolución de cilindros, sin cambios por esta opción.

GLB y STL usan posiciones float32. Se comprueba la malla cuantizada y se rechazan colapsos de vértices, degeneraciones o cambios relativos de volumen mayores que `1e-5`. No es una tolerancia de fabricación ni una garantía sobre cualquier detalle geométrico. 3MF conserva posiciones con precisión de doble representación decimal.

Para un material GLB opcional:

```json
"asset": {"base_color": [0.08, 0.55, 0.43, 1]}
```

Son componentes RGBA lineales entre 0 y 1; sólo afectan al aspecto del GLB. Este prototipo no incorpora texturas, UV, colisiones, esqueletos ni animaciones de personaje. Los SVG conservan su estilo técnico y el giro sigue mostrando la pieza rígida.

## Biblioteca inicial

`assets/modulos/` contiene rampa, bloque y escalera de 40 × 40 mm y altura máxima de 20 mm. El origen está en la esquina frontal de la base. La rampa es continua; la escalera tiene cuatro peldaños de 10 mm de huella y 5 mm de altura. Se pueden usar como miniaturas o escalar instancias uniformemente en un motor de juego.

El proyecto incluye una galería local que abre los GLB y compone un pequeño recorrido usando los mismos módulos. Construir esa galería usa Three.js como dependencia de desarrollo; no interviene en el cálculo SVG ni es necesaria para exportar las mallas.

## Comprobar y entregar

La suite completa de desarrollo requiere instalar `requirements-mesh.txt`. Los validadores de Python comprueban topología, orientación, volúmenes, medidas, cambios de escala, equivalencias físicas, precisión de formato y conservación de SVG/Cota. Para los taladros se leen los tres formatos y se comprueban los huecos mediante ángulo sólido, puntos de material/vacío contra las ecuaciones originales, ausencia de caras enterradas y convergencia. La validación externa del prototipo utiliza el validador oficial de glTF y la importación de 3MF/STL en PrusaSlicer; estas herramientas sólo son de desarrollo.

Para impresión, entregar un modelo y comprobar que el laminador lo abre no equivale a validar una impresión física. Los archivos no incluyen perfil de impresora, parámetros de laminado ni G-code. Revisa tamaño, material, orientación, espesores y ajustes del equipo elegido antes de fabricar. Mantén los SVG y el JSON como documentación de la geometría original.

Referencias de formato: [glTF 2.0](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) y [3MF Core](https://github.com/3MFConsortium/spec_core/blob/master/3MF%20Core%20Specification.md).
