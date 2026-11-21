#!/usr/bin/env bash
# Repository hygiene check for a PUBLIC repo. Run before every PR; also runs in CI.
#  1. forbidden file names (credentials, private notes, Office temp files, thesis/course material)
#  2. files larger than MAX_MB
#  3. secret-looking keywords in text files
# Checks tracked + untracked (not ignored) files. Exit code 1 on any finding.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
MAX_MB=${MAX_MB:-10}
SELF="scripts/check-repo.sh"
fail=0

mapfile -d '' files < <(git ls-files -z --cached --others --exclude-standard)

forbidden='(^|/)(credentials[^/]*|rasp_wifi[^/]*|software-tests\.txt|~\$[^/]*|~WRL[^/]*\.tmp|\.env(\..*)?|[^/]*\.(pem|key|pptx|docx))$|(^|/)(KiCad-udemy-kurs|bricktronics|obrona|tresc_inzynierki)(/|$)'
keywords='password|passwd|haslo|hasło|token|ssid|psk='

for f in "${files[@]}"; do
  [[ -f "$f" ]] || continue
  if [[ "$f" =~ $forbidden ]]; then
    echo "FORBIDDEN FILE: $f"; fail=1
  fi
  size=$(stat -c %s "$f")
  if (( size > MAX_MB * 1024 * 1024 )); then
    echo "TOO LARGE (> ${MAX_MB} MB): $f ($((size / 1024 / 1024)) MB)"; fail=1
  fi
  [[ "$f" == "$SELF" ]] && continue
  if grep -IinE "$keywords" -- "$f" >/dev/null 2>&1; then
    grep -IinE "$keywords" -- "$f" | cut -c1-160 | sed "s|^|KEYWORD $f:|"
    fail=1
  fi
done

if (( fail )); then
  echo "check-repo: FAILED"; exit 1
fi
echo "check-repo: OK (${#files[@]} files)"
