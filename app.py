"""
app.py — Flask web interface for the Job Intelligence Engine.

Usage:
    python app.py
    Then open http://localhost:5000 in your browser.
"""

import json
import os
from datetime import datetime

from flask import Flask, render_template, request, session
from pipeline import ingest, capture, validate, repair, analyze, validate_analysis, repair_analysis

app = Flask(__name__)
app.secret_key = "jie-local-session-key"


def run_pipeline(raw_jd: str, profile: str = "") -> tuple:
    """Run the full pipeline. Returns (capture_parsed, analysis_parsed, error)."""
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    try:
        jd_text = ingest(raw_jd)
    except ValueError as e:
        return None, None, str(e)

    capture_artifact = capture(jd_text)
    validated = validate(capture_artifact)

    if not validated["valid"]:
        validated = repair(validated)
        if not validated["valid"]:
            return None, None, f"Capture failed after repair: {validated['validation_errors']}"

    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/{run_id}_capture.json", "w") as f:
        json.dump(validated, f, indent=2)

    analysis_artifact = analyze(validated, jd_text, profile=profile or None)
    analysis_artifact = validate_analysis(analysis_artifact)

    if not analysis_artifact["valid"]:
        analysis_artifact = repair_analysis(analysis_artifact)

    with open(f"outputs/{run_id}_analysis.json", "w") as f:
        json.dump(analysis_artifact, f, indent=2)

    if not analysis_artifact["valid"]:
        return validated.get("parsed"), None, "Analysis failed to validate after repair."

    return validated.get("parsed"), analysis_artifact.get("parsed"), None


@app.route("/", methods=["GET", "POST"])
def index():
    jd_text = ""
    capture_data = None
    analysis = None
    error = None

    # Load saved profile from session
    profile = session.get("profile", "")

    if request.method == "POST":
        jd_text = request.form.get("jd_text", "").strip()
        profile = request.form.get("profile", "").strip()

        # Persist profile in session
        session["profile"] = profile

        if jd_text:
            capture_data, analysis, error = run_pipeline(jd_text, profile)
        else:
            error = "Please paste a job description."

    return render_template("index.html",
                           jd_text=jd_text,
                           profile=profile,
                           capture=capture_data,
                           analysis=analysis,
                           error=error)


if __name__ == "__main__":
    app.run(debug=True)
