#!/usr/bin/env python3
"""Append validated source and claim records to a Codex Science ledger."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys


STATUSES = ("observed", "derived", "hypothesis", "conflicted", "unsupported")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def ledger_path(root: pathlib.Path, name: str) -> pathlib.Path:
    path = root.expanduser().resolve() / ".science" / "evidence" / name
    if not path.is_file():
        raise FileNotFoundError(f"missing ledger: {path}")
    return path


def existing_ids(path: pathlib.Path) -> set[str]:
    ids: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: invalid JSON: {exc}") from exc
        if "id" in record:
            ids.add(str(record["id"]))
    return ids


def append(path: pathlib.Path, record: dict[str, object]) -> None:
    if str(record["id"]) in existing_ids(path):
        raise ValueError(f"duplicate id {record['id']} in {path}")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    source = sub.add_parser("add-source")
    source.add_argument("--id", required=True)
    source.add_argument("--title", required=True)
    source.add_argument("--location", required=True)
    source.add_argument("--authors", default="")
    source.add_argument("--year", type=int)
    source.add_argument("--doi", default="")
    source.add_argument("--version", default="")
    source.add_argument(
        "--type",
        choices=("paper", "preprint", "review", "dataset", "code", "protocol", "standard", "report", "web", "note", "unknown"),
        default="unknown",
    )
    source.add_argument("--evidence-level", choices=("high", "medium", "low", "unknown"), default="unknown")
    source.add_argument("--review-status", choices=("peer-reviewed", "preprint", "not-applicable", "unknown"), default="unknown")
    source.add_argument("--access-status", choices=("full", "abstract-only", "metadata-only", "unavailable", "unknown"), default="unknown")
    source.add_argument("--correction-status", choices=("none-found", "corrected", "retracted", "unknown"), default="unknown")
    source.add_argument("--license", default="unknown")
    source.add_argument("--sha256", default="")
    source.add_argument("--notes", default="")

    claim = sub.add_parser("add-claim")
    claim.add_argument("--id", required=True)
    claim.add_argument("--text", required=True)
    claim.add_argument("--status", choices=STATUSES, required=True)
    claim.add_argument("--sources", default="")
    claim.add_argument("--experiments", default="")
    claim.add_argument("--notes", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "add-source":
            path = ledger_path(args.root, "sources.jsonl")
            record: dict[str, object] = {
                "id": args.id,
                "title": args.title,
                "location": args.location,
                "retrieved_at": utc_now(),
                "type": args.type,
                "evidence_level": args.evidence_level,
                "review_status": args.review_status,
                "access_status": args.access_status,
                "correction_status": args.correction_status,
                "license": args.license,
            }
            for key in ("authors", "year", "doi", "version", "sha256", "notes"):
                value = getattr(args, key)
                if value not in (None, ""):
                    record[key] = value
        else:
            path = ledger_path(args.root, "claims.jsonl")
            sources = [item.strip() for item in args.sources.split(",") if item.strip()]
            experiments = [
                item.strip() for item in args.experiments.split(",") if item.strip()
            ]
            if not sources and not experiments and args.status not in ("hypothesis", "unsupported"):
                raise ValueError(
                    f"status {args.status} requires a source or experiment ID"
                )
            record = {
                "id": args.id,
                "text": args.text,
                "status": args.status,
                "sources": sources,
                "experiments": experiments,
                "created_at": utc_now(),
            }
            if args.notes:
                record["notes"] = args.notes
        append(path, record)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Appended {record['id']} to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
