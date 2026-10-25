# Estado del proyecto Proyecciones SVG

Fecha de corte: **25 de octubre de 2026**.

La candidata **1.2.0** reúne cortes SVG, batería adversarial y mallas GLB/3MF/STL, con hasta cuatro taladros comunicados. Su publicación está condicionada a la matriz completa del paquete instalado en Windows, Linux y macOS con Python 3.10/3.14. Las secciones 1–10 conservan los hitos históricos anteriores; sus referencias a 1.1.0 y al desarrollo local describen esos momentos, no la candidata actual.

Los contratos de geometría se mantienen en las referencias de la skill. La evidencia del hito de cortes está en [cortes-validacion-local.json](reports/cortes-validacion-local.json); los cambios posteriores de mallas producen un paquete diferente.

## 1. Publicado, instalado y en desarrollo

| Elemento | Estado comprobado |
| --- | --- |
| Release estable | 1.1.0, MIT, repositorio público y descarga directa |
| Skill instalada | Coincide con los 44 archivos del manifiesto de la release 1.1.0 |
| Código canónico | `skills/proyecciones-svg/` |
| Ampliación de cortes | Implementada en el código local; todavía sin publicar |
| Batería adversarial de cortes | Integrada en la validación habitual del código local |
| Landing y descarga públicas | Conservan la distribución estable 1.1.0 documentada |
| Git del desarrollo | Cambios locales sin commit; base `449a324be54f9838251d830f958aa3989209019e` |

La skill instalada se obtiene del paquete publicado. Por tanto, **`--sections` se usa actualmente desde el código del proyecto**, no desde la instalación estable. No se ha cambiado la instalación para hacerla pasar por una release nueva.

La release 1.1.0 fue publicada y verificada con la matriz completa de Windows, Linux y macOS, con Python 3.10 y 3.14. Ese alcance corresponde a la release y está respaldado por [su informe de publicación](reports/1.1.0-stable.md) y [la evidencia de CI](reports/1.1.0-full-matrix.json).

## 2. Producto y alcance funcional

La skill transforma una descripción, un croquis o vistas técnicas en un modelo JSON reproducible y deriva las salidas de ese modelo. La interpretación de la entrada la realiza el agente; el generador Python recibe geometría JSON.

| Capacidad | Estable 1.1.0 | Desarrollo local |
| --- | --- | --- |
| Alzado, planta y perfil; primer o tercer diedro | Incluida | Conservada |
| Vista oblicua ortográfica | Incluida | Conservada |
| Giro SVG con visibilidad recalculada por ángulo | Incluida | Conservada |
| Visor HTML autónomo, reproducción y control de ángulo | Incluida | Conservado y ampliado con cortes |
| Hasta cuatro taladros pasantes comunicados, según los contratos geométricos | Incluida | Conservada |
| Exportación opcional `.cota` | Incluida | Conservada |
| Cortes planos de cuerpos convexos | No incluida | `--sections` |
| Guías auxiliares de los taladros en el corte | No incluida | Control opcional en el visor |
| Batería adversarial específica de cortes | No incluida | 18 pruebas y 230 subcasos por ejecución documentada |

Los SVG se calculan con Python estándar y geometría vectorial. Las curvas usan las construcciones analíticas o aproximaciones documentadas de cada modelo. La generación SVG no requiere imágenes generadas ni un motor 3D. Cota usa su propio motor para abrir el archivo exportado.

## 3. Contrato de las salidas

Los productos dependen de `--mode` y de las opciones activadas:

| Archivo | Contenido |
| --- | --- |
| `vistas.svg` | Tres vistas a escala común, unidades y cotas generales |
| `angulo.svg` | Vista ortográfica desde un ángulo definido |
| `giro.svg` | Giro vectorial autónomo |
| `visor.html` | Plano, giro y controles; añade los cortes cuando se solicitan |
| `cortes.svg` | Secciones planas opcionales del material |
| `modelo.cota` | Volumen completo para Cota, con medidas convertidas a milímetros |
| `modelo.json` | Geometría fuente conservada |
| `informe.json` | Versión declarada, opciones, tiempos, planos de corte y sumas de los productos |

Activar `--sections` conserva idénticos los archivos de las tres vistas, la vista oblicua, el giro, el JSON y el `.cota` generados con los mismos parámetros. El visor incorpora el panel adicional y el informe registra la nueva salida.

