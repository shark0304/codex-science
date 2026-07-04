#!/usr/bin/env python3
"""Append search records and immutable paper cards to a Codex Science project."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_jsonl(path: pathlib.Path) -> list[dict[str, object]]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: record must be an object")
        records.append(value)
    return records


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--root", type=pathlib.Path, required=True)
    sub = root.add_subparsers(dest="command_name", required=True)

    search = sub.add_parser("search")
    search.add_argument("--id", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--database", required=True)
    search.add_argument("--filters", default="")
    search.add_argument("--reason", required=True)
    search.add_argument("--selected", default="")
    search.add_argument("--rejected", default="")
    search.add_argument("--next-search", default="")

    card = sub.add_parser("paper-card")
    card.add_argument("--id", required=True)
    card.add_argument("--source", required=True)
    card.add_argument("--question", required=True)
    card.add_argument("--design", default="")
    card.add_argument("--population", default="")
    card.add_argument("--method", required=True)
    card.add_argument("--sample-size", default="")
    card.add_argument("--outcomes", default="")
    card.add_argument("--effect", default="")
    card.add_argument("--uncertainty", default="")
    card.add_argument("--limitations", default="")
    card.add_argument("--data-code", default="")
    card.add_argument("--claim-location", action="append", default=[])
    card.add_argument("--notes", default="")
    return root


def main() -> int:
    args = parser().parse_args()
    science = args.root.expanduser().resolve() / ".science"
    try:
        if args.command_name == "search":
            path = science / "evidence/searches.jsonl"
            if not path.is_file():
                raise FileNotFoundError(f"missing search ledger: {path}")
            ids = {record.get("id") for record in read_jsonl(path)}
            if args.id in ids:
                raise ValueError(f"duplicate search id: {args.id}")
            record = {
                "id": args.id,
                "created_at": utc_now(),
                "query": args.query,
                "database": args.database,
                "filters": args.filters,
                "reason": args.reason,
                "selected_sources": split_csv(args.selected),
                "rejected_sources": split_csv(args.rejected),
                "next_search": args.next_search,
            }
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            print(f"Appended search record {args.id}")
        else:
            source_path = science / "evidence/sources.jsonl"
            cards = science / "evidence/paper-cards"
            if not source_path.is_file() or not cards.is_dir():
                raise FileNotFoundError("missing source ledger or paper-card directory")
            source_ids = {record.get("id") for record in read_jsonl(source_path)}
            if args.source not in source_ids:
                raise ValueError(f"unknown source id: {args.source}")
            path = cards / f"{args.id}.json"
            if path.exists():
                raise ValueError(f"paper card already exists: {path}")
            record = {
                "schema": "codex-science.paper-card.v1",
                "id": args.id,
                "source_id": args.source,
                "created_at": utc_now(),
                "question": args.question,
                "design": args.design,
                "population_or_system": args.population,
                "method": args.method,
                "sample_size": args.sample_size,
                "outcomes": args.outcomes,
                "effect": args.effect,
                "uncertainty": args.uncertainty,
                "limitations": args.limitations,
                "data_and_code": args.data_code,
                "claim_locations": args.claim_location,
                "notes": args.notes,
            }
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Created paper card {args.id} for {args.source}")
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
