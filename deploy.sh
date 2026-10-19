#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: ./deploy.sh [user@]host --role NAME [--colour '#RRGGBB'] [--width PX] [--height PX]"
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && { usage; exit 0; }
[[ $# -ge 1 ]] || { usage >&2; exit 1; }
target="$1"
shift
[[ "$target" =~ ^[a-zA-Z0-9._@:-]+$ ]] || { echo "Invalid SSH target" >&2; exit 1; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
archive="$(mktemp --suffix=.tar.gz)"
trap 'rm -f "$archive"' EXIT
tar -C "$script_dir" -czf "$archive" pi-wallpaper.py pi-wallpaper-refresh install.sh uninstall.sh systemd

printf 'Deploying Pi Wallpaper to %s…\n' "$target"
ssh "$target" 'set -e; work_dir=$(mktemp -d); trap '\''rm -rf "$work_dir"'\'' EXIT; tar -xzf - -C "$work_dir"; cd "$work_dir"; ./install.sh "$@"' pi-wallpaper-install "$@" < "$archive"
printf 'Deployment to %s complete.\n' "$target"
