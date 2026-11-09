import re
from typing import Any

PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)((?:api[_-]?key|password|secret|token)\s*[=:]\s*[\"']?)[^\s\"',;}]+"
    ),
    re.compile(r"(?i)(sk-)[a-zA-Z0-9_-]{8,}"),
]
SENSITIVE = re.compile(
    r"(?i)(authorization|api.?key|password|secret|(?:^|[_-])token$|access.?token|refresh.?token)"
)


class Redactor:
    def __init__(self, secrets: list[str] | None = None):
        self.secrets = [s for s in (secrets or []) if s]

    def clean(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(k): "[REDACTED]" if SENSITIVE.search(str(k)) else self.clean(v)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self.clean(v) for v in value]
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[REDACTED]")
            for pattern in PATTERNS:
                value = pattern.sub(lambda m: m.group(1) + "[REDACTED]", value)
            return value
        return value
