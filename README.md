# Image Compressor

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

**Solución de optimización de imágenes con procesamiento paralelo**

Herramienta escalable para la conversión y compresión de imágenes (JPG, JPEG, PNG) al formato WebP, implementada en Python con soporte para procesamiento multi-hilo eficiente.

---

## Contenidos

- [Descripción](#descripción)
- [Características](#características)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Configuración](#configuración)
- [Rendimiento](#rendimiento)
- [Ejemplos](#ejemplos)
- [Autor](#autor)

---

## Descripción

Image Compressor es una utilidad de línea de comandos diseñada para optimizar colecciones de imágenes mediante la conversión al formato WebP, que proporciona mejor compresión en comparación con formatos tradicionales. La herramienta implementa procesamiento paralelo mediante `ThreadPoolExecutor` para maximizar el rendimiento en sistemas multi-núcleo.

---

## Características

- **Conversión inteligente**: Convierte imágenes (JPG, JPEG, PNG) a formato WebP con mejor ratio de compresión
- **Procesamiento paralelo**: Implementación multi-hilo para optimizar tiempos de procesamiento
- **Validación comparativa**: Compara tamaños de archivo y preserva la versión original si no hay mejora
- **Recorrido recursivo**: Procesa automáticamente subdirectorios
- **Altamente configurable**: Control fino sobre calidad, retención de originales y concurrencia

---

## Requisitos

- **Python**: 3.8 o superior
- **Sistema Operativo**: Linux, macOS, Windows
- **Espacio en disco**: Suficiente para almacenar archivos convertidos (recomendado duplicar espacio de originales)
- **Dependencias**: Pillow (PIL)

---

## Instalación

### 1. Clonar o descargar el proyecto

```bash
cd /ruta/del/proyecto
```

### 2. Crear y activar entorno virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno (Linux/macOS)
source venv/bin/activate

# Activar entorno (Windows)
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Uso

### Instrucción básica

```bash
python image_compressor.py
```

El script buscará automáticamente todas las imágenes en la carpeta `imagenes/` y sus subdirectorios, procediendo con la conversión según la configuración establecida.

### Estructura de directorios

```
proyecto/
├── image_compressor.py
├── imagenes/              # Carpeta con imágenes a procesar
│   ├── foto1.jpg
│   ├── foto2.png
│   └── subfolder/
│       └── foto3.jpeg
└── venv/
```

---

## Configuración

Edite el archivo `image_compressor.py` para ajustar los siguientes parámetros:

| Parámetro | Tipo | Rango | Descripción | Recomendación |
|-----------|------|-------|-------------|----------------|
| `EXTENSIONES` | tuple | N/A | Formatos de entrada a procesar | `('jpg', 'jpeg', 'png')` |
| `CALIDAD` | int | 1-95 | Nivel de compresión WebP | 80 (balance óptimo) |
| `BORRAR_ORIGINAL` | bool | True/False | Eliminar archivo original después de convertir | False (primera ejecución) |
| `THREADS` | int | 1-32 | Número de threads paralelos | CPU count (ej: 8 en i7) |

### Ejemplo de configuración

```python
EXTENSIONES = ('jpg', 'jpeg', 'png')
CALIDAD = 80           # Mayor = mejor calidad, mayor tamaño
BORRAR_ORIGINAL = False  # Conservar originales
THREADS = 8            # Ajustar según núcleos disponibles
```

---

## Rendimiento

### Benchmarks estimados

- **Velocidad**: ~50-200 imágenes/minuto (depende de resolución y threads)
- **Ratio de compresión**: Típicamente 30-50% de reducción de tamaño vs. PNG/JPG original
- **Memoria**: <500 MB para lotes de 1000+ imágenes con threading
- **Escalabilidad**: Lineal hasta el número de núcleos del procesador

### Recomendaciones de optimización

- Ajustar `THREADS` al número de núcleos disponibles
- Usar `CALIDAD=70-75` para mayor compresión en imágenes no profesionales
- Usar `CALIDAD=85-90` para fotografía de alta fidelidad

---

## Ejemplos

### Salida estándar

```
═══════════════════════════════════════════════════════════════
Encontradas 15 imágenes en la carpeta
───────────────────────────────────────────────────────────────

✔ imagenes/foto1.jpg 
  → imagenes/foto1.webp 
  Reducción: 2.5 MB → 1.2 MB (52% menor)

✔ imagenes/subfolder/foto2.png 
  → imagenes/subfolder/foto2.webp 
  Reducción: 3.0 MB → 1.4 MB (53% menor)

✘ imagenes/pequena.jpg 
  Omitida: WebP no proporciona mejora de compresión

───────────────────────────────────────────────────────────────
Optimización completada exitosamente
Procesadas: 14 imágenes | Omitidas: 1 | Tiempo: 24.3s
═══════════════════════════════════════════════════════════════
```

---

## Licencia

Este proyecto se distribuye bajo la licencia MIT. Consulte el archivo [LICENSE](LICENSE) para más detalles.

---

## Autor

**Nicolas Butterfield**

- 📧 Email: nicobutter@gmail.com
- 📦 Versión: 1.0.0
- 📅 Última actualización: 2026
