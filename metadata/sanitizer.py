"""Creación no destructiva de copias sanitizadas."""

from __future__ import annotations

import hashlib
import logging
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PIL import ExifTags, Image, ImageOps

from .models import (
    MetadataEntry,
    MetadataReport,
    SanitizationMode,
    SanitizationResult,
    ScanResult,
)
from .reports import build_verification, compare_scans
from .scanner import MetadataError, MetadataScanner, validate_image_path

LOGGER = logging.getLogger(__name__)

SENSITIVE_ARGS = (
    "-GPS:all=",
    "-EXIF:CameraOwnerName=",
    "-EXIF:OwnerName=",
    "-EXIF:Artist=",
    "-EXIF:Copyright=",
    "-EXIF:BodySerialNumber=",
    "-EXIF:CameraSerialNumber=",
    "-EXIF:LensSerialNumber=",
    "-EXIF:ImageUniqueID=",
    "-EXIF:UserComment=",
    "-EXIF:ImageDescription=",
    "-XMP:Location=",
    "-XMP:City=",
    "-XMP:State=",
    "-XMP:Country=",
    "-XMP:Creator=",
    "-XMP:Rights=",
)

RECOMMENDED_ARGS = SENSITIVE_ARGS + (
    "-EXIF:DateTimeOriginal=",
    "-EXIF:CreateDate=",
    "-EXIF:ModifyDate=",
    "-EXIF:OffsetTime=",
    "-EXIF:OffsetTimeOriginal=",
    "-EXIF:OffsetTimeDigitized=",
    "-EXIF:Software=",
    "-XMP:all=",
    "-IPTC:all=",
    "-JUMBF:all=",
)

SAFE_TAG_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def _file_fingerprint(path: Path) -> Tuple[int, str]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return path.stat().st_size, digest.hexdigest()


def safe_output_path(source: Path) -> Path:
    candidate = source.with_name(source.stem + "_sanitizada" + source.suffix)
    counter = 2
    while candidate.exists():
        candidate = source.with_name(
            "{}_sanitizada_{}{}".format(source.stem, counter, source.suffix)
        )
        counter += 1
    return candidate


