"""Print deterministic SHA-256 inventory for the model and confirmatory outputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATHS = [
    "ai_engine/models/isolation_forest.joblib",
    "docs/evaluation/PROTOCOL.md",
    "docs/evaluation/confirmatory_v1/metadata.json",
    "docs/evaluation/confirmatory_v1/raw_metrics.csv",
    "docs/evaluation/confirmatory_v1/results.csv",
    "docs/evaluation/confirmatory_v1/paired_tests.csv",
    "docs/evaluation/confirmatory_v1/unsupported_conditions.csv",
]


def main() -> int:
    records = []
    for relative in PATHS:
        path = ROOT / relative
        if not path.is_file():
            records.append({"path": relative, "status": "MISSING"})
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": digest})
    print(json.dumps({"manifest_scope": "selected model/protocol/confirmatory artifacts", "artifacts": records}, indent=2))
    return 1 if any(item.get("status") == "MISSING" for item in records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
