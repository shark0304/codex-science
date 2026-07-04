#!/usr/bin/env python3
"""Build a self-contained, read-only HTML research workspace portal."""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import sys
from typing import Any

from parity_report import ParityError, build_report
from science import ScienceError, atomic_text, compute_status, load_catalog, read_json, read_jsonl, science_root


def esc(value: object) -> str:
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return html.escape(str(value if value is not None else ""), quote=True)


def table(headers: list[str], rows: list[list[object]], empty: str) -> str:
    if not rows:
        return f'<p class="empty">{esc(empty)}</p>'
    head = "".join(f"<th scope=\"col\">{esc(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{esc(item)}</td>" for item in row) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def metric(label: str, value: object, note: str) -> str:
    return (
        '<article class="metric">'
        f'<p class="eyebrow">{esc(label)}</p><p class="metric-value">{esc(value)}</p>'
        f'<p class="muted">{esc(note)}</p></article>'
    )


def load_optional(path: pathlib.Path) -> dict[str, Any]:
    return read_json(path) if path.is_file() else {}


def build_portal(root: pathlib.Path) -> pathlib.Path:
    root = root.expanduser().resolve()
    science = science_root(root)
    status = compute_status(root, write=True)
    study = read_json(science / "study.json")
    services = load_catalog()
    parity = build_report(root)
    doctor = load_optional(science / "DOCTOR.json")
    sources = read_jsonl(science / "evidence/sources.jsonl")
    claims = read_jsonl(science / "evidence/claims.jsonl")
    searches = read_jsonl(science / "evidence/searches.jsonl")
    datasets = read_jsonl(science / "datasets/registry.jsonl")
    experiments = read_jsonl(science / "experiments/registry.jsonl")
    compute = read_jsonl(science / "compute/jobs.jsonl")
    artifacts = read_jsonl(science / "artifacts/manifest.jsonl")
    forks = read_jsonl(science / "forks.jsonl")
    audit_paths = sorted((science / "reviews").glob("audit-*.json"))
    latest_audit = load_optional(audit_paths[-1]) if audit_paths else {}
    coverage = float(status.get("coverage_percent", 0.0))
    status_cards = "".join(
        (
            f'<article class="stage {esc(item.get("status"))}">'
            f'<div><span class="badge">{esc(item.get("requirement"))}</span>'
            f'<span class="state">{esc(item.get("status"))}</span></div>'
            f'<h3>{esc(item.get("label"))}</h3>'
            f'<p>{esc(", ".join(str(value) for value in item.get("evidence", [])))}</p>'
            f'<p class="next">{esc(item.get("next_action") or "Recorded minimum coverage is present.")}</p>'
            "</article>"
        )
        for item in status.get("stages", [])
        if isinstance(item, dict)
    )
    next_actions = "".join(
        f'<li><strong>{esc(item.get("stage"))}</strong><span>{esc(item.get("action"))}</span></li>'
        for item in status.get("next_actions", [])
        if isinstance(item, dict)
    ) or "<li><strong>Revalidate</strong><span>No required coverage gap is recorded; run audit and expert review before release.</span></li>"
    service_rows = [
        [item.get("label"), item.get("skill"), item.get("availability"), item.get("commands")]
        for item in services.get("services", [])
        if isinstance(item, dict)
    ]
    parity_cards = "".join(
        (
            f'<article class="parity {esc(item.get("status"))}">'
            f'<div><span class="state">{esc(item.get("status"))}</span></div>'
            f'<h3>{esc(item.get("label"))}</h3>'
            f'<p>{esc(item.get("gap"))}</p>'
            f'<p class="muted">Evidence: {esc(item.get("evidence"))}</p>'
            "</article>"
        )
        for item in parity.get("capabilities", [])
        if isinstance(item, dict)
    )
    provider_rows = [
        [name, value.get("status"), value.get("authentication")]
        for name, value in doctor.get("providers", {}).items()
        if isinstance(value, dict)
    ]
    audit_summary = (
        f"{latest_audit.get('status', 'not recorded')} · {latest_audit.get('counts', {})}"
        if latest_audit
        else "not recorded"
    )
    css = """
    :root { color-scheme: light; --ink:#17221b; --muted:#66736a; --line:#dce5de; --paper:#f5f7f2; --card:#ffffff; --green:#176b45; --green-soft:#dff3e8; --amber:#9a5b00; --amber-soft:#fff0cf; --red:#a43a32; --red-soft:#fde7e3; --blue:#245a73; --blue-soft:#e5f1f6; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:var(--paper); line-height:1.5; }
    a { color:var(--blue); }
    .shell { max-width:1440px; margin:auto; padding:32px; }
    header { background:#13271d; color:white; border-radius:24px; padding:34px; display:grid; grid-template-columns:minmax(0,1fr) auto; gap:30px; box-shadow:0 18px 45px rgba(23,34,27,.14); }
    header h1 { font-size:clamp(2rem,5vw,4.25rem); line-height:.96; margin:12px 0 18px; max-width:900px; letter-spacing:-.04em; }
    header p { max-width:820px; color:#d9e6dc; }
    .eyebrow { margin:0; text-transform:uppercase; letter-spacing:.14em; font-weight:750; font-size:.72rem; }
    .stamp { align-self:start; border:1px solid rgba(255,255,255,.2); border-radius:16px; padding:15px 18px; min-width:220px; }
    .stamp strong { display:block; font-size:1.65rem; margin-top:6px; }
    .progress { margin-top:22px; height:10px; border-radius:999px; background:rgba(255,255,255,.18); overflow:hidden; }
    .progress span { display:block; height:100%; background:#8de0ae; border-radius:inherit; }
    main { display:grid; gap:24px; margin-top:24px; }
    section { background:var(--card); border:1px solid var(--line); border-radius:22px; padding:26px; }
    h2 { margin:0 0 6px; font-size:1.45rem; letter-spacing:-.02em; }
    h3 { margin:12px 0 8px; font-size:1rem; }
    .section-intro { margin:0 0 20px; color:var(--muted); }
    .metrics { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:14px; }
    .metric { border:1px solid var(--line); border-radius:18px; padding:18px; min-height:132px; }
    .metric-value { margin:8px 0 2px; font-size:2rem; font-weight:780; letter-spacing:-.04em; }
    .muted { color:var(--muted); font-size:.88rem; }
    .next-list { list-style:none; margin:0; padding:0; display:grid; gap:10px; }
    .next-list li { display:grid; grid-template-columns:120px 1fr; gap:16px; padding:15px 17px; background:var(--blue-soft); border-radius:14px; }
    .stages,.parity-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }
    .stage,.parity { border:1px solid var(--line); border-radius:18px; padding:18px; border-top-width:4px; }
    .stage.ready,.parity.ready { border-top-color:var(--green); }
    .stage.in-progress,.parity.degraded { border-top-color:var(--amber); }
    .stage.not-started,.parity.unavailable { border-top-color:var(--red); }
    .stage.not-requested { border-top-color:var(--muted); }
    .badge,.state { display:inline-block; padding:4px 9px; border-radius:999px; font-size:.68rem; font-weight:760; text-transform:uppercase; letter-spacing:.06em; background:#eef2ee; }
    .state { float:right; }
    .ready .state { background:var(--green-soft); color:var(--green); }
    .in-progress .state,.degraded .state { background:var(--amber-soft); color:var(--amber); }
    .not-started .state,.unavailable .state { background:var(--red-soft); color:var(--red); }
    .next { color:var(--blue); font-size:.88rem; }
    .two-col { display:grid; grid-template-columns:1fr 1fr; gap:24px; }
    .table-wrap { overflow:auto; border:1px solid var(--line); border-radius:15px; }
    table { width:100%; border-collapse:collapse; font-size:.86rem; }
    th,td { padding:12px 13px; text-align:left; vertical-align:top; border-bottom:1px solid var(--line); }
    th { background:#f0f4f0; font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; }
    tr:last-child td { border-bottom:0; }
    .empty { color:var(--muted); padding:18px; border:1px dashed var(--line); border-radius:14px; }
    .boundary { background:#fff8e8; border-color:#f0d9a7; }
    footer { padding:24px 4px 10px; color:var(--muted); font-size:.82rem; }
    @media (max-width:1000px) { .metrics { grid-template-columns:repeat(2,1fr); } .stages,.parity-grid { grid-template-columns:repeat(2,1fr); } header { grid-template-columns:1fr; } }
    @media (max-width:680px) { .shell { padding:14px; } header,section { border-radius:16px; padding:20px; } .metrics,.stages,.parity-grid,.two-col { grid-template-columns:1fr; } .next-list li { grid-template-columns:1fr; gap:4px; } }
    """
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
  <title>{esc(study.get('title', 'Codex Science'))} · Research portal</title>
  <style>{css}</style>
