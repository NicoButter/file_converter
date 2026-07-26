# Image Converter

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-image%20processing-306998)
![License](https://img.shields.io/badge/License-MIT-green)

Herramienta de línea de comandos para convertir, optimizar, renombrar y
auditar imágenes de forma segura. Incluye un subsistema completo para leer,
clasificar, sanitizar y verificar metadatos.

## Producto y autoría

Desarrollado por **Nicolás Butterfield**.

**Producto de Vetrabyte** — desarrollo de software.

- Correo: [nicobutter@gmail.com](mailto:nicobutter@gmail.com)
- Sitio web: [vetrabyte.com.ar](https://vetrabyte.com.ar)

## Qué permite hacer

### Conversión y procesamiento por lotes

- Convertir JPEG, PNG y WebP a WebP.
- Convertir PNG a JPEG, incluyendo imágenes con transparencia mediante fondo
  blanco.
- Mantener la estructura de subcarpetas en el directorio de salida.
- Comparar el tamaño del WebP generado y conservar en destino el original si
  la conversión no reduce el peso.
- Procesar varios archivos en paralelo mediante `ThreadPoolExecutor`.
- Mostrar barras de progreso durante las conversiones y el renombrado.
- Destacar menús, resultados, advertencias, errores y créditos finales con
  colores cuando la terminal los admite.
- Renombrar archivos recursivamente con prefijo y numeración correlativa.
- Ejecutar conversión y renombrado en una única operación.
- Usar nombres de salida incrementales sin sobrescribir archivos existentes.

### Auditoría y privacidad de metadatos

- Analizar automáticamente todas las imágenes JPEG, PNG y WebP de una carpeta
  y sus subcarpetas.
- Leer EXIF, XMP, IPTC, ICC, GPS, información de cámara, fechas, autoría,
  software, números de serie y bloques JUMBF/C2PA cuando están disponibles.
- Separar datos incrustados de valores calculados por ExifTool.
- Clasificar cada etiqueta por categoría y nivel de riesgo: alto, medio, bajo
  o informativo.
- Mostrar la procedencia XMP/JUMBF/C2PA sin afirmar que, por sí sola, pruebe
  generación mediante inteligencia artificial.
- Elegir entre no modificar, eliminar datos sensibles, limpieza recomendada,
  limpieza total o selección personalizada.
- Crear copias sanitizadas sin modificar el original.
- Volver a analizar la copia y comparar metadatos anteriores y posteriores.
- Verificar dimensiones, orientación visual, perfil ICC, eliminación de datos
  sensibles e integridad SHA-256 del original.
- Exportar auditorías y reportes de sanitización en JSON o texto.
- Continuar con un análisis limitado mediante Pillow si ExifTool no está
  instalado.

## Requisitos

- Python 3.8 o posterior.
- Pillow (se instala desde `requirements.txt`).
- ExifTool: recomendado para auditar y necesario para una sanitización completa
  de bloques de metadatos que Pillow no reconoce.
- `tqdm` agrega barras de progreso durante las conversiones y el renombrado.

### Instalar ExifTool

```bash
# Debian / Ubuntu
sudo apt install libimage-exiftool-perl

# macOS
brew install exiftool

# Windows
winget install OliverBetz.ExifTool
```

## Instalación

```bash
git clone <URL_DEL_REPOSITORIO>
cd file_converter
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows PowerShell
venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Uso rápido

Ejecutar el menú interactivo:

```bash
python image_compressor.py
```

Al iniciar, la aplicación crea `source/` y `output/` si todavía no existen.
Para las opciones de procesamiento se puede aceptar la ruta predeterminada o
indicar un directorio personalizado. En el segundo caso, los resultados se
guardan en `output_convertidas/` dentro del directorio elegido.

## Menú de operaciones

| Opción | Función | Resultado predeterminado |
|---:|---|---|
| 1 | Convertir imágenes a WebP | `output/` |
| 2 | Renombrar archivos por lote | Renombra en el origen elegido |
| 3 | Convertir y renombrar a WebP | `output/` |
| 4 | Convertir PNG a JPEG | `output/` |
| 5 | Auditar y sanitizar metadatos | Copias y reportes en `output/` |
| 6 | Salir | — |

### Opción 1 — convertir a WebP

Busca recursivamente JPEG, PNG y WebP. Para cada imagen genera un WebP y
compara su tamaño con el original. Si el WebP no representa un ahorro, copia el
original al destino sin alterar sus datos.

### Opción 2 — renombrar por lote

Solicita un prefijo y aplica numeración correlativa con formato fijo a los
archivos del directorio seleccionado. Esta opción renombra los archivos en el
origen; conviene conservar una copia de respaldo antes de ejecutarla.

### Opción 3 — convertir y renombrar

Combina la conversión inteligente a WebP con un prefijo y numeración
correlativa. Mantiene la estructura de carpetas en el directorio de salida.

### Opción 4 — convertir PNG a JPEG

Procesa exclusivamente archivos PNG. Las imágenes transparentes se colocan
sobre un fondo blanco antes de guardarse como JPEG.

### Opción 5 — auditar y sanitizar metadatos

Al aceptar `source/`, se procesan directamente todas las imágenes compatibles
en esa carpeta y sus subcarpetas; no es necesario volver a indicar una ruta de
archivo. Las copias sanitizadas se guardan en `output/`, conservando la
estructura relativa del origen. Para cada imagen se elige el modo de limpieza y
se puede exportar el reporte.

#### Modos de limpieza

| Modo | Comportamiento |
|---|---|
| No modificar | Sólo analiza y permite exportar la auditoría. |
| Datos sensibles | Elimina GPS, ubicación, propietario, autor, seriales, identificadores y comentarios privados. |
| Recomendada | También elimina fechas, software, XMP, IPTC y procedencia; conserva ICC y orientación. |
| Total | Elimina todos los metadatos posibles; puede recomprimir JPEG y modificar ligeramente el color. |
| Personalizada | Permite seleccionar etiquetas incrustadas por índice. |

Las salidas usan nombres como `foto_sanitizada.png`. Si ya existe el nombre,
se genera `foto_sanitizada_2.png`, y así sucesivamente. Nunca se sobrescribe el
original ni una salida existente.

## Directorios de trabajo

```text
file_converter/
├── source/                  # imágenes originales
├── output/                  # resultados con las rutas predeterminadas
├── image_compressor.py      # menú y conversiones
├── metadata/                # auditoría, sanitización y reportes
├── tests/                   # pruebas automatizadas
├── docs/metadata.md         # documentación técnica de metadatos
├── requirements.txt
└── LICENSE
```

Cuando se selecciona un origen personalizado, la aplicación utiliza
`<origen>/output_convertidas/` como destino y replica allí las subcarpetas.

## Configuración

Los valores de conversión se encuentran al comienzo de
[`image_compressor.py`](image_compressor.py):

| Parámetro | Valor inicial | Descripción |
|---|---:|---|
| `EXTENSIONES` | `.jpg`, `.jpeg`, `.png`, `.webp` | Extensiones buscadas recursivamente. |
| `CALIDAD` | `80` | Calidad de salida WebP/JPEG. |
| `BORRAR_ORIGINAL` | `False` | Conservación del original. |
| `THREADS` | `8` | Cantidad máxima de tareas concurrentes. |

## API de metadatos

El subsistema puede utilizarse desde Python además del menú:

```python
from pathlib import Path
from metadata import MetadataScanner, MetadataSanitizer, SanitizationMode

imagen = Path("source/foto.jpg")
scanner = MetadataScanner()
antes = scanner.scan(imagen)

resultado = MetadataSanitizer(scanner).sanitize(
    imagen,
    SanitizationMode.RECOMMENDED,
    before=antes,
    output_path=Path("output/foto_sanitizada.jpg"),
)

print(resultado.output_path)
print(resultado.report.verification)
```

La documentación detallada de arquitectura, políticas, fallback y seguridad
está en [`docs/metadata.md`](docs/metadata.md).

## Pruebas

```bash
python -m unittest discover -v
```

Las pruebas cubren clasificación de GPS, EXIF y XMP, fallback de Pillow,
limpieza total, orientación, integridad del original, rutas de salida y
generación incremental de nombres.

## Seguridad y limitaciones

- Las rutas se validan con `pathlib` y sólo se aceptan JPEG, PNG y WebP para la
  auditoría.
- ExifTool se ejecuta sin `shell=True`.
- La limpieza con Pillow es un fallback limitado: puede recomprimir JPEG y no
  garantiza eliminar bloques desconocidos como XMP, IPTC o C2PA.
- El modo total puede eliminar perfiles ICC y producir cambios leves de color.
- La opción de renombrado modifica los nombres en el origen seleccionado.

## Licencia

Este proyecto se distribuye bajo la licencia [MIT](LICENSE) y es de uso libre
para todas las personas, proyectos y organizaciones que lo necesiten, siempre
respetando los términos de dicha licencia. Se permite utilizarlo, estudiarlo,
modificarlo y redistribuirlo según las condiciones de MIT.

---

**Nicolás Butterfield**<br>
Producto de **Vetrabyte**<br>
[nicobutter@gmail.com](mailto:nicobutter@gmail.com) · [vetrabyte.com.ar](https://vetrabyte.com.ar)
