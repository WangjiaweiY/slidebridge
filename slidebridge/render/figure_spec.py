from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from slidebridge.core.protocol import Slide
from slidebridge.overlays.raster_heatmap import RasterHeatmap
from slidebridge.render.view import render_view_to_image


HeatmapSource = str | Path | RasterHeatmap

FIGURE_CANVAS = (2400, 1800)
MAIN_PANEL = (80, 80, 2240, 980)
PATCH_SLOT_SIZE = 300
PATCH_SLOT_GUTTER = 32
PATCH_GRID_COLUMNS = 3
PATCH_GRID_ROWS = 2
PATCH_GRID_Y = 1088


def render_figure_spec_to_image(
    slide: Slide,
    spec: dict[str, Any],
    raster_heatmap_paths: dict[str, HeatmapSource] | None = None,
) -> tuple[Image.Image, dict[str, Any]]:
    raster_heatmap_paths = raster_heatmap_paths or {}
    normalized = normalize_figure_spec(spec, slide, raster_heatmap_paths)
    canvas = Image.new("RGB", FIGURE_CANVAS, _background_color(normalized["canvas"]["background"]))
    draw = ImageDraw.Draw(canvas)
    font_label = _font(28)
    font_small = _font(15)
    heatmap_source = raster_heatmap_paths.get(normalized["heatmap_layer_id"])
    show_labels = bool(normalized["show_labels"])

    main = normalized["main"]
    main_image, main_summary = _render_panel(
        slide,
        tuple(main["bbox"]),
        MAIN_PANEL[2],
        MAIN_PANEL[3],
        main["mode"],
        heatmap_source,
        normalized["overlay_opacity"],
        fit=main["fit"],
    )
    canvas.paste(main_image, MAIN_PANEL[:2])
    _draw_border(draw, MAIN_PANEL, width=3)
    if show_labels:
        _draw_panel_label(draw, MAIN_PANEL, main["label"], font_label)
    scalebar_drawn = False
    if main.get("scalebar_um") is not None:
        scalebar_drawn = _draw_scalebar(
            draw,
            MAIN_PANEL,
            float(main["scalebar_um"]),
            _slide_mpp(slide),
            float(main_summary["scale"]),
            font_small,
        )

    rendered_patches: list[dict[str, Any]] = []
    for patch in normalized["patches"]:
        panel = _patch_panel_for_slot(int(patch["slot"]))
        image, summary = _render_panel(
            slide,
            tuple(patch["bbox"]),
            panel[2],
            panel[3],
            patch["mode"],
            heatmap_source,
            normalized["overlay_opacity"],
        )
        canvas.paste(image, panel[:2])
        _draw_border(draw, panel, width=2)
        if show_labels:
            _draw_panel_label(draw, panel, patch["label"], font_label)
        rendered_patches.append(
            {
                "slot": patch["slot"],
                "panel": list(panel),
                "bbox": patch["bbox"],
                "mode": patch["mode"],
                "label": patch["label"],
                "view": summary,
            }
        )

    return canvas, {
        "figure_size": list(FIGURE_CANVAS),
        "slide_id": normalized["slide_id"],
        "heatmap_layer_id": normalized["heatmap_layer_id"],
        "show_labels": show_labels,
        "main": {
            "panel": list(MAIN_PANEL),
            "bbox": main["bbox"],
            "mode": main["mode"],
            "fit": main["fit"],
            "label": main["label"],
            "view": main_summary,
            "scalebar_um": main.get("scalebar_um"),
            "scalebar_drawn": scalebar_drawn,
        },
        "patches": rendered_patches,
    }


