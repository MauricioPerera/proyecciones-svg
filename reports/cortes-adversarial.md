# Batería adversarial de cortes SVG

Validación local del código en desarrollo, 25 de octubre de 2026. La descarga estable 1.1.0 no se ha modificado ni publicado de nuevo. Las pruebas usan sólo bibliotecas Python estándar; el visor se comprobó además mediante CUA.

El [estado formal del proyecto](../ESTADO.md) sitúa este resultado frente a la release publicada. Una [copia consolidada de los informes y sumas](cortes-validacion-local.json) conserva la evidencia pequeña dentro del repositorio; los enlaces a `build/` de este informe apuntan a los archivos locales originales.

## Resultado

| Ejecución | Resultado |
| --- | --- |
| Batería, Windows/Python 3.14.6, semilla 20261025 | 18 pruebas, 230 subcasos, sin fallos ni omisiones |
| Batería, Windows/Python 3.10.20, semilla 20261025 | 18 pruebas, 230 subcasos, sin fallos ni omisiones |
| Batería, Windows/Python 3.14.6, semilla 8675309 | 18 pruebas, 230 subcasos, sin fallos ni omisiones |
| Suite completa, Windows/Python 3.14.6 | 129 pruebas: 99 de geometría y 30 de distribución; todas pasan |
| Suite completa, Windows/Python 3.10.20 | 129 pruebas: 99 de geometría y 30 de distribución; todas pasan |

Ambas ejecuciones completas producen el mismo ZIP de desarrollo: SHA-256 `660f6f8f907da036f3a443cc9748baf354430c875ff031c45f21ba69ed5cc0f4`. El identificador de versión del árbol sigue en 1.1.0; este ZIP de prueba es distinto de la release publicada y no se debe distribuir como ella. No se ejecutó CI remota ni se añadió evidencia nueva de Linux/macOS.

## Cobertura

- 32 planos pseudoaleatorios por semilla a escalas `1e-8`, `1` y `1e6`. Cada sección contrasta una cuadrícula de 17 × 13 puntos con la ecuación independiente del cuerpo y la distancia por producto vectorial a los cilindros.
- Normales y vectores de orientación entre `1e-300` y `1.7e308`; planos casi paralelos, tangentes, exteriores y secciones de espesor muy pequeño.
- Orígenes lejanos dentro del mismo plano, incluidos planos oblicuos; 24 permutaciones de los cuatro taladros; nombres duplicados y referencias SVG únicas.
- Vectores incompletos, booleanos, valores no finitos, listas malformadas, `sections: null`, controles XML y sustitutos Unicode inválidos.
- Textos parecidos a HTML/JavaScript y marcas internas de la plantilla; no deben convertirse en nodos ejecutables, eventos ni solicitudes externas.
- Presupuestos de salida, tiempo agotado, fallo del cálculo y fallo inyectado durante la publicación. Los archivos ajenos al generador se conservan.
- Conservación de las tres vistas, giro y `.cota` mediante las pruebas de distribución de la suite completa.

## Regresiones detectadas y corregidas

1. Los vectores grandes podían desbordar el cálculo de su norma y rechazarse pese a definir una dirección válida. Se normalizan primero por su componente máxima.
2. Un origen lejano desplazaba o deformaba la sección por cancelación numérica. Se calcula la ecuación del plano en coordenadas originales y se usa un anclaje cercano al cuerpo; se conserva el origen declarado en los metadatos.
3. El redondeo de coordenadas SVG podía colapsar secciones aceptadas de espesor pequeño. Los contornos y máscaras del corte conservan precisión adicional y se prueba su área emitida.
4. `sections: null` activaba planos automáticos silenciosamente. Ahora se rechaza como lista inválida.
5. Un `up` explícito paralelo a la normal se admitía o rechazaba según su signo. Ahora se rechaza en ambas direcciones; la orientación automática sigue teniendo su alternativa para cortes horizontales.
6. Algunos caracteres inválidos llegaban a producir XML ilegible o mensajes con un traceback. Se valida el nombre del corte y se comprueba el XML generado antes de publicarlo.
7. Marcas como `__ROTATION__` dentro de textos válidos podían romper las sustituciones del visor. La plantilla se valida y se sustituye en una sola pasada, sin interpretar de nuevo el contenido insertado.

## Límite comprobado

La publicación es atómica **por archivo**, no una transacción de toda la carpeta. El fallo de E/S inyectado durante la segunda sustitución deja el primer archivo nuevo y otros anteriores; los archivos individuales quedan completos y el proceso devuelve error. Este límite ya estaba documentado y la batería lo hace reproducible. Los fallos previos a la publicación no cambian la entrega existente.

## Reproducir

Desde la raíz del repositorio:

```sh
python -B tools/adversarial.py --seed 20261025 --output build/adversarial/report.json
python -B tools/adversarial.py --seed 8675309 --output build/adversarial/alternate.json
python -B tools/verify.py --report-dir build/adversarial/full
```

Los módulos `test_cortes_adversarial.py` y `test_adversarial_io.py` se descubren automáticamente en la validación habitual y en CI. El ejecutor separado conserva semilla, versión del intérprete, subcasos, errores y SHA-256 de los scripts y recursos usados.

Evidencia local: [Python 3.14](../build/adversarial/final-python314.json), [Python 3.10](../build/adversarial/final-python310.json), [segunda semilla](../build/adversarial/seed-8675309.json), [suite 3.14](../build/adversarial/verification-python314/report.json), [suite 3.10](../build/adversarial/verification-python310/report.json).

En el navegador se verificaron textos literales parecidos a scripts, ausencia de scripts dentro de SVG y atributos de evento, identificadores únicos, metadatos del origen lejano, guías y ocho fotogramas del giro. [Resultado DOM](../build/adversarial/browser.json).

![Prueba de texto literal y origen lejano](../build/adversarial/browser.png)
