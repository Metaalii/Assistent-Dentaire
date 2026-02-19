#!/usr/bin/env python3
"""
SmartNote evaluation runner.

Usage:
    # Score the gold-standard reference notes (sanity check / baseline):
    python -m app.eval.run_eval

    # Score the references AND run live generation if the LLM is up:
    python -m app.eval.run_eval --live --base-url http://localhost:9000

    # Score a single SmartNote from stdin:
    echo "- Motif : ..." | python -m app.eval.run_eval --stdin --transcription "..."

    # Export results as JSON:
    python -m app.eval.run_eval --json
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from typing import Any

from app.eval.samples import SAMPLES, EvalSample
from app.eval.scorer import score_smartnote


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------

_BAR_WIDTH = 20


def _bar(score: float) -> str:
    filled = round(score * _BAR_WIDTH)
    return f"[{'#' * filled}{'.' * (_BAR_WIDTH - filled)}] {score:.0%}"


def _grade(score: float) -> str:
    if score >= 0.9:
        return "PASS"
    if score >= 0.7:
        return "WARN"
    return "FAIL"


def _print_report(scenario: str, report: dict[str, Any]) -> None:
    overall = report["overall"]
    grade = _grade(overall)
    print(f"\n{'=' * 60}")
    print(f"  {scenario:<30s}  {grade:>4s}  {_bar(overall)}")
    print(f"{'=' * 60}")
    for key in ("format", "field_fill", "length", "language", "faithfulness"):
        if key not in report:
            continue
        sub = report[key]
        print(f"  {key:<18s} {_bar(sub['score'])}")
        # Show diagnostics for failures
        if sub["score"] < 1.0:
            if "missing" in sub and sub["missing"]:
                print(f"    missing fields: {', '.join(sub['missing'])}")
            if "empty" in sub and sub["empty"]:
                print(f"    empty fields:   {', '.join(sub['empty'])}")
            if "missed" in sub and sub["missed"]:
                print(f"    missed terms:   {', '.join(sub['missed'])}")
            if "line_count" in sub:
                print(f"    lines: {sub['line_count']} (target 5-10)")


# ------------------------------------------------------------------
# Evaluation modes
# ------------------------------------------------------------------

def eval_references() -> list[dict[str, Any]]:
    """Score the gold-standard reference notes (baseline sanity check)."""
    results = []
    for sample in SAMPLES:
        report = score_smartnote(
            smartnote=sample.reference_note,
            transcription=sample.transcription,
            key_terms=sample.key_terms,
        )
        report["scenario"] = sample.scenario
        report["mode"] = "reference"
        results.append(report)
        _print_report(f"[ref] {sample.scenario}", report)
    return results


def eval_live(base_url: str) -> list[dict[str, Any]]:
    """Generate SmartNotes via the running API and score them."""
    try:
        import requests
    except ImportError:
        print("ERROR: 'requests' package required for --live mode", file=sys.stderr)
        sys.exit(1)

    results = []
    for sample in SAMPLES:
        url = f"{base_url.rstrip('/')}/summarize"
        try:
            resp = requests.post(url, json={"text": sample.transcription}, timeout=120)
            resp.raise_for_status()
            smartnote = resp.json().get("summary", "")
        except Exception as exc:
            print(f"\n  ERROR generating for {sample.scenario}: {exc}")
            continue

        report = score_smartnote(
            smartnote=smartnote,
            transcription=sample.transcription,
            key_terms=sample.key_terms,
        )
        report["scenario"] = sample.scenario
        report["mode"] = "live"
        report["generated_note"] = smartnote
        results.append(report)
        _print_report(f"[live] {sample.scenario}", report)
    return results


def eval_stdin(transcription: str) -> dict[str, Any]:
    """Score a SmartNote read from stdin."""
    smartnote = sys.stdin.read()
    if not smartnote.strip():
        print("ERROR: no input on stdin", file=sys.stderr)
        sys.exit(1)
    report = score_smartnote(smartnote=smartnote, transcription=transcription)
    _print_report("[stdin]", report)
    return report


# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

def _print_summary(results: list[dict[str, Any]], threshold: float) -> bool:
    """Print summary table. Returns True if all pass the threshold."""
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")
    all_pass = True
    for r in results:
        grade = _grade(r["overall"])
        label = f"[{r.get('mode', '?')}] {r.get('scenario', '?')}"
        passed = r["overall"] >= threshold
        if not passed:
            all_pass = False
        status = "ok" if passed else "BELOW THRESHOLD"
        print(f"  {label:<40s} {r['overall']:.2%}  {grade}  {status}")
    avg = sum(r["overall"] for r in results) / len(results) if results else 0
    print(f"\n  Average: {avg:.2%}   Threshold: {threshold:.0%}")
    print(f"  Result:  {'ALL PASS' if all_pass else 'SOME BELOW THRESHOLD'}")
    return all_pass


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate SmartNote quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              python -m app.eval.run_eval                  # baseline reference check
              python -m app.eval.run_eval --live            # generate + score
              python -m app.eval.run_eval --json            # JSON output
              python -m app.eval.run_eval --threshold 0.85  # CI gate
        """),
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Also generate SmartNotes via the API and score them",
    )
    parser.add_argument(
        "--base-url", default="http://localhost:9000",
        help="Backend URL for --live mode (default: http://localhost:9000)",
    )
    parser.add_argument(
        "--stdin", action="store_true",
        help="Score a single SmartNote from stdin",
    )
    parser.add_argument(
        "--transcription", default="",
        help="Transcription text for --stdin mode (for faithfulness scoring)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.80,
        help="Minimum overall score to pass (default: 0.80)",
    )
    args = parser.parse_args()

    if args.stdin:
        result = eval_stdin(args.transcription)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["overall"] >= args.threshold else 1)

    print("SmartNote Evaluation Framework")
    print("=" * 60)

    all_results: list[dict[str, Any]] = []

    # Always run reference baseline
    print("\n--- Reference Notes (gold standard baseline) ---")
    all_results.extend(eval_references())

    # Optionally run live generation
    if args.live:
        print("\n--- Live Generation ---")
        all_results.extend(eval_live(args.base_url))

    if args.json:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))
    else:
        all_pass = _print_summary(all_results, args.threshold)
        sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
