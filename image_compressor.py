"""file_converter.image_compressor

Compresor de imágenes a WebP.

Este módulo busca recursivamente imágenes JPG/JPEG/PNG en un directorio
y las convierte a WebP usando Pillow. Conserva la imagen sólo si el WebP
resultante es más pequeño.

Ejemplo de uso::

    python image_compressor.py

Requisitos:
    - Pillow

Autor: Nicolas Butterfield (nicobutter@gmail.com)
"""

from __future__ import annotations

import os
from typing import List, Tuple
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

# --- Configuración ---
EXTENSIONES: Tuple[str, ...] = (".jpg", ".jpeg", ".png")
CALIDAD: int = 80
BORRAR_ORIGINAL: bool = False
THREADS: int = 8


def convertir_imagen(ruta_original: str) -> None:
    """Convierte una imagen a WebP si produce ahorro de espacio.

    Parámetros:
        ruta_original: Ruta al archivo de imagen de entrada.

    Comportamiento:
        - Genera un archivo con la misma ruta y extensión `.webp`.
        - Si el archivo WebP es más pequeño que el original, mantiene el WebP
          y (opcionalmente) borra el original si `BORRAR_ORIGINAL` es True.
        - Si no mejora, elimina el WebP temporal y deja el original.

    Nota:
        El manejo de errores se realiza por impresión simple en consola.
    """

    nombre_base, _ = os.path.splitext(ruta_original)
    ruta_webp = nombre_base + ".webp"

    try:
        with Image.open(ruta_original) as img:
            img.save(ruta_webp, "WEBP", quality=CALIDAD)

        size_original = os.path.getsize(ruta_original)
        size_webp = os.path.getsize(ruta_webp)

        if size_webp < size_original:
            print(f"✔ {ruta_original} → {ruta_webp} ({size_original} → {size_webp})")
            if BORRAR_ORIGINAL:
                os.remove(ruta_original)
        else:
            os.remove(ruta_webp)
            print(f"✘ {ruta_original} (webp no mejora)")

    except Exception as e:  # pragma: no cover - comportamiento de tiempo de ejecución
        print(f"Error con {ruta_original}: {e}")


def buscar_imagenes(directorio: str) -> List[str]:
    """Busca imágenes dentro de `directorio` y devuelve rutas completas.

    Parámetros:
        directorio: Ruta del directorio raíz donde buscar recursivamente.

    Retorna:
        Lista de rutas (str) a archivos que coinciden con `EXTENSIONES`.
    """

    archivos: List[str] = []

    for root, _, files in os.walk(directorio):
        for file in files:
            if file.lower().endswith(EXTENSIONES):
                archivos.append(os.path.join(root, file))

    return archivos


def _main() -> None:
    """Punto de entrada principal para ejecución como script."""

    directorio = "imagenes"  # carpeta base

    imagenes = buscar_imagenes(directorio)

    print(f"Encontradas {len(imagenes)} imágenes")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(convertir_imagen, imagenes)

    print("Optimización terminada 🚀")


if __name__ == "__main__":
    _main()
