# Modelo y ejecución

Usa Python 3.10 o posterior; el helper no instala paquetes. Resuelve `scripts/proyectar.py` desde el directorio de esta skill, independientemente del directorio de trabajo. En Windows usa el Python disponible o el runtime de dependencias de Codex.

## Perfil extruido

`profile` es un polígono simple de puntos `[x,z]`, sin repetir el primero al final. `depth` es la longitud en `y`, desde `y=0`. Se aceptan los dos sentidos de recorrido y perfiles cóncavos sin agujeros.

```json
{
  "name": "Pieza escalonada",
  "units": "cm",
  "type": "extrusion",
  "profile": [[0,0],[6,0],[6,2],[2,2],[2,4],[0,4]],
  "depth": 4,
  "assumptions": ["Perfil constante y pieza maciza."]
}
```

## Poliedro general

`vertices` contiene `[x,y,z]`. `faces` contiene índices de vértices, comenzando en cero, en orden alrededor de cada cara; no repitas el primer índice. Las caras deben cerrar una frontera orientada: cada arista tiene exactamente dos caras con sentidos opuestos. Se aceptan caras cóncavas simples. No se aceptan caras no planas, agujeros dentro de una cara ni intersecciones entre caras. El validador comprueba el cierre topológico y cada cara; la ausencia de intersecciones entre caras sigue siendo responsabilidad de la construcción y revisión.

```json
{
  "name": "Tetraedro",
  "units": "u",
  "type": "mesh",
  "vertices": [[0,0,0],[4,0,0],[0,3,0],[0,0,2]],
  "faces": [[0,2,1],[0,1,3],[1,2,3],[2,0,3]],
  "assumptions": []
}
```

No concatenes cajas superpuestas y sus caras internas en `mesh`. Construye su frontera exterior o usa una extrusión cuando corresponda. El helper no realiza booleanas CAD.

## Comandos

`<skill>` representa el directorio absoluto de la skill. `<salida>` es una carpeta de trabajo del usuario; no generes resultados dentro de los recursos instalados.

```sh
python <skill>/scripts/proyectar.py modelo.json --output-dir <salida> --mode sheet
python <skill>/scripts/proyectar.py modelo.json --output-dir <salida> --mode view --azimuth 45 --elevation 35.2643897 --hidden omit
python <skill>/scripts/proyectar.py modelo.json --output-dir <salida> --mode animation --frames 96 --seconds 8 --hidden omit
python <skill>/scripts/proyectar.py modelo.json --output-dir <salida> --mode all --system first
```

- `--mode sheet|view|animation|all`: genera `vistas.svg`, `angulo.svg`, `giro.svg` según el modo. Predeterminado: `sheet`.
- `--system third|first`: sólo afecta a la disposición del plano; predeterminado `third`.
- `--hidden dash|omit`: predeterminado `dash`; para un giro de lectura limpia suele convenir `omit`.
- `--azimuth`: 0° frente, 90° lado derecho, 180° parte trasera, 270° lado izquierdo.
- `--elevation`: 0° a nivel horizontal, 90° desde arriba, −90° desde abajo.
- `--frames`: entre 8 y 240 muestras vectoriales; predeterminado 72.
- `--seconds`: duración positiva; predeterminado 6.
- `--sweep`: giro horizontal, predeterminado 360°. `--loop` repite; sin él hace un giro y conserva el último fotograma.
- `--force`: permite reemplazar archivos de salida existentes. Sin él se detiene antes de modificar archivos que colisionen.

El JSON original, incluidos los supuestos, queda en `<metadata>` de cada SVG. Las cotas muestran los tamaños máximos de la pieza en las unidades originales, sin inferir tolerancias ni cotas interiores. Conserva también el JSON como archivo independiente para editarlo.

Las medidas y diámetros se rotulan con hasta 12 cifras significativas y notación científica cuando corresponde. Este formato es independiente de los cuatro decimales de las coordenadas de pantalla. No se redondean a cero las medidas pequeñas por el umbral geométrico de SVG ni se cambian automáticamente las unidades del JSON.

El coste de ocultación crece con aristas × triángulos × fotogramas. Está pensado para piezas pequeñas: comienza con un fotograma y reduce detalles o muestras si el modelo es grande.

