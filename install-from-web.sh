#!/usr/bin/env bash
set -euo pipefail

# Pin PI_WALLPAPER_VERSION to a tag for reproducible installs.
version="${PI_WALLPAPER_VERSION:-main}"
base_url="${PI_WALLPAPER_BASE_URL:-https://raw.githubusercontent.com/snuffsprojects/pi-info-wallpaper/$version}"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT
mkdir -p "$work_dir/systemd"

for file in pi-wallpaper.py pi-wallpaper-refresh install.sh uninstall.sh systemd/pi-wallpaper.service systemd/pi-wallpaper.timer; do
  printf 'Downloading %s…\n' "$file"
  curl -fsS "$base_url/$file" -o "$work_dir/$file"
done

chmod +x "$work_dir/pi-wallpaper.py" "$work_dir/pi-wallpaper-refresh" "$work_dir/install.sh" "$work_dir/uninstall.sh"
"$work_dir/install.sh" "$@"
