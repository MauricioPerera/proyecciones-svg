# Cortes SVG opcionales

Esta opción se incluye desde la distribución 1.2.0. El cálculo usa Python estándar y SVG analítico, sin instalar Cota ni usar un motor 3D.

```sh
python <skill>/scripts/generar.py <skill>/assets/cuatro-taladros.json --output-dir salida --sections --viewer --export-cota
```

`--sections` añade `cortes.svg` a cualquier `--mode`. Con `--viewer --mode all` también incorpora el corte y el control de contornos auxiliares al HTML autónomo. Las tres vistas, el giro y `.cota` siguen derivándose del mismo modelo y no cambian al activar esta opción. El informe incluye planos, unidades y la suma del SVG. Los cortes participan en los límites de tiempo, tamaño y sobrescritura. Para cambiar la selección de productos usa otra carpeta, incluso con `--force`.

## Elegir los planos

Sin `sections` en el JSON se generan dos cortes. En los cuatro taladros, el primero contiene los ejes A y B y el segundo los ejes C y D; ambos pasan por el cruce. En tres se usan A/B y B/C; en dos, un plano común a los ejes y otro que contiene el primer eje. En un taladro se eligen dos planos que contienen su eje. En poliedros convexos sin taladros se usan planos XZ e YZ por el centro de la caja envolvente. Los planos automáticos no siempre son perpendiculares.

Para un corte concreto, añade una lista `sections` al modelo:

```json
"sections": [
  {"name": "Horizontal por el cruce", "origin": [4, 3, 1.5], "normal": [0, 0, 1]},
  {"name": "Vertical", "origin": [4, 3, 1.5], "normal": [1, 0, 0], "up": [0, 0, 1]}
]
```

En el ejemplo de cuatro taladros las coordenadas están en centímetros. El origen define un punto del plano; la normal es un vector no nulo perpendicular a él. `up` orienta el dibujo y, si se omite, se aproxima a +Z; para un corte horizontal se usa +Y. Un `up` indicado explícitamente no puede ser paralelo a la normal, en ninguna dirección. Los vectores se normalizan sin depender de su magnitud y no llevan unidades. Se admiten de uno a cuatro planos con nombres de hasta 80 caracteres válidos en XML; `sections: null` se rechaza. Cada plano debe atravesar el interior del cuerpo; un plano exterior o coincidente con una cara se rechaza. El origen declarado se conserva en los metadatos y el cálculo usa un punto equivalente cercano al cuerpo, para evitar pérdida de precisión cuando el origen está muy alejado dentro del mismo plano.

## Leer el corte

El rayado muestra material cortado y el blanco la unión de todos los vaciados. Se eliminan los bordes que quedan dentro de otro taladro: usar relleno par/impar superpuesto devolvería material falso en las zonas compartidas. Las bocas y curvas del corte se calculan por intersección con su plano, no por proyección de una vista exterior. Las cotas de ancho y alto son extensiones reales medidas en la base ortonormal del corte.

El visor permite activar guías discontinuas de cada cilindro, incluso donde su superficie queda enterrada en otro vaciado. Son auxiliares y no aristas del material. Un taladro menor puede no aportar ningún borde real en cierto corte por quedar contenido en el vaciado mayor. Los islotes de material que aparecen separados en una sección pueden seguir unidos fuera de ese plano.

## Alcance y escalas

Se admiten extrusiones y mallas convexas, bloques taladrados y prismas convexos con cubierta plana y hasta cuatro taladros del contrato habitual. Los cuerpos cóncavos conservan sus vistas y giros cuando no se pide `--sections`, pero sus cortes todavía no están implementados. No se generan superficies de fondo vistas más allá del plano: es la sección del material, no una vista con medio volumen retirado.

El cuerpo se corta con semiespacios normalizados. Un cilindro produce una elipse analítica o una franja recta si es paralelo al plano; se considera también un plano paralelo desplazado respecto del eje. Si no corta el cilindro o sólo lo toca, no se abre un vaciado de área positiva. Se rechazan planos casi paralelos con `5e-15 < |n·eje| < 1e-7` para evitar elipses mal condicionadas; ajusta la normal en esos casos.

Al escalar la geometría, escala también el origen de cada plano personalizado; no escales normales, `up` ni las pendientes de cubierta. Las cotas conservan las unidades y cifras significativas del JSON; no se convierten a milímetros. La conversión a mm se aplica sólo al `.cota`. Las pruebas comparan fronteras con la ecuación independiente del cilindro, comprueban la unión y el cuerpo, y contrastan curvas y medidas con factores `1e-8`, `1e-5`, `1` y `1e6`. Esto no certifica tolerancias de fabricación ni la precisión de malla de Cota.

El `.cota` conserva el volumen completo; no incorpora planos de sección, la lámina SVG ni su estado interactivo. Las ediciones en Cota no actualizan los cortes: regenera desde el JSON.
