"""
run.py — Job Intelligence Engine entry point.

Usage:
    python run.py                        # uses JD_TEXT variable below
    python run.py --file path/to/jd.txt  # load from file
"""

import argparse
import json
import os
import sys
from datetime import datetime

from pipeline import ingest, capture, validate, repair, analyze, validate_analysis, repair_analysis


# ─────────────────────────────────────────────
# PASTE YOUR JOB DESCRIPTION HERE
# ─────────────────────────────────────────────
JD_TEXT = """

"""


def save(artifact: dict, label: str, run_id: str):
    os.makedirs("outputs", exist_ok=True)
    path = f"outputs/{run_id}_{label}.json"
    with open(path, "w") as f:
        json.dump(artifact, f, indent=2)
    print(f"  [saved] {path}")


def print_analysis(analysis: dict):
    parsed = analysis.get("parsed")
    if not parsed:
        print("\n[!] Analysis parse failed. Raw output:\n")
        print(analysis.get("raw_output"))
        return

    print("\n" + "="*60)
    print("JOB INTELLIGENCE ENGINE — RESULTS")
    print("="*60)

    print(f"\nSUMMARY\n{parsed.get('summary', 'N/A')}")

    print("\nMUST-HAVES")
    for item in parsed.get("must_haves", []):
        print(f"  • {item['text']}  [{', '.join(item.get('source_ids', []))}]")

    print("\nNICE-TO-HAVES")
    for item in parsed.get("nice_to_haves", []):
        print(f"  • {item['text']}  [{', '.join(item.get('source_ids', []))}]")

    print("\nSKILL MAP")
    for category, skills in parsed.get("skill_map", {}).items():
        if skills:
            print(f"  {category.capitalize()}: {', '.join(skills)}")

    print("\nINTERVIEW TOPICS")
    for topic in parsed.get("interview_topics", []):
        print(f"  • {topic['topic']}  [{', '.join(topic.get('source_ids', []))}]")
        print(f"    → {topic['rationale']}")

    print("\nQUESTIONS TO PREPARE")
    for q in parsed.get("prep_questions", []):
        print(f"  • {q}")

    print("\nQUESTIONS TO ASK THEM")
    for q in parsed.get("questions_to_ask", []):
        print(f"  • {q}")

    print("\nWHAT TO EMPHASIZE")
    for point in parsed.get("what_to_emphasize", []):
        print(f"  • {point}")

    if parsed.get("fit_summary"):
        print("\nFIT ASSESSMENT")
        print(f"  {parsed['fit_summary']}")

    if parsed.get("strengths"):
        print("\nYOUR STRENGTHS")
        for s in parsed["strengths"]:
            print(f"  + {s}")

    if parsed.get("gaps"):
        print("\nGAPS TO ADDRESS")
        for g in parsed["gaps"]:
            print(f"  - {g}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Job Intelligence Engine")
    parser.add_argument("--file", type=str, help="Path to a .txt file with the job description")
    parser.add_argument("--profile", type=str, help="Path to a .txt file with your resume/background")
    args = parser.parse_args()

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    print(f"\nJIE run started — {run_id}\n")

    # Stage 1: Ingest (in memory only)
    print("[1/4] Ingesting...")
    if args.file:
        with open(args.file, "r") as f:
            raw = f.read()
    else:
        if not JD_TEXT.strip():
            print("[!] JD_TEXT is empty. Paste a job description into the JD_TEXT variable at the top of run.py")
            sys.exit(1)
        raw = JD_TEXT
    jd_text = ingest(raw)
    print(f"  ✓ {len(jd_text)} chars")

    # Load optional profile
    profile = None
    if args.profile:
        with open(args.profile, "r") as f:
            profile = f.read()
        print(f"  ✓ profile loaded ({len(profile)} chars)")

    # Stage 2: Capture
    print("\n[2/4] Capturing...")
    capture_artifact = capture(jd_text)
    print(f"  {'✓ parsed' if capture_artifact['parse_success'] else '✗ parse failed'}")

    # Stage 3: Validate + repair
    print("\n[3/4] Validating...")
    validated = validate(capture_artifact)
    if not validated["valid"]:
        print(f"  ✗ errors: {validated['validation_errors']}")
        validated = repair(validated)
        if not validated["valid"]:
            print("  ✗ repair failed. Check outputs.")
            save(validated, "capture_failed", run_id)
            sys.exit(1)
    print("  ✓ valid")
    save(validated, "capture", run_id)

    # Stage 4: Analyze
    print("\n[4/4] Analyzing...")
    analysis_artifact = analyze(validated, jd_text, profile=profile)
    analysis_artifact = validate_analysis(analysis_artifact)
    if not analysis_artifact["valid"]:
        analysis_artifact = repair_analysis(analysis_artifact)
    print(f"  {'✓ done' if analysis_artifact['valid'] else '✗ failed'}")
    if not analysis_artifact["valid"]:
        print("  [!] Analysis repair failed. Check outputs.")
    save(analysis_artifact, "analysis", run_id)

    print_analysis(analysis_artifact)


if __name__ == "__main__":
    main()