Para comprobar regresiones de los helpers, ejecuta `python -m unittest discover -s <skill>/scripts -p "test_*.py"`. `test_escalas.py` contrasta las curvas y generatrices de vaciados reescalados con ecuaciones independientes del JSON y verifica las cotas emitidas por todos los constructores, incluido un bloque en micrómetros expresado en metros. Estas pruebas no sustituyen la revisión de una geometría nueva ni garantizan estabilidad para valores próximos a los límites de representación de coma flotante.

## Bloque con un taladro cilíndrico analítico

Este caso usa `scripts/taladro_cilindrico.py`, no el constructor poliédrico. El eje es `z`, el taladro atraviesa toda la altura y el círculo debe quedar completamente dentro de la base. Su centro puede ser excéntrico.

```json
{
  "name": "Bloque con agujero cilíndrico pasante",
  "units": "cm",
  "type": "block_with_bore",
  "size": [8,6,2],
  "bore": {"axis":"z","center":[4,3],"diameter":3,"through":true},
  "assumptions": ["Taladro vertical pasante, sin avellanados."]
}
```

```sh
python <skill>/scripts/taladro_cilindrico.py modelo.json --output-dir <salida> --mode all --loop
```

Acepta las opciones de salida, sistema y ocultas del constructor general. Sus valores predeterminados son modo `all`, elevación 45°, 120 muestras y 10 segundos; la elevación está limitada a 0..90°. Los SVG conservan círculos/elipses y comandos de arco `A`. En planta se ve el círculo y su diámetro; en alzado/perfil, los límites ocultos del taladro y su eje. No se aproxima el cilindro con una malla de caras planas.

## Base irregular convexa, cubierta inclinada y taladro

Usa `scripts/pieza_taladrada.py`. `footprint` es un polígono estrictamente convexo en `[x,y]`, sin puntos colineales ni primer punto repetido. La base inferior es `z=0`; la cubierta es un único plano `z=offset+slope_x*x+slope_y*y`, positivo en toda la base. Se admiten taladros pasantes verticales o inclinados y centros excéntricos; ambas bocas completas deben quedar dentro de las caras, sin salidas laterales.

```json
{
  "name": "Pieza irregular con taladro",
  "units": "cm",
  "type": "sloped_prism_with_bore",
  "footprint": [[0,0],[7,0],[8,1.5],[8,5],[6,6],[0,6]],
  "roof": {"offset":1.5,"slope_x":0.2,"slope_y":0.1},
  "bore": {"axis":"z","center":[4,3],"diameter":3,"through":true},
  "assumptions": ["Cubierta plana inclinada; taladro vertical pasante."]
}
```

```sh
python <skill>/scripts/pieza_taladrada.py modelo.json --output-dir <salida> --mode all --loop
```

Opciones como en el constructor de bloque taladrado, con elevación predeterminada de 50°. Mantiene las intersecciones entre cilindro y planos como círculos unitarios transformados afínmente, y los tramos del borde inferior como arcos SVG. No admite bases cóncavas, cubiertas con varios planos, taladros ciegos ni salidas laterales: esos casos requieren otra construcción y comprobación. El contorno exterior es convexo y su ocultación sigue siendo válida al vaciar el cilindro interior. La ocultación de los bordes del agujero se calcula por separado mediante rayos y el plano inclinado.

Para inclinar el cilindro, sustituye `bore` por:

```json
"bore": {
  "axis":"inclined",
  "center":[3.4,2.6],
  "direction":[0.5,0.25,1],
  "diameter":3,
  "through":true
}
```

`center` es el punto `[x,y]` donde el eje atraviesa la base `z=0`. `direction` es un vector espacial no nulo, no necesita estar normalizado y debe tener componente `z` positiva. El diámetro se mide en un plano perpendicular al eje, no sobre las elipses de entrada o salida. La dirección del ejemplo forma aproximadamente 29,21° con la vertical. El código rechaza ejes paralelos a la base o a la cubierta, bocas que se tocan entre sí y elipses que cortan paredes laterales. En las tres vistas se representa la proyección real del eje; en planta ya no debe suponerse un círculo.

## Dos taladros cruzados y comunicados

