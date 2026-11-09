import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from apps.api.contracts import RuntimeCredential
from apps.runtime.client import RuntimeClient, api_url
from apps.runtime.vault import SavedCredential, load, save


@pytest.mark.parametrize(
    "url",
    [
        "http://evil.example",
        "file:///tmp",
        "http://127.0.0.1@evil.example",
        "http://127.0.0.1/path",
        "http://127.0.0.1?token=secret",
        "http://127.0.0.1#x",
        "http://127.0.0.1:0",
        "http://user:secret@localhost",
    ],
)
def test_helper_refuses_nonlocal_or_ambiguous_api(url):
    with pytest.raises(ValueError):
        api_url(url)


def test_helper_does_not_follow_redirects_or_accept_revoked_tokens():
    seen = []

    def redirect(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"Location": "http://example.com/leak"})

    client = RuntimeClient(
        "http://127.0.0.1:8000", transport=httpx.MockTransport(redirect)
    )
    credential = RuntimeCredential(
        runtimeId=str(uuid4()),
        token="sensitive-test-token",
        expiresAt="2099-01-01T00:00:00Z",
    )
    try:
        with pytest.raises(ConnectionError):
            client.heartbeat(credential)
    finally:
        client.close()
    assert len(seen) == 1 and seen[0].startswith("http://127.0.0.1:8000/")
    client = RuntimeClient(
        "http://127.0.0.1:8000",
        transport=httpx.MockTransport(lambda _: httpx.Response(401)),
    )
    try:
        with pytest.raises(PermissionError):
            client.heartbeat(credential)
    finally:
        client.close()


@pytest.mark.skipif(os.name != "nt", reason="Current-user DPAPI requires Windows")
def test_windows_credential_encryption_roundtrip_and_tampering(tmp_path):
    credential = RuntimeCredential(
        runtimeId=str(uuid4()),
        token="unique-token-for-dpapi-test",
        expiresAt=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
    )
    value = SavedCredential(api="http://127.0.0.1:8000", credential=credential)
    path = tmp_path / "runtime.dpapi"
    save(path, value)
    assert credential.token.encode() not in path.read_bytes()
    assert b"127.0.0.1" not in path.read_bytes()
    assert load(path) == value
    with pytest.raises(FileExistsError):
        save(path, value)
    path.write_bytes(b"not-a-dpapi-file")
    with pytest.raises(OSError):
        load(path)
