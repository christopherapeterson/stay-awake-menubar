#!/bin/bash
# Build a double-clickable StayAwake.app bundle that runs the menu bar app from
# this project's virtualenv. The app is a lightweight launcher (LSUIElement
# agent: menu bar only, no Dock icon) that execs the venv Python on main.py.
#
# Usage:  scripts/make_app.sh
# Output: build/StayAwake.app
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$PROJECT_DIR/build/StayAwake.app"
PY="$PROJECT_DIR/.venv/bin/python"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# Info.plist
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>            <string>Stay Awake</string>
    <key>CFBundleDisplayName</key>     <string>Stay Awake</string>
    <key>CFBundleIdentifier</key>      <string>com.chrispeterson.stayawake</string>
    <key>CFBundleVersion</key>         <string>0.1.0</string>
    <key>CFBundleShortVersionString</key><string>0.1.0</string>
    <key>CFBundleExecutable</key>      <string>StayAwake</string>
    <key>CFBundlePackageType</key>     <string>APPL</string>
    <key>CFBundleIconFile</key>        <string>AppIcon</string>
    <key>LSUIElement</key>             <true/>
    <key>LSMinimumSystemVersion</key>  <string>10.13</string>
    <key>NSHumanReadableCopyright</key><string>MIT License</string>
</dict>
</plist>
PLIST

# Launcher executable
cat > "$APP/Contents/MacOS/StayAwake" <<LAUNCH
#!/bin/bash
exec "$PY" "$PROJECT_DIR/main.py"
LAUNCH
chmod +x "$APP/Contents/MacOS/StayAwake"

# Icon
if [ -f "$PROJECT_DIR/Resources/AppIcon.icns" ]; then
    cp "$PROJECT_DIR/Resources/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"
fi

# Refresh icon/registration caches so Finder shows the new icon immediately.
touch "$APP"
echo "Built: $APP"
