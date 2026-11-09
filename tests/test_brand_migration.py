"""Rebranding must not strand saved conversations or pairing credentials."""

from apps.api.config import Config
from apps.runtime.vault import default_path


def test_database_name_preserves_existing_data(tmp_path, monkeypatch):
    monkeypatch.setattr("apps.api.config.ROOT", tmp_path)
    monkeypatch.delenv("MITRA_DATABASE", raising=False)
    old = tmp_path / ".data" / "jaris-slice1.db"
    old.parent.mkdir()
    old.touch()
    assert Config().database == old
    current = old.with_name("mitra-slice1.db")
    current.touch()
    assert Config().database == current
    monkeypatch.setenv("MITRA_DATABASE", str(tmp_path / "explicit.db"))
    assert Config().database == tmp_path / "explicit.db"


def test_existing_encrypted_pairing_remains_discoverable(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    old = tmp_path / "JARIS" / "runtime.dpapi"
    old.parent.mkdir()
    old.write_bytes(b"opaque-fixture")
    assert default_path() == old
    current = tmp_path / "MITRA" / "runtime.dpapi"
    current.parent.mkdir()
    current.write_bytes(b"opaque-current-fixture")
    assert default_path() == current
    assert old.read_bytes() == b"opaque-fixture"
