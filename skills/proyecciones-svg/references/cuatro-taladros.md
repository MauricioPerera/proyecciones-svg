# Cuatro taladros concurrentes de distinto diámetro

`scripts/cuatro_taladros.py` usa el cálculo compartido de `tres_taladros.py` para restar cuatro cilindros al mismo cuerpo convexo. Exige diámetros distintos, ocho bocas separadas, un punto común a los cuatro ejes y los seis cruces por parejas completamente interiores. El límite de soporte de `taladros_desiguales.py` certifica cada cruce de forma conservadora; puede rechazar casos válidos muy próximos a las caras.

## Frontera del vaciado conjunto

Las seis parejas producen doce ramas espaciales. Cada rama se recorta contra los dos cilindros que no participan en ella: los tramos interiores a cualquiera de esos vaciados se omiten incluso de las líneas ocultas. Reutiliza las raíces de grado máximo ocho descritas en [tres-taladros.md](tres-taladros.md), conserva ambos conjuntos de eventos y clasifica contra la unión. Las generatrices aparentes también se recortan contra los otros tres cilindros.

## Comunicación a través de cuatro intervalos

Un rayo corta cada cilindro en un intervalo. Los seis clips de los volúmenes comunes por parejas describen las aristas del grafo de solapamiento de esos cuatro intervalos. Para comunicar una boca superior `i` y una inferior `j`, basta con que exista un camino en ese grafo: su unión cubre el segmento entre ambas bocas. No se necesita un punto del rayo que pertenezca a los cuatro cilindros simultáneamente.

Entre bocas de cilindros distintos hay cinco caminos simples posibles: el directo, dos con un cilindro intermedio y dos con ambos intermedios en distinto orden. Anida un `clipPath` por arista de cada camino y une los caminos con rellenos de papel. La misma boca de entrada y salida no requiere cambios de conducto. No limites la transparencia a tres cilindros ni exijas la intersección de los seis clips.

Las bocas son elipses analíticas. Las ramas interiores usan Bézier y los clips envolventes poligonales 2D adaptativas, sin mallas cilíndricas ni motor 3D. Conserva la tolerancia nominal de 0,025 píxeles del SVG y comprueba el caso mediante rayos y muestreo independientes; no es una cota dimensional de fabricación ni una garantía global demostrada para cualquier entrada.
