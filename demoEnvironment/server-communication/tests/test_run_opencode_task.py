from __future__ import annotations

import importlib.util
import io
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_build_message_payload_uses_single_text_part(self):
        module = load_module()

        payload = module.build_message_payload("build the app")

        self.assertEqual(payload, {"parts": [{"type": "text", "text": "build the app"}]})

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

    def test_main_sends_task_to_opencode(self):
        module = load_module()
        stdout = io.StringIO()

        with patch.object(module, "run_task", return_value={"ok": True}) as run_task:
            with patch.object(module.sys, "stdout", stdout):
                exit_code = module.main(["build the app"])

        self.assertEqual(exit_code, 0)
        run_task.assert_called_once()
        self.assertEqual(run_task.call_args.args, ("build the app",))
        self.assertIn('"ok": true', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
