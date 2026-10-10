# Mirrored Camera for Omarchy

A bar button that sends a horizontally flipped webcam feed to your video apps.
Click to turn it on, click again to turn it off. The icon shows whether the
camera is running, switching, or needs attention.

Uses FFmpeg and v4l2loopback. All processing stays on your computer. No OBS,
recordings, accounts, or background video processing when the camera is off.

## Requirements

- Omarchy with the Quickshell bar and `omarchy plugin` support.
- Kernel headers matching the **running** kernel, required by DKMS.
- A V4L2 webcam. The default preset needs MJPEG at 1280×720, 30 FPS.

This is a Quickshell plugin. It does not target the older Waybar-based bar.
Tested on Omarchy 4.0.4 with one integrated USB camera.

## Install

```sh
omarchy plugin add https://github.com/itsmeares/omarchy-mirrored-camera
cd ~/.config/omarchy/plugins/aras.mirrored-camera
sudo bash scripts/setup-system.sh
bash scripts/install.sh
omarchy plugin enable aras.mirrored-camera --section right
```

The system setup installs FFmpeg, v4l-utils, and v4l2loopback-dkms. It creates
`/dev/video10`, named **Mirrored Camera**, with WebRTC-compatible exclusive
capabilities. It loads the virtual device on boot, but **does not turn your
physical camera on at login**. If a compatible loopback module is already
loaded under an older name, the new name takes effect after a reboot.

Use the matching headers for your kernel, such as `linux-omarchy-headers` for
`linux-omarchy`. If you have just updated your kernel, reboot before setup.

## Use

1. Click the camera icon in the bar, or open **Mirrored Camera** from the app menu.
2. Choose **Mirrored Camera** as the camera source in your video app.
3. Click the icon again when you are done.

The camera stays on until you turn it off or end your user session. Its physical
indicator light stays on while it runs. Hiding or removing the widget does not
stop an already-running camera; use the app-menu launcher or
`systemctl --user stop mirrored-camera.service` to stop it.

The outgoing video is mirrored. If your video app also mirrors its own preview,
turn that setting off to see the same orientation as the outgoing feed. Other
participants will see text and logos flipped too.

## Configure your camera

Edit `~/.config/mirrored-camera/camera.conf`, then turn the camera off and on.
Your settings survive plugin updates.

```ini
CAMERA_DEVICE=/dev/v4l/by-id/your-camera-video-index0
CAMERA_OUTPUT=/dev/video10
CAMERA_FORMAT=mjpeg
CAMERA_SIZE=1280x720
CAMERA_FPS=30
```

Leave `CAMERA_DEVICE` empty to use the first USB camera with a stable `by-id`
path, falling back to `/dev/video0`. With multiple cameras, set it explicitly.
Only choose a resolution, frame rate, and format supported by your webcam:

```sh
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

The plugin does not upscale or negotiate an unsupported preset. An invalid
preset produces a visible error instead. If you change `CAMERA_OUTPUT`, create
a matching loopback device yourself; system setup uses `/dev/video10`.

## Bar placement

```sh
omarchy bar move aras.mirrored-camera --section left
omarchy plugin disable aras.mirrored-camera
omarchy plugin enable aras.mirrored-camera --section right
```

You can also manage it through Omarchy's widget settings.

## Quality and performance

Horizontal flipping preserves the image's spatial detail. The default pipeline
decodes the webcam's MJPEG, flips it, and outputs uncompressed YUV420P frames.
There is no additional lossy encoder, but the pixel-format conversion means the
output is not bit-identical to the input. Your video app may compress it again.

On the tested eight-thread laptop at 720p/30, FFmpeg used about 6% of one logical
CPU core and 130 MB RSS during short measurements. That is about 0.8% of total
CPU capacity. These are observations, not hardware requirements; resolution,
camera format, and video-app processing change the cost. A running camera also
uses battery and adds a processing step to the video path.

## Troubleshooting

An attention icon means setup is missing or the stream failed. Close apps using
the physical camera and retry. Inspect the actual error with:

```sh
journalctl --user -u mirrored-camera.service -n 30
```

If the virtual camera is absent, check `lsmod | rg v4l2loopback` and rerun system
setup. With `exclusive_caps=1`, some apps only discover the virtual camera after
you turn it on. Reopen the app or its camera picker after starting the stream.

## Update and remove

```sh
omarchy plugin update aras.mirrored-camera
bash ~/.config/omarchy/plugins/aras.mirrored-camera/scripts/install.sh
```

Reinstalling the user service preserves your camera configuration and does not
restart an active stream. Changes apply the next time you start the camera.

To remove it, stop the stream, disable the widget, then remove its files:

```sh
systemctl --user stop mirrored-camera.service
omarchy plugin disable aras.mirrored-camera
omarchy plugin remove aras.mirrored-camera
rm -f ~/.config/systemd/user/mirrored-camera.service
rm -f ~/.local/bin/mirrored-camera ~/.local/share/applications/mirrored-camera.desktop
systemctl --user daemon-reload
```

If you no longer need its boot configuration, remove only the two files created
by this plugin: `/etc/modprobe.d/mirrored-camera.conf` and
`/etc/modules-load.d/mirrored-camera.conf`. Keep v4l2loopback installed if other
apps depend on it. Your saved `~/.config/mirrored-camera/camera.conf` is retained.

## Development

```sh
python3 -m unittest discover -s tests -v
omarchy plugin validate .
```

The backend tests use fake services and camera devices. Live video and the QML
widget also need verification on an Omarchy desktop.

## License

MIT. See [LICENSE](LICENSE).
