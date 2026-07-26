from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from metadata.cli import _image_path_from_directory
from metadata.models import RiskLevel, SanitizationMode
from metadata.sanitizer import MetadataSanitizer, safe_output_path
from metadata.scanner import MetadataScanner


class Completed:
    def __init__(self, payload):
        self.stdout = json.dumps([payload])
        self.stderr = ""
        self.returncode = 0


class MetadataCliTests(unittest.TestCase):
    def test_relative_image_path_uses_selected_directory(self):
        selected = Path("source")
        self.assertEqual(
            _image_path_from_directory("sample.jpg", selected),
            selected / "sample.jpg",
        )

    def test_absolute_image_path_is_preserved(self):
        absolute = Path("/tmp/sample.jpg")
        self.assertEqual(
            _image_path_from_directory(str(absolute), Path("source")),
            absolute,
        )


class MetadataScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.image_path = Path(self.temp_dir.name) / "sample.jpg"
        Image.new("RGB", (20, 10), "red").save(self.image_path, "JPEG")

    def _scan_payload(self, payload):
        with patch(
            "metadata.scanner.subprocess.run",
            return_value=Completed(payload),
        ):
            return MetadataScanner(
                exiftool_path="/fake/exiftool", allow_pillow_fallback=False
            ).scan(self.image_path)

    def test_image_with_gps_is_high_risk_and_embedded(self):
        scan = self._scan_payload(
            {
                "ExifTool:ExifToolVersion": 13.0,
                "File:FileName": "sample.jpg",
                "GPS:GPSLatitude": -51.62,
                "GPS:GPSLongitude": -69.22,
            }
        )
        gps = [entry for entry in scan.entries if entry.tag.startswith("GPS")]
        self.assertEqual(len(gps), 2)
        self.assertTrue(all(entry.risk == RiskLevel.HIGH for entry in gps))
        self.assertTrue(all(entry.category == "Ubicación" for entry in gps))
        self.assertTrue(all(entry.embedded for entry in gps))

    def test_image_without_embedded_metadata(self):
        scan = MetadataScanner(
            exiftool_path=None, allow_pillow_fallback=True
        )
        scan.exiftool_path = None
        result = scan.scan(self.image_path)
        self.assertEqual(result.width, 20)
        self.assertEqual(result.height, 10)
        self.assertFalse(
            any(
                entry.group == "EXIF" and entry.embedded
                for entry in result.entries
            )
        )

    def test_image_with_exif_and_xmp(self):
        scan = self._scan_payload(
            {
                "IFD0:Make": "Example Camera",
                "ExifIFD:DateTimeOriginal": "2025:01:02 03:04:05",
                "XMP:CreatorTool": "Example Editor",
                "XMP:HistoryAction": "saved",
            }
        )
        make = next(entry for entry in scan.entries if entry.tag == "Make")
        xmp = [entry for entry in scan.entries if entry.group == "XMP"]
        self.assertEqual(make.category, "Cámara y captura")
        self.assertEqual(len(xmp), 2)
        self.assertTrue(all(entry.risk == RiskLevel.MEDIUM for entry in xmp))


class MetadataSanitizerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.image_path = Path(self.temp_dir.name) / "plain.png"
        Image.new("RGB", (16, 8), "blue").save(self.image_path, "PNG")

    def test_pillow_total_creates_copy_and_preserves_original(self):
        scanner = MetadataScanner(exiftool_path=None)
        scanner.exiftool_path = None
        before_bytes = self.image_path.read_bytes()
        result = MetadataSanitizer(scanner).sanitize(
            self.image_path, SanitizationMode.TOTAL
        )
        self.assertTrue(result.success)
        self.assertIsNotNone(result.output_path)
        self.assertTrue(result.output_path.exists())
        self.assertEqual(self.image_path.read_bytes(), before_bytes)
        self.assertTrue(
            result.report.verification["dimensiones_conservadas"]
        )
        self.assertTrue(
            result.report.verification["archivo_original_intacto"]
        )

    def test_incremental_output_name(self):
        first = safe_output_path(self.image_path)
        first.touch()
        second = safe_output_path(self.image_path)
        self.assertEqual(second.name, "plain_sanitizada_2.png")

    def test_total_materializes_exif_orientation(self):
        rotated = Path(self.temp_dir.name) / "rotated.jpg"
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (10, 20), "purple").save(
            rotated, "JPEG", exif=exif
        )
        scanner = MetadataScanner(exiftool_path=None)
        scanner.exiftool_path = None
        result = MetadataSanitizer(scanner).sanitize(
            rotated, SanitizationMode.TOTAL
        )
        self.assertEqual(
            (result.report.after.width, result.report.after.height), (20, 10)
        )
        self.assertTrue(
            result.report.verification["dimensiones_conservadas"]
        )
        self.assertTrue(
            result.report.verification["orientacion_visual_conservada"]
        )


if __name__ == "__main__":
    unittest.main()
