import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from apps.api.config import ROOT, Config
from memory.store import Store
from security.redaction import Redactor


def main() -> None:
    parser = argparse.ArgumentParser(description="Export redacted task traces as JSONL")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    config = Config()
    store = Store(
        config.database, Redactor([k.get_secret_value() for k in config.keys.values()])
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        for row in store.trace_rows():
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    store.close()
    print(f"Exported redacted traces to {args.output}")


if __name__ == "__main__":
    main()
