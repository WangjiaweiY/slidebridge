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
LEGACY_PATCH_SLOTS = PATCH_GRID_COLUMNS * PATCH_GRID_ROWS
MAX_PATCH_SLOTS = 12
MAIN_PATCH_GAP = 32
PATCH_ROW_GUTTER = PATCH_SLOT_GUTTER
BOTTOM_MARGIN = 80


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
    layout = _resolve_layout(normalized)
    main_panel = layout["main_panel"]

    main = normalized["main"]
    scalebar_drawn = False
    rendered_patches: list[dict[str, Any]] = []
    main_summary: dict[str, Any] | None = None
    main_render_bbox = tuple(main["bbox"])
    patches_by_slot = {int(patch["slot"]): patch for patch in normalized["patches"]}

    for panel_spec in layout["ordered_panels"]:
        panel = tuple(panel_spec["panel"])
        if panel_spec["role"] == "main":
            main_render_bbox = _adjust_bbox_to_panel_aspect(tuple(main["bbox"]), panel[2], panel[3], slide)
            image, main_summary = _render_panel(
                slide,
                main_render_bbox,
                panel[2],
                panel[3],
                main["mode"],
                heatmap_source,
                normalized["overlay_opacity"],
                fit="cover",
            )
            canvas.paste(image, panel[:2])
            _draw_border(draw, panel, width=3)
            if show_labels:
                _draw_panel_label(draw, panel, main["label"], font_label)
            if main.get("scalebar_um") is not None:
                scalebar_drawn = _draw_scalebar(
                    draw,
                    panel,
                    float(main["scalebar_um"]),
                    _slide_mpp(slide),
                    float(main_summary["scale"]),
                    font_small,
                )
            continue

        slot = int(panel_spec["slot"])
        patch = patches_by_slot.get(slot)
        if patch is None:
            continue
        patch_render_bbox = _adjust_bbox_to_panel_aspect(tuple(patch["bbox"]), panel[2], panel[3], slide)
        image, summary = _render_panel(
            slide,
            patch_render_bbox,
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
                "render_bbox": list(patch_render_bbox),
                "mode": patch["mode"],
                "label": patch["label"],
                "view": summary,
            }
        )

    if main_summary is None:
        raise ValueError("layout.panels must include a main panel.")

    return canvas, {
        "figure_size": list(FIGURE_CANVAS),
        "slide_id": normalized["slide_id"],
        "heatmap_layer_id": normalized["heatmap_layer_id"],
        "show_labels": show_labels,
        "layout": normalized.get("layout"),
        "main": {
            "panel": list(main_panel),
            "max_panel": list(MAIN_PANEL),
            "bbox": main["bbox"],
            "render_bbox": list(main_render_bbox),
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
    layout = _normalize_layout(spec.get("layout"))
    patch_slots_with_panels = _layout_patch_slots(layout)

    main = spec.get("main") or {}
    main_mode = _mode(main.get("mode", "overlay" if heatmap_layer_id else "raw"))
    main_fit = _fit(main.get("fit", "contain"))
    _require_heatmap_for_overlay(main_mode, heatmap_layer_id, raster_heatmap_paths)
    raw_main_bbox = _bbox(main.get("bbox"), "main.bbox")
    main_bbox = _clamp_bbox(raw_main_bbox, slide)
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
        max_slot = MAX_PATCH_SLOTS if layout is not None else LEGACY_PATCH_SLOTS
        if slot < 0 or slot >= max_slot:
            raise ValueError(f"patch.slot must be between 0 and {max_slot - 1}.")
        if slot in used_slots:
            raise ValueError(f"patch.slot {slot} is duplicated.")
        if layout is not None and slot not in patch_slots_with_panels:
            raise ValueError(f"layout.panels must include a patch panel for patch.slot {slot}.")
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
                "label": str(raw_patch.get("label") or _slot_label(slot)),
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
        "layout": layout,
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


def _resolve_layout(normalized: dict[str, Any]) -> dict[str, Any]:
    if normalized.get("layout") is not None:
        panels = normalized["layout"]["panels"]
        main_panel = next(panel["panel"] for panel in panels if panel["role"] == "main")
        patch_panels = {
            int(panel["slot"]): tuple(panel["panel"])
            for panel in panels
            if panel["role"] == "patch"
        }
        return {
            "main_panel": tuple(main_panel),
            "patch_panels": patch_panels,
            "ordered_panels": panels,
        }
    main_panel = _main_panel_for_bbox(tuple(normalized["main"]["bbox"]))
    patch_panels = {
        slot: _patch_panel_for_slot(slot, main_panel)
        for slot in range(PATCH_GRID_COLUMNS * PATCH_GRID_ROWS)
    }
    ordered_panels = [{"id": "A", "role": "main", "panel": main_panel}]
    ordered_panels.extend(
        {"id": _slot_label(slot), "role": "patch", "slot": slot, "panel": patch_panels[slot]}
        for slot in range(PATCH_GRID_COLUMNS * PATCH_GRID_ROWS)
    )
    return {"main_panel": main_panel, "patch_panels": patch_panels, "ordered_panels": ordered_panels}


def _normalize_layout(value: Any) -> dict[str, Any] | None:
    if value in (None, ""):
        return None
    if not isinstance(value, dict):
        raise ValueError("layout must be a JSON object.")
    panels_value = value.get("panels")
    if panels_value in (None, ""):
        return None
    if str(value.get("template") or "custom").strip().lower() != "custom":
        raise ValueError("layout.template must be custom.")
    if not isinstance(panels_value, list) or not panels_value:
        raise ValueError("layout.panels must be a non-empty list.")

    panels: list[dict[str, Any]] = []
    seen_main = False
    used_slots: set[int] = set()
    for index, item in enumerate(panels_value):
        if not isinstance(item, dict):
            raise ValueError("Each layout panel must be a JSON object.")
        role = str(item.get("role") or "").strip().lower()
        rect = _rect(item.get("rect"), f"layout.panels[{index}].rect")
        if role == "main":
            if seen_main:
                raise ValueError("layout.panels must include only one main panel.")
            seen_main = True
            panels.append({"id": str(item.get("id") or "A"), "role": "main", "panel": rect})
        elif role == "patch":
            try:
                slot = int(item.get("slot"))
            except Exception as exc:
                raise ValueError("layout patch panel requires an integer slot.") from exc
            if slot < 0 or slot >= MAX_PATCH_SLOTS:
                raise ValueError(f"layout patch slot must be between 0 and {MAX_PATCH_SLOTS - 1}.")
            if slot in used_slots:
                raise ValueError(f"layout patch slot {slot} is duplicated.")
            if rect[2] != rect[3]:
                raise ValueError("layout patch panel rect must be square.")
            used_slots.add(slot)
            panels.append({"id": str(item.get("id") or _slot_label(slot)), "role": "patch", "slot": slot, "panel": rect})
        else:
            raise ValueError("layout panel role must be main or patch.")
    if not seen_main:
        raise ValueError("layout.panels must include a main panel.")
    return {"template": "custom", "panels": panels}


def _layout_patch_slots(layout: dict[str, Any] | None) -> set[int]:
    if layout is None:
        return set()
    return {int(panel["slot"]) for panel in layout["panels"] if panel["role"] == "patch"}


def _rect(value: Any, name: str) -> tuple[int, int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"{name} must be [x, y, width, height].")
    x, y, width, height = [int(round(float(item))) for item in value]
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError(f"{name} must have non-negative origin and positive size.")
    if x + width > FIGURE_CANVAS[0] or y + height > FIGURE_CANVAS[1]:
        raise ValueError(f"{name} must stay within the fixed figure canvas.")
    return x, y, width, height


def _main_panel_for_bbox(bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bbox
    bbox_width = max(1, x1 - x0)
    bbox_height = max(1, y1 - y0)
    aspect = bbox_width / float(bbox_height)
    available_height = (
        FIGURE_CANVAS[1]
        - MAIN_PANEL[1]
        - BOTTOM_MARGIN
        - MAIN_PATCH_GAP
        - (PATCH_GRID_ROWS - 1) * PATCH_ROW_GUTTER
    )
    max_main_height = min(
        MAIN_PANEL[3],
        MAIN_PANEL[2] / aspect,
        available_height / (1.0 + PATCH_GRID_ROWS * aspect / PATCH_GRID_COLUMNS),
    )
    raw_width = max(1.0, max_main_height * aspect)
    slot_size = max(1, int(raw_width // PATCH_GRID_COLUMNS))

    while slot_size > 1:
        width = slot_size * PATCH_GRID_COLUMNS
        height = max(1, int(round(width / aspect)))
        total_height = (
            MAIN_PANEL[1]
            + height
            + MAIN_PATCH_GAP
            + PATCH_GRID_ROWS * slot_size
            + (PATCH_GRID_ROWS - 1) * PATCH_ROW_GUTTER
            + BOTTOM_MARGIN
        )
        if width <= MAIN_PANEL[2] and height <= MAIN_PANEL[3] and total_height <= FIGURE_CANVAS[1]:
            break
        slot_size -= 1

    width = slot_size * PATCH_GRID_COLUMNS
    height = max(1, int(round(width / aspect)))
    x = int(round((FIGURE_CANVAS[0] - width) / 2))
    return x, MAIN_PANEL[1], width, height


def _patch_panel_for_slot(slot: int, main_panel: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    slot_size = max(1, main_panel[2] // PATCH_GRID_COLUMNS)
    col = slot % PATCH_GRID_COLUMNS
    row = slot // PATCH_GRID_COLUMNS
    return (
        main_panel[0] + col * slot_size,
        main_panel[1] + main_panel[3] + MAIN_PATCH_GAP + row * (slot_size + PATCH_ROW_GUTTER),
        slot_size,
        slot_size,
    )


def _slot_label(slot: int) -> str:
    return chr(ord("B") + int(slot))


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
