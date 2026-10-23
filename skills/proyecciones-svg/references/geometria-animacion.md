# Geometría, visibilidad y giro vectorial

## Convención de cámara

El helper mide el azimut `a` desde el frente hacia el lado derecho, y la elevación `e` desde el plano horizontal. En radianes:

```text
derecha = (cos a, sin a, 0)
observador = (sin a cos e, -cos a cos e, sin e)
arriba = observador × derecha
u = punto · derecha
v = punto · arriba
profundidad = punto · observador
```

Una profundidad mayor está más cerca del observador. En SVG se invierte `v` porque su eje vertical crece hacia abajo. Se normaliza el tamaño para la aritmética; las cotas se obtienen de las coordenadas originales. El plano usa la misma escala para las tres vistas. El giro usa un centro y una escala constantes para toda la secuencia.

La disposición de primer y tercer diedro sigue las vistas indicadas en la [documentación de proyección de Autodesk](https://help.autodesk.com/cloudhelp/ENU/Fusion-Drawing/files/GUID-0DB05CD9-BE99-4E45-9FBD-8B8AF1F297BF.htm). Cambiar la disposición no cambia la geometría observada de cada vista.

## Ocultación sin un motor 3D

Cada cara plana se triangula sólo para el cálculo. Para cada arista:

1. Proyecta sus extremos y cada triángulo.
2. Recorta el intervalo de la arista que cae dentro de la proyección del triángulo.
3. Compara las profundidades interpoladas. Sólo queda oculto el intervalo donde la cara está por delante.
4. Une los intervalos ocultos y dibuja el resto como trazo visible.

Esto resuelve aristas parcialmente ocultas y concavidades sencillas. Las diagonales de triangulación y las aristas entre caras coplanares no se dibujan. Todos los polígonos usan el mismo relleno de papel; por tanto el relleno no necesita ordenarse por distancia. Los trazos físicos, ya recortados, se dibujan después. No añadas sombreado diferente por cara sin resolver también el orden de los rellenos.

Las caras deben representar la frontera de una pieza válida. El helper no detecta todas las autointersecciones entre caras ni reconstruye automáticamente una foto o un croquis.

## Caso analítico: taladro vertical pasante

El constructor `taladro_cilindrico.py` conserva los círculos como curvas: en una vista de elevación `e`, cada borde horizontal se proyecta como elipse con semiejes `r` y `r sin(e)`, antes de aplicar la escala del dibujo. La abertura que permite ver a través del bloque es la intersección de las elipses de entrada y salida; se presenta mediante un `clipPath` SVG.

Para decidir qué arco del borde inferior se ve, traza un rayo hacia el observador hasta el plano superior. Debe salir dentro del círculo superior. Si `h` es el espesor y `s = h cot(e)`, ese arco cumple `cos(t − phi) <= −s/(2r)`, donde `phi` es la dirección horizontal hacia el observador. Si `s >= 2r` el borde inferior queda oculto. Desde arriba ambos bordes coinciden. Los límites aparentes laterales del cilindro son generatrices ocultas; no son aristas entre facetas. La elevación de este constructor se limita a 0..90°.

## Taladro que atraviesa una cubierta inclinada

En `pieza_taladrada.py`, para la cubierta `z=h0+a*x+b*y`, la entrada del agujero se parametriza como `C+(r,0,a*r) cos(t)+(0,r,b*r) sin(t)`. Proyectar los dos vectores y el centro da una matriz SVG afín que transforma un círculo unitario en la elipse correcta, incluida su orientación. `vector-effect:non-scaling-stroke` conserva el grosor del trazo.

Para un rayo hacia el observador `d=(dx,dy,dz)`, la cubierta es visible si `q=dz-a*dx-b*dy > 0`. Un punto del borde inferior sale por la abertura si `hc*(dx²+dy²)+r*(a*(dx²+dy²)+2*q*dx)*cos(t)+r*(b*(dx²+dy²)+2*q*dy)*sin(t) <= 0`, siendo `hc` la altura del plano en el centro del taladro. Es una desigualdad sinusoidal que permite recortar arcos analíticos. Si la cubierta queda de espaldas al observador, los bordes superiores del taladro se dibujan ocultos.

## Extensión a un eje cilíndrico inclinado

En `pieza_taladrada.py` el eje unitario `w` pasa por `C=(cx,cy,0)`. Dos vectores unitarios ortogonales `U,V`, perpendiculares a `w`, definen el radio real. La intersección con un plano `n·X=k` es la elipse exacta:

```text
centro = C + w * (k - n·C)/(n·w)
A = r * (U - w * (n·U)/(n·w))
B = r * (V - w * (n·V)/(n·w))
X(t) = centro + A cos(t) + B sin(t)
```

Se aplica por separado a la base y a la cubierta. Proyectar estos centros y vectores conserva las elipses como círculos unitarios con matrices SVG. El taladro debe quedar dentro de todas las paredes; para una semirrecta normal interior `m`, la distancia mínima de la elipse a su pared es la distancia del centro menos `hypot(m·A,m·B)`.

Para la visibilidad del borde inferior se compara el tiempo de salida del rayo por la cubierta con el tiempo de salida del cilindro. Si `d` apunta hacia el observador, `n=(-a,-b,1)`, `q=n·d>0`, `d_z>0` y `H²=|d-w(w·d)|²`, los puntos visibles cumplen:

```text
hc*H² + (-n·A_base*H² + 2*q*r*(U·d))*cos(t)
       + (-n·B_base*H² + 2*q*r*(V·d))*sin(t) <= 0
```

Sigue siendo una desigualdad sinusoidal y permite dibujar arcos analíticos. Al mirar a lo largo del eje ambos bordes se proyectan sobre el mismo círculo y se omite el duplicado. Las generatrices tangentes se calculan con `U·d,V·d`; no se reutilizan los ángulos de tangencia de un eje vertical. La abertura transparente sigue siendo la intersección proyectada de los dos discos elípticos, mediante `clipPath`.

## SVG animado autónomo

`giro.svg` contiene grupos vectoriales precomputados, uno por ángulo, con animación SMIL discreta de `visibility`. No contiene imágenes, vídeo, JavaScript ni llamadas de red. El cambio discreto conserva la topología de la visibilidad cuando aparecen o desaparecen segmentos; interpolar un `path` con distinto número de segmentos daría deformaciones falsas. Más muestras mejoran la fluidez y aumentan el archivo.

Con `prefers-reduced-motion: reduce` se presenta una vista estática. El archivo `angulo.svg` sirve además como alternativa estática. Si se necesita explorar libremente, monta estos cálculos en SVG dentro de HTML con controles nativos de azimut, elevación y pausa, en vez de convertir la salida en vídeo. Si se pide un ejercicio, mantén la solución oculta hasta la acción del usuario.

Para comprobar el resultado en un navegador abre directamente `giro.svg`, pausa su línea temporal con `document.documentElement.pauseAnimations()` y usa `setCurrentTime(segundos)` para inspeccionar frontal, lateral, trasera y el cierre. Comprueba que se muestra un único grupo, que la escala no cambia y que las aristas traseras no atraviesan caras opacas. Esta inspección usa la presentación 2D de SVG, no un renderizador 3D.

Referencias oficiales para el formato: [SVG animate](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/animate), [calcMode](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/calcMode), [keyTimes](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/keyTimes).
