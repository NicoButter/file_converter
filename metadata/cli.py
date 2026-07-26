"""Interfaz de texto para auditoría y sanitización."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .models import MetadataEntry, RiskLevel, SanitizationMode, ScanResult
from .reports import export_report_json, export_report_text, report_as_text
from .sanitizer import MetadataSanitizer
from .scanner import MetadataError, MetadataScanner

COLORS: Dict[RiskLevel, str] = {
    RiskLevel.HIGH: "\033[31m",
    RiskLevel.MEDIUM: "\033[33m",
    RiskLevel.LOW: "\033[36m",
    RiskLevel.INFO: "\033[90m",
}
RESET = "\033[0m"


def _human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return "{:.1f} {}".format(value, unit)
        value /= 1024
    return "{} B".format(size)


def _short_value(value: object, limit: int = 72) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def show_scan(scan: ScanResult) -> None:
    print("\n=== Auditoría de metadatos ===")
    print("Archivo: {}".format(scan.path.name))
    print("Formato: {}".format(scan.format or "desconocido"))
    print("Dimensiones: {} x {}".format(scan.width or "?", scan.height or "?"))
    print("Tamaño: {}".format(_human_size(scan.size_bytes)))
    print("Motor: {}".format(scan.engine))
    print("Metadatos totales: {}".format(len(scan.entries)))

    by_risk = Counter(entry.risk.value for entry in scan.entries)
    by_category = Counter(entry.category for entry in scan.entries)
    print(
        "Riesgo: alto={alto}, medio={medio}, bajo={bajo}, "
        "informativo={informativo}".format(
            alto=by_risk["alto"],
            medio=by_risk["medio"],
            bajo=by_risk["bajo"],
            informativo=by_risk["informativo"],
        )
    )
    print("Categorías:")
    for category, amount in sorted(by_category.items()):
        print("  - {}: {}".format(category, amount))

    print("\nDetalle ordenado:")
    current_category = None
    for index, entry in enumerate(scan.entries, 1):
        if entry.category != current_category:
            current_category = entry.category
            print("\n[{}]".format(current_category))
        color = COLORS[entry.risk]
        origin = "incrustado" if entry.embedded else "calculado"
        marker = "[{}]".format(index) if entry.embedded else " - "
        print(
            "{}{} {:11} | {:10} | {:18} | {} ({}) = {}{}".format(
                color,
                marker,
                entry.risk.value,
                entry.group,
                entry.display_name[:18],
                entry.tag,
                origin,
                _short_value(entry.value),
                RESET,
            )
        )
    for warning in scan.warnings:
        print("\nADVERTENCIA: {}".format(warning))
    print(
        "\nNota: XMP, JUMBF o C2PA indican procedencia; por sí solos no "
        "demuestran que una imagen haya sido creada con IA."
    )


def _select_custom(entries: Sequence[MetadataEntry]) -> List[MetadataEntry]:
    removable = {
        index: entry
        for index, entry in enumerate(entries, 1)
        if entry.embedded
    }
    raw = input(
        "Índices a eliminar, separados por coma (ej. 1,3,8): "
    ).strip()
    chosen: List[MetadataEntry] = []
    for value in raw.split(","):
        value = value.strip()
        if not value:
            continue
        try:
            index = int(value)
        except ValueError:
            continue
        if index in removable and removable[index] not in chosen:
            removable[index].selected_for_removal = True
            chosen.append(removable[index])
    return chosen


def _choose_mode() -> Optional[SanitizationMode]:
    print("\nOpciones de sanitización:")
    print("1. No modificar")
    print("2. Eliminar solo datos sensibles")
    print("3. Limpieza recomendada (conserva ICC y orientación)")
    print("4. Limpieza total (puede alterar ligeramente el color)")
    print("5. Selección personalizada")
    choices = {
        "1": SanitizationMode.NONE,
        "2": SanitizationMode.SENSITIVE,
        "3": SanitizationMode.RECOMMENDED,
        "4": SanitizationMode.TOTAL,
        "5": SanitizationMode.CUSTOM,
    }
    return choices.get(input("Seleccione una opción: ").strip())


def run_metadata_audit() -> None:
    raw_path = input("Ruta de la imagen a analizar: ").strip()
    if not raw_path:
        print("No se indicó una imagen.")
        return

    scanner = MetadataScanner()
    try:
        scan = scanner.scan(Path(raw_path))
        show_scan(scan)
        mode = _choose_mode()
        if mode is None:
            print("Opción inválida.")
            return

        selected: Sequence[MetadataEntry] = []
        if mode == SanitizationMode.CUSTOM:
            selected = _select_custom(scan.entries)
            if not selected:
                print("No se seleccionaron etiquetas eliminables.")
                return

        result = MetadataSanitizer(scanner).sanitize(
            scan.path, mode, selected_entries=selected, before=scan
        )
        if mode == SanitizationMode.NONE:
            print("No se modificó ni creó ningún archivo.")
            export_choice = input(
                "¿Exportar la auditoría? [j] JSON, [t] texto, [Enter] no: "
            ).strip().lower()
            if export_choice in {"j", "t"}:
                suffix = ".json" if export_choice == "j" else ".txt"
                report_path = scan.path.with_name(
                    scan.path.stem + "_auditoria" + suffix
                )
                if report_path.exists():
                    print("El reporte ya existe; no se sobrescribió: {}".format(report_path))
                    return
                if export_choice == "j":
                    export_report_json(result.report, report_path)
                else:
                    export_report_text(result.report, report_path)
                print("Reporte guardado en: {}".format(report_path))
            return

        report = result.report
        print("\n" + report_as_text(report))
        export_choice = input(
            "\n¿Exportar reporte? [j] JSON, [t] texto, [Enter] no: "
        ).strip().lower()
        if export_choice in {"j", "t"} and result.output_path:
            suffix = ".json" if export_choice == "j" else ".txt"
            report_path = result.output_path.with_name(
                result.output_path.stem + "_reporte" + suffix
            )
            if export_choice == "j":
                export_report_json(report, report_path)
            else:
                export_report_text(report, report_path)
            print("Reporte guardado en: {}".format(report_path))
    except MetadataError as exc:
        print("No se pudo completar la operación: {}".format(exc))