Los cortes admiten planos automáticos o de uno a cuatro planos definidos por nombre, origen, normal y orientación opcional. Las cotas del corte son longitudes reales en su plano y conservan las unidades del JSON. El blanco muestra la unión de los vaciados; el rayado indica material. Las guías discontinuas son auxiliares y no aristas reales. El [contrato de cortes](skills/proyecciones-svg/references/cortes.md) define los casos admitidos y los rechazos numéricos.

La exportación Cota es de un solo sentido hacia Cota 1.0.0, esquema 1. El `.cota` contiene el volumen completo; los planos de sección, la lámina y el giro permanecen en los SVG. Las ediciones posteriores en Cota no regeneran las salidas de la skill. Véase [el contrato de intercambio](skills/proyecciones-svg/references/cota.md).

## 4. Validación del desarrollo actual

| Comprobación | Resultado y alcance |
| --- | --- |
| Suite completa, Windows/Python 3.10.20 | 129 pruebas aprobadas: 99 de geometría y 30 de distribución |
| Suite completa, Windows/Python 3.14.6 | 129 pruebas aprobadas: 99 de geometría y 30 de distribución |
| Batería adversarial, semilla 20261025 | 18 pruebas y 230 subcasos aprobados en ambos intérpretes |
| Batería adversarial, semilla 8675309 | 18 pruebas y 230 subcasos aprobados en Python 3.14.6 |
| Reproducibilidad local del paquete | ZIP idéntico entre ambos intérpretes de Windows |
| Conservación de vistas, giro y `.cota` | Comprobada por comparación de bytes y por pruebas de geometría y medidas |
| Revisión manual del visor | Casos de desarrollo y caso adversarial; este último comprueba textos literales, referencias, guías y ocho ángulos |
| CI remota del código con cortes | Pendiente |
| Desarrollo actual en Linux/macOS | Pendiente |
| Motor real de Cota y matriz automatizada de navegadores sobre el ZIP final a publicar | Pendiente |

Las 18 pruebas adversariales **forman parte de las 129**, no se suman a ellas. Las 230 variaciones son subcasos de la batería, no 230 métodos de prueba adicionales.

La batería contrasta planos aleatorios con ecuaciones independientes, escalas extremas, tangencias, secciones finas, permutaciones de taladros, entradas malformadas, textos adversariales y fallos de cálculo o escritura. Se detectaron y corrigieron siete familias de defectos; el [informe adversarial](reports/cortes-adversarial.md) detalla cada regresión y cómo reproducirla.

La evidencia de la release estable sí incluye pruebas con el motor Cota y navegadores. La ampliación también tuvo comprobaciones con el motor durante su desarrollo, pero no se presentan como validación del último ZIP: la nueva publicación debe verificar su paquete definitivo.

## 5. Identidad de los artefactos

El campo `VERSION` del árbol continúa en **1.1.0**, aunque sus cambios locales no pertenecen a la release publicada. `PLATFORMS.json` sigue describiendo el alcance de esa release. Ninguno de esos campos, por sí solo, acredita el estado del desarrollo actual.

| Artefacto | Tamaño | Archivos del manifiesto | SHA-256 |
| --- | --- | --- | --- |
| ZIP estable 1.1.0 | 263099 bytes | 44 | `014c6aee5f73936faa4f59177137b0de99515698f892200c6c2eeeadd1c8d80e` |
| ZIP local validado con cortes | 313997 bytes | 48 | `660f6f8f907da036f3a443cc9748baf354430c875ff031c45f21ba69ed5cc0f4` |

El ZIP local es un artefacto de prueba. **No debe sustituir ni distribuirse como la release 1.1.0**, aunque conserve ese nombre y campo de versión.

Los informes locales contienen el commit que era `HEAD` al ejecutarlos. Ese commit es la base del trabajo, no un commit que contenga los cambios nuevos. La vinculación del contenido probado se conserva mediante las sumas del paquete, su manifiesto y los archivos fuente en [la evidencia archivada](reports/cortes-validacion-local.json). En ese hito se verificó la coincidencia del código con el manifiesto normalizando finales de línea como el empaquetador; el prototipo de mallas es posterior y modifica ese contenido.

## 6. Límites y decisiones abiertas

- Los cortes admiten cuerpos convexos. Los cuerpos cóncavos conservan las capacidades ya admitidas de vistas y giro, pero su corte se rechaza.
- El alcance habitual de los taladros exige geometrías, bocas y cruces compatibles con los contratos; no es un sistema CAD general.
- Las cotas y tolerancias numéricas no certifican precisión de fabricación. El motor de Cota representa curvas mediante mallas y tiene sus propios límites.
- Los errores de validación, presupuesto y cálculo anteriores a la publicación conservan la entrega existente.
- La publicación final es atómica **por archivo**. Un fallo de E/S durante la sustitución puede mezclar archivos completos de dos entregas. La batería reproduce este caso; queda pendiente decidir entre una publicación transaccional y una política de recuperación documentada con la garantía actual.

