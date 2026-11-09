"""Run with python -m apps.runtime. Model startup is never performed here."""

import argparse
import getpass
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

from apps.api.contracts import DesktopResult
from apps.runtime.client import RuntimeClient
from apps.runtime.desktop import NativeDesktop
from apps.runtime.vault import SavedCredential, default_path, load, save, transform


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MITRA Windows runtime: pairing and heartbeat only"
    )
    parser.add_argument(
        "--credential-file",
        type=Path,
        help="Override the current-user DPAPI credential path",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    pair = commands.add_parser("pair", help="Pair using a code generated in Settings")
    pair.add_argument("--api", default="http://127.0.0.1:8000")
    pair.add_argument("--name", default="My Windows PC")
    pair.add_argument(
        "--replace",
        action="store_true",
        help="Replace a local credential after revoking its old pairing",
    )
    run = commands.add_parser("run", help="Send heartbeats; Ctrl+C stops this helper")
    run.add_argument(
        "--desktop",
        action="store_true",
        help="Opt in to approved window inspection, capture and focus",
    )
    run.add_argument(
        "--once",
        action="store_true",
        help="Verify one heartbeat, then disconnect and exit",
    )
    args = parser.parse_args()
    if os.name != "nt":
        print(
            "This helper requires Windows; no plaintext credential fallback is available.",
            file=sys.stderr,
        )
        return 1
    client = None
    credential = None
    try:
        path = args.credential_file or default_path()
        if args.command == "pair":
            if path.exists() and not args.replace:
                raise FileExistsError(
                    "Credential exists. Revoke it in Settings before using pair --replace."
                )
            transform(
                b"storage-check"
            )  # Check DPAPI before consuming the one-time code.
            path.parent.mkdir(parents=True, exist_ok=True)
            client = RuntimeClient(args.api)
            code = (
                getpass.getpass("Pairing code: ")
                if sys.stdin.isatty()
                else sys.stdin.readline().strip()
            )
            paired = client.pair(code, args.name)
            save(
                path,
                SavedCredential(api=client.api, credential=paired),
                replace=args.replace,
            )
            print(
                "Paired. Credential protected for this Windows user. Run the helper to connect."
            )
            return 0
        saved = load(path)
        credential = saved.credential
        client = RuntimeClient(saved.api)
        desktop = NativeDesktop() if args.desktop else None
        failures = 0
        announced = False
        while True:
            try:
                status = client.heartbeat(credential, desktop=bool(desktop))
                if not status.connected or status.runtimeId != credential.runtimeId:
                    raise ConnectionError(
                        "API did not confirm this runtime's heartbeat"
                    )
                if not announced or failures or args.once:
                    print(
                        "Runtime heartbeat verified. Desktop capabilities follow explicit --desktop opt-in."
                    )
                announced = True
                failures = 0
                if args.once:
                    return 0
                if desktop:
                    job = client.desktop_request(credential, "poll")
                    if job:
                        confirmed = client.desktop_request(
                            credential, job.id + "/authorize"
                        )
                        if confirmed and confirmed.model_dump() == job.model_dump():
                            try:
                                outcome = desktop.execute(job)
                            except (OSError, ValueError, subprocess.TimeoutExpired):
                                outcome = DesktopResult(
                                    success=False,
                                    message="Operation refused, timed out or target changed; inspect again",
                                )
                            client.desktop_request(
                                credential, job.id + "/result", outcome
                            )
            except (httpx.HTTPError, ConnectionError):
                if args.once:
                    raise
                if failures == 0:
                    print(
                        "Local API unavailable; retrying with bounded backoff.",
                        file=sys.stderr,
                    )
                failures += 1
            time.sleep(min(30, 5 * max(1, failures)))
    except KeyboardInterrupt:
        print("Runtime stopped.")
        return 0
    except (OSError, ValueError, httpx.HTTPError):
        # Do not echo validation bodies, credentials, pairing codes or request headers.
        print(
            "Runtime could not connect or store credentials. Check Settings, the API and your credential file; re-pair if revoked or expired.",
            file=sys.stderr,
        )
        return 1
    finally:
        if client:
            if credential:
                try:
                    client.disconnect(credential)
                except (OSError, httpx.HTTPError):
                    pass
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
