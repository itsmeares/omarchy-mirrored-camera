#!/usr/bin/env bash
set -euo pipefail
plugin_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
expected="$HOME/.config/omarchy/plugins/aras.mirrored-camera"
[[ $plugin_dir == "$expected" ]] || { echo "Install the plugin into $expected first." >&2; exit 1; }
for dependency in ffmpeg systemctl flock; do
  command -v "$dependency" >/dev/null || { echo "Missing dependency: $dependency" >&2; exit 1; }
done
mkdir -p "$HOME/.config/systemd/user" "$HOME/.config/mirrored-camera" "$HOME/.local/bin" "$HOME/.local/share/applications"
if [[ ! -f $HOME/.config/mirrored-camera/camera.conf ]]; then
  install -m 600 "$plugin_dir/camera.conf.example" "$HOME/.config/mirrored-camera/camera.conf"
fi
install -m 644 "$plugin_dir/mirrored-camera.service" "$HOME/.config/systemd/user/mirrored-camera.service"
# Keep the existing launcher working after upgrades.
cat > "$HOME/.local/bin/mirrored-camera" <<'WRAPPER'
#!/usr/bin/env bash
exec "$HOME/.config/omarchy/plugins/aras.mirrored-camera/scripts/mirrored-camera" "$@"
WRAPPER
chmod +x "$HOME/.local/bin/mirrored-camera"
cat > "$HOME/.local/share/applications/mirrored-camera.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Mirrored Camera
Comment=Turn your mirrored virtual webcam on or off
Exec="$HOME/.local/bin/mirrored-camera"
Icon=camera-web
Terminal=false
Categories=AudioVideo;Video;
DESKTOP
systemctl --user daemon-reload
printf 'User service installed. Camera state unchanged.\n'
if [[ ! -e /dev/video10 ]]; then
  printf 'Virtual camera missing. Run: sudo bash %q/scripts/setup-system.sh\n' "$plugin_dir"
fi
