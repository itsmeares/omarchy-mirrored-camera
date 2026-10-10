import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

CONTROLLER = Path(__file__).resolve().parents[1] / 'scripts' / 'mirrored-camera'


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.state = self.root / 'state'
        self.state.write_text('inactive')
        self.env = os.environ | {
            'PATH': f'{self.bin}:/usr/bin:/bin',
            'XDG_RUNTIME_DIR': str(self.root),
            'TEST_ROOT': str(self.root),
        }
        self.stub('systemctl', '''
case "$*" in
  *show*)
    if test "${TEST_MISSING:-0}" = 1; then
      printf 'LoadState=not-found\\nActiveState=inactive\\n'
      exit 4
    fi
    printf 'LoadState=loaded\\nActiveState=%s\\n' "$(cat "$TEST_ROOT/state")"
    ;;
  *start*)
    if test "${TEST_FAIL:-0}" = 1; then echo failed > "$TEST_ROOT/state"
    else echo active > "$TEST_ROOT/state"; fi
    ;;
  *stop*) echo inactive > "$TEST_ROOT/state" ;;
  *daemon-reload*) exit 0 ;;
  *) exit 2 ;;
esac
''')
        self.stub('sleep', 'exit 0')
        self.stub('notify-send', 'printf "%s\\n" "$*" > "$TEST_ROOT/notification"')
        self.stub('ffmpeg', '''
exec /usr/bin/python3 -c 'import json,os,sys; open(os.environ["TEST_ROOT"]+"/args", "w").write(json.dumps(sys.argv[1:]))' "$@"
''')

    def stub(self, name, body):
        script = self.bin / name
        script.write_text('#!/bin/bash\nset -eu\n' + body)
        script.chmod(0o755)

    def run_backend(self, action, **environment):
        return subprocess.run([str(CONTROLLER), action], env=self.env | environment,
                              text=True, capture_output=True)

    def test_status_states(self):
        for state, expected in [('active', 'on'), ('inactive', 'off'),
                                ('activating', 'starting'), ('deactivating', 'stopping'),
                                ('failed', 'failed')]:
            with self.subTest(state=state):
                self.state.write_text(state)
                result = self.run_backend('status')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)
        self.assertEqual(self.run_backend('status', TEST_MISSING='1').stdout.strip(), 'setup')

    def test_toggle_starts_and_stops(self):
        self.assertEqual(self.run_backend('toggle').returncode, 0)
        self.assertEqual(self.state.read_text().strip(), 'active')
        self.assertEqual(self.run_backend('toggle').returncode, 0)
        self.assertEqual(self.state.read_text().strip(), 'inactive')

    def test_retry_failed_service(self):
        self.state.write_text('failed')
        self.assertEqual(self.run_backend('toggle').returncode, 0)
        self.assertEqual(self.state.read_text().strip(), 'active')

    def test_failed_stream_and_missing_setup_report_error(self):
        self.assertEqual(self.run_backend('toggle', TEST_FAIL='1').returncode, 1)
        self.assertIn('Could not start', (self.root / 'notification').read_text())
        self.assertEqual(self.run_backend('toggle', TEST_MISSING='1').returncode, 1)
        self.assertIn('Setup required', (self.root / 'notification').read_text())

    def test_stream_preserves_paths_and_requested_mode(self):
        camera = self.root / 'camera with spaces'
        output = self.root / 'virtual camera'
        camera.touch()
        output.touch()
        result = self.run_backend('run', CAMERA_DEVICE=str(camera), CAMERA_OUTPUT=str(output),
                                  CAMERA_SIZE='1920x1080', CAMERA_FPS='25', CAMERA_FORMAT='yuyv422')
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads((self.root / 'args').read_text())
        for flag, value in [('-i', str(camera)), ('-video_size', '1920x1080'),
                            ('-framerate', '25'), ('-input_format', 'yuyv422'),
                            ('-vf', 'hflip,format=yuv420p')]:
            self.assertEqual(args[args.index(flag) + 1], value)
        self.assertEqual(args[-1], str(output))

    def test_missing_camera_and_feedback_loop_are_rejected(self):
        camera = self.root / 'camera'
        camera.touch()
        self.assertEqual(self.run_backend('run', CAMERA_DEVICE=str(camera),
                                         CAMERA_OUTPUT=str(self.root / 'missing')).returncode, 1)
        alias = self.root / 'same camera'
        alias.symlink_to(camera)
        self.assertEqual(self.run_backend('run', CAMERA_DEVICE=str(camera),
                                         CAMERA_OUTPUT=str(alias)).returncode, 1)
        self.assertFalse((self.root / 'args').exists())

    def test_install_preserves_settings_and_running_camera(self):
        import shutil
        home = self.root / 'home with spaces'
        plugin = home / '.config/omarchy/plugins/aras.mirrored-camera'
        shutil.copytree(CONTROLLER.parents[1], plugin,
                        ignore=shutil.ignore_patterns('.git', '__pycache__'))
        config = home / '.config/mirrored-camera/camera.conf'
        config.parent.mkdir(parents=True)
        config.write_text('CAMERA_SIZE=1920x1080\n')
        self.state.write_text('active')
        for _ in range(2):
            result = subprocess.run(['bash', str(plugin / 'scripts/install.sh')],
                                    env=self.env | {'HOME': str(home)},
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(config.read_text(), 'CAMERA_SIZE=1920x1080\n')
            self.assertEqual(self.state.read_text(), 'active')
        self.assertTrue((home / '.config/systemd/user/mirrored-camera.service').is_file())
        self.assertTrue(os.access(home / '.local/bin/mirrored-camera', os.X_OK))

    def test_invalid_command(self):
        self.assertEqual(self.run_backend('invalid').returncode, 2)


if __name__ == '__main__':
    unittest.main()
