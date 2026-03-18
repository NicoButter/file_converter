# Requerimientos del proyecto

Este documento lista los requerimientos y pasos mínimos para ejecutar
la aplicación `image_compressor.py` siguiendo buenas prácticas de Python.

## Requerimientos

- Python 3.8 o superior
- Pillow (biblioteca de procesamiento de imágenes)

## Instalación (entorno virtual recomendado)

1. Crear y activar un entorno virtual:

   - Linux / macOS:

     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

2. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

## Notas

- `Pillow` gestiona la lectura/escritura de formatos (JPEG/PNG/WebP).
- Ajusta `CALIDAD`, `THREADS` y `BORRAR_ORIGINAL` en `image_compressor.py`.

## Licencia

Revisa el archivo `LICENSE` en la raíz del repositorio para detalles.
