---
name: proyecciones-svg
description: Genera vistas técnicas y giros SVG de poliedros y prismas con hasta cuatro taladros cilíndricos pasantes comunicados a partir de descripciones, croquis o vistas. Úsala para alzado, planta, perfil y reconstrucción sin imágenes generadas ni motores 3D.
---

# Proyecciones SVG

Construye una geometría coherente y proyéctala a SVG editable. Entrega vectores calculados, sin imágenes generadas, capturas como producto final, Blender, WebGL, Three.js, vídeo ni servicios externos. Las coordenadas espaciales son datos matemáticos; no requieren un motor 3D.

## Interpretar la entrada

- Para una descripción, identifica sólidos, medidas, unidades, vaciados y orientación del frente.
- Para un croquis, inspecciona la imagen adjunta o el archivo con las herramientas de visión disponibles. Lee las cotas antes que las proporciones del dibujo. No midas como exacto un croquis a mano alzada ni confundas una línea auxiliar con una arista.
- Para reconstruir desde vistas, cruza ancho entre alzado/planta, altura entre alzado/perfil y profundidad entre planta/perfil. Comprueba también aristas interiores y ocultas. Tres siluetas no siempre determinan un volumen único.
- Separa medidas dadas, medidas deducidas y supuestos. Si falta una medida no crítica para una demostración, usa unidades relativas y declara el supuesto. Pregunta cuando la ambigüedad cambie materialmente la forma, el frente o la intención del usuario; continúa con el trabajo independiente mientras tanto.

## Un modelo para todas las vistas

Fija `x = ancho`, `y = profundidad hacia atrás`, `z = altura`. El frente se observa desde `y < 0`.

1. Define la pieza una sola vez en un JSON reproducible. Para un perfil constante usa `extrusion`; para otros poliedros, `mesh`; para un bloque con taladro vertical pasante usa `block_with_bore`; para una base convexa con cubierta plana y taladro vertical o inclinado usa `sloped_prism_with_bore`; para dos cilindros con ejes que se cruzan usa `crossed_bores` si sus diámetros son iguales o `unequal_crossed_bores` si difieren. Para tres o cuatro diámetros distintos con ejes concurrentes usa `triple_crossed_bores` o `quadruple_crossed_bores`. Lee [references/modelos.md](references/modelos.md) para contratos y comandos.
2. Deriva las vistas y ángulos de ese modelo. No dibujes cada vista ni cada fotograma como una interpretación independiente.
3. Usa caras planas cerradas y aristas compartidas. Las triangulaciones internas y divisiones coplanares no son aristas de la pieza. No dejes caras interiores de una unión de sólidos: construye primero la frontera del volumen.
4. Para un bloque con taladro vertical pasante usa `scripts/taladro_cilindrico.py`; para una base convexa con cubierta plana y taladro vertical o inclinado, `scripts/pieza_taladrada.py`. Ambos calculan curvas analíticas, sin facetas. Las bocas deben derivarse de las intersecciones cilindro-plano; no pegues círculos horizontales sobre ellas. En el taladro inclinado el diámetro se mide perpendicular al eje y ambas bocas deben quedar enteras en la base y la cubierta. El helper general `proyectar.py` sigue siendo poliédrico. Para otras curvas, agujeros ciegos, salidas laterales o superficies libres, usa construcción analítica cuando puedas resolverla correctamente; cualquier aproximación poligonal debe ser explícita. No simules precisión CAD ni ocultes una limitación con un dibujo plausible.

El helper `scripts/proyectar.py` usa únicamente la biblioteca estándar de Python. Acepta perfiles cóncavos simples, poliedros cerrados y coordenadas negativas. Valida caras planas, índices, orientación y cierre. Calcula la ocultación de segmentos contra las caras por profundidad; no decide visibilidad únicamente por la normal de la cara ni ordena caras por su centro.

Usa preferentemente `scripts/generar.py`: selecciona el constructor según `type`, conserva el JSON fuente y crea un informe con versión, tiempos y sumas de los archivos. Ejecuta el cálculo en un proceso con presupuesto de tiempo y valida las salidas antes de publicarlas. Para el comando común, el visor portable y los límites numéricos lee [references/ejecucion.md](references/ejecucion.md). Los helpers especializados siguen disponibles para desarrollo geométrico.

