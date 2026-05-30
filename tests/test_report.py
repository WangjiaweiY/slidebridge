from __future__ import annotations

import json

from slidebridge.qc.report import generate_html_report, generate_json_report


def test_generate_html_report_with_summary_and_badges(tmp_path):
    out = tmp_path / "report.html"
    results = [
        {
            "filename": "demo.png",
            "reader": "image",
            "width": 100,
            "height": 80,
            "level_count": 1,
            "mpp_x": None,
            "mpp_y": None,
            "objective_power": None,
            "vendor": None,
            "tissue_percent": 50.0,
            "blur_score": 12.5,
            "warnings": ["missing_mpp"],
        }
    ]

    generate_html_report(results, out)
    text = out.read_text(encoding="utf-8")

    assert "Total slides" in text
    assert "missing_mpp" in text
    assert "SlideBridge QC Report" in text


def test_generate_json_report_omits_thumbnail(tmp_path):
    out = tmp_path / "report.json"
    results = [
        {
            "filename": "demo.png",
            "thumbnail_b64": "abc",
            "reader": "image",
            "tissue_percent": 25.0,
            "warnings": [],
        }
    ]

    generate_json_report(results, out)
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload["summary"]["total_slides"] == 1
    assert "thumbnail_b64" not in payload["slides"][0]

