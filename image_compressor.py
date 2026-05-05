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
import shutil
from typing import List, Tuple
from functools import partial
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

# --- Configuración ---
EXTENSIONES: Tuple[str, ...] = (".jpg", ".jpeg", ".png")
CALIDAD: int = 80
BORRAR_ORIGINAL: bool = False
THREADS: int = 8


def convertir_imagen(ruta_original: str, dir_origen: str, dir_destino: str) -> None:
    """Convierte una imagen a WebP si produce ahorro de espacio, copiándola al directorio destino.

    Parámetros:
        ruta_original: Ruta al archivo de imagen de entrada.
        dir_origen: Directorio raíz de origen para mantener la estructura de carpetas.
        dir_destino: Directorio raíz de destino donde se guardarán las imágenes.

    Comportamiento:
        - Mantiene la estructura de carpetas del origen en el directorio destino.
        - Genera un archivo con extensión `.webp` en destino.
        - Si el archivo WebP es más pequeño que el original, lo mantiene.
        - Si no mejora, elimina el WebP temporal en destino y copia el original a destino.
    """

    # Mantener la estructura de carpetas de origen en el destino
    rel_path = os.path.relpath(ruta_original, dir_origen)
    ruta_destino_base = os.path.join(dir_destino, os.path.dirname(rel_path))
    os.makedirs(ruta_destino_base, exist_ok=True)

    nombre_base, ext = os.path.splitext(os.path.basename(ruta_original))
    ruta_webp = os.path.join(ruta_destino_base, nombre_base + ".webp")
    ruta_destino_original = os.path.join(ruta_destino_base, nombre_base + ext)

    try:
        with Image.open(ruta_original) as img:
            img.save(ruta_webp, "WEBP", quality=CALIDAD)

        size_original = os.path.getsize(ruta_original)
        size_webp = os.path.getsize(ruta_webp)

        if size_webp < size_original:
            print(f"✔ {ruta_original} → {ruta_webp} ({size_original} → {size_webp})")
        else:
            os.remove(ruta_webp)
            shutil.copy2(ruta_original, ruta_destino_original)
            print(f"✘ {ruta_original} (webp no mejora, copiado original a destino)")

    except Exception as e:  # pragma: no cover
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


def renombrar_archivos(directorio: str) -> None:
    """Renombra todas las imágenes en el directorio secuencialmente con un prefijo."""
    prefijo = input("Ingrese el prefijo para los archivos (ej. foto_familiar): ")
    if not prefijo:
        print("Prefijo inválido.")
        return

    imagenes = buscar_imagenes(directorio)
    if not imagenes:
        print("No se encontraron imágenes para renombrar.")
        return

    imagenes.sort()
    for idx, ruta_original in enumerate(imagenes):
        dir_archivo = os.path.dirname(ruta_original)
        _, ext = os.path.splitext(ruta_original)
        nuevo_nombre = f"{prefijo}_{idx:02d}{ext}"
        nueva_ruta = os.path.join(dir_archivo, nuevo_nombre)
        
        try:
            os.rename(ruta_original, nueva_ruta)
            print(f"✔ Renombrado: {os.path.basename(ruta_original)} → {nuevo_nombre}")
        except Exception as e:
            print(f"Error al renombrar {ruta_original}: {e}")

    print("Renombrado terminado 🚀")


def _main() -> None:
    """Punto de entrada principal para ejecución como script."""

    directorio = "source"  # carpeta base de origen
    directorio_destino = "output" # carpeta base de destino
    
    if not os.path.exists(directorio):
        os.makedirs(directorio)
    if not os.path.exists(directorio_destino):
        os.makedirs(directorio_destino)

    while True:
        print("\n--- MENÚ PRINCIPAL ---")
        print("1. Convertir imágenes a WebP")
        print("2. Renombrar archivos por lote")
        print("3. Salir")
        
        opcion = input("Seleccione una opción: ")

        if opcion in ["1", "2"]:
            usar_default = input("¿Usar la carpeta por defecto 'source'? (S/n): ").strip().lower()
            if usar_default == 'n':
                dir_origen = input("Ingrese la ruta absoluta o relativa del directorio de imágenes: ").strip()
                if not os.path.exists(dir_origen):
                    print(f"El directorio '{dir_origen}' no existe. Volviendo al menú...")
                    continue
                # El destino será una subcarpeta 'output_convertidas' dentro de la carpeta elegida
                dir_destino = os.path.join(dir_origen, "output_convertidas")
            else:
                dir_origen = directorio
                dir_destino = directorio_destino
        
        if opcion == "1":
            imagenes = buscar_imagenes(dir_origen)
            print(f"Encontradas {len(imagenes)} imágenes en {dir_origen}")
            
            # Crear directorio destino si no existe
            if not os.path.exists(dir_destino) and imagenes:
                try:
                    os.makedirs(dir_destino)
                except PermissionError:
                    print("Error: No tienes permisos para crear carpetas en este directorio. Ejecuta con permisos de administrador o elige otro directorio.")
                    continue
                except Exception as e:
                    print(f"Error al crear directorio destino: {e}")
                    continue
            
            funcion_convertir = partial(convertir_imagen, dir_origen=dir_origen, dir_destino=dir_destino)
            
            with ThreadPoolExecutor(max_workers=THREADS) as executor:
                executor.map(funcion_convertir, imagenes)
            print(f"Optimización terminada 🚀. Resultados en: {dir_destino}")
        elif opcion == "2":
            renombrar_archivos(dir_origen)
        elif opcion == "3":
            print("Saliendo del programa...")
            break
        else:
            print("Opción no válida, por favor intente de nuevo.")


if __name__ == "__main__":
    _main()