Usa `type: crossed_bores`, conserva `footprint` y `roof`, y sustituye `bore` por una lista `bores` de exactamente dos taladros con el mismo contrato individual. Deben tener diámetros iguales, ejes no paralelos que se intersecan y cuatro bocas independientes. El constructor comprueba que las dos curvas de intersección completas queden estrictamente dentro de la pieza. Consulta [taladros-cruzados.md](taladros-cruzados.md) para la geometría y los límites.

El ejemplo completo está en `assets/taladros-cruzados.json`. El diámetro de ambos agujeros es 1,2 cm y los ejes se cruzan en `(4,3,1.5)` cm.

```sh
python <skill>/scripts/taladros_cruzados.py modelo.json --output-dir <salida> --mode all --loop
```

Las opciones coinciden con `pieza_taladrada.py`: elevación 50°, 120 fotogramas y 10 segundos por defecto. No se aceptan diámetros diferentes, ejes alabeados, bocas que se fusionan en las caras ni intersecciones que cortan la superficie exterior.

## Diámetros distintos en dos taladros cruzados

Usa `type: unequal_crossed_bores`, con el mismo contrato de cuerpo y lista `bores`, y ejecuta:

```sh
python <skill>/scripts/taladros_desiguales.py modelo.json --output-dir <salida> --mode all --loop
```

El ejemplo `assets/taladros-desiguales.json` mantiene los ejes anteriores y usa diámetros 1,2 y 0,8 cm. Los ejes deben intersecarse y las cuatro bocas permanecer separadas. Un límite analítico conservador certifica que el cruce completo es interior; puede rechazar geometrías muy próximas a las caras aunque algunos puntos muestreados parezcan caber. No admite ejes alabeados ni radios casi iguales (diferencia relativa menor que 0,0001); para radios exactamente iguales usa el constructor anterior.

Las bocas siguen siendo elipses analíticas. La curva de intersección no plana se calcula en el espacio y se aproxima con Bézier en el SVG; el clip del volumen común usa una envolvente poligonal 2D adaptativa. Ambos declaran una tolerancia nominal de 0,025 píxeles del SVG y se comprueban mediante muestras adicionales. Esto no representa una tolerancia dimensional de fabricación. Detalles y fórmulas en [taladros-desiguales.md](taladros-desiguales.md).

## Tres taladros de diámetros diferentes

Usa `type: triple_crossed_bores` y una lista `bores` de exactamente tres taladros del mismo contrato. Sus diámetros deben ser distintos, los tres ejes pasar por un mismo punto interior y las seis bocas quedar separadas. Cada cruce por parejas debe satisfacer el margen interior conservador del constructor de dos radios diferentes.

```sh
python <skill>/scripts/tres_taladros.py modelo.json --output-dir <salida> --mode all --loop
```

Opciones como en los otros constructores de cruces. El ejemplo `assets/tres-taladros.json` usa diámetros 1,2/0,8/0,6 cm y cruce común `(4,3,1.5)` cm. Lee [tres-taladros.md](tres-taladros.md) para el recorte por el tercer cilindro y la transparencia con dos cambios de conducto. Se mantiene la aproximación de curvas y clips 2D con tolerancia nominal de 0,025 píxeles del SVG. No admite tres radios iguales, ejes alabeados, cruces en puntos separados o bocas fusionadas.

## Cuatro taladros de diámetros diferentes

Usa `type: quadruple_crossed_bores` y exactamente cuatro elementos en `bores`, con diámetros diferentes y ejes concurrentes. Conserva el contrato individual, el cuerpo convexo y las ocho bocas separadas. Cada una de las seis parejas debe cumplir el margen interior conservador del constructor de dos radios distintos.

```sh
python <skill>/scripts/cuatro_taladros.py modelo.json --output-dir <salida> --mode all --loop
```

El ejemplo `assets/cuatro-taladros.json` conserva los tres primeros taladros, añade uno de 0,4 cm desde la dirección opuesta al de 0,6 cm y mantiene el cruce `(4,3,1.5)` cm. Las opciones de salida son las mismas. Lee [cuatro-taladros.md](cuatro-taladros.md) para el recorte por varios cilindros y la conectividad completa de los intervalos. La tolerancia nominal de curvas y clips sigue siendo 0,025 píxeles del SVG. No admite diámetros repetidos o casi iguales, ejes alabeados, puntos de cruce separados ni bocas fusionadas.
