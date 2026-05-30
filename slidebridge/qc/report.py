from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from slidebridge.utils.paths import ensure_parent


def generate_html_report(results: list[dict[str, Any]], out_path: str | Path) -> Path:
    output = ensure_parent(out_path)
    report_summary = _summary(results)
    body = "\n".join(_render_card(result) for result in results)
    summary_html = _render_summary(report_summary)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SlideBridge QC Report</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #20242a; background: #f5f7fa; }}
    header {{ padding: 24px 32px; background: #1d2733; color: white; }}
    h1 {{ margin: 0 0 6px; font-size: 24px; }}
    main {{ max-width: 1180px; margin: 24px auto; padding: 0 18px 32px; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 18px; }}
    .metric {{ padding: 14px; background: white; border: 1px solid #dfe5ee; border-radius: 8px; }}
    .metric-value {{ display: block; font-size: 24px; font-weight: 700; }}
    .metric-label {{ color: #626c78; font-size: 13px; }}
    .card {{ display: grid; grid-template-columns: 220px 1fr; gap: 18px; margin-bottom: 16px; padding: 16px; background: white; border: 1px solid #dfe5ee; border-radius: 8px; }}
    .thumb {{ width: 220px; max-height: 180px; object-fit: contain; background: #fff; border: 1px solid #e4e8ef; }}
    .missing-thumb {{ width: 220px; height: 140px; display: grid; place-items: center; color: #7b8490; border: 1px dashed #cbd3df; }}
    .title {{ margin: 0 0 10px; font-size: 18px; overflow-wrap: anywhere; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 8px 14px; font-size: 14px; }}
    .label {{ color: #626c78; }}
    .warnings {{ color: #9a5a00; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .badge {{ display: inline-block; padding: 3px 7px; border-radius: 999px; background: #fff3cd; color: #7a5200; border: 1px solid #f2d47a; font-size: 12px; }}
    .badge-ok {{ background: #e8f4ec; color: #1d6b3a; border-color: #aed9bd; }}
    .error {{ color: #9d1c1c; font-weight: 600; }}
    @media (max-width: 720px) {{ .card {{ grid-template-columns: 1fr; }} .thumb, .missing-thumb {{ width: 100%; }} }}
  </style>
</head>
<body>
  <header>
    <h1>SlideBridge QC Report</h1>
    <div>Research and algorithm development only. Not for clinical diagnosis.</div>
  </header>
  <main>
    {summary_html}
    {body}
  </main>
</body>
</html>
"""
    output.write_text(document, encoding="utf-8")
    return output


def generate_json_report(results: list[dict[str, Any]], out_path: str | Path) -> Path:
    output = ensure_parent(out_path)
    payload = {
        "summary": _summary(results),
        "slides": [_strip_thumbnail(result) for result in results],
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _render_card(result: dict[str, Any]) -> str:
    filename = html.escape(str(result.get("filename") or Path(str(result.get("path", ""))).name))
    thumb = result.get("thumbnail_b64")
    if thumb:
        thumb_html = f'<img class="thumb" alt="thumbnail" src="data:image/jpeg;base64,{thumb}">'
    else:
        thumb_html = '<div class="missing-thumb">No thumbnail</div>'

    if result.get("error"):
        detail = f'<div class="error">{html.escape(str(result["error"]))}</div>'
        return f'<section class="card">{thumb_html}<div><h2 class="title">{filename}</h2>{detail}</div></section>'

    warnings = result.get("warnings") or []
    warning_html = _warning_badges(warnings)
    fields = [
        ("Reader", result.get("reader")),
        ("Dimensions", _dimensions(result)),
        ("Levels", result.get("level_count")),
        ("MPP", _mpp(result)),
        ("Objective", result.get("objective_power")),
        ("Vendor", result.get("vendor")),
        ("Tissue %", _fmt(result.get("tissue_percent"), 2)),
        ("Blur score", _fmt(result.get("blur_score"), 2)),
    ]
    rows = "\n".join(
        f'<div><span class="label">{html.escape(label)}:</span> {html.escape(str(value if value is not None else "unknown"))}</div>'
        for label, value in fields
    )
    return f'<section class="card">{thumb_html}<div><h2 class="title">{filename}</h2><div class="grid">{rows}</div><div style="margin-top:10px;"><span class="label">Warnings:</span> {warning_html}</div></div></section>'


def _render_summary(report_summary: dict[str, Any]) -> str:
    fields = [
        ("Total slides", report_summary["total_slides"]),
        ("Success", report_summary["success"]),
        ("Failed", report_summary["failed"]),
        ("Average tissue %", _fmt(report_summary["average_tissue_percent"], 2)),
        ("Slides with warnings", report_summary["slides_with_warnings"]),
    ]
    cards = "\n".join(
        f'<div class="metric"><span class="metric-value">{html.escape(str(value))}</span><span class="metric-label">{html.escape(label)}</span></div>'
        for label, value in fields
    )
    return f'<section class="summary">{cards}</section>'


def _warning_badges(warnings: list[Any]) -> str:
    if not warnings:
        return '<span class="badge badge-ok">none</span>'
    return '<span class="badges">' + "".join(
        f'<span class="badge">{html.escape(str(item))}</span>' for item in warnings
    ) + "</span>"


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    failed = sum(1 for result in results if result.get("error"))
    success = total - failed
    tissue_values = [
        float(result["tissue_percent"])
        for result in results
        if not result.get("error") and result.get("tissue_percent") is not None
    ]
    warning_count = sum(1 for result in results if result.get("warnings"))
    average_tissue = sum(tissue_values) / len(tissue_values) if tissue_values else None
    return {
        "total_slides": total,
        "success": success,
        "failed": failed,
        "average_tissue_percent": average_tissue,
        "slides_with_warnings": warning_count,
    }


def _strip_thumbnail(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "thumbnail_b64"}


def _dimensions(result: dict[str, Any]) -> str:
    width = result.get("width")
    height = result.get("height")
    return f"{width} x {height}" if width and height else "unknown"


def _mpp(result: dict[str, Any]) -> str:
    x = result.get("mpp_x")
    y = result.get("mpp_y")
    if x is None or y is None:
        return "unknown"
    return f"{_fmt(x, 4)} x {_fmt(y, 4)}"


def _fmt(value: Any, digits: int) -> str:
    if value is None:
        return "unknown"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)
