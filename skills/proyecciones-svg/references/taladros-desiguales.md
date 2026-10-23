# Taladros cruzados de radios diferentes

`scripts/taladros_desiguales.py` usa la misma pieza convexa y los intervalos de rayos del constructor de taladros cruzados. Requiere ejes que se intersecan, cuatro bocas separadas y cruce completo interior. Las bocas conservan sus círculos unitarios con matrices afines.

## Curva espacial

En el punto de cruce `C`, toma `u` como eje unitario del cilindro menor de radio `r`, `v` como eje del mayor de radio `R`, `c=u·v`, `s=sqrt(1-c²)`, `e1=(v-c*u)/s`, `e2=u×e1`. Las dos ramas exactas de la intersección son:

```text
Q(t) = sqrt(R²-r² sin²(t))
lambda(t) = (r*c*cos(t) ± Q(t))/s
X(t) = C + r*e1*cos(t) + r*e2*sin(t) + u*lambda(t)
```

Con `r<R` estas curvas suaves no son generalmente elipses ni curvas planas. El constructor usa su derivada analítica para generar Bézier cúbicas adaptativas en coordenadas de pantalla. Comprueba el error en varios puntos interiores y subdivide con margen; la tolerancia nominal es 0,025 píxeles del SVG. Valida con muestras adicionales independientes. No alteres el radio del cilindro para ajustar una Bézier.

## Visibilidad sin muestreo angular ciego

En una rama de intersección ambos intervalos de vacío contienen el punto inicial. Verla requiere que al menos uno llegue hasta la cubierta. Cada condición es una forma lineal sobre `X(t)`; sus ceros se reducen a una cuártica al elevar al cuadrado el término `Q`. Filtra después las raíces extrañas contra la ecuación original.

En una boca inferior el rayo puede seguir por su cilindro o cambiar al otro. Para el cambio, el segundo intervalo debe contener tanto la salida del primero como el punto en la cubierta. Esos dos lugares geométricos son elipses afines de `t`; la distancia al otro eje produce ecuaciones trigonométricas de segundo orden. Resuelve todos los eventos y clasifica un punto por intervalo mediante el oráculo de rayos conjunto.

## Transparencia y límites de aproximación

La proyección del volumen común es la envolvente convexa de las proyecciones de ambas curvas espaciales. Se aproxima sólo su contorno 2D, mediante subdivisión adaptativa con la misma tolerancia nominal, y se combina con las bocas por `clipPath`. No se genera una malla ni se utiliza un motor 3D.

El soporte conservador de las curvas debe quedar dentro de cada semiespacio del cuerpo. Se rechazan ejes paralelos o alabeados, radios casi iguales y geometrías sin margen interior certificable. La tolerancia de pantalla no equivale a exactitud CAD ni a una tolerancia en centímetros. Conserva este límite en los supuestos del JSON y los metadatos de los SVG.
