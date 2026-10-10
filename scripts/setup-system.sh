#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run this script with sudo.' >&2; exit 1; }
[[ -d /usr/lib/modules/$(uname -r)/build ]] || {
  echo 'Install headers matching your running kernel before installing v4l2loopback-dkms.' >&2
  exit 1
}
export PATH="/usr/share/omarchy/bin:$PATH"
omarchy pkg add ffmpeg v4l-utils v4l2loopback-dkms
# Do not reuse an unrelated camera's device number.
if [[ -e /dev/video10 ]]; then
  info=$(v4l2-ctl -d /dev/video10 -D)
  [[ $info == *"v4l2 loopback"* ]] || { echo '/dev/video10 belongs to another driver. Choose a free device number.' >&2; exit 1; }
  label=$(cat /sys/class/video4linux/video10/name)
  [[ $label == 'Mirrored Camera' || $label == 'Aynali Kamera' ]] || {
    echo '/dev/video10 is an existing virtual camera owned by another setup.' >&2
    exit 1
  }
fi
printf '%s\n' 'options v4l2loopback devices=1 video_nr=10 card_label="Mirrored Camera" exclusive_caps=1' > /etc/modprobe.d/mirrored-camera.conf
printf '%s\n' 'v4l2loopback' > /etc/modules-load.d/mirrored-camera.conf
modprobe v4l2loopback devices=1 video_nr=10 card_label='Mirrored Camera' exclusive_caps=1
if [[ $(cat /sys/class/video4linux/video10/name) != 'Mirrored Camera' ]]; then
  echo 'Module already loaded. The camera name will change to Mirrored Camera after a reboot.'
fi
