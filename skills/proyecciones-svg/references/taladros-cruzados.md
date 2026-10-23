# Dos cilindros que se cruzan dentro de una pieza

`scripts/taladros_cruzados.py` trata el sólido como el cuerpo convexo menos la **unión** de dos cilindros. Reutiliza el constructor de taladro inclinado para sus cuatro bocas, pero resuelve conjuntamente el interior.

## Alcance del constructor

- Dos cilindros circulares de igual radio real y ejes que se intersecan, no paralelos.
- Base convexa, fondo `z=0` y una sola cubierta plana.
- Cada taladro entra por la cubierta y sale por la base. Ambas curvas de intersección deben quedar estrictamente dentro de la pieza; esto garantiza cuatro bocas separadas.
- Para diámetros distintos usa la construcción de [taladros-desiguales.md](taladros-desiguales.md). No generaliza a ejes alabeados, más de dos agujeros o bocas fusionadas. Esos casos necesitan otra construcción, no una superposición de las vistas independientes.

## Intersección exacta de los cilindros

Sitúa el origen en el cruce de los ejes, con direcciones unitarias `w1,w2`. Restar las ecuaciones de los cilindros de radio `r` da:

```text
((w1-w2)·X) ((w1+w2)·X) = 0
```

La curva de intersección se compone de dos elipses, una en cada plano bisector. Se construyen mediante la misma intersección cilindro-plano del taladro individual. Se proyectan como círculos unitarios con matrices afines; sus tramos visibles/ocultos conservan arcos SVG, sin facetas.

## Visibilidad conjunta

Para cada punto de borde, recorta el rayo contra el cuerpo convexo y obtiene los intervalos del rayo dentro de ambos cilindros. El borde es visible sólo si la unión de esos intervalos cubre todo el trayecto por el cuerpo. Un rayo puede entrar en un taladro y salir por el otro. Las generatrices que quedan enterradas dentro del otro vaciado se eliminan.

La visibilidad puede cambiar en las intersecciones proyectadas de las elipses y las generatrices tangentes. Estas intersecciones se resuelven con polinomios trigonométricos de segundo orden, reducidos a cuárticas mediante la tangente del ángulo mitad. Clasifica un punto por intervalo de esa partición; no sustituyas este cálculo por muestreo angular que pueda saltarse arcos estrechos.

## Abertura transparente

No basta con unir las dos transparencias calculadas para taladros individuales. Para un trayecto que cambia de cilindro, la proyección debe pertenecer a la boca superior del primero, la inferior del segundo y la proyección del volumen común.

El volumen común de estos cilindros es convexo y es la envolvente convexa de las dos elipses de intersección. Su proyección es la envolvente convexa de dos elipses concéntricas: se dibuja exactamente con arcos elípticos y bitangentes. La igualdad de sus funciones de soporte determina los cambios de elipse. Los `clipPath` anidados combinan esta envolvente con las bocas de entrada y salida.

Comprueba tanto caminos que pasan por un solo cilindro como caminos que cambian al otro y caminos con extremos dentro de bocas pero con material en medio. Estos últimos deben seguir opacos.
