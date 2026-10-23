# Prueba manual independiente desde entradas reales

Usar el ZIP instalado en una carpeta vacía y un espacio de salida aislado. El evaluador recibe la skill y estas entradas, sin los JSON esperados ni los resultados previos. No cambiar la skill durante la evaluación. Registrar supuestos, productos, cálculos independientes y límites de la inspección.

## A · descripción

Tengo un bloque de base rectangular 80 por 60 mm. Su altura es 20 mm en el borde delantero y 32 mm en el borde trasero; la cubierta es plana e inclinada. Lleva un agujero cilíndrico vertical pasante de diámetro 10 mm, cuyo eje pasa por el centro de la base. Genera las tres vistas en tercer diedro y un giro SVG de 24 ángulos, con un visor HTML portable.

## B · croquis

Reconstruye la pieza del archivo `fixtures/croquis.svg`, inspeccionándolo visualmente. Genera las tres vistas y un giro SVG de 24 ángulos, con un visor HTML portable. Las cotas están en mm. Si hay ambigüedades que cambien la forma, indícalas.

## Evaluar

Contrastar modelo y cotas originales, coherencia entre vistas, ángulos, visibilidad, portabilidad y apertura en navegador. Distinguir cálculos, rasterizados de inspección y pruebas reales del navegador. Las cotas generales del programa no incluyen automáticamente todas las medidas del encargo: registrar las que falten sin presentarlas como un plano completamente acotado.