def normalize_figure_spec(
    spec: dict[str, Any],
    slide: Slide,
    raster_heatmap_paths: dict[str, HeatmapSource] | None = None,
) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("Figure spec must be a JSON object.")
    raster_heatmap_paths = raster_heatmap_paths or {}
    canvas = spec.get("canvas") or {}
    heatmap_layer_id = str(spec.get("heatmap_layer_id") or "").strip()
    overlay_opacity = _clamp_float(spec.get("overlay_opacity", 0.45), 0.0, 1.0)
    show_labels = bool(spec.get("show_labels", True))

    main = spec.get("main") or {}
    main_mode = _mode(main.get("mode", "overlay" if heatmap_layer_id else "raw"))
    main_fit = _fit(main.get("fit", "contain"))
    _require_heatmap_for_overlay(main_mode, heatmap_layer_id, raster_heatmap_paths)
    raw_main_bbox = _bbox(main.get("bbox"), "main.bbox")
    main_bbox = (
        _clamp_bbox(raw_main_bbox, slide)
        if main_fit == "contain"
        else _adjust_bbox_to_panel_aspect(raw_main_bbox, MAIN_PANEL[2], MAIN_PANEL[3], slide)
    )
    scalebar_um = main.get("scalebar_um")
    if scalebar_um is not None:
        scalebar_um = float(scalebar_um)
        if scalebar_um <= 0:
            raise ValueError("main.scalebar_um must be positive.")
        if _slide_mpp(slide) is None:
            raise ValueError("main.scalebar_um requires slide mpp metadata.")

    patches = []
    used_slots: set[int] = set()
    for index, raw_patch in enumerate(spec.get("patches") or []):
        if not isinstance(raw_patch, dict):
            raise ValueError("Each patch entry must be a JSON object.")
        slot = int(raw_patch.get("slot", index))
        if slot < 0 or slot >= PATCH_GRID_COLUMNS * PATCH_GRID_ROWS:
            raise ValueError("patch.slot must be between 0 and 5.")
        if slot in used_slots:
            raise ValueError(f"patch.slot {slot} is duplicated.")
        used_slots.add(slot)
        mode = _mode(raw_patch.get("mode", "raw"))
        _require_heatmap_for_overlay(mode, heatmap_layer_id, raster_heatmap_paths)
        patches.append(
            {
                "slot": slot,
                "bbox": list(_adjust_bbox_to_panel_aspect(
                    _bbox(raw_patch.get("bbox"), f"patches[{index}].bbox"),
                    PATCH_SLOT_SIZE,
                    PATCH_SLOT_SIZE,
                    slide,
                )),
                "mode": mode,
                "label": str(raw_patch.get("label") or chr(ord("B") + slot)),
            }
        )

    return {
        "slide_id": int(spec.get("slide_id", 0)),
        "canvas": {
            "width": FIGURE_CANVAS[0],
            "height": FIGURE_CANVAS[1],
            "background": str(canvas.get("background") or "white"),
        },
        "heatmap_layer_id": heatmap_layer_id,
        "overlay_opacity": overlay_opacity,
        "show_labels": show_labels,
        "main": {
            "bbox": list(main_bbox),
            "mode": main_mode,
            "fit": main_fit,
            "label": str(main.get("label") or "A"),
            "scalebar_um": scalebar_um,
        },
        "patches": patches,
    }


def _render_panel(
    slide: Slide,
    bbox: tuple[int, int, int, int],
    width: int,
    height: int,
    mode: str,
    heatmap_source: HeatmapSource | None,
    opacity: float,
    fit: str = "cover",
) -> tuple[Image.Image, dict[str, Any]]:
    x0, y0, x1, y1 = bbox
    heatmap_path = heatmap_source if isinstance(heatmap_source, (str, Path)) else None
    heatmap = heatmap_source if isinstance(heatmap_source, RasterHeatmap) else None
    target_width, target_height = width, height
    offset_x = 0
    offset_y = 0
    if fit == "contain":
        bbox_width = max(1, x1 - x0)
        bbox_height = max(1, y1 - y0)
        scale = min(width / float(bbox_width), height / float(bbox_height))
        target_width = max(1, int(round(bbox_width * scale)))
        target_height = max(1, int(round(bbox_height * scale)))
        offset_x = int(round((width - target_width) / 2))
        offset_y = int(round((height - target_height) / 2))

    image, summary = render_view_to_image(
        slide,
        center_x=(x0 + x1) / 2,
        center_y=(y0 + y1) / 2,
        window_width=x1 - x0,
        window_height=y1 - y0,
        out_width=target_width,
        out_height=target_height,
        raster_heatmap_path=heatmap_path if mode == "overlay" else None,
        raster_heatmap=heatmap if mode == "overlay" else None,
        raster_heatmap_opacity=opacity,
    )
    if fit == "contain" and (target_width != width or target_height != height):
        panel = Image.new("RGB", (width, height), (255, 255, 255))
        panel.paste(image, (offset_x, offset_y))
        summary = dict(summary)
        summary["content_box"] = [offset_x, offset_y, target_width, target_height]
        return panel, summary
    summary = dict(summary)
    summary["content_box"] = [0, 0, width, height]
    return image, summary


def _patch_panel_for_slot(slot: int) -> tuple[int, int, int, int]:
    if PATCH_GRID_COLUMNS > 1:
        column_gap = (MAIN_PANEL[2] - PATCH_GRID_COLUMNS * PATCH_SLOT_SIZE) / float(PATCH_GRID_COLUMNS - 1)
    else:
        column_gap = 0.0
    col = slot % PATCH_GRID_COLUMNS
    row = slot // PATCH_GRID_COLUMNS
    return (
        int(round(MAIN_PANEL[0] + col * (PATCH_SLOT_SIZE + column_gap))),
        PATCH_GRID_Y + row * (PATCH_SLOT_SIZE + PATCH_SLOT_GUTTER),
        PATCH_SLOT_SIZE,
        PATCH_SLOT_SIZE,
    )


def _bbox(value: Any, name: str) -> tuple[int, int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"{name} must be [x0, y0, x1, y1].")
    x0, y0, x1, y1 = [float(item) for item in value]
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"{name} must have positive width and height.")
    return int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))


