"""Modelos de datos del subsistema de metadatos."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class RiskLevel(str, Enum):
    HIGH = "alto"
    MEDIUM = "medio"
    LOW = "bajo"
    INFO = "informativo"


class SanitizationMode(str, Enum):
    NONE = "no_modificar"
    SENSITIVE = "sensibles"
    RECOMMENDED = "recomendada"
    TOTAL = "total"
    CUSTOM = "personalizada"


@dataclass
class MetadataEntry:
    group: str
    tag: str
    display_name: str
    value: Any
    category: str
    risk: RiskLevel
    embedded: bool
    selected_for_removal: bool = False
    ordinal: int = 0

    @property
    def key(self) -> Tuple[str, str, str]:
        """Identidad estable que también tolera etiquetas repetidas."""
        return (self.group, self.tag, repr(self.value))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["risk"] = self.risk.value
        return data


@dataclass
class ScanResult:
    path: Path
    entries: List[MetadataEntry]
    engine: str
    warnings: List[str] = field(default_factory=list)
    format: str = ""
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: int = 0
    visual_orientation: Optional[int] = None

    @property
    def embedded_entries(self) -> List[MetadataEntry]:
        return [entry for entry in self.entries if entry.embedded]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "engine": self.engine,
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "size_bytes": self.size_bytes,
            "visual_orientation": self.visual_orientation,
            "warnings": list(self.warnings),
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass
class MetadataReport:
    original_file: Path
    generated_file: Optional[Path]
    analyzed_at: str
    mode: SanitizationMode
    before: ScanResult
    after: Optional[ScanResult]
    removed: List[MetadataEntry]
    preserved: List[MetadataEntry]
    warnings: List[str]
    verification: Dict[str, Any]

    @classmethod
    def now(
        cls,
        original_file: Path,
        mode: SanitizationMode,
        before: ScanResult,
        generated_file: Optional[Path] = None,
        after: Optional[ScanResult] = None,
        removed: Optional[List[MetadataEntry]] = None,
        preserved: Optional[List[MetadataEntry]] = None,
        warnings: Optional[List[str]] = None,
        verification: Optional[Dict[str, Any]] = None,
    ) -> "MetadataReport":
        return cls(
            original_file=original_file,
            generated_file=generated_file,
            analyzed_at=datetime.now(timezone.utc).isoformat(),
            mode=mode,
            before=before,
            after=after,
            removed=removed or [],
            preserved=preserved or [],
            warnings=warnings or [],
            verification=verification or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archivo_original": str(self.original_file),
            "archivo_generado": (
                str(self.generated_file) if self.generated_file else None
            ),
            "fecha_analisis": self.analyzed_at,
            "modo": self.mode.value,
            "cantidad_anterior": len(self.before.entries),
            "cantidad_posterior": len(self.after.entries) if self.after else None,
            "metadatos_encontrados": [
                entry.to_dict() for entry in self.before.entries
            ],
            "metadatos_eliminados": [entry.to_dict() for entry in self.removed],
            "metadatos_conservados": [
                entry.to_dict() for entry in self.preserved
            ],
            "advertencias": list(self.warnings),
            "verificacion": dict(self.verification),
        }


@dataclass
class SanitizationResult:
    output_path: Optional[Path]
    report: MetadataReport
    success: bool

