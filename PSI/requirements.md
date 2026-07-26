# Requerimientos de Usuario - Image Compressor

Este documento detalla los requerimientos de usuario para la herramienta de conversión y procesamiento de imágenes por lotes, sirviendo como base para la posterior generación de Casos de Uso.

## 1. Interfaz de Usuario
- **REQ-UI-01**: El sistema debe presentar una interfaz interactiva basada en texto (Menú Principal) que permita al usuario seleccionar entre varias opciones de procesamiento.
- **REQ-UI-02**: El sistema debe permitir salir de la aplicación de manera segura mediante una opción explícita en el menú.

## 2. Gestión de Directorios
- **REQ-DIR-01**: El usuario debe tener la opción de usar directorios por defecto (`source/` como origen y `output/` como destino) en la raíz de la herramienta.
- **REQ-DIR-02**: El usuario debe tener la opción de seleccionar una ruta completa del sistema de archivos para definir su propio directorio de origen.
- **REQ-DIR-03**: Cuando el usuario selecciona una ruta personalizada, el sistema debe crear un subdirectorio llamado `output_convertidas/` para evitar escribir de forma destructiva los archivos originales.
- **REQ-DIR-04**: El sistema debe replicar la misma estructura de carpetas que encuentre en origen dentro del árbol base de la ruta de destino elegida.
- **REQ-DIR-05**: El sistema debe manejar los problemas de permisos de escritura, notificando al usuario si no tiene acceso en lugar de crashear la aplicación.

## 3. Comportamiento y Procesamiento
- **REQ-IMG-01 (Conversión Simple)**: El sistema debe buscar y analizar archivos de imágenes (.jpg, .jpeg, .png) y convertirlos hacia formato `.webp`.
- **REQ-IMG-02 (Ahorro Inteligente)**: La compresión sólo debe aprobarse en el directorio de salida si el nuevo archivo pesa menos en disco que su antecesor original. Si no produce mejoras, se debe conservar (copiar a destino) la matriz original inalterada.
- **REQ-IMG-03 (Renombrar Lotes)**: El usuario debe poder especificar un sufijo o prefijo, por medio de un prompt y el sistema renombrará todo el set de imágenes aplicando dicho prefijo continuado por una cuenta progresiva numérica y con formato.
- **REQ-IMG-04 (Mixto)**: El sistema debe otorgar un ciclo mixto donde lea las imágenes, aplique el renombramiento de prefijo+numérico en la nueva ruta de salida, e individualmente aplique la regla del *Ahorro Inteligente* sobre ellas.
- **REQ-IMG-05 (Rendimiento)**: El tratamiento de múltiples piezas de imágenes simultáneamente debe resolverse aprovechando tareas concurrentes (Multithreading).

## 4. Requerimientos Técnicos
- El sistema se basa en script nativo compilado en versiones Python >= 3.8.
- Gestión de píxeles a través de la SDK del framework `Pillow`.

## 5. Auditoría de Metadatos
- **REQ-META-01**: El usuario debe poder seleccionar una imagen JPEG, PNG o WebP y analizar sus metadatos con ExifTool.
- **REQ-META-02**: El sistema debe agrupar y ordenar las etiquetas, distinguir datos incrustados de información calculada y clasificarlas con riesgo alto, medio, bajo o informativo.
- **REQ-META-03**: El análisis debe incluir EXIF, XMP, IPTC, ICC, GPS, autoría, software, fechas, cámara, seriales y bloques de procedencia JUMBF/C2PA cuando existan.
- **REQ-META-04**: XMP, JUMBF o C2PA deben mostrarse como procedencia, sin afirmar por su sola presencia que una imagen fue creada mediante IA.
- **REQ-META-05**: Si ExifTool no está instalado, el sistema debe continuar con un fallback limitado de Pillow y mostrar una instrucción de instalación.

## 6. Sanitización y Verificación
- **REQ-SAN-01**: El usuario debe poder elegir entre no modificar, eliminar datos sensibles, limpieza recomendada, limpieza total y selección personalizada.
- **REQ-SAN-02**: Toda limpieza debe crear una copia con nombre seguro incremental y nunca sobrescribir el original.
- **REQ-SAN-03**: La limpieza recomendada debe conservar ICC y la orientación visual.
- **REQ-SAN-04**: Antes de eliminar Orientation mediante reexportación, el sistema debe aplicar la transposición EXIF.
- **REQ-SAN-05**: Después de limpiar, el sistema debe volver a analizar la copia y comparar etiquetas eliminadas y conservadas.
- **REQ-SAN-06**: La verificación debe comprobar datos sensibles, ICC cuando corresponda, dimensiones, orientación e integridad SHA-256 del original.
- **REQ-SAN-07**: El usuario debe poder exportar el reporte de auditoría o sanitización como JSON o texto.