def _adjust_bbox_to_panel_aspect(
    bbox: tuple[int, int, int, int],
    panel_width: int,
    panel_height: int,
    slide: Slide,
) -> tuple[int, int, int, int]:
    bbox = _clamp_bbox(bbox, slide)
    slide_width, slide_height = slide.dimensions
    x0, y0, x1, y1 = bbox
    width = max(1.0, float(x1 - x0))
    height = max(1.0, float(y1 - y0))
    target = max(1.0, float(panel_width)) / max(1.0, float(panel_height))
    if width / height > target:
        new_width = width
        new_height = width / target
    else:
        new_height = height
        new_width = height * target
    if new_width > slide_width:
        new_width = float(slide_width)
        new_height = new_width / target
    if new_height > slide_height:
        new_height = float(slide_height)
        new_width = new_height * target
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    left = max(0, min(int(round(cx - new_width / 2.0)), max(0, int(round(slide_width - new_width)))))
    top = max(0, min(int(round(cy - new_height / 2.0)), max(0, int(round(slide_height - new_height)))))
    right = max(left + 1, min(slide_width, int(round(left + new_width))))
    bottom = max(top + 1, min(slide_height, int(round(top + new_height))))
    return left, top, right, bottom


def _clamp_bbox(bbox: tuple[int, int, int, int], slide: Slide) -> tuple[int, int, int, int]:
    slide_width, slide_height = slide.dimensions
    x0, y0, x1, y1 = bbox
    x0 = max(0, min(slide_width - 1, x0))
    y0 = max(0, min(slide_height - 1, y0))
    x1 = max(x0 + 1, min(slide_width, x1))
    y1 = max(y0 + 1, min(slide_height, y1))
    return x0, y0, x1, y1


def _mode(value: Any) -> str:
    mode = str(value or "raw").strip().lower()
    if mode not in {"raw", "overlay"}:
        raise ValueError("panel mode must be raw or overlay.")
    return mode


def _fit(value: Any) -> str:
    fit = str(value or "cover").strip().lower()
    if fit not in {"cover", "contain"}:
        raise ValueError("panel fit must be cover or contain.")
    return fit


def _require_heatmap_for_overlay(
    mode: str,
    heatmap_layer_id: str,
    raster_heatmap_paths: dict[str, HeatmapSource],
) -> None:
    if mode == "overlay" and (not heatmap_layer_id or heatmap_layer_id not in raster_heatmap_paths):
        raise ValueError("overlay mode requires an available heatmap_layer_id.")


def _clamp_float(value: Any, min_value: float, max_value: float) -> float:
    numeric = float(value)
    return max(min_value, min(max_value, numeric))


def _draw_border(draw: ImageDraw.ImageDraw, panel: tuple[int, int, int, int], width: int = 2) -> None:
    x, y, w, h = panel
    draw.rectangle((x, y, x + w - 1, y + h - 1), outline=(24, 38, 48), width=width)


def _draw_panel_label(draw: ImageDraw.ImageDraw, panel: tuple[int, int, int, int], label: str, font: ImageFont.ImageFont) -> None:
    x, y, _, _ = panel
    text = str(label)
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0] + 26
    height = bbox[3] - bbox[1] + 18
    draw.rectangle((x + 14, y + 14, x + 14 + width, y + 14 + height), fill=(255, 255, 255), outline=(24, 38, 48), width=2)
    draw.text((x + 27, y + 22), text, fill=(15, 23, 31), font=font)


def _draw_scalebar(
    draw: ImageDraw.ImageDraw,
    panel: tuple[int, int, int, int],
    scalebar_um: float,
    mpp: float | None,
    output_scale: float,
    font: ImageFont.ImageFont,
) -> bool:
    if mpp is None or float(mpp) <= 0:
        raise ValueError("main.scalebar_um requires slide mpp metadata.")
    x, y, w, h = panel
    length_px = int(round(float(scalebar_um) / float(mpp) * float(output_scale)))
    length_px = max(10, min(length_px, int(w * 0.55)))
    x1 = x + w - 42
    x0 = x1 - length_px
    y0 = y + h - 44
    label = f"{scalebar_um:g} um"
    bbox = draw.textbbox((0, 0), label, font=font)
    draw.rectangle((x0 - 10, y0 - 25, x1 + 10, y0 + 14), fill=(255, 255, 255), outline=(220, 224, 228))
    draw.line((x0, y0, x1, y0), fill=(15, 23, 31), width=6)
    draw.text((x0 + (length_px - (bbox[2] - bbox[0])) / 2, y0 - 23), label, fill=(15, 23, 31), font=font)
    return True


def _slide_mpp(slide: Slide) -> float | None:
    mpp_x, mpp_y = slide.mpp
    values = [float(value) for value in (mpp_x, mpp_y) if value is not None and float(value) > 0]
    if not values:
        return None
    return sum(values) / len(values)


def _background_color(value: str) -> tuple[int, int, int]:
    normalized = str(value or "white").strip().lower()
    if normalized in {"white", "#fff", "#ffffff"}:
        return 255, 255, 255
    if normalized in {"paper", "light"}:
        return 248, 250, 252
    if normalized.startswith("#") and len(normalized) == 7:
        return int(normalized[1:3], 16), int(normalized[3:5], 16), int(normalized[5:7], 16)
    raise ValueError("canvas.background must be white, paper, or #RRGGBB.")


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()
