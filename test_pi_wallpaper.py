import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("pi-wallpaper.py")
SPEC = importlib.util.spec_from_file_location("pi_wallpaper", MODULE_PATH)
pi_wallpaper = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = pi_wallpaper
SPEC.loader.exec_module(pi_wallpaper)


class PiWallpaperTests(unittest.TestCase):
    def test_memory_formatting(self):
        self.assertEqual(pi_wallpaper.format_memory(8 * 1024 * 1024), "8 GB")
        self.assertEqual(pi_wallpaper.format_memory(512 * 1024), "512 MB")

    def test_uptime_formatting(self):
        self.assertEqual(pi_wallpaper.format_uptime(59), "0m")
        self.assertEqual(pi_wallpaper.format_uptime(3720), "1h 2m")
        self.assertEqual(pi_wallpaper.format_uptime(183600), "2d 3h")

    def test_model_normalisation(self):
        self.assertEqual(
            pi_wallpaper.normalise_model("Raspberry Pi 5 Model B Rev 1.0"),
            "Pi 5 Model B · Rev 1.0",
        )

    def test_xml_text_escapes_markup_and_removes_controls(self):
        self.assertEqual(pi_wallpaper.xml_text("Lab & <display>\x00"), "Lab &amp; &lt;display&gt;")

    def test_panel_positions_stay_inside_canvas(self):
        for position in pi_wallpaper.POSITIONS:
            x, y = pi_wallpaper.panel_origin(1920, 1080, 760, 620, position)
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + 760, 1920)
            self.assertLessEqual(y + 620, 1080)

    def test_render_is_valid_svg_and_escapes_role(self):
        info = pi_wallpaper.SystemInfo(
            hostname="demo-pi",
            model="Pi 5 Model B",
            memory="8 GB",
            ip_address="192.0.2.25",
            operating_system="Raspberry Pi OS",
            role="Kitchen & status <screen>",
            uptime="2d 3h",
        )
        svg = pi_wallpaper.render_svg(
            info,
            width=1920,
            height=1080,
            colour="#10243a",
            accent="#ffad42",
            position="bottom-left",
            generated_at=datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc),
        )
        ET.fromstring(svg)
        self.assertIn("Kitchen &amp; status &lt;screen&gt;", svg)
        self.assertIn("Updated 19 Oct 2026 · 12:00", svg)

    def test_minimum_supported_canvas_uses_compact_layout(self):
        info = pi_wallpaper.SystemInfo("pi", "Pi 4", "4 GB", "192.0.2.2", "Linux", "Display", "1h 2m")
        svg = pi_wallpaper.render_svg(
            info,
            width=640,
            height=480,
            colour="#000000",
            accent="#ffad42",
            position="bottom-right",
        )
        ET.fromstring(svg)
        self.assertIn("font-size: 36px", svg)

    def test_atomic_write_replaces_content(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "wallpaper.svg"
            target.write_text("old", encoding="utf-8")
            pi_wallpaper.atomic_write(target, "new")
            self.assertEqual(target.read_text(encoding="utf-8"), "new")
            self.assertEqual(list(target.parent.glob(".wallpaper.svg.*")), [])

    def test_collect_system_info_uses_role(self):
        with (
            mock.patch.object(pi_wallpaper, "read_text", return_value="Raspberry Pi 5 Model B Rev 1.0"),
            mock.patch.object(pi_wallpaper, "total_ram", return_value="8 GB"),
            mock.patch.object(pi_wallpaper, "ip_address", return_value="192.0.2.25"),
            mock.patch.object(pi_wallpaper, "os_name", return_value="Raspberry Pi OS"),
            mock.patch.object(pi_wallpaper, "system_uptime", return_value="1h 2m"),
            mock.patch.object(pi_wallpaper.socket, "gethostname", return_value="demo-pi"),
        ):
            info = pi_wallpaper.collect_system_info("Status display")
        self.assertEqual(info.role, "Status display")
        self.assertEqual(info.hostname, "demo-pi")
        self.assertEqual(info.model, "Pi 5 Model B · Rev 1.0")


if __name__ == "__main__":
    unittest.main()
