# Tres taladros concurrentes con diámetros diferentes

`scripts/tres_taladros.py` resta la unión de tres cilindros al cuerpo convexo. Cada pareja reutiliza las curvas espaciales de `taladros_desiguales.py`. Requiere seis bocas separadas, diámetros distintos y un punto común a los tres ejes. Cada cruce por parejas queda certificado dentro del cuerpo mediante el mismo límite conservador de soporte. No generaliza a ejes alabeados ni a radios casi iguales.

## Frontera física

Una curva de intersección de dos cilindros deja de pertenecer a la frontera del sólido en los tramos interiores al tercero: se eliminan por completo, incluso de la capa de ocultas. Las generatrices aparentes se recortan contra la unión de los otros dos vaciados.

Evaluar la distancia al tercer eje sobre una rama radical del cruce da una ecuación de la forma `L(t)+M(t)*sqrt(Q(t))=0`. La sustitución de la tangente del ángulo mitad y el cuadrado producen un polinomio de grado máximo ocho. Aísla sus raíces reales y filtra contra la ecuación original para eliminar la rama extraña. Conserva esos eventos de recorte en el modelo, independientes de la cámara.

El cálculo divide las distancias por el radio del cilindro de recorte y normaliza el radical por el radio mayor del cruce. La pertenencia compara la distancia radial al cuadrado dividida por el radio al cuadrado con `1-tolerancia`, donde la tolerancia es adimensional. Los intervalos de rayo se resuelven también en unidades de radio y luego se convierten al parámetro original; no uses tolerancias absolutas en las unidades del JSON.

## Visibilidad y comunicación

Los tres intervalos de vacío de un rayo deben cubrir toda su intersección con el cuerpo para que el punto se vea. Comprueba la unión completa, no sólo dos conductos cada vez.

Cada pareja de cilindros tiene un volumen común convexo completamente interior. Su proyección, aproximada mediante la envolvente de las curvas espaciales, indica dónde los intervalos de esa pareja se solapan. En un rayo, tres intervalos forman un camino conectado entre la entrada y la salida si se comunican directamente o a través del tercer intervalo. Por eso la abertura transparente entre boca superior `i` e inferior `j` combina:

- El trayecto directo: ambas bocas y el clip del volumen común `ij`.
- El trayecto `i → k → j`: ambas bocas y los dos clips `ik` y `kj`.

No se exige que los tres cilindros coincidan en un mismo punto del rayo para el segundo caso. Los `clipPath` se anidan por trayecto y los trayectos se unen con rellenos opacos de papel.

Las intersecciones proyectadas con bocas y límites de los clips localizan los eventos de visibilidad; se refinan las transiciones observadas mediante el rayo contra el material exacto. Las bocas son elipses analíticas; los cruces se dibujan con Bézier y los clips con polígonos 2D adaptativos de tolerancia nominal 0,025 píxeles. Conserva este límite en el JSON y verifica el resultado mediante un oráculo independiente, especialmente cerca de eventos de ocultación y de las intersecciones triples.
