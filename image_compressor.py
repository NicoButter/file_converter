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
import uuid
from collections import defaultdict
from typing import List, Tuple, Dict, Iterable, TypeVar, Iterator
from functools import partial
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

T = TypeVar("T")

# --- tqdm opcional ---
try:
    from tqdm import tqdm  # type: ignore
except ImportError:
    tqdm = None


def iterar_con_progreso(iterable: Iterable[T], desc: str) -> Iterator[T]:
    """Envuelve un iterable con una barra de progreso si tqdm está disponible."""
    if tqdm:
        return tqdm(iterable, desc=desc, unit="archivo")
    else:
        print(f"{desc}...")
        return iter(iterable)


def log(msg: str) -> None:
    """Imprime un mensaje compatible con tqdm o print estándar."""
    if tqdm:
        tqdm.write(msg)
    else:
        print(msg)


# --- Configuración ---
EXTENSIONES: Tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp")
CALIDAD: int = 80
BORRAR_ORIGINAL: bool = False
THREADS: int = 8


def convertir_imagen(ruta_original: str, dir_origen: str, dir_destino: str, nuevo_nombre_base: str = None) -> None:
    """Convierte una imagen a WebP si produce ahorro de espacio, copiándola al directorio destino.

    Parámetros:
        ruta_original: Ruta al archivo de imagen de entrada.
        dir_origen: Directorio raíz de origen para mantener la estructura de carpetas.
        dir_destino: Directorio raíz de destino donde se guardarán las imágenes.
        nuevo_nombre_base: Opcional. Permite reemplazar el nombre del archivo de salida.

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

    nombre_base_orig, ext = os.path.splitext(os.path.basename(ruta_original))
    nombre_base = nuevo_nombre_base if nuevo_nombre_base else nombre_base_orig
    
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


def convertir_png_a_jpg(ruta_original: str, dir_origen: str, dir_destino: str, nuevo_nombre_base: str = None) -> None:
    """Convierte una imagen PNG a JPEG, manejando la transparencia si es necesario.

    Parámetros:
        ruta_original: Ruta al archivo PNG de entrada.
        dir_origen: Directorio raíz de origen para mantener la estructura de carpetas.
        dir_destino: Directorio raíz de destino.
        nuevo_nombre_base: Opcional. Permite reemplazar el nombre del archivo de salida.
    """
    rel_path = os.path.relpath(ruta_original, dir_origen)
    ruta_destino_base = os.path.join(dir_destino, os.path.dirname(rel_path))
    os.makedirs(ruta_destino_base, exist_ok=True)

    nombre_base_orig, _ = os.path.splitext(os.path.basename(ruta_original))
    nombre_base = nuevo_nombre_base if nuevo_nombre_base else nombre_base_orig
    
    ruta_jpg = os.path.join(ruta_destino_base, nombre_base + ".jpg")

    try:
        with Image.open(ruta_original) as img:
            # JPEG no soporta canal Alpha, convertir a RGB si es necesario
            if img.mode in ("RGBA", "P", "LA") or (img.mode == "RGB" and "transparency" in img.info):
                # Crear fondo blanco para las partes transparentes
                fondo = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    fondo.paste(img, mask=img.split()[3]) # 3 es el canal alpha
                else:
                    fondo.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[3])
                img = fondo
            elif img.mode != "RGB":
                img = img.convert("RGB")
                
            img.save(ruta_jpg, "JPEG", quality=CALIDAD, optimize=True)
            print(f"✔ {ruta_original} → {ruta_jpg}")

    except Exception as e:
        print(f"Error al convertir {ruta_original} a JPEG: {e}")


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
    """Renombra TODOS los archivos en el directorio de forma recursiva y segura.

    Implementa una estrategia de dos fases para evitar colisiones de nombres:
    Fase 1: Mueve cada archivo a un nombre temporal único (UUID).
    Fase 2: Renombra los temporales al formato final {prefijo}_{indice:03d}{ext}.

    Argumentos:
        directorio: Ruta del directorio raíz para procesar.
    """
    prefijo = input("Ingrese el prefijo para los archivos: ").strip()
    if not prefijo:
        log("Error: Prefijo inválido.")
        return

    # Recopilar todos los archivos recursivamente
    archivos: list[str] = []
    for root, _, files in os.walk(directorio):
        for f in files:
            archivos.append(os.path.join(root, f))

    if not archivos:
        log("No se encontraron archivos para renombrar.")
        return

    # Ordenar determinísticamente
    archivos.sort(key=lambda x: os.path.basename(x).lower())

    total = len(archivos)
    padding = max(3, len(str(total)))

    log(f"\n--- Fase 1: Creando nombres temporales para {total} archivos ---")
    temporales: list[tuple[str, str]] = []

    # FASE 1: Renombrar a nombres temporales únicos
    for ruta in iterar_con_progreso(archivos, "Fase 1"):
        dir_padre = os.path.dirname(ruta)
        _, ext = os.path.splitext(ruta)
        
        nombre_temp = f"__tmp_collision_safe_{uuid.uuid4().hex}{ext}"
        ruta_temp = os.path.join(dir_padre, nombre_temp)
        
        try:
            os.rename(ruta, ruta_temp)
            temporales.append((ruta_temp, ext))
        except Exception as e:
            log(f"Error crítico en Fase 1 al procesar {ruta}: {e}")

    # FASE 2: Renombrar de temporal a nombre final secuencial
    log(f"\n--- Fase 2: Aplicando nombres finales ({prefijo}_NNN) ---")
    
    for i, (ruta_temp, ext) in enumerate(iterar_con_progreso(temporales, "Fase 2")):
        dir_padre = os.path.dirname(ruta_temp)
        nombre_final = f"{prefijo}_{i:0{padding}d}{ext}"
        ruta_final = os.path.join(dir_padre, nombre_final)
        
        try:
            os.rename(ruta_temp, ruta_final)
        except Exception as e:
            log(f"Error crítico en Fase 2 al procesar {ruta_temp}: {e}")

    log("\nProceso de renombrado completado con éxito 🚀")


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
        print("3. Convertir y renombrar imágenes a WebP")
        print("4. Convertir PNG a JPEG")
        print("5. Auditar y sanitizar metadatos")
        print("6. Salir")
        
        opcion = input("Seleccione una opción: ")

        if opcion in ["1", "2", "3", "4", "5"]:
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
        
        if opcion in ["1", "3", "4"]:
            if opcion == "4":
                # Solo buscamos PNGs para esta opción
                imagenes = [f for f in buscar_imagenes(dir_origen) if f.lower().endswith('.png')]
            else:
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
            
            prefijo = None
            if opcion == "3":
                prefijo = input("Ingrese el prefijo para los nuevos archivos (ej. foto_familiar): ").strip()
                if not prefijo:
                    print("Prefijo inválido. Volviendo al menú...")
                    continue
                imagenes.sort() # Importante para ordenar la numeración
            
            with ThreadPoolExecutor(max_workers=THREADS) as executor:
                if opcion == "3":
                    for idx, ruta_orig in enumerate(imagenes):
                        nuevo_nom = f"{prefijo}_{idx:02d}"
                        executor.submit(convertir_imagen, ruta_orig, dir_origen, dir_destino, nuevo_nom)
                elif opcion == "4":
                    for ruta_orig in imagenes:
                        executor.submit(convertir_png_a_jpg, ruta_orig, dir_origen, dir_destino)
                else:
                    for ruta_orig in imagenes:
                        executor.submit(convertir_imagen, ruta_orig, dir_origen, dir_destino)

            print(f"Proceso terminado 🚀. Resultados en: {dir_destino}")
        elif opcion == "2":
            renombrar_archivos(dir_origen)
        elif opcion == "5":
            from metadata.cli import run_metadata_audit

            run_metadata_audit(dir_origen)
        elif opcion == "6":
            print("Saliendo del programa...")
            break
        else:
            print("Opción no válida, por favor intente de nuevo.")


if __name__ == "__main__":
    _main()
