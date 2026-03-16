"""
Compresor de Imágenes a WebP
Autor: Nicolas Butterfield (nicobutter@gmail.com)
Convierte imágenes JPG, JPEG y PNG a formato WebP con compresión paralela.
"""

import os
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

EXTENSIONES = (".jpg", ".jpeg", ".png")
CALIDAD = 80
BORRAR_ORIGINAL = False
THREADS = 8


def convertir_imagen(ruta_original):

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

    except Exception as e:
        print(f"Error con {ruta_original}: {e}")


def buscar_imagenes(directorio):

    archivos = []

    for root, _, files in os.walk(directorio):

        for file in files:

            if file.lower().endswith(EXTENSIONES):

                archivos.append(os.path.join(root, file))

    return archivos


if __name__ == "__main__":

    directorio = "imagenes"   # carpeta base

    imagenes = buscar_imagenes(directorio)

    print(f"Encontradas {len(imagenes)} imágenes")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(convertir_imagen, imagenes)

    print("Optimización terminada 🚀")
