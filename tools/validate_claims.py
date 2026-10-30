"""Validate claim-ledger evidence paths and structured result selectors."""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "paper" / "claims_ledger.csv"


def main() -> int:
    errors: list[str] = []
    with LEDGER.open(newline="", encoding="utf-8") as stream:
        claims = list(csv.DictReader(stream))
    if not claims:
        errors.append("ledger has no claims")
    seen: set[str] = set()
    for row in claims:
        claim_id = row.get("claim_id", "").strip()
        if not claim_id or claim_id in seen:
            errors.append(f"missing or duplicate claim id: {claim_id!r}")
        seen.add(claim_id)
        if not row.get("claim", "").strip() or not row.get("category", "").strip():
            errors.append(f"{claim_id}: claim and category are required")
        paths = [item.strip() for item in row.get("evidence_paths", "").split(";") if item.strip()]
        if not paths:
            errors.append(f"{claim_id}: at least one evidence path is required")
        resolved: list[Path] = []
        for relative in paths:
            candidate = (ROOT / relative).resolve()
            if ROOT.resolve() not in candidate.parents:
                errors.append(f"{claim_id}: evidence path escapes repository: {relative}")
            elif not candidate.is_file():
                errors.append(f"{claim_id}: evidence file missing: {relative}")
            else:
                resolved.append(candidate)
        selector = row.get("result_selector", "").strip()
        if selector:
            result_files = [path for path in resolved if path.suffix.lower() == ".csv"]
            if not result_files:
                errors.append(f"{claim_id}: selector supplied without a CSV evidence file")
            selectors = dict(
                part.split("=", 1) for part in selector.split(";") if "=" in part
            )
            if not selectors:
                errors.append(f"{claim_id}: malformed result selector")
            elif result_files and not any(_has_row(path, selectors) for path in result_files):
                errors.append(f"{claim_id}: no CSV row matches {selector}")
        citation = row.get("citation_key", "").strip()
        if citation:
            bib = ROOT / "paper" / "references.bib"
            if not bib.is_file() or not re.search(
                rf"@\w+\s*\{{\s*{re.escape(citation)}\s*,", bib.read_text(encoding="utf-8")
            ):
                errors.append(f"{claim_id}: bibliography key not found: {citation}")
        if not row.get("verification_status", "").strip() or not row.get("limitation", "").strip():
            errors.append(f"{claim_id}: verification status and limitation are required")
    if errors:
        print("Claim validation FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Claim validation passed: {len(claims)} claims, all evidence paths and references resolved.")
    return 0


def _has_row(path: Path, selectors: dict[str, str]) -> bool:
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if not set(selectors).issubset(reader.fieldnames or []):
                return False
            return any(all(row.get(key) == value for key, value in selectors.items()) for row in reader)
    except (OSError, csv.Error):
        return False


if __name__ == "__main__":
    sys.exit(main())
