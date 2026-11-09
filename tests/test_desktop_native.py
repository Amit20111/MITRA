"""Exercise only a synthetic test-owned window, never capture user applications."""

import base64
import os
import subprocess
import sys
import time

import pytest

from apps.runtime.desktop import NativeDesktop
from tests.test_desktop import native_job


@pytest.mark.skipif(os.name != "nt", reason="Native Windows APIs")
def test_native_window_observation_capture_focus_and_stale_target(tmp_path):
    ready = tmp_path / "ready"
    fixture = tmp_path / "window.py"
    fixture.write_text(
        "import tkinter as t\nimport os\nfrom pathlib import Path\nr=t.Tk()\nr.title('MITRA synthetic desktop fixture')\nr.geometry('320x180')\nt.Label(r,text='Synthetic content only',bg='#00aaff').pack(fill='both',expand=True)\nr.update()\nPath("
        + repr(str(ready))
        + ").write_text(str(os.getpid()))\nr.mainloop()\n",
        encoding="utf-8",
    )
    process = subprocess.Popen(
        [sys.executable, str(fixture)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        for _ in range(100):
            if ready.exists():
                break
            if process.poll() is not None:
                pytest.fail(
                    "Synthetic window failed to start: "
                    + process.communicate()[1].decode()
                )
            time.sleep(0.05)
        assert ready.exists()
        desktop = NativeDesktop()
        targets = desktop.inspect()
        target = next(
            t
            for t in targets
            if t.title == "MITRA synthetic desktop fixture"
            and t.processId == int(ready.read_text())
        )
        image = desktop.execute(native_job("screenshot", target.id, target.title))
        raw = base64.b64decode(image.image)
        assert image.success and raw[:2] == b"BM" and len(raw) > 10000
        focus = desktop.execute(native_job("focus", target.id, target.title))
        assert focus.success or focus.message == "Windows refused foreground activation"
        process.terminate()
        process.communicate(timeout=5)
        with pytest.raises(ValueError):
            desktop.execute(native_job("focus", target.id, target.title))
    finally:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=5)
