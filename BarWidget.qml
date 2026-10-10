import QtQuick
import Quickshell.Io
import qs.Ui

BarWidget {
  id: root
  moduleName: "aras.mirrored-camera"
  property string cameraState: "checking"
  property bool actionFailed: false
  readonly property string controller: decodeURIComponent(Qt.resolvedUrl("scripts/mirrored-camera").toString().replace(/^file:\/\//, ""))
  readonly property bool busy: toggleProcess.running || cameraState === "starting" || cameraState === "stopping"
  readonly property bool cameraActive: cameraState === "on"
  readonly property bool hasError: actionFailed || cameraState === "failed" || cameraState === "setup"
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function refresh() {
    if (!statusProcess.running) statusProcess.running = true
  }

  function toggle() {
    if (busy) return
    actionFailed = false
    toggleProcess.running = true
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.hasError ? "󰀦" : (root.cameraActive ? "󰄀" : "󰗟")
    active: root.cameraActive || root.hasError
    dimmed: !active
    interactive: !root.busy
    tooltipText: root.busy ? "Mirrored Camera · Switching…" :
      root.cameraState === "checking" ? "Mirrored Camera · Checking…" :
      root.cameraState === "setup" ? "Mirrored Camera · Setup required. See the plugin README." :
      root.hasError ? "Mirrored Camera · Could not start. Close other camera apps and click to retry." :
      root.cameraActive ? "Mirrored Camera · On\nClick to turn off. Select Mirrored Camera in your video app." :
      "Mirrored Camera · Off\nClick to turn on."
    onPressed: function(mouseButton) {
      if (mouseButton === Qt.LeftButton) root.toggle()
    }
  }

  Process {
    id: statusProcess
    command: [root.controller, "status"]
    running: true
    stdout: StdioCollector {
      onStreamFinished: {
        root.cameraState = this.text.trim() || "setup"
        if (root.cameraState === "on") root.actionFailed = false
      }
    }
  }

  Process {
    id: toggleProcess
    command: [root.controller, "toggle"]
    onExited: function(exitCode, exitStatus) {
      root.actionFailed = exitCode !== 0
      root.refresh()
    }
  }

  Timer {
    interval: 3000
    running: true
    repeat: true
    onTriggered: root.refresh()
  }
}
