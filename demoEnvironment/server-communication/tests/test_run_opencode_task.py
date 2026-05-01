from __future__ import annotations

import importlib.util
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "run_opencode_task.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_opencode_task", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunOpencodeTaskTests(unittest.TestCase):
    def test_default_timeout_is_seven_and_a_half_minutes(self):
        module = load_module()

        self.assertEqual(module.DEFAULT_TIMEOUT_SECONDS, 450)

    def test_build_message_payload_includes_png_screenshot_part(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            screenshot_path = Path(tmp) / "screenshot.png"
            screenshot_path.write_bytes(b"png-bytes")

            payload = module.build_message_payload("build the app", screenshot_path=screenshot_path)

        self.assertEqual(payload["parts"][0], {"type": "text", "text": "build the app"})
        self.assertEqual(payload["parts"][1], {"type": "file", "mime": "image/png", "url": "data:image/png;base64,cG5nLWJ5dGVz"})

    def test_build_message_payload_requires_screenshot_path(self):
        module = load_module()

        with self.assertRaises(TypeError):
            module.build_message_payload("build the app")

    def test_cleanup_ports_deduplicates_requested_ports(self):
        module = load_module()
        calls: list[list[str]] = []
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        def runner(command: list[str]):
            calls.append(command)
            return completed

        with patch.object(module.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}" if name == "lsof" else None):
            killed = module.kill_listeners_on_ports([5173, 5173, 8080], runner=runner)

        self.assertEqual(killed, [5173, 8080])
        self.assertEqual(calls, [["lsof", "-tiTCP:5173", "-sTCP:LISTEN"], ["lsof", "-tiTCP:8080", "-sTCP:LISTEN"]])

    def test_cleanup_uses_lsof_when_macos_fuser_does_not_support_kill(self):
        module = load_module()
        calls: list[list[str]] = []

        def runner(command: list[str]):
            calls.append(command)
            if command == ["fuser", "-k", "5173/tcp"]:
                return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="Unknown option: k")
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

        with patch.object(module.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}" if name in {"fuser", "lsof"} else None):
            killed = module.kill_listeners_on_ports([5173], runner=runner)

        self.assertEqual(killed, [5173])
        self.assertEqual(calls, [["lsof", "-tiTCP:5173", "-sTCP:LISTEN"]])

    def test_main_requires_url(self):
        module = load_module()
        stderr = io.StringIO()

        with patch.object(module.sys, "stderr", stderr):
            with self.assertRaises(SystemExit) as error:
                module.main(["build the app"])

        self.assertEqual(error.exception.code, 2)
        self.assertIn("--url", stderr.getvalue())

    def test_main_skips_opencode_and_captures_generated_screenshot(self):
        module = load_module()
        stdout = io.StringIO()
        reference_screenshot_path = Path("screenshots") / "opencode-task.png"
        generated_screenshot_path = Path("screenshots") / "ai-generated-screenshot.png"
        dev_server = Mock()

        with patch.object(module, "capture_screenshot", side_effect=[reference_screenshot_path, generated_screenshot_path]) as capture_screenshot:
            with patch.object(module, "run_task", return_value={"ok": True}) as run_task:
                with patch.object(module, "start_dev_server", return_value=dev_server) as start_dev_server:
                    with patch.object(module, "wait_for_url") as wait_for_url:
                        with patch.object(module.sys, "stdout", stdout):
                            exit_code = module.main(["build the app", "--url", "localhost:5173"])

        self.assertEqual(exit_code, 0)
        run_task.assert_not_called()
        start_dev_server.assert_called_once_with(module.APP_DIR)
        wait_for_url.assert_called_once_with("http://localhost:5173")
        self.assertEqual(
            capture_screenshot.call_args_list,
            [
                unittest.mock.call("localhost:5173", reference_screenshot_path),
                unittest.mock.call("http://localhost:5173", module.AI_GENERATED_SCREENSHOT_PATH),
            ],
        )
        dev_server.terminate.assert_called_once()
        dev_server.wait.assert_called_once_with(timeout=5)
        self.assertIn('"opencode_skipped": true', stdout.getvalue())
        self.assertIn(str(generated_screenshot_path), stdout.getvalue())

    def test_main_captures_url_screenshot_before_sending_task(self):
        module = load_module()
        stdout = io.StringIO()
        screenshot_path = Path("screenshots") / "opencode-task.png"
        dev_server = Mock()

        with patch.object(module, "capture_screenshot", side_effect=[screenshot_path, module.AI_GENERATED_SCREENSHOT_PATH]) as capture_screenshot:
            with patch.object(module, "run_task", return_value={"ok": True}) as run_task:
                with patch.object(module, "start_dev_server", return_value=dev_server):
                    with patch.object(module, "wait_for_url"):
                        with patch.object(module.sys, "stdout", stdout):
                            exit_code = module.main(["build the app", "--url", "localhost:5173"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(capture_screenshot.call_args_list[0], unittest.mock.call("localhost:5173", screenshot_path))
        run_task.assert_not_called()
        self.assertIn('"reference_screenshot"', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
