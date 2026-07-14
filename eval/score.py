#!/usr/bin/env python3
"""Standalone eval script for A股智能监控系统.

Outputs JSON with dimension scores and overall weighted score.
Usage: uv run python eval/score.py
"""

import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_PROFILE = PROJECT_ROOT / ".factory" / "eval_profile.json"


def run_command(cmd: str, timeout: int = 120) -> tuple[str, int]:
    """Run a shell command, return (output, returncode)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        output = result.stdout + result.stderr
        return output, result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 1
    except Exception as e:
        return str(e), 1


def score_dimension(dim: dict) -> dict:
    """Score a single eval dimension. Returns 0.0 or 1.0."""
    output, returncode = run_command(dim["command"])

    passed = False
    if returncode == 0:
        passed = True
    if dim.get("pass_pattern"):
        passed = passed and bool(re.search(dim["pass_pattern"], output))
    if dim.get("fail_pattern") and re.search(dim["fail_pattern"], output):
        passed = False

    # For tests, extract pass/fail counts for richer scoring
    detail = {}
    if dim["name"] == "tests":
        m = re.search(r"(\d+) passed", output)
        if m:
            detail["tests_passed"] = int(m.group(1))
        m = re.search(r"(\d+) failed", output)
        if m:
            detail["tests_failed"] = int(m.group(1))
        m = re.search(r"(\d+) error", output)
        if m:
            detail["tests_errors"] = int(m.group(1))

    return {
        "name": dim["name"],
        "weight": dim["weight"],
        "score": 1.0 if passed else 0.0,
        "passed": passed,
        "detail": detail,
        "output_tail": output[-500:] if output else "",
    }


def main():
    if not EVAL_PROFILE.exists():
        print(json.dumps({"error": "eval_profile.json not found"}))
        sys.exit(1)

    profile = json.loads(EVAL_PROFILE.read_text())
    results = []

    for dim in profile["dimensions"]:
        result = score_dimension(dim)
        results.append(result)

    weighted_total = sum(r["score"] * r["weight"] for r in results)
    weight_sum = sum(r["weight"] for r in results)
    overall = weighted_total / weight_sum if weight_sum > 0 else 0.0

    output = {
        "project": profile["project"],
        "overall_score": round(overall, 3),
        "dimensions": results,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
