# File Converter - Image Compressor

Compresor de imágenes en Python que convierte imágenes (JPG, JPEG, PNG) a formato WebP con procesamiento paralelo.

## Características

- ✨ Convierte imágenes a WebP (mejor compresión)
- 🚀 Procesamiento paralelo con ThreadPoolExecutor
- 📊 Compara tamaños y solo guarda si mejora la compresión
- 🔄 Recorre subdirectorios recursivamente
- ⚙️ Configurable (calidad, borrado de originales, número de threads)

## Instalación

El proyecto usa `venv` y `Pillow`:

```bash
# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias (si aún no está instalado)
pip install Pillow
```

## Uso

1. Coloca tus imágenes en la carpeta `imagenes/` o en subdirectorios
2. Ejecuta el script:

```bash
python image_compressor.py
```

## Configuración

En el archivo `image_compressor.py` puedes ajustar:

- **EXTENSIONES**: Formatos a buscar (jpg, jpeg, png)
- **CALIDAD**: Rango 1-95 (80 es recomendado)
- **BORRAR_ORIGINAL**: `True` para eliminar archivos originales después de comprimir
- **THREADS**: Número de threads paralelos (recomendado: número de núcleos CPU)

## Ejemplo de salida

```
Encontradas 15 imágenes
✔ imagenes/foto1.jpg → imagenes/foto1.webp (2500000 → 1200000)
✔ imagenes/subfolder/foto2.png → imagenes/subfolder/foto2.webp (3000000 → 1400000)
✘ imagenes/pequena.jpg (webp no mejora)
Optimización terminada 🚀
```

## Autor

**Nicolas Butterfield**  
📧 nicobutter@gmail.com
