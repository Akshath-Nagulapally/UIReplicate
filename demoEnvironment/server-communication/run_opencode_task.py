from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable


DEFAULT_OPENCODE_URL = "http://127.0.0.1:4096"
DEFAULT_CLEANUP_PORTS = (4096, 5173, 5174, 3000, 3001, 8000, 8080)
DEFAULT_TIMEOUT_SECONDS = 450
APP_DIR = Path(__file__).resolve().parents[1] / "my-app"
DEFAULT_SCREENSHOT_PATH = Path("screenshots") / "opencode-task.png"
AI_GENERATED_SCREENSHOT_PATH = Path("screenshots") / "ai-generated-screenshot.png"
LOCAL_APP_URL = "http://localhost:5173"
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from screenshot import capture_screenshot


Runner = Callable[[list[str]], object]


def build_message_payload(task: str, *, screenshot_path: Path) -> dict[str, Any]:
    parts = [{"type": "text", "text": task}]
    parts.append({"type": "file", "mime": image_mime_type(screenshot_path), "url": image_data_url(screenshot_path)})
    return {"parts": parts}


def image_mime_type(image_path: Path) -> str:
    return mimetypes.guess_type(image_path.name)[0] or "image/png"


def image_data_url(image_path: Path) -> str:
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{image_mime_type(image_path)};base64,{encoded}"


def unique_ports(ports: Iterable[int]) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for port in ports:
        if port not in seen:
            seen.add(port)
            ordered.append(port)
    return ordered


def default_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def start_dev_server(directory: Path) -> subprocess.Popen[str]:
    return subprocess.Popen(
        ["bun", "run", "dev"],
        cwd=directory,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def wait_for_url(url: str, *, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception as error:
            last_error = error
            time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def stop_dev_server(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def kill_listeners_on_ports(ports: Iterable[int], *, runner: Runner = default_runner) -> list[int]:
    killed: list[int] = []
    if shutil.which("lsof"):
        for port in unique_ports(ports):
            pids = listener_pids_for_port(port, runner=runner)
            terminate_pids(pids)
            if pids:
                wait_for_port_to_close(port, timeout=2)
                remaining = listener_pids_for_port(port, runner=runner)
                terminate_pids(remaining, sig=signal.SIGKILL)
            killed.append(port)
        return killed

    fuser_command_builder = fuser_kill_command_builder()
    if fuser_command_builder is None:
        print("warning: neither fuser nor lsof is available; skipping port cleanup", file=sys.stderr)
        return killed

    for port in unique_ports(ports):
        runner(fuser_command_builder(port))
        killed.append(port)
    return killed


def listener_pids_for_port(port: int, *, runner: Runner = default_runner) -> list[int]:
    result = runner(["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"])
    stdout = getattr(result, "stdout", "") or ""
    pids: list[int] = []
    for line in stdout.splitlines():
        line = line.strip()
        if line:
            pids.append(int(line))
    return pids


def terminate_pids(pids: Iterable[int], *, sig: signal.Signals = signal.SIGTERM) -> None:
    for pid in pids:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass
        except PermissionError as error:
            print(f"warning: could not kill pid {pid}: {error}", file=sys.stderr)


def wait_for_port_to_close(port: int, *, timeout: float) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = default_runner(["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"])
        if not (result.stdout or "").strip():
            return
        time.sleep(0.1)


def fuser_kill_command_builder() -> Callable[[int], list[str]] | None:
    if shutil.which("fuser"):
        return lambda port: ["fuser", "-k", f"{port}/tcp"]
    return None


def request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    directory: Path = APP_DIR,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        headers=build_headers(directory),
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {error.code}: {error_body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"{method} {url} failed: {error.reason}") from error

    return json.loads(response_body) if response_body else {}


def build_headers(directory: Path) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "x-opencode-directory": str(directory),
    }
    username = os.environ.get("OPENCODE_SERVER_USERNAME", "opencode")
    password = os.environ.get("OPENCODE_SERVER_PASSWORD")
    if password:
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
    return headers


def run_task(
    task: str,
    *,
    screenshot_path: Path,
    base_url: str = DEFAULT_OPENCODE_URL,
    directory: Path = APP_DIR,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    session_id: str | None = None
    try:
        health = request_json("GET", f"{base_url}/global/health", directory=directory, timeout=30)
        if not health.get("healthy"):
            raise RuntimeError(f"OpenCode server is not healthy: {health}")

        session = request_json("POST", f"{base_url}/session", payload={}, directory=directory, timeout=30)
        session_id = session["id"]
        response = request_json(
            "POST",
            f"{base_url}/session/{session_id}/message",
            payload=build_message_payload(task, screenshot_path=screenshot_path),
            directory=directory,
            timeout=timeout,
        )
        error = response.get("info", {}).get("error")
        if error:
            raise RuntimeError(f"OpenCode task failed: {error}")
        return response
    finally:
        if session_id:
            safe_request("POST", f"{base_url}/session/{session_id}/abort", directory=directory, timeout=10)
        safe_request("POST", f"{base_url}/instance/dispose", directory=directory, timeout=10)
        kill_listeners_on_ports(DEFAULT_CLEANUP_PORTS)


def safe_request(method: str, url: str, *, directory: Path, timeout: int) -> None:
    try:
        request_json(method, url, directory=directory, timeout=timeout)
    except Exception as error:
        print(f"warning: cleanup request failed: {error}", file=sys.stderr)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send one task to OpenCode, then clean up local dev servers.")
    parser.add_argument("task", help="Task prompt to send to OpenCode")
    parser.add_argument("--url", required=True, help="URL to screenshot and attach to the OpenCode task")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    base_url = os.environ.get("OPENCODE_SERVER_URL", DEFAULT_OPENCODE_URL).rstrip("/")
    timeout = int(os.environ.get("OPENCODE_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    directory = Path(os.environ.get("OPENCODE_APP_DIR", str(APP_DIR))).expanduser().resolve()

    try:
        screenshot_path = capture_screenshot(args.url, DEFAULT_SCREENSHOT_PATH)

        # Temporarily disabled while testing the screenshot pipeline without model calls.
        # response = run_task(args.task, screenshot_path=screenshot_path, base_url=base_url, directory=directory, timeout=timeout)
        response = {"opencode_skipped": True, "task": args.task, "reference_screenshot": str(screenshot_path)}

        dev_server = start_dev_server(directory)
        try:
            wait_for_url(LOCAL_APP_URL)
            generated_screenshot_path = capture_screenshot(LOCAL_APP_URL, AI_GENERATED_SCREENSHOT_PATH)
        finally:
            stop_dev_server(dev_server)
        response["ai_generated_screenshot"] = str(generated_screenshot_path)
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
