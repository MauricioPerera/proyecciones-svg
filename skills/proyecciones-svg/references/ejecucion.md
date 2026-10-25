# Ejecución portable

Requiere Python 3.10 o posterior. SVG, cortes, Cota, instalador y visor SVG no necesitan paquetes Python, Node, red ni rutas de una máquina concreta. La exportación opcional de mallas taladradas necesita `requirements-mesh.txt`; los poliedros sin vaciados no la necesitan.

La versión 1.2.0 está validada en Windows, Linux y macOS con Python 3.10 y 3.14 mediante GitHub Actions. El archivo `PLATFORMS.json` conserva este alcance junto al paquete; `release-readiness.json`, adjunto a la release, identifica las versiones y arquitecturas efectivamente probadas. En macOS y Linux usa `python3` si ése es el nombre del intérprete instalado.

```sh
python <skill>/scripts/generar.py modelo.json --output-dir salida --mode all --viewer
```

`--mode sheet|view|animation|all` selecciona los SVG. `--viewer` requiere `all` y añade un HTML autónomo con plano, control de ángulo, reproducción manual y opción de ocultar las aristas discontinuas disponibles. No abre programas ni sirve archivos por red. Abre `visor.html` o los SVG con un navegador. El giro autónomo usa SMIL y ofrece una vista estática con movimiento reducido; el visor siempre empieza detenido.

`--export-cota` añade `modelo.cota` junto a los productos seleccionados, sin cambiar los SVG ni el visor. Funciona con todos los tipos de modelo admitidos y no necesita instalar Cota, Node ni paquetes Python. El archivo usa milímetros; para una unidad relativa o personalizada añade `--cota-unit-mm N`, donde N son los milímetros por unidad del JSON. Consulta [cota.md](cota.md) para la compatibilidad y los límites.

`--sections` añade `cortes.svg` y, si se pide visor, los cortes y sus guías al HTML. Admite sólo cuerpos convexos, incluidos los taladrados. Los planos se eligen automáticamente o mediante `sections` en el JSON; conserva las unidades de origen y es compatible con `--export-cota`. Consulta [cortes.md](cortes.md) para el contrato y el alcance. Esta opción se incluye desde 1.2.0.

Las opciones `--export-glb`, `--export-3mf` y `--export-stl` añaden mallas para extrusiones simples, poliedros convexos y los constructores de taladros admitidos. Sólo estos últimos requieren la dependencia opcional Manifold. `--mesh-tolerance-mm N` limita la flecha radial de sus cilindros facetados (por defecto 0,02 mm); no cambia SVG/Cota ni es una tolerancia de fabricación. `--unit-mm N` define una equivalencia común para esos formatos y Cota sin cambiar las cotas SVG. Consulta [assets-mallas.md](assets-mallas.md) antes de exportar: define instalación opcional, unidades, ejes, precisión y casos rechazados.

Valores comunes: tercer diedro, ocultas discontinuas, azimut 45°, elevación 35,2643897°, 72 fotogramas, 6 segundos, barrido 360°, una reproducción. Usa `--system first`, `--hidden omit`, `--azimuth`, `--elevation`, `--frames`, `--seconds`, `--sweep` o `--loop` según el encargo. Los poliedros permiten elevaciones −90..90°; los cuerpos taladrados, 0..90°.

La salida incluye `modelo.json` e `informe.json`. El informe registra la versión, opciones, duración del cálculo y tamaño/SHA-256 de cada producto; no es una certificación de fabricación. Se rechaza sobrescribir productos existentes salvo `--force`. Para cambiar de selección de productos utiliza una carpeta nueva; no mezcles entregas de modelos distintos.

## Presupuestos y alcance numérico

- Entrada JSON: hasta 1 MiB. Perfil o base: hasta 64 puntos. Malla: hasta 256 vértices, 512 caras y 64 vértices por cara. Giro: 8..240 fotogramas.
- Tiempo máximo predeterminado: 180 s, configurable con `--timeout` hasta 600 s. Salida total: 16 MiB, configurable con `--max-bytes` hasta 64 MiB. Incluye SVG, modelo, visor e informe. Si se agota un presupuesto o falla la geometría, el proceso se interrumpe y las salidas previas se conservan. No se aplica un límite independiente de memoria.
- Las dimensiones de la caja envolvente deben ser positivas y su relación máxima no superar 1 000 000:1. La comprobación de caras usa coordenadas locales para admitir piezas esbeltas. Las tolerancias siguen siendo numéricas; aristas o detalles extremadamente próximos pueden resultar indistinguibles. El límite de aspecto por sí solo no certifica todos los detalles interiores de una malla arbitraria.
- No es un validador general de sólidos CAD: no detecta exhaustivamente autointersecciones ni vértices topológicamente singulares. La entrada debe describir una frontera simple, cerrada y coherente. Rechaza los casos dudosos o declara su alcance antes de entregar.
- Bocas cilíndricas: elipses analíticas. Cruces de distinto diámetro: Bézier y clips 2D con tolerancia nominal de 0,025 píxeles del SVG original; ampliar el SVG amplía también ese error gráfico. No lo conviertas en una tolerancia física.

Para mantener los archivos anteriores intactos, el cálculo se realiza en una carpeta temporal vecina y se publica sólo al completarse. La sustitución de cada archivo es atómica; un fallo del sistema de archivos durante la publicación puede dejar una entrega parcial. Ante ese error, vuelve a generar en una carpeta nueva.
