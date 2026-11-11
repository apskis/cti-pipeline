"""Build specs as the pipeline leaves them: who each report is for."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


def write_specs(out: Path) -> None:
    work = out / "bulletin-scan/state/_work"
    work.mkdir(parents=True, exist_ok=True)
    old = {"report_id": "CTI26-01", "audience": "DRAFT for review: Old Team", "questions": []}
    (work / "CTI26-01_spec.json").write_text(json.dumps(old), encoding="utf-8")
    stamp = datetime(2026, 11, 1, 12, 0).timestamp()
    os.utime(work / "CTI26-01_spec.json", (stamp, stamp))
    spec = {
        "report_id": "CTI26-01",
        "audience": "DRAFT for April's review: Product Security, Lab Operations",
        "questions": [
            ["SOC", "Would we see this in Falcon?"],
            ["Security Operations", "Is the detection tuned?"],
            ["Product Security", "Which instruments run it?"],
            ["DevOps / Platform Engineering", "Is the image pinned?"],
        ],
    }
    (work / "CTI26-01-spec.json").write_text(json.dumps(spec), encoding="utf-8")
    grouped = {
        "report_id": "CTI26-02",
        "questions": [{"audience": "Third Party Risk", "items": ["Is the vendor affected?"]}],
    }
    (work / "spec_CTI26-02.json").write_text(json.dumps(grouped), encoding="utf-8")
    (work / "TH26-01-spec.json").write_text(json.dumps({"hunt_id": "TH26-01"}), encoding="utf-8")
    (work / "broken-spec.json").write_text("{not json", encoding="utf-8")
