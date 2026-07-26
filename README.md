# Image Compressor

![Version](https://img.shields.io/badge/Version-2.0-orange.svg)
![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

Herramienta de línea de comandos para convertir, comprimir y renombrar imágenes,
con auditoría y sanitización verificable de metadatos.

## Funcionalidades

- Conversión de JPEG y PNG a WebP con comparación de tamaño.
- Conversión de PNG a JPEG.
- Renombrado recursivo en dos fases para evitar colisiones.
- Procesamiento por lotes con `ThreadPoolExecutor`.
- Auditoría de EXIF, XMP, IPTC, ICC, GPS, JUMBF/C2PA y otros bloques mediante
  ExifTool.
- Clasificación de cada etiqueta por categoría y riesgo.
- Limpieza sensible, recomendada, total o personalizada.
- Copias sanitizadas no destructivas y nombres incrementales seguros.
- Comparación antes/después, verificación del original y reportes JSON o texto.
- Fallback limitado con Pillow cuando ExifTool no está disponible.

La presencia de XMP, JUMBF o C2PA se presenta como información de procedencia:
no se interpreta por sí sola como prueba de generación mediante IA.

## Requisitos

- Python 3.8 o posterior.
- [Pillow](https://python-pillow.org/).
- ExifTool, recomendado para el análisis y necesario para una sanitización
  completa sin perder bloques no reconocidos por Pillow.
- `tqdm`, opcional, para barras de progreso.

Instalación de ExifTool:

```bash
# Debian/Ubuntu
sudo apt install libimage-exiftool-perl

# macOS con Homebrew
brew install exiftool

# Windows con winget
winget install OliverBetz.ExifTool
```

## Instalación

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Uso

```bash
python image_compressor.py
```

El menú ofrece:

1. Convertir imágenes a WebP.
2. Renombrar archivos por lote.
3. Convertir y renombrar imágenes a WebP.
4. Convertir PNG a JPEG.
5. Auditar y sanitizar metadatos.
6. Salir.

Las operaciones por lotes usan `source/` y `output/` por defecto. También se
puede indicar otro directorio; en ese caso los resultados se escriben en
`output_convertidas/`.

### Auditoría de metadatos

En la opción 5 se ofrece `source/` como directorio predeterminado, igual que
en las operaciones por lotes. Se puede indicar otro directorio y luego se
solicita una imagen JPEG, PNG o WebP dentro de la carpeta elegida. El resultado
incluye:

- archivo, formato, dimensiones y tamaño;
- cantidad total y resumen por categoría/riesgo;
- grupo, nombre técnico, nombre legible y valor de cada etiqueta;
- distinción entre datos incrustados y valores calculados por ExifTool.

Los niveles se muestran con colores: rojo para alto, amarillo para medio, azul
para bajo y gris para informativo/calculado.

### Modos de sanitización

| Modo | Comportamiento |
|---|---|
| No modificar | Sólo analiza; permite exportar la auditoría. |
| Datos sensibles | Elimina GPS, ubicación, propietario, autor, seriales y comentarios privados. |
| Recomendada | También elimina fechas, software, historial, XMP, IPTC y procedencia; conserva ICC y orientación. |
| Total | Elimina todos los metadatos posibles. Quitar ICC puede cambiar ligeramente el color. |
| Personalizada | El usuario selecciona etiquetas incrustadas por su índice. |

La salida se guarda junto al original como `nombre_sanitizada.ext`. Si ese
archivo existe se usa `nombre_sanitizada_2.ext`, y así sucesivamente. Nunca se
sobrescribe el original ni una salida existente.

Después de limpiar se vuelve a escanear la copia y se informa:

- cantidades anterior y posterior;
- etiquetas eliminadas y conservadas;
- ausencia de GPS/datos sensibles cuando corresponde;
- conservación de ICC en el modo recomendado;
- dimensiones y orientación visual;
- integridad del archivo original.

El reporte se puede exportar como JSON o texto. La especificación técnica,
limitaciones del fallback y ejemplos de API están en
[`docs/metadata.md`](docs/metadata.md).

## API de metadatos

```python
from pathlib import Path
from metadata import MetadataScanner, MetadataSanitizer, SanitizationMode

image = Path("foto.jpg")
scanner = MetadataScanner()
before = scanner.scan(image)

result = MetadataSanitizer(scanner).sanitize(
    image,
    SanitizationMode.RECOMMENDED,
    before=before,
)

print(result.output_path)
print(result.report.verification)
```

## Configuración de conversión

Los valores principales están al comienzo de `image_compressor.py`:

| Parámetro | Valor inicial | Descripción |
|---|---:|---|
| `EXTENSIONES` | JPEG, PNG y WebP | Formatos buscados recursivamente. |
| `CALIDAD` | `80` | Calidad de salida WebP/JPEG. |
| `BORRAR_ORIGINAL` | `False` | Reservado para control de conservación. |
| `THREADS` | `8` | Cantidad de tareas concurrentes. |

## Pruebas

```bash
python -m unittest discover -v
```

Las pruebas incluyen imágenes con GPS, sin metadatos, con EXIF+XMP, creación de
copias mediante Pillow e incremento seguro del nombre de salida.

## Estructura

```text
metadata/
├── classifier.py   # categorías, riesgo y nombres legibles
├── cli.py          # flujo interactivo
├── models.py       # entidades y resultados
├── reports.py      # comparación, verificación y exportación
├── sanitizer.py    # limpieza ExifTool/Pillow
└── scanner.py      # lectura ExifTool/Pillow
tests/
└── test_metadata.py
```

## Licencia y autor

Distribuido bajo la licencia MIT. Autor original: Nicolas Butterfield
([@nicobutter](https://github.com/nicobutter)).