Para `crossed_bores` usa `scripts/taladros_cruzados.py`: calcula la unión de los vaciados, las dos curvas de intersección internas y la visibilidad del material restante. No superpongas dos dibujos de agujeros independientes. Este caso requiere cuatro bocas separadas y el cruce completo dentro del cuerpo; lee [references/taladros-cruzados.md](references/taladros-cruzados.md) para su alcance y construcción analítica.

Para diámetros distintos usa `scripts/taladros_desiguales.py` y lee [references/taladros-desiguales.md](references/taladros-desiguales.md). La curva espacial del cruce ya no es una elipse: el SVG la aproxima con Bézier y el clip con una envolvente poligonal 2D de tolerancia nominal declarada. Conserva las bocas elípticas analíticas y la visibilidad del vaciado conjunto. No presentes esta aproximación como curva SVG exacta ni como malla de un cilindro.

Para tres diámetros distintos usa `scripts/tres_taladros.py` y lee [references/tres-taladros.md](references/tres-taladros.md). Recorta las intersecciones y generatrices enterradas en el tercer vaciado y contempla trayectos que cambian dos veces de conducto. No acumules tres dibujos independientes ni conserves como ocultas curvas que ya no pertenecen a la frontera del sólido.

Para cuatro diámetros distintos usa `scripts/cuatro_taladros.py` y lee [references/cuatro-taladros.md](references/cuatro-taladros.md). Reutiliza el cálculo común de unión: recorta cada curva por ambos cilindros restantes y contempla todos los caminos simples entre bocas, incluidos los que usan cuatro conductos. Mantén ocho bocas separadas y un único punto común a los ejes.

## Elegir la salida

- **Plano:** alzado, planta y perfil derecho a una misma escala, con nombres, unidades y cotas generales reales. Respeta el sistema indicado por el usuario. Si no lo indica, usa tercer diedro y rotúlalo: planta arriba; perfil derecho a la derecha. En primer diedro: planta abajo; perfil derecho a la izquierda. No reflejes las piezas para acomodar las vistas.
- **Vista oblicua:** proyección ortográfica desde azimut/elevación especificados. La isométrica usa azimut 45° y elevación aproximada de 35,264°. No la llames perspectiva cónica: las paralelas no convergen.
- **Giro SVG:** recalcula las proyecciones y la visibilidad para cada ángulo. Un `rotate()` aplicado al dibujo plano no equivale a girar el volumen. Lee [references/geometria-animacion.md](references/geometria-animacion.md) para animación y revisión.
- **Ejercicio:** muestra primero sólo las vistas. Revela la solución mediante una acción explícita. Antes de revelar no incluyas el nombre del sólido, pistas decisivas, texto alternativo con la solución ni un modelo visible. Una solución correcta del usuario se confirma relacionándola con las vistas.

No impongas animación, ejercicios o un plano completo si el usuario pide únicamente una vista. Para una explicación dentro del chat, puede usarse una presentación SVG interactiva; para archivos solicitados conserva los SVG autónomos y el JSON fuente.

## Comprobar y entregar

- Reproyecta el modelo y contrasta contornos, aristas y cotas con la entrada. Conserva escala común en el plano y escala/centro estables durante el giro.
- Al cambiar unidades o escala, conserva las decisiones de recorte y visibilidad usando distancias y tolerancias relativas. Formatea las medidas originales con cifras significativas, separadas del redondeo de coordenadas SVG; una longitud positiva no debe rotularse como cero.
- Revisa aristas visibles continuas, ocultas discontinuas y líneas auxiliares finas. Si omites las ocultas, indícalo. Las cotas generales del helper no sustituyen un plano acotado para fabricación.
- Abre el SVG en un navegador disponible. Para animaciones comprueba varios tiempos, incluyendo laterales y parte trasera; no basta con validar XML. Si produces una captura para inspección, mantenla como evidencia de revisión, no como sustituto del vector.
- Entrega enlaces a los archivos solicitados, el JSON y los supuestos relevantes. No afirmes haber inspeccionado un croquis o probado una animación si no lo hiciste.

Los ejemplos reutilizables están en `assets/cuna.json`, `assets/escalon.json`, `assets/bloque-taladrado.json`, `assets/irregular-taladrada.json`, `assets/taladro-inclinado.json`, `assets/taladros-cruzados.json`, `assets/taladros-desiguales.json`, `assets/tres-taladros.json` y `assets/cuatro-taladros.json`. No los confundas con el croquis del usuario.
