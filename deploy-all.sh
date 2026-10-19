#!/usr/bin/env bash
set -euo pipefail

inventory="${1:-inventory.csv}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "$inventory" ]] || { echo "Inventory not found: $inventory" >&2; exit 1; }

failures=0
while IFS=',' read -r host user role colour; do
  [[ -z "${host// }" || "$host" == "host" || "$host" == \#* ]] && continue
  host="${host// /}"
  user="${user// /}"
  role="${role# }"; role="${role% }"
  colour="${colour// /}"
  target="$host"
  [[ -n "$user" ]] && target="$user@$host"
  args=("$target" --role "${role:-Raspberry Pi}")
  [[ -n "$colour" ]] && args+=(--colour "$colour")
  "$script_dir/deploy.sh" "${args[@]}" || failures=$((failures + 1))
done < "$inventory"

[[ $failures -eq 0 ]] || { echo "$failures deployment(s) failed." >&2; exit 1; }
echo "All deployments completed successfully."
