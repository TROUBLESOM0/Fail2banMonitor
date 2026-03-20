#!/bin/bash

NEW_VERSION="2.1.1"

month=$(date +"%B")
year=$(date +"%Y")

FILES=(
  "./static/css/custom.css"
  "./static/js/main.js"
  "./app.py"
  "./fail2ban_service.py"
  "./install.sh"
  "./uninstall.sh"
  "./templates/ban_times.html"
  "./templates/index.html"
)

echo "=== Updating version strings to $NEW_VERSION ==="

update_line4() {
  local file="$1"
  # Extract line 4
  local line
  line=$(sed -n '4p' "$file")

  # Check for "Version" or "version"
  if [[ "$line" =~ [Vv]ersion ]]; then
    # Preserve case and formatting
    if [[ "$line" =~ [Vv]ersion[[:space:]]*[:=][[:space:]]*v ]]; then
      sed -i "4s|\([Vv]ersion[[:space:]]*[:=][[:space:]]*v\).*|\1$NEW_VERSION|" "$file"
      echo "→ Updated $file (kept 'v' prefix)"
    elif [[ "$line" =~ [Vv]ersion[[:space:]]*[:=] ]]; then
      sed -i "4s|\([Vv]ersion[[:space:]]*[:=][[:space:]]*\).*|\1$NEW_VERSION|" "$file"
      echo "→ Updated $file (no 'v' prefix)"
    else
      sed -i "4s|\([Vv]ersion[[:space:]]*\).*|\1$NEW_VERSION|" "$file"
      echo "→ Updated $file (loose match)"
    fi
  else
    echo "→ Skipped $file (no version string on line 4)"
  fi
}

# Check for and update date on line 6
update_date_line() {
  local file="$1"
  for lineno in 6 7; do
    line=$(sed -n "${lineno}p" "$file")
    # Match optional leading spaces or '* ' before 'Date:'
    if [[ "$line" =~ [[:space:]]*\*?[[:space:]]*Date: ]]; then
      # Replace the entire line, preserving leading characters
      leading=$(echo "$line" | sed -E 's/([[:space:]]*\*?[[:space:]]*)Date:.*/\1/')
      sed -i "${lineno}s|.*|${leading}Date: $month $year|" "$file"
      echo "→ Updated $file line $lineno with Date: $month $year"
      return 0  # stop after first match
    fi
  done
  echo "→ Skipped $file (no 'Date:' found in line 6 or 7)"
}

update_uv_lock() {
  local file="uv.lock"
  if [[ -f "$file" ]]; then
    # Find the line number of 'name = "fail2ban-monitor"'
    local lineno
    lineno=$(grep -n 'name = "fail2ban-monitor"' "$file" | cut -d: -f1)

    if [[ -n "$lineno" ]]; then
      # Next line number
      local nextline=$((lineno + 1))
      # Replace next line with version = "$NEW_VERSION"
      sed -i "${nextline}s|.*|version = \"$NEW_VERSION\"|" "$file"
      echo "→ Updated $file line $nextline with version = \"$NEW_VERSION\""
    else
      echo "→ Skipped $file (no 'name = \"fail2ban-monitor\"' found)"
    fi
  else
    echo "→ uv.lock not found"
  fi
}

# update app.py version
update_app_version() {
  local file="app.py"
  if [[ -f "$file" ]]; then
    if grep -q 'APP_VERSION =' "$file"; then
      # Replace the line containing 'APP_VERSION =' with the new version
      sed -i "s|^APP_VERSION =.*|APP_VERSION = \"$NEW_VERSION\"|" "$file"
      echo "→ Updated $file with APP_VERSION = \"$NEW_VERSION\""
    else
      echo "→ Skipped $file (no 'APP_VERSION =' found)"
    fi
  else
    echo "→ $file not found"
  fi
}

update_version_file() {
  local file="VERSION"
  if [[ -f "$file" ]]; then
    echo "v$NEW_VERSION" > "$file"
    echo "→ Updated $file with v$NEW_VERSION"
  else
    echo "→ VERSION file not found"
  fi
}

# Process all target files
for file in "${FILES[@]}"; do
  if [[ -f "$file" ]]; then
    update_line4 "$file"
    update_date_line "$file"
  else
    echo "→ File not found: $file"
  fi
done

# Handle pyproject.toml (line 3)
PYPROJECT="./pyproject.toml"
if [[ -f "$PYPROJECT" ]]; then
  echo "Processing $PYPROJECT ..."
  line=$(sed -n '3p' "$PYPROJECT")   # removed 'local'

  if [[ "$line" =~ version[[:space:]]*=[[:space:]]*v ]]; then
    sed -i "3s|version[[:space:]]*=[[:space:]]*v.*|version = v\"$NEW_VERSION\"|" "$PYPROJECT"
    echo "→ Updated pyproject.toml (kept 'v' prefix)"
  elif [[ "$line" =~ version[[:space:]]*= ]]; then
    sed -i "3s|version[[:space:]]*=.*|version = \"$NEW_VERSION\"|" "$PYPROJECT"
    echo "→ Updated pyproject.toml (no 'v' prefix)"
  else
    echo "→ Skipped pyproject.toml (no version key on line 3)"
  fi
else
  echo "→ pyproject.toml not found"
fi

update_uv_lock
update_app_version
update_version_file

echo "=== Version update complete ==="
