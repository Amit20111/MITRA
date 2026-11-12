"""Real HTTP + separately launched Windows helper; synthetic credentials only."""

import os
import socket
import subprocess
import sys
import threading
import time

import httpx
import pytest
import uvicorn

from apps.api.main import create_app
from apps.runtime.vault import load
from tests.client import login
from tests.fakes import FakeProvider


@pytest.mark.skipif(os.name != "nt", reason="Windows helper uses current-user DPAPI")
def test_native_helper_pair_heartbeat_and_revocation(tmp_path):
    app = create_app(
        tmp_path / "process.sqlite", FakeProvider([]), tmp_path / "workspace"
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(
        target=lambda: server.run(sockets=[listener]), daemon=True
    )
    thread.start()
    helper = None
    try:
        with httpx.Client(base_url=origin, trust_env=False, timeout=2) as client:
            for _ in range(100):
                try:
                    # The API is up once its boundary answers; health needs a session.
                    if client.get("/api/v1/health").status_code == 401:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.05)
            else:
                pytest.fail("Fixture API did not start")
            login(client, app)
            assert client.get("/api/v1/health").status_code == 200
            code = client.post("/api/v1/runtime/pairing").json()["pairingCode"]
            credential_file = tmp_path / "helper.dpapi"
            command = [
                sys.executable,
                "-m",
                "apps.runtime",
                "--credential-file",
                str(credential_file),
            ]
            paired = subprocess.run(
                command + ["pair", "--api", origin, "--name", "Process test helper"],
                input=code + "\n",
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )
            assert paired.returncode == 0, paired.stderr
            assert code not in paired.stdout + paired.stderr
            credential = load(credential_file).credential
            assert credential.token.encode() not in credential_file.read_bytes()
            once = subprocess.run(
                command + ["run", "--once"],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            assert once.returncode == 0, once.stderr
            state = client.get("/api/v1/runtime/status").json()
            assert state["paired"] and not state["connected"] and state["lastSeen"]
            helper = subprocess.Popen(
                command + ["run"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(100):
                state = client.get("/api/v1/runtime/status").json()
                if state["connected"]:
                    break
                time.sleep(0.05)
            assert state["connected"] and state["capabilities"] == ["heartbeat"]
            response = client.post(
                "/api/v1/runtime/revoke", json={"runtimeId": credential.runtimeId}
            )
            assert response.status_code == 200 and not response.json()["paired"]
            stdout, stderr = helper.communicate(timeout=12)
            assert (
                helper.returncode == 1
            )  # Revocation is a hard stop, not a retry loop.
            assert credential.token not in stdout + stderr
    finally:
        if helper and helper.poll() is None:
            helper.terminate()
            helper.communicate(timeout=5)
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
        assert not thread.is_alive()
