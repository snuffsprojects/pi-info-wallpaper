#!/usr/bin/env python3
"""Generate a lightweight BGInfo-style SVG wallpaper for Raspberry Pi desktops."""

from __future__ import annotations

import argparse
import html
import os
import platform
import re
import socket
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


HEX_COLOUR = re.compile(r"#[0-9a-fA-F]{6}")
POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")


@dataclass(frozen=True)
class SystemInfo:
    hostname: str
    model: str
    memory: str
    ip_address: str
    operating_system: str
    role: str
    uptime: str


def read_text(path: str | Path, default: str = "Unknown") -> str:
    try:
        return Path(path).read_text(encoding="utf-8").strip() or default
    except OSError:
        return default


def os_name(path: str | Path = "/etc/os-release") -> str:
    values: dict[str, str] = {}
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
    except OSError:
        return platform.platform()
    return values.get("PRETTY_NAME") or values.get("NAME") or platform.platform()


def format_memory(kib: int) -> str:
    gib = kib / 1024 / 1024
    return f"{gib:.0f} GB" if gib >= 0.95 else f"{kib / 1024:.0f} MB"


def total_ram(path: str | Path = "/proc/meminfo") -> str:
    try:
        line = next(item for item in Path(path).read_text().splitlines() if item.startswith("MemTotal:"))
        return format_memory(int(line.split()[1]))
    except (OSError, StopIteration, ValueError):
        return "Unknown"


def format_uptime(seconds: float) -> str:
    minutes = max(0, int(seconds)) // 60
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def system_uptime(path: str | Path = "/proc/uptime") -> str:
    try:
        return format_uptime(float(Path(path).read_text().split()[0]))
    except (OSError, IndexError, ValueError):
        return "Unknown"


def ip_address() -> str:
    sock = None
    try:
        # TEST-NET-1 is never contacted; UDP connect only asks the kernel which
        # local interface it would use.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("192.0.2.1", 80))
        return sock.getsockname()[0]
    except (OSError, PermissionError):
        try:
            result = subprocess.run(
                ["hostname", "-I"], check=False, capture_output=True, text=True, timeout=2
            )
            addresses = [item for item in result.stdout.split() if not item.startswith("127.") and ":" not in item]
            if addresses:
                return addresses[0]
            resolved = socket.gethostbyname(socket.gethostname())
            return resolved if not resolved.startswith("127.") else "Not connected"
        except (OSError, subprocess.SubprocessError):
            return "Not connected"
    finally:
        if sock is not None:
            sock.close()


def normalise_model(value: str) -> str:
    return value.replace("Raspberry Pi ", "Pi ").replace(" Rev ", " · Rev ")


def xml_text(value: object) -> str:
    # XML 1.0 does not allow most ASCII control characters.
    cleaned = "".join(char for char in str(value) if char in "\t\n\r" or ord(char) >= 0x20)
    return html.escape(cleaned, quote=True)


def collect_system_info(role: str) -> SystemInfo:
    model = normalise_model(read_text("/proc/device-tree/model", platform.machine()).rstrip("\x00"))
    return SystemInfo(
        hostname=socket.gethostname(),
        model=model,
        memory=total_ram(),
        ip_address=ip_address(),
        operating_system=os_name(),
        role=role,
        uptime=system_uptime(),
    )


