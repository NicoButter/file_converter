"""Comparación, verificación y exportación de reportes."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

from .models import MetadataEntry, MetadataReport, ScanResult


def compare_scans(
    before: ScanResult, after: ScanResult
) -> Tuple[List[MetadataEntry], List[MetadataEntry]]:
    """Devuelve entradas incrustadas eliminadas y conservadas, respetando duplicados."""
    after_counts = Counter(entry.key for entry in after.embedded_entries)
    removed: List[MetadataEntry] = []
    preserved: List[MetadataEntry] = []
    for entry in before.embedded_entries:
        if after_counts[entry.key]:
            preserved.append(entry)
            after_counts[entry.key] -= 1
        else:
            removed.append(entry)
    return removed, preserved


def has_sensitive_entries(scan: ScanResult) -> bool:
    sensitive_terms = (
        "gps",
        "latitude",
        "longitude",
        "location",
        "owner",
        "serial",
        "artist",
        "author",
        "creator",
        "copyright",
        "person",
        "contact",
    )
    return any(
        entry.embedded
        and any(
            term in (entry.group + entry.tag).lower()
            for term in sensitive_terms
        )
        for entry in scan.entries
    )


def has_icc_profile(scan: ScanResult) -> bool:
    return any(
        entry.embedded
        and (
            entry.group.lower().startswith("icc")
            or "icc" in entry.tag.lower()
            or "profile" in entry.tag.lower()
        )
        for entry in scan.entries
    )


def _display_dimensions(scan: ScanResult) -> Tuple[object, object]:
    dimensions: Tuple[object, object] = (scan.width, scan.height)
    if scan.visual_orientation in {5, 6, 7, 8}:
        return dimensions[1], dimensions[0]
    return dimensions


def build_verification(
    before: ScanResult,
    after: ScanResult,
    original_unchanged: bool,
    remove_sensitive: bool,
    preserve_icc: bool,
) -> Dict[str, object]:
    before_icc = has_icc_profile(before)
    dimensions_preserved = _display_dimensions(before) == _display_dimensions(after)
    return {
        "gps_y_datos_sensibles_ausentes": (
            not has_sensitive_entries(after) if remove_sensitive else None
        ),
        "perfil_icc_conservado": (
            has_icc_profile(after) if preserve_icc and before_icc else None
        ),
        "dimensiones_conservadas": dimensions_preserved,
        "orientacion_visual_conservada": dimensions_preserved,
        "archivo_original_intacto": original_unchanged,
    }


def export_report_json(report: MetadataReport, path: Path) -> Path:
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return destination


def report_as_text(report: MetadataReport) -> str:
    lines = [
        "REPORTE DE AUDITORÍA Y SANITIZACIÓN",
        "===================================",
        "Archivo original: {}".format(report.original_file),
        "Archivo generado: {}".format(report.generated_file or "No generado"),
        "Fecha del análisis: {}".format(report.analyzed_at),
        "Modo: {}".format(report.mode.value),
        "Metadatos anteriores: {}".format(len(report.before.entries)),
        "Metadatos posteriores: {}".format(
            len(report.after.entries) if report.after else "N/A"
        ),
        "Metadatos eliminados: {}".format(len(report.removed)),
        "Metadatos conservados: {}".format(len(report.preserved)),
        "",
        "Etiquetas eliminadas:",
    ]
    lines.extend(
        "  - [{}] {}:{} = {}".format(
            entry.risk.value, entry.group, entry.tag, entry.value
        )
        for entry in report.removed
    )
    lines.append("")
    lines.append("Verificación:")
    lines.extend(
        "  - {}: {}".format(key, value)
        for key, value in report.verification.items()
    )
    if report.warnings:
        lines.append("")
        lines.append("Advertencias:")
        lines.extend("  - {}".format(item) for item in report.warnings)
    return "\n".join(lines)


def export_report_text(report: MetadataReport, path: Path) -> Path:
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report_as_text(report), encoding="utf-8")
    return destination