## 7. Trabajo pendiente para otra versión estable

1. Revisar y guardar los cambios locales en un commit identificable, excluyendo archivos ajenos al proyecto.
2. Asignar una nueva versión y alinear metadatos, nombres de paquetes, configuración de CI y notas de versión. Conservar intacta la publicación 1.1.0.
3. Cerrar la decisión sobre la recuperación ante fallos de E/S durante la publicación y reflejar la garantía elegida en código, pruebas e instrucciones.
4. Ejecutar la matriz completa del mismo commit en Windows, Linux y macOS, con Python 3.10 y 3.14, sin pruebas omitidas y con un paquete reproducible.
5. Validar ese ZIP exacto con el motor Cota fijado y ejecutar la matriz automatizada de Chromium/Firefox, incluidos los cortes. Archivar evidencia de paquete, commit y resultados.
6. Publicar la nueva release, actualizar la instalación local desde su paquete y actualizar landing, ejemplos y descarga directa.

Este hito documenta la implementación y la validación local. No crea una release, un tag ni una publicación nueva.

## 8. Uso y comprobación desde el código

Desde la raíz del repositorio, para una entrega nueva con todas las salidas:

```sh
python -B skills/proyecciones-svg/scripts/generar.py skills/proyecciones-svg/assets/cuatro-taladros.json --output-dir build/entrega-con-cortes --sections --viewer --export-cota
```

Para reproducir la batería y la suite completa:

```sh
python -B tools/adversarial.py --seed 20261025 --output build/adversarial/repeticion.json
python -B tools/verify.py --report-dir build/verificacion-repeticion
```

No se presupone que estos comandos se hayan vuelto a ejecutar al redactar el documento. Los resultados consignados son los de la evidencia archivada y contrastada en este hito.

## 9. Prototipo posterior: assets genéricos e impresión

Se incorporan `--export-glb`, `--export-3mf` y `--export-stl` al generador del proyecto. El alcance inicial es extrusión simple, incluida la escalera cóncava, o malla convexa sin vaciados. Una representación común de vértices y triángulos alimenta los tres formatos, conservando SVG, JSON y Cota. `--unit-mm` fija una equivalencia física común cuando es necesaria.

La biblioteca `assets/modulos/` contiene rampa, bloque y escalera de 40 × 40 mm y altura máxima de 20 mm. GLB utiliza metros con Y arriba; 3MF y las coordenadas STL se exportan en milímetros con Z arriba. La galería local abre los GLB y compone un recorrido con instancias de los mismos modelos; el ZIP permite descargarlos juntos. No se ha asignado un motor de juego ni una impresora.

Se comprueban superficies cerradas, orientación, conectividad, volúmenes, precisión float32 y conservación de medidas. El prototipo tiene validación externa mediante glTF-Validator y la importación de los seis archivos 3MF/STL en PrusaSlicer. No incorpora texturas, colisiones, animación de personajes, parámetros de laminado ni G-code; no se realizó impresión física. El alcance de este primer hito no incluía taladros; la ampliación posterior se registra a continuación.

El [contrato de mallas](skills/proyecciones-svg/references/assets-mallas.md) define el alcance. La evidencia específica y la suite actualizada se conservan en [el informe del prototipo](reports/assets-prototipo.md). La release publicada y la instalación estable 1.1.0 continúan siendo las anteriores.

## 10. Ampliación posterior: mallas con taladros comunicados

Los seis constructores taladrados del proyecto se exportan ahora mediante la resta booleana de la unión de cilindros poligonales inscritos. Sólo estas exportaciones requieren la dependencia opcional Manifold 3.5.4. El cálculo SVG y Cota no depende de ella. `--mesh-tolerance-mm` define la flecha radial máxima; no limita por sí sola el error de las intersecciones ni constituye una tolerancia de fabricación.

Se conserva una única frontera cerrada de género 1, 3, 5 o 7 según el número de conductos. El ejemplo de cuatro taladros mantiene sus tres vistas, giro, cortes y `.cota`, y añade GLB/3MF/STL y una previsualización del GLB con recorte visual independiente de los archivos completos. La evidencia de esta ampliación se registra en [su informe](reports/mallas-taladradas.md). Sigue siendo desarrollo local, separado de la versión estable 1.1.0.