class MetadataSanitizer:
    def __init__(self, scanner: Optional[MetadataScanner] = None) -> None:
        self.scanner = scanner or MetadataScanner()

    def sanitize(
        self,
        path: Path,
        mode: SanitizationMode,
        selected_entries: Optional[Sequence[MetadataEntry]] = None,
        output_path: Optional[Path] = None,
        before: Optional[ScanResult] = None,
    ) -> SanitizationResult:
        source = validate_image_path(Path(path))
        initial_scan = before or self.scanner.scan(source)
        if mode == SanitizationMode.NONE:
            report = MetadataReport.now(source, mode, initial_scan)
            return SanitizationResult(None, report, True)

        destination = (
            Path(output_path).expanduser().resolve()
            if output_path
            else safe_output_path(source)
        )
        if destination == source:
            raise MetadataError("La salida no puede sobrescribir el archivo original.")
        if destination.exists():
            raise MetadataError("La ruta de salida ya existe.")
        if destination.suffix.lower() != source.suffix.lower():
            raise MetadataError("La copia debe conservar el formato de la imagen.")
        destination.parent.mkdir(parents=True, exist_ok=True)

        fingerprint_before = _file_fingerprint(source)
        warnings: List[str] = []
        try:
            if self.scanner.exiftool_available:
                self._sanitize_exiftool(
                    source, destination, mode, selected_entries or []
                )
            else:
                warnings.append(
                    "Sanitización realizada con Pillow: la imagen puede haber sido "
                    "recomprimida y algunos bloques no reconocidos podrían persistir."
                )
                self._sanitize_pillow(
                    source, destination, mode, selected_entries or []
                )

            after = self.scanner.scan(destination)
            removed, preserved = compare_scans(initial_scan, after)
            original_unchanged = _file_fingerprint(source) == fingerprint_before
            verification = build_verification(
                initial_scan,
                after,
                original_unchanged=original_unchanged,
                remove_sensitive=mode
                in {
                    SanitizationMode.SENSITIVE,
                    SanitizationMode.RECOMMENDED,
                    SanitizationMode.TOTAL,
                },
                preserve_icc=mode == SanitizationMode.RECOMMENDED,
            )
            if verification.get("gps_y_datos_sensibles_ausentes") is False:
                warnings.append(
                    "Persisten etiquetas de riesgo alto; revise la copia antes de compartirla."
                )
            if verification.get("perfil_icc_conservado") is False:
                warnings.append("No se pudo verificar la conservación del perfil ICC.")
            if mode == SanitizationMode.TOTAL:
                warnings.append(
                    "La limpieza total elimina ICC y puede alterar ligeramente el color."
                )
            report = MetadataReport.now(
                source,
                mode,
                initial_scan,
                generated_file=destination,
                after=after,
                removed=removed,
                preserved=preserved,
                warnings=initial_scan.warnings + after.warnings + warnings,
                verification=verification,
            )
            return SanitizationResult(destination, report, True)
        except Exception:
            if destination.exists():
                destination.unlink()
            raise

    def _sanitize_exiftool(
        self,
        source: Path,
        destination: Path,
        mode: SanitizationMode,
        selected_entries: Sequence[MetadataEntry],
    ) -> None:
        orientation = self._orientation(source)
        must_transpose = (
            orientation not in (None, 1)
            and (
                mode == SanitizationMode.TOTAL
                or (
                    mode == SanitizationMode.CUSTOM
                    and any(entry.tag == "Orientation" for entry in selected_entries)
                )
            )
        )

        if must_transpose:
            self._pillow_transposed_copy(source, destination)
            if mode == SanitizationMode.CUSTOM:
                copy_command = [
                    str(self.scanner.exiftool_path),
                    "-overwrite_original",
                    "-TagsFromFile",
                    str(source),
                    "-all:all",
                    str(destination),
                ]
                self._run_exiftool(copy_command)
            command = [
                str(self.scanner.exiftool_path),
                "-overwrite_original",
            ]
            command.extend(
                self._exiftool_removal_args(mode, selected_entries)
            )
            command.append(str(destination))
        else:
            command = [str(self.scanner.exiftool_path)]
            command.extend(
                self._exiftool_removal_args(mode, selected_entries)
            )
            command.extend(["-o", str(destination), str(source)])

        self._run_exiftool(command)

    @staticmethod
    def _run_exiftool(command: Sequence[str]) -> None:
        try:
            subprocess.run(
                list(command),
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            LOGGER.warning("Falló la sanitización con ExifTool: %s", detail)
            raise MetadataError("ExifTool no pudo crear la copia sanitizada.") from exc

    @staticmethod
    def _exiftool_removal_args(
        mode: SanitizationMode, selected_entries: Sequence[MetadataEntry]
    ) -> List[str]:
        if mode == SanitizationMode.SENSITIVE:
            return list(SENSITIVE_ARGS)
        if mode == SanitizationMode.RECOMMENDED:
            return list(RECOMMENDED_ARGS)
        if mode == SanitizationMode.TOTAL:
            return ["-all="]
        if mode == SanitizationMode.CUSTOM:
            args: List[str] = []
            for entry in selected_entries:
                if not entry.embedded:
                    continue
                if not (
                    SAFE_TAG_PATTERN.fullmatch(entry.group)
                    and SAFE_TAG_PATTERN.fullmatch(entry.tag)
                ):
                    raise MetadataError("Una etiqueta seleccionada no es válida.")
                args.append("-{}:{}=".format(entry.group, entry.tag))
            if not args:
                raise MetadataError("No se seleccionaron metadatos eliminables.")
            return args
        raise MetadataError("Modo de sanitización desconocido.")

    def _sanitize_pillow(
        self,
        source: Path,
        destination: Path,
        mode: SanitizationMode,
        selected_entries: Sequence[MetadataEntry],
    ) -> None:
        with Image.open(source) as opened:
            image = opened.copy()
            image_format = opened.format
            original_info = dict(opened.info)
            exif = opened.getexif()

        tag_names = {
            tag_id: ExifTags.TAGS.get(tag_id, str(tag_id))
            for tag_id in list(exif.keys())
        }
        pillow_entries = {
            (item.group, item.tag): item
            for item in self.scanner._scan_pillow(source).entries
        }
        if mode == SanitizationMode.TOTAL:
            image = ImageOps.exif_transpose(image)
            exif.clear()
            save_options = {}
        else:
            selected_names = {entry.tag for entry in selected_entries}
            for tag_id, tag_name in tag_names.items():
                entry = pillow_entries.get(("EXIF", tag_name))
                remove = False
                if mode == SanitizationMode.SENSITIVE:
                    remove = bool(entry and entry.risk.value == "alto")
                    remove = remove or tag_name in {
                        "Artist",
                        "Copyright",
                        "UserComment",
                        "ImageDescription",
                    }
                elif mode == SanitizationMode.RECOMMENDED:
                    remove = bool(
                        entry and entry.risk.value in {"alto", "medio"}
                    )
                elif mode == SanitizationMode.CUSTOM:
                    remove = tag_name in selected_names
                if remove and tag_id in exif:
                    del exif[tag_id]

            if mode == SanitizationMode.CUSTOM and "Orientation" in selected_names:
                image = ImageOps.exif_transpose(image)
                exif.pop(274, None)
            save_options = {"exif": exif.tobytes()} if exif else {}
            selected_icc = any(
                entry.group.lower().startswith("icc")
                or "icc" in entry.tag.lower()
                or "profile" in entry.tag.lower()
                for entry in selected_entries
            )
            if (
                mode in {
                    SanitizationMode.SENSITIVE,
                    SanitizationMode.RECOMMENDED,
                    SanitizationMode.CUSTOM,
                }
                and not selected_icc
                and original_info.get("icc_profile")
            ):
                save_options["icc_profile"] = original_info["icc_profile"]

        if image_format == "JPEG":
            save_options.update({"quality": 95, "optimize": True})
        image.save(destination, format=image_format, **save_options)

    @staticmethod
    def _orientation(path: Path) -> Optional[int]:
        try:
            with Image.open(path) as image:
                return int(image.getexif().get(274, 1))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _pillow_transposed_copy(source: Path, destination: Path) -> None:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened)
            image_format = opened.format
            if image_format == "JPEG":
                image.save(destination, format=image_format, quality=95, optimize=True)
            else:
                image.save(destination, format=image_format)
