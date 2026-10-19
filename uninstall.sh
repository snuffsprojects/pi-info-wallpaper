#!/usr/bin/env bash
set -euo pipefail

data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/pi-wallpaper"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/pi-wallpaper"
service_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
  systemctl --user disable --now pi-wallpaper.timer >/dev/null 2>&1 || true
  systemctl --user daemon-reload
fi

rm -f "$HOME/.local/bin/pi-wallpaper-refresh"
rm -f "$HOME/.local/bin/pi-info-wallpaper-uninstall"
rm -f "$service_dir/pi-wallpaper.service" "$service_dir/pi-wallpaper.timer"
rm -rf "$data_dir" "$config_dir"
echo "Pi Info Wallpaper was removed. Your desktop may keep the last generated image until you choose another wallpaper."
