import os
import tempfile

# Never read or create the real per-user key while testing.
_secrets = tempfile.TemporaryDirectory(prefix="mitra-test-secrets-")
os.environ["MITRA_SECRET_DIR"] = _secrets.name
