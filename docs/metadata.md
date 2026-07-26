# Auditoría y sanitización de metadatos

## Arquitectura

El subsistema `metadata` no modifica la lógica de conversión existente:

- `models.py`: dataclasses `MetadataEntry`, `ScanResult`, `MetadataReport` y
  `SanitizationResult`, más los enums de riesgo y modo.
- `classifier.py`: separa información de archivo/calculada de los bloques
  incrustados y asigna categoría y riesgo.
- `scanner.py`: valida la ruta y ejecuta
  `exiftool -j -G1 -a -s -n archivo` sin `shell=True`.
- `sanitizer.py`: genera una salida nueva, aplica la política elegida y vuelve
  a escanearla.
- `reports.py`: compara multiconjuntos de etiquetas, verifica invariantes y
  exporta JSON o texto.
- `cli.py`: presenta el flujo en la opción 5 del menú principal.

## Modelo y clasificación

Cada `MetadataEntry` contiene grupo, etiqueta técnica, nombre legible, valor,
categoría, riesgo, origen incrustado/calculado y estado de selección. El
ordinal permite representar ocurrencias repetidas.

Categorías:

1. Información del archivo.
2. Cámara y captura.
3. Fecha y hora.
4. Ubicación.
5. Autoría e identidad.
6. Software y procedencia.
7. Color y visualización.
8. Información calculada.
9. Otros metadatos.

Riesgos:

- Alto: GPS, ubicación, propietario, contactos y números de serie.
- Medio: fechas, autoría, copyright, comentarios, software, historial, XMP,
  IPTC y procedencia (incluidos JUMBF/C2PA).
- Bajo: captura, orientación, resolución, color e ICC.
- Informativo: formato, tamaño, dimensiones y cálculos de ExifTool.

Los grupos `File`, `System`, `Composite` y `ExifTool` se consideran información
del archivo o calculada, no bloques incrustados eliminables.

## Políticas de limpieza

### Sensibles

Elimina familias GPS y etiquetas conocidas de propietario, autor, copyright,
seriales, identificadores, comentarios y ubicación. Conserva el resto.

### Recomendada

Amplía la anterior con fechas EXIF, zona horaria, software, XMP, IPTC y JUMBF.
No elimina ICC ni Orientation. En JPEG ExifTool modifica sólo metadatos y evita
recomprimir los datos visuales.

### Total

Usa `-all=`. Si Orientation no es 1, primero aplica
`ImageOps.exif_transpose()` para materializar la orientación visual y luego
elimina los metadatos. Esta reexportación puede recomprimir un JPEG. ICC
también se elimina y el color puede variar ligeramente.

### Personalizada

Sólo acepta entradas incrustadas y valida grupo/etiqueta antes de construir
argumentos para ExifTool. Si se quita Orientation, se transpone primero la
imagen y luego se restauran los demás metadatos desde el original antes de
eliminar la selección.

## Seguridad de archivos

- Se aceptan `.jpg`, `.jpeg`, `.png` y `.webp`.
- Todas las rutas se normalizan con `pathlib`.
- No se usa `shell=True`.
- La salida no puede ser el original, conservará la extensión y no puede
  existir previamente.
- Los nombres automáticos son incrementales.
- Antes de limpiar se registra tamaño y SHA-256 del original; después se
  recalculan para comprobar que sigue intacto.
- Una salida parcial se elimina si el proceso falla.

## Fallback de Pillow

Sin ExifTool la aplicación no se cierra: muestra el comando de instalación y
realiza un análisis limitado. Pillow puede leer EXIF básico, ICC y algunos
campos del contenedor, pero puede omitir XMP, IPTC, etiquetas duplicadas y
Content Credentials.

La limpieza con fallback reexporta la imagen. Puede recomprimir JPEG y no
garantiza la eliminación de bloques desconocidos, por lo que el reporte incluye
una advertencia. El modo recomendado conserva ICC cuando Pillow logra leerlo.

## Verificación y reportes

La copia se vuelve a analizar con el mismo motor disponible. El reporte
contiene los escaneos, eliminados, conservados, advertencias y comprobaciones:

- ausencia de GPS/datos sensibles en modos que lo requieren;
- conservación de ICC en limpieza recomendada, si existía;
- dimensiones y orientación visual;
- huella intacta del original.

`export_report_json()` produce un documento estructurado y
`export_report_text()` una versión legible. Ninguna función sobrescribe
automáticamente un reporte desde la CLI.

## Errores controlados

`MetadataError` representa ruta inválida, formato no soportado, archivo
corrupto, JSON inválido, fallo de ExifTool, selección vacía o salida insegura.
Los detalles potencialmente sensibles quedan en logging técnico; la interfaz
muestra un mensaje breve.
