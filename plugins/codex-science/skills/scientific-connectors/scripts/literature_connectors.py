#!/usr/bin/env python3
"""Query scientific metadata APIs and import reviewed records into a study."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


VERSION = "0.4.0"
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
USER_AGENT = "codex-science/0.4 (+https://github.com/shark0304/codex-science)"
PRODUCTION_URLS = {
    "crossref": "https://api.crossref.org/works",
    "pubmed": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
    "openalex": "https://api.openalex.org/works",
}
PRODUCTION_HOSTS = {
    "crossref": "api.crossref.org",
    "pubmed": "eutils.ncbi.nlm.nih.gov",
    "openalex": "api.openalex.org",
}
SECRET_QUERY_KEYS = {"api_key", "mailto", "email", "token", "access_token"}


class ConnectorError(ValueError):
    """A connector input, provider, or snapshot error."""


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep credential-bearing requests on the reviewed endpoint."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: pathlib.Path, value: dict[str, object]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ConnectorError(f"output exists; refusing to overwrite: {path}")
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        temporary = pathlib.Path(stream.name)
    temporary.replace(path)


def endpoint(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (local and parsed.scheme == "http"):
        raise ConnectorError("production connector endpoints must use HTTPS")
    return value.rstrip("/")


def is_production_endpoint(provider: str, value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return (
        parsed.scheme == "https"
        and parsed.hostname == PRODUCTION_HOSTS[provider]
        and parsed.port in (None, 443)
    )


def build_url(base: str, parameters: dict[str, object]) -> str:
    values = {key: value for key, value in parameters.items() if value not in (None, "")}
    return base + ("&" if "?" in base else "?") + urllib.parse.urlencode(values)


def sanitized_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    query = [
        (key, "REDACTED" if key.lower() in SECRET_QUERY_KEYS else item)
        for key, item in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))


def redact(value: object, secrets: list[str]) -> object:
    if isinstance(value, dict):
        return {
            str(key): (
                "REDACTED"
                if str(key).lower() in SECRET_QUERY_KEYS
                else redact(item, secrets)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, str):
        result = value
        for secret in secrets:
            if secret:
                result = result.replace(secret, "REDACTED")
        return result
    return value


def fetch_json(url: str, timeout: float, retries: int = 2) -> tuple[dict[str, Any], dict[str, object]]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )
    opener = urllib.request.build_opener(NoRedirectHandler())
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with opener.open(request, timeout=timeout) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                if len(payload) > MAX_RESPONSE_BYTES:
                    raise ConnectorError("provider response exceeded 10 MiB")
                final_url = response.geturl()
                status = getattr(response, "status", 200)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504) or attempt >= retries:
                break
            delay = min(float(exc.headers.get("Retry-After", 0) or 0), 5.0)
            time.sleep(delay or 0.5 * (attempt + 1))
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(0.5 * (attempt + 1))
            continue
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ConnectorError(f"provider returned invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ConnectorError("provider response root must be an object")
        secrets = [
            item
            for key, item in urllib.parse.parse_qsl(
                urllib.parse.urlparse(url).query, keep_blank_values=True
            )
            if key.lower() in SECRET_QUERY_KEYS and item
        ]
        value = redact(value, secrets)
        if not isinstance(value, dict):
            raise ConnectorError("sanitized provider response root must be an object")
        metadata = {
            "url": sanitized_url(final_url),
            "status": int(status),
            "sha256": digest_bytes(payload),
            "bytes": len(payload),
        }
        return value, metadata
    raise ConnectorError(f"provider request failed after bounded retries: {last_error}")


def first_text(value: object) -> str:
    if isinstance(value, list) and value:
        return str(value[0] or "").strip()
    return str(value or "").strip()


def date_year(value: object) -> int | None:
    if isinstance(value, dict):
        parts = value.get("date-parts")
        if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                return None
    match = re.search(r"\b(18|19|20|21)\d{2}\b", str(value or ""))
    return int(match.group(0)) if match else None


def crossref(args: argparse.Namespace) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, Any]]]:
    base = endpoint(args.base_url)
    parameters: dict[str, object] = {
        "query.bibliographic": args.query,
        "rows": min(args.limit * 5, 50),
        "select": "DOI,title,author,published,type,URL,container-title",
        "mailto": (
            os.environ.get("CROSSREF_MAILTO", "")
            if is_production_endpoint("crossref", base)
            else ""
        ),
    }
    url = build_url(base, parameters)
    response, request_meta = fetch_json(url, args.timeout)
    message = response.get("message")
    items = message.get("items", []) if isinstance(message, dict) else []
    if not isinstance(items, list):
        raise ConnectorError("Crossref response has no message.items list")
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = first_text(item.get("title"))
        if not title:
            continue
        authors = []
        for author in item.get("author", []):
            if isinstance(author, dict):
                name = " ".join(
                    part for part in (str(author.get("given", "")).strip(), str(author.get("family", "")).strip()) if part
                )
                if name:
                    authors.append(name)
        normalized.append(
            {
                "provider_id": str(item.get("DOI") or item.get("URL") or ""),
                "title": title,
                "authors": authors,
                "year": date_year(item.get("published")),
                "doi": str(item.get("DOI") or "").lower(),
                "url": str(item.get("URL") or ""),
                "type": str(item.get("type") or "unknown"),
                "venue": first_text(item.get("container-title")),
            }
        )
        if len(normalized) >= args.limit:
            break
    return normalized, [request_meta], [response]


def pubmed(args: argparse.Namespace) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, Any]]]:
    base = endpoint(args.base_url)
    production = is_production_endpoint("pubmed", base)
    common: dict[str, object] = {
        "db": "pubmed",
        "retmode": "json",
        "tool": "codex-science",
        "email": os.environ.get("NCBI_EMAIL", "") if production else "",
        "api_key": os.environ.get("NCBI_API_KEY", "") if production else "",
    }
    search_url = build_url(
        base + "/esearch.fcgi",
        {**common, "term": args.query, "retmax": args.limit},
    )
    search, search_meta = fetch_json(search_url, args.timeout)
    result = search.get("esearchresult")
    identifiers = result.get("idlist", []) if isinstance(result, dict) else []
    if not isinstance(identifiers, list):
        raise ConnectorError("PubMed ESearch response has no idlist")
    identifiers = [str(value) for value in identifiers[: args.limit]]
    if not identifiers:
        return [], [search_meta], [search]
    summary_url = build_url(
        base + "/esummary.fcgi",
        {**common, "id": ",".join(identifiers)},
    )
    summary, summary_meta = fetch_json(summary_url, args.timeout)
    values = summary.get("result")
    if not isinstance(values, dict):
        raise ConnectorError("PubMed ESummary response has no result object")
    normalized = []
    for pmid in identifiers:
        item = values.get(pmid)
        if not isinstance(item, dict):
            continue
        authors = [
            str(author.get("name"))
            for author in item.get("authors", [])
            if isinstance(author, dict) and author.get("name")
        ]
        doi = ""
        for article_id in item.get("articleids", []):
            if isinstance(article_id, dict) and article_id.get("idtype") == "doi":
                doi = str(article_id.get("value") or "").lower()
                break
        normalized.append(
            {
                "provider_id": pmid,
                "title": str(item.get("title") or "").strip(),
                "authors": authors,
                "year": date_year(item.get("pubdate") or item.get("sortpubdate")),
                "doi": doi,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "type": first_text(item.get("pubtype")) or "journal-article",
                "venue": str(item.get("fulljournalname") or item.get("source") or ""),
            }
        )
    return normalized, [search_meta, summary_meta], [search, summary]


def openalex(args: argparse.Namespace) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, Any]]]:
    base = endpoint(args.base_url)
    api_key = os.environ.get("OPENALEX_API_KEY", "")
    production = is_production_endpoint("openalex", base)
    if production and not api_key:
        raise ConnectorError("OPENALEX_API_KEY is required for production OpenAlex access")
    url = build_url(
        base,
        {
            "search": args.query,
            "per_page": args.limit,
            "select": "id,doi,title,publication_year,authorships,type,primary_location",
            "api_key": api_key if production else "",
        },
    )
    response, request_meta = fetch_json(url, args.timeout)
    items = response.get("results")
    if not isinstance(items, list):
        raise ConnectorError("OpenAlex response has no results list")
    normalized = []
    for item in items[: args.limit]:
        if not isinstance(item, dict):
            continue
        authors = []
        for authorship in item.get("authorships", []):
            author = authorship.get("author") if isinstance(authorship, dict) else None
            if isinstance(author, dict) and author.get("display_name"):
                authors.append(str(author["display_name"]))
        location = item.get("primary_location")
        source = location.get("source") if isinstance(location, dict) else None
        doi = str(item.get("doi") or "")
        doi = re.sub(r"^https?://doi\.org/", "", doi, flags=re.IGNORECASE).lower()
        normalized.append(
            {
                "provider_id": str(item.get("id") or ""),
                "title": str(item.get("title") or "").strip(),
                "authors": authors,
                "year": item.get("publication_year"),
                "doi": doi,
                "url": str(item.get("id") or ""),
                "type": str(item.get("type") or "unknown"),
                "venue": str(source.get("display_name") or "") if isinstance(source, dict) else "",
            }
        )
    return normalized, [request_meta], [response]


def search(args: argparse.Namespace) -> None:
    if not args.query.strip():
        raise ConnectorError("query must not be empty")
    if not 1 <= args.limit <= 50:
        raise ConnectorError("limit must be between 1 and 50")
    if not 1 <= args.timeout <= 60:
        raise ConnectorError("timeout must be between 1 and 60 seconds")
    normalized, requests, responses = globals()[args.connector](args)
    snapshot = {
        "schema": "codex-science.connector-snapshot.v1",
        "connector": args.connector,
        "connector_version": VERSION,
        "query": args.query,
        "limit": args.limit,
        "retrieved_at": utc_now(),
        "requests": requests,
        "provider_responses": responses,
        "results": normalized,
        "interpretation_boundary": "Discovery metadata only; records require source screening before supporting claims.",
    }
    atomic_json(args.output, snapshot)
    print(f"Saved {len(normalized)} {args.connector} records to {args.output.expanduser().resolve()}")


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConnectorError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConnectorError(f"JSON root must be an object: {path}")
    return value


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ConnectorError(f"{path}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ConnectorError(f"{path}:{number}: record must be an object")
        records.append(value)
    return records


def import_snapshot(args: argparse.Namespace) -> None:
    root = args.root.expanduser().resolve()
    snapshot_path = args.file.expanduser().resolve()
    snapshot = read_json(snapshot_path)
    if snapshot.get("schema") != "codex-science.connector-snapshot.v1":
        raise ConnectorError("unsupported connector snapshot schema")
    results = snapshot.get("results")
    if not isinstance(results, list):
        raise ConnectorError("snapshot results must be a list")
    selected = args.select or list(range(1, len(results) + 1))
    if len(set(selected)) != len(selected):
        raise ConnectorError("selected result indices must be unique")
    if any(index < 1 or index > len(results) for index in selected):
        raise ConnectorError("selected result index is out of range")
    prefix = re.sub(r"[^A-Za-z0-9-]+", "", args.prefix).upper()
    if not prefix:
        raise ConnectorError("prefix must contain letters or numbers")
    science = root / ".science/evidence"
    source_path = science / "sources.jsonl"
    search_path = science / "searches.jsonl"
    if not source_path.is_file() or not search_path.is_file():
        raise ConnectorError("initialize a Codex Science project before importing")
    sources = read_jsonl(source_path)
    searches = read_jsonl(search_path)
    if any(item.get("id") == args.search_id for item in searches):
        raise ConnectorError(f"duplicate search id: {args.search_id}")
    existing_ids = {str(item.get("id")) for item in sources}
    existing_dois = {str(item.get("doi", "")).lower() for item in sources if item.get("doi")}
    existing_locations = {str(item.get("location")) for item in sources if item.get("location")}
    records: list[dict[str, object]] = []
    skipped: list[str] = []
    next_number = 1
    for index in selected:
        item = results[index - 1]
        if not isinstance(item, dict):
            raise ConnectorError(f"result {index} must be an object")
        title = str(item.get("title") or "").strip()
        doi = str(item.get("doi") or "").lower()
        location = str(item.get("url") or (f"https://doi.org/{doi}" if doi else ""))
        if not title or not location:
            skipped.append(f"result-{index}:missing-title-or-location")
            continue
        if (doi and doi in existing_dois) or location in existing_locations:
            skipped.append(f"result-{index}:duplicate")
            continue
        while f"{prefix}{next_number:03d}" in existing_ids:
            next_number += 1
        identifier = f"{prefix}{next_number:03d}"
        next_number += 1
        record: dict[str, object] = {
            "id": identifier,
            "title": title,
            "location": location,
            "retrieved_at": snapshot.get("retrieved_at") or utc_now(),
            "type": "paper",
            "evidence_level": "unknown",
            "review_status": "unknown",
            "access_status": "metadata-only",
            "correction_status": "unknown",
            "license": "provider-metadata",
            "notes": (
                f"Imported from {snapshot.get('connector')} snapshot {snapshot_path}; "
                f"snapshot_sha256={digest_file(snapshot_path)}; provider_id={item.get('provider_id', '')}."
            ),
        }
        if item.get("authors"):
            record["authors"] = "; ".join(str(author) for author in item["authors"])
        if isinstance(item.get("year"), int):
            record["year"] = item["year"]
        if doi:
            record["doi"] = doi
        records.append(record)
        existing_ids.add(identifier)
        if doi:
            existing_dois.add(doi)
        existing_locations.add(location)
    with source_path.open("a", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    search_record = {
        "id": args.search_id,
        "created_at": utc_now(),
        "query": snapshot.get("query"),
        "database": snapshot.get("connector"),
        "filters": f"limit={snapshot.get('limit')}; selected_indices={selected}",
        "reason": args.reason,
        "selected_sources": [record["id"] for record in records],
        "rejected_sources": skipped,
        "next_search": args.next_search,
        "snapshot": {
            "path": str(snapshot_path),
            "sha256": digest_file(snapshot_path),
            "bytes": snapshot_path.stat().st_size,
        },
    }
    with search_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(search_record, ensure_ascii=False, sort_keys=True) + "\n")
    print(
        f"Imported {len(records)} sources and search {args.search_id}; "
        f"skipped={len(skipped)}"
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="connector", required=True)
    for name in ("crossref", "pubmed", "openalex"):
        command = sub.add_parser(name)
        command.add_argument("--query", required=True)
        command.add_argument("--limit", type=int, default=10)
        command.add_argument("--output", type=pathlib.Path, required=True)
        command.add_argument("--timeout", type=float, default=20.0)
        command.add_argument("--base-url", default=PRODUCTION_URLS[name])
        command.set_defaults(func=search)
    importing = sub.add_parser("import")
    importing.add_argument("--root", type=pathlib.Path, required=True)
    importing.add_argument("--file", type=pathlib.Path, required=True)
    importing.add_argument("--prefix", required=True)
    importing.add_argument("--search-id", required=True)
    importing.add_argument("--reason", required=True)
    importing.add_argument("--select", type=int, action="append", default=[])
    importing.add_argument("--next-search", default="")
    importing.set_defaults(func=import_snapshot)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
    except (ConnectorError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
