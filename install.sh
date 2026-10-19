#!/usr/bin/env bash
set -euo pipefail

role="Raspberry Pi"
colour="#000000"
width="1920"
height="1080"
accent="#ffad42"
position="bottom-left"
generate_only=0

usage() {
  echo "Usage: ./install.sh [--role NAME] [--colour '#RRGGBB'] [--accent '#RRGGBB'] [--position POSITION] [--width PX] [--height PX] [--generate-only]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --role) role="${2:?Missing role}"; shift 2 ;;
    --colour|--color) colour="${2:?Missing colour}"; shift 2 ;;
    --accent) accent="${2:?Missing accent}"; shift 2 ;;
    --position) position="${2:?Missing position}"; shift 2 ;;
    --width) width="${2:?Missing width}"; shift 2 ;;
    --height) height="${2:?Missing height}"; shift 2 ;;
    --generate-only) generate_only=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

[[ "$role" != *$'\n'* && "$role" != *$'\r'* ]] || { echo "Role must be a single line" >&2; exit 1; }
[[ "$colour" =~ ^#[0-9a-fA-F]{6}$ ]] || { echo "Colour must look like #000000" >&2; exit 1; }
[[ "$accent" =~ ^#[0-9a-fA-F]{6}$ ]] || { echo "Accent must look like #ffad42" >&2; exit 1; }
[[ "$position" =~ ^(top-left|top-right|bottom-left|bottom-right)$ ]] || { echo "Unsupported panel position: $position" >&2; exit 1; }
[[ "$width" =~ ^[0-9]+$ && "$height" =~ ^[0-9]+$ ]] || { echo "Width and height must be numbers" >&2; exit 1; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/pi-wallpaper"
bin_dir="$HOME/.local/bin"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/pi-wallpaper"
service_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$data_dir" "$bin_dir" "$config_dir" "$service_dir"
install -m 755 "$script_dir/pi-wallpaper.py" "$data_dir/pi-wallpaper.py"
install -m 755 "$script_dir/pi-wallpaper-refresh" "$bin_dir/pi-wallpaper-refresh"
install -m 755 "$script_dir/uninstall.sh" "$bin_dir/pi-info-wallpaper-uninstall"
{
  printf 'ROLE=%s\n' "$role"
  printf 'COLOUR=%s\n' "$colour"
  printf 'WIDTH=%s\n' "$width"
  printf 'HEIGHT=%s\n' "$height"
  printf 'ACCENT=%s\n' "$accent"
  printf 'POSITION=%s\n' "$position"
  printf 'GENERATE_ONLY=%s\n' "$generate_only"
} > "$config_dir/config"
chmod 600 "$config_dir/config"

sed "s|@HOME@|$HOME|g" "$script_dir/systemd/pi-wallpaper.service" > "$service_dir/pi-wallpaper.service"
install -m 644 "$script_dir/systemd/pi-wallpaper.timer" "$service_dir/pi-wallpaper.timer"

if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
  systemctl --user daemon-reload
  systemctl --user enable --now pi-wallpaper.timer
fi

if ! "$bin_dir/pi-wallpaper-refresh"; then
  echo "Installed successfully. Log into the desktop (or reboot) to apply the wallpaper." >&2
fi
echo "Installed Pi Info Wallpaper for $USER ($role, $colour, $position)."