def panel_origin(width: int, height: int, panel_width: int, panel_height: int, position: str) -> tuple[int, int]:
    margin = max(32, min(64, width // 20, height // 14))
    x = margin if position.endswith("left") else width - panel_width - margin
    y = margin if position.startswith("top") else height - panel_height - margin
    return max(24, x), max(24, y)


def render_svg(
    info: SystemInfo,
    *,
    width: int,
    height: int,
    colour: str,
    accent: str,
    position: str,
    generated_at: datetime | None = None,
) -> str:
    panel_width = min(760, width - 64)
    panel_height = min(620, height - 64)
    x, y = panel_origin(width, height, panel_width, panel_height, position)
    compact = panel_height < 540
    kicker_y = y + (50 if compact else 64)
    title_y = y + (94 if compact else 126)
    divider_y = y + (116 if compact else 154)
    rows_start = y + (150 if compact else 196)
    title_size = 36 if compact else 48
    rows = [
        ("Model", info.model),
        ("Memory", info.memory),
        ("IP address", info.ip_address),
        ("OS", info.operating_system),
        ("Role", info.role),
        ("Uptime", info.uptime),
    ]
    row_gap = max(34, min(48, (panel_height - (190 if compact else 250)) // len(rows)))
    row_svg = []
    for index, (label, value) in enumerate(rows):
        row_y = rows_start + (index * row_gap)
        row_svg.append(f'<text x="{x + 48}" y="{row_y}" class="label">{xml_text(label.upper())}</text>')
        row_svg.append(f'<text x="{x + 220}" y="{row_y}" class="value">{xml_text(value)}</text>')

    generated = (generated_at or datetime.now().astimezone()).strftime("Updated %d %b %Y · %H:%M")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    text {{ font-family: "DejaVu Sans", "Liberation Sans", sans-serif; }}
    .kicker {{ fill: {accent}; font-size: 18px; font-weight: 700; letter-spacing: 4px; }}
    .title {{ fill: #f4f1e9; font-size: {title_size}px; font-weight: 700; }}
    .label {{ fill: #9ca59e; font-size: 16px; font-weight: 700; letter-spacing: 1.5px; }}
    .value {{ fill: #f4f1e9; font-size: 23px; }}
    .updated {{ fill: #737b75; font-size: 15px; }}
  </style>
  <rect width="100%" height="100%" fill="{colour}"/>
  <rect x="{x}" y="{y}" width="{panel_width}" height="{panel_height}" rx="24" fill="#171b19" fill-opacity=".94" stroke="#303832"/>
  <rect x="{x}" y="{y}" width="8" height="{panel_height}" rx="4" fill="{accent}"/>
  <text x="{x + 48}" y="{kicker_y}" class="kicker">RASPBERRY PI</text>
  <text x="{x + 48}" y="{title_y}" class="title">{xml_text(info.hostname)}</text>
  <line x1="{x + 48}" y1="{divider_y}" x2="{x + panel_width - 48}" y2="{divider_y}" stroke="#303832"/>
  {''.join(row_svg)}
  <text x="{x + 48}" y="{y + panel_height - 30}" class="updated">{xml_text(generated)}</text>
</svg>'''


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as output:
            output.write(content)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--role", default=os.environ.get("PI_WALLPAPER_ROLE", "Raspberry Pi"))
    result.add_argument("--colour", "--color", default=os.environ.get("PI_WALLPAPER_COLOUR", "#000000"))
    result.add_argument("--accent", default=os.environ.get("PI_WALLPAPER_ACCENT", "#ffad42"))
    result.add_argument("--position", choices=POSITIONS, default=os.environ.get("PI_WALLPAPER_POSITION", "bottom-left"))
    result.add_argument("--output", default=str(Path.home() / ".local/share/pi-wallpaper/wallpaper.svg"))
    result.add_argument("--width", type=int, default=1920)
    result.add_argument("--height", type=int, default=1080)
    return result


def main() -> None:
    args = parser().parse_args()
    if not HEX_COLOUR.fullmatch(args.colour):
        parser().error("colour must be a six-digit hex value such as #000000")
    if not HEX_COLOUR.fullmatch(args.accent):
        parser().error("accent must be a six-digit hex value such as #ffad42")
    if not 640 <= args.width <= 7680 or not 480 <= args.height <= 4320:
        parser().error("wallpaper dimensions are outside the supported range")
    if "\n" in args.role or "\r" in args.role or len(args.role) > 80:
        parser().error("role must be a single line of at most 80 characters")

    svg = render_svg(
        collect_system_info(args.role),
        width=args.width,
        height=args.height,
        colour=args.colour,
        accent=args.accent,
        position=args.position,
    )
    output = Path(args.output).expanduser()
    atomic_write(output, svg)
    print(output)


if __name__ == "__main__":
    main()
