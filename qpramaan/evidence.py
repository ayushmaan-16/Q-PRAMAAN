"""Recompute the public measurement decision. This does not authenticate the file."""
import json
import sys
from .detection import analyze


def check(report):
    config = report["config"]
    result = analyze(report["observations"], baseline=config["baseline"],
                     calibrated=report["channel_analysis"]["calibration"] != "absent")
    recorded = report["channel_analysis"]
    matches = result == recorded
    return {"matches": matches, "recomputed_status": result["status"],
            "meaning": "Checks statistical calculation only; it does not establish provenance or physical security."}


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        result = check(json.load(f))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["matches"] else 1)
