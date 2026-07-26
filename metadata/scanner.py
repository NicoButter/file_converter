"""Lectura de metadatos mediante ExifTool con fallback limitado a Pillow."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import ExifTags, Image, UnidentifiedImageError

from .classifier import classify, display_name, is_embedded
from .models import MetadataEntry, ScanResult

LOGGER = logging.getLogger(__name__)
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class MetadataError(RuntimeError):
    """Error controlado durante la auditoría o sanitización."""


def installation_hint() -> str:
    if shutil.which("apt") or shutil.which("apt-get"):
        return "Instalá ExifTool con: sudo apt install libimage-exiftool-perl"
    if shutil.which("brew"):
        return "Instalá ExifTool con: brew install exiftool"
    if shutil.which("winget"):
        return "Instalá ExifTool con: winget install OliverBetz.ExifTool"
    return "Instalá ExifTool desde https://exiftool.org/"


def validate_image_path(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if not candidate.is_file():
        raise MetadataError("La ruta no corresponde a un archivo existente.")
    if candidate.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise MetadataError(
            "Formato no soportado. Use JPEG, PNG o WebP."
        )
    return candidate


def _split_exiftool_key(key: str) -> Tuple[str, str]:
    if key.startswith("[") and "]" in key:
        end = key.index("]")
        return key[1:end], key[end + 1 :]
    if ":" in key:
        return tuple(key.split(":", 1))  # type: ignore[return-value]
    return "Unknown", key


class MetadataScanner:
    def __init__(
        self, exiftool_path: Optional[str] = None, allow_pillow_fallback: bool = True
    ) -> None:
        self.exiftool_path = exiftool_path or shutil.which("exiftool")
        self.allow_pillow_fallback = allow_pillow_fallback

    @property
    def exiftool_available(self) -> bool:
        return bool(self.exiftool_path)

    def scan(self, path: Path) -> ScanResult:
        image_path = validate_image_path(Path(path))
        if self.exiftool_available:
            return self._scan_exiftool(image_path)
        if not self.allow_pillow_fallback:
            raise MetadataError(
                "ExifTool no está disponible. " + installation_hint()
            )
        result = self._scan_pillow(image_path)
        result.warnings.append(
            "ExifTool no está disponible: el análisis de Pillow es limitado "
            "y puede omitir XMP, IPTC, JUMBF/C2PA y etiquetas duplicadas. "
            + installation_hint()
        )
        return result

    def _scan_exiftool(self, path: Path) -> ScanResult:
        command = [
            str(self.exiftool_path),
            "-j",
            "-G1",
            "-a",
            "-s",
            "-n",
            str(path),
        ]
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            LOGGER.warning("ExifTool no pudo analizar %s: %s", path.name, detail)
            if self.allow_pillow_fallback:
                result = self._scan_pillow(path)
                result.warnings.append(
                    "ExifTool falló; se usó el análisis limitado de Pillow."
                )
                return result
            raise MetadataError("ExifTool no pudo analizar la imagen.") from exc

        try:
            documents = json.loads(completed.stdout)
            document = documents[0]
            if not isinstance(document, dict):
                raise ValueError("La raíz JSON no es un objeto")
        except (
            json.JSONDecodeError,
            IndexError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise MetadataError("ExifTool devolvió una respuesta JSON inválida.") from exc

        entries: List[MetadataEntry] = []
        occurrences: Dict[Tuple[str, str], int] = defaultdict(int)
        for raw_key, value in document.items():
            group, tag = _split_exiftool_key(str(raw_key))
            occurrences[(group, tag)] += 1
            category, risk = classify(group, tag, value)
            entries.append(
                MetadataEntry(
                    group=group,
                    tag=tag,
                    display_name=display_name(tag),
                    value=value,
                    category=category,
                    risk=risk,
                    embedded=is_embedded(group, tag),
                    ordinal=occurrences[(group, tag)],
                )
            )

        properties = self._image_properties(path)
        entries.sort(
            key=lambda item: (
                not item.embedded,
                -_risk_order(item.risk.value),
                item.category,
                item.group,
                item.tag,
                item.ordinal,
            )
        )
        return ScanResult(
            path=path,
            entries=entries,
            engine="ExifTool",
            size_bytes=path.stat().st_size,
            **properties,
        )

    def _scan_pillow(self, path: Path) -> ScanResult:
        entries: List[MetadataEntry] = []
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image_format = image.format or path.suffix.lstrip(".").upper()
                width, height = image.size
                orientation = image.getexif().get(274)

                raw_entries: List[Tuple[str, str, Any, bool]] = [
                    ("File", "FileName", path.name, False),
                    ("File", "FileSize", path.stat().st_size, False),
                    ("File", "FileType", image_format, False),
                    ("File", "MIMEType", Image.MIME.get(image_format, ""), False),
                    ("Composite", "ImageWidth", width, False),
                    ("Composite", "ImageHeight", height, False),
                ]
                for tag_id, value in image.getexif().items():
                    tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                    raw_entries.append(("EXIF", tag, value, True))
                for key, value in image.info.items():
                    if key in {"exif", "icc_profile"}:
                        if key == "icc_profile":
                            raw_entries.append(
                                ("ICC_Profile", "Profile", "<datos binarios>", True)
                            )
                        continue
                    safe_value = (
                        "<datos binarios>"
                        if isinstance(value, bytes)
                        else value
                    )
                    raw_entries.append(("Pillow", key, safe_value, True))

                for ordinal, (group, tag, value, embedded) in enumerate(
                    raw_entries, 1
                ):
                    category, risk = classify(group, tag, value)
                    entries.append(
                        MetadataEntry(
                            group=group,
                            tag=tag,
                            display_name=display_name(tag),
                            value=value,
                            category=category,
                            risk=risk,
                            embedded=embedded,
                            ordinal=ordinal,
                        )
                    )
                entries.sort(
                    key=lambda item: (
                        not item.embedded,
                        -_risk_order(item.risk.value),
                        item.category,
                        item.group,
                        item.tag,
                    )
                )
                return ScanResult(
                    path=path,
                    entries=entries,
                    engine="Pillow (limitado)",
                    format=image_format,
                    width=width,
                    height=height,
                    size_bytes=path.stat().st_size,
                    visual_orientation=int(orientation) if orientation else 1,
                )
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            raise MetadataError("La imagen está corrupta o no es válida.") from exc

    @staticmethod
    def _image_properties(path: Path) -> Dict[str, Any]:
        try:
            with Image.open(path) as image:
                orientation = image.getexif().get(274, 1)
                return {
                    "format": image.format or path.suffix.lstrip(".").upper(),
                    "width": image.width,
                    "height": image.height,
                    "visual_orientation": int(orientation),
                }
        except (OSError, ValueError):
            return {
                "format": path.suffix.lstrip(".").upper(),
                "width": None,
                "height": None,
                "visual_orientation": None,
            }


def _risk_order(risk: str) -> int:
    return {"alto": 4, "medio": 3, "bajo": 2, "informativo": 1}.get(risk, 0)