</head>
<body>
<div class="shell">
  <header>
    <div>
      <p class="eyebrow">Codex Science · Research workspace</p>
      <h1>{esc(study.get('title', 'Untitled study'))}</h1>
      <p>{esc(study.get('question', ''))}</p>
      <div class="progress" role="progressbar" aria-label="Recorded required workflow coverage" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{esc(coverage)}"><span style="width:{esc(max(0.0, min(100.0, coverage)))}%"></span></div>
    </div>
    <div class="stamp"><p class="eyebrow">Recorded coverage</p><strong>{esc(status.get('required_ready', 0))}/{esc(status.get('required_total', 0))}</strong><span>{esc(coverage)}% · {esc(status.get('profile'))} / {esc(status.get('domain'))}</span></div>
  </header>
  <main>
    <section>
      <h2>Research pulse</h2><p class="section-intro">A compact view of recorded state, not a score of scientific truth.</p>
      <div class="metrics">
        {metric('Evidence', len(sources), f'{len(searches)} searches · {len(claims)} claims')}
        {metric('Datasets', len(datasets), 'registered source and derived datasets')}
        {metric('Experiment events', len(experiments), 'plans, results, failures, and inconclusive runs')}
        {metric('Artifacts', len(artifacts), 'registered outputs including packets')}
        {metric('Latest audit', latest_audit.get('status', '—'), audit_summary)}
      </div>
    </section>
    <section>
      <h2>Next required actions</h2><p class="section-intro">The shortest path through currently recorded workflow gaps.</p>
      <ol class="next-list">{next_actions}</ol>
    </section>
    <section>
      <h2>Workflow stages</h2><p class="section-intro">Required, adaptive, and intentionally not-requested stages remain distinct.</p>
      <div class="stages">{status_cards}</div>
    </section>
    <div class="two-col">
      <section><h2>Evidence sources</h2><p class="section-intro">Discovery metadata still requires source screening.</p>{table(['ID','Title','Type','Review status'], [[item.get('id'),item.get('title'),item.get('type'),item.get('review_status')] for item in sources[:12]], 'No sources recorded.')}</section>
      <section><h2>Claims</h2><p class="section-intro">Observed, derived, hypothesis, conflicted, and unsupported claims stay explicit.</p>{table(['ID','Status','Claim','Evidence'], [[item.get('id'),item.get('status'),item.get('text'),list(item.get('sources') or []) + list(item.get('experiments') or [])] for item in claims[:12]], 'No claims recorded.')}</section>
    </div>
    <div class="two-col">
      <section><h2>Data and experiments</h2>{table(['Dataset','Type','Description'], [[item.get('id'),item.get('record_type'),item.get('description')] for item in datasets[:10]], 'No datasets recorded.')}{table(['Experiment','Type','Status / oracle'], [[item.get('id'),item.get('record_type'),item.get('status') or item.get('test_oracle')] for item in experiments[:10]], 'No experiment events recorded.')}</section>
      <section><h2>Compute and artifacts</h2>{table(['Compute','Type','Backend','Status'], [[item.get('id'),item.get('record_type'),item.get('backend'),item.get('status')] for item in compute[:10]], 'No compute events recorded.')}{table(['Artifact','Kind','Path'], [[item.get('id'),item.get('kind'),item.get('path')] for item in artifacts[-10:]], 'No artifacts recorded.')}</section>
    </div>
    <section>
      <h2>Scientific service ecosystem</h2><p class="section-intro">Availability describes the workflow or local environment, not authorization or scientific validation.</p>
      {table(['Service','Skill','Availability','Unified commands'], service_rows, 'No services found.')}
      <div style="margin-top:18px">{table(['Provider','Status','Authentication'], provider_rows, 'Run science.py doctor --save to capture provider configuration without secret values.')}</div>
    </section>
    <section>
      <h2>Public Claude Science capability audit</h2>
      <p class="section-intro">Compared with <a href="{esc(parity.get('source', {}).get('url'))}" rel="noreferrer">the public product description</a>. This is feature conformance, not model-quality or product parity.</p>
      <div class="parity-grid">{parity_cards}</div>
    </section>
    <section class="boundary">
      <h2>Interpretation boundary</h2>
      <p>{esc(status.get('boundary'))}</p><p>{esc(parity.get('boundary'))}</p>
      <p>Forks recorded: {esc(len(forks))}. This portal is a read-only projection of local ledgers and may contain paths or metadata unsuitable for public sharing.</p>
    </section>
  </main>
  <footer>Generated {esc(status.get('generated_at'))} from local Codex Science state. No external scripts, fonts, trackers, or network resources are embedded.</footer>
</div>
</body>
</html>
"""
    output = science / "PORTAL.html"
    atomic_text(output, document)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        output = build_portal(args.root)
    except (ScienceError, ParityError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Built research portal at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
