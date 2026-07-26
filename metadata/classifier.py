"""Clasificación semántica y de riesgo de etiquetas de metadatos."""

from __future__ import annotations

import re
from typing import Any, Tuple

from .models import RiskLevel


CALCULATED_GROUPS = {
    "File",
    "System",
    "Composite",
    "ExifTool",
}

FILE_TAGS = {
    "Directory",
    "FileAccessDate",
    "FileCreateDate",
    "FileModifyDate",
    "FileName",
    "FilePermissions",
    "FileSize",
    "FileType",
    "FileTypeExtension",
    "MIMEType",
    "SourceFile",
}

INFO_TAGS = FILE_TAGS | {
    "BitsPerSample",
    "ColorComponents",
    "EncodingProcess",
    "ImageHeight",
    "ImageSize",
    "ImageWidth",
    "Megapixels",
}

HIGH_TERMS = (
    "gps",
    "latitude",
    "longitude",
    "location",
    "city",
    "country",
    "state",
    "province",
    "sublocation",
    "serial",
    "owner",
    "personinimage",
    "persondisplayname",
    "contact",
    "email",
    "phone",
)

MEDIUM_TERMS = (
    "date",
    "time",
    "author",
    "artist",
    "creator",
    "copyright",
    "comment",
    "description",
    "history",
    "software",
    "producer",
    "credit",
    "source",
    "c2pa",
    "jumbf",
    "provenance",
)

LOW_TERMS = (
    "orientation",
    "resolution",
    "colorspace",
    "colortype",
    "icc",
    "profile",
    "gamma",
    "chromatic",
)

CAPTURE_TERMS = (
    "camera",
    "make",
    "model",
    "lens",
    "exposure",
    "aperture",
    "fnumber",
    "focallength",
    "iso",
    "flash",
    "shutter",
    "metering",
)


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def is_embedded(group: str, tag: str) -> bool:
    """Distingue bloques incrustados de datos de archivo/calculados."""
    return group not in CALCULATED_GROUPS and tag not in FILE_TAGS


def classify(group: str, tag: str, value: Any) -> Tuple[str, RiskLevel]:
    group_key = normalized(group)
    tag_key = normalized(tag)
    combined = group_key + tag_key

    if not is_embedded(group, tag) or tag in INFO_TAGS:
        category = (
            "Información del archivo"
            if group in {"File", "System"} or tag in FILE_TAGS
            else "Información calculada"
        )
        return category, RiskLevel.INFO

    if any(term in combined for term in HIGH_TERMS):
        category = (
            "Ubicación"
            if any(
                term in combined
                for term in (
                    "gps",
                    "latitude",
                    "longitude",
                    "location",
                    "city",
                    "country",
                    "state",
                    "province",
                )
            )
            else "Autoría e identidad"
        )
        return category, RiskLevel.HIGH

    if any(term in combined for term in ("date", "time")):
        return "Fecha y hora", RiskLevel.MEDIUM

    if any(
        term in combined
        for term in ("author", "artist", "creator", "copyright", "credit")
    ):
        return "Autoría e identidad", RiskLevel.MEDIUM

    if (
        group_key in {"xmp", "iptc", "jumbf", "c2pa"}
        or any(term in combined for term in MEDIUM_TERMS)
    ):
        return "Software y procedencia", RiskLevel.MEDIUM

    if group_key == "icc_profile" or any(
        term in combined for term in LOW_TERMS
    ):
        return "Color y visualización", RiskLevel.LOW

    if any(term in combined for term in CAPTURE_TERMS):
        return "Cámara y captura", RiskLevel.LOW

    return "Otros metadatos", RiskLevel.LOW


def display_name(tag: str) -> str:
    """Convierte nombres CamelCase técnicos a una etiqueta legible."""
    value = re.sub(r"[_-]+", " ", tag)
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return value.strip() or tag
