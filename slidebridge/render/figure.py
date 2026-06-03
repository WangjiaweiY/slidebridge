from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from slidebridge.core.protocol import Slide
from slidebridge.render.overlay import _format_from_path
from slidebridge.render.view import render_view_to_image
from slidebridge.utils.image import ensure_rgb
from slidebridge.utils.paths import ensure_parent


def render_figure(
    slide: Slide,
    out_path: str | Path,
    center_x: float | None = None,
    center_y: float | None = None,
    window_width: int = 4096,
    window_height: int = 3072,
    main_width: int = 1600,
    main_height: int | None = None,
    raster_heatmap_path: str | Path | None = None,
    raster_heatmap_opacity: float = 0.45,
    max_raster_heatmap_size: int = 4096,
    raster_heatmap_threshold: float | None = None,
    raster_heatmap_invert: bool = False,
    raster_heatmap_colormap: str = "auto",
    inset_x: float | None = None,
    inset_y: float | None = None,
    inset_width: int = 1024,
    inset_height: int = 1024,
    inset_size: int = 360,
    inset_heatmap_path: str | Path | None = None,
    include_inset_heatmap: bool = True,
    inset_heatmap_opacity: float | None = None,
    title: str | None = None,
    panel_label: str | None = None,
    scalebar_um: float | None = None,
    mpp: float | None = None,
    background: str = "white",
    image_format: str | None = None,
    jpeg_quality: int = 95,
) -> dict[str, Any]:
    image, summary = render_figure_to_image(
        slide,
        center_x=center_x,
        center_y=center_y,
        window_width=window_width,
        window_height=window_height,
        main_width=main_width,
        main_height=main_height,
        raster_heatmap_path=raster_heatmap_path,
        raster_heatmap_opacity=raster_heatmap_opacity,
        max_raster_heatmap_size=max_raster_heatmap_size,
        raster_heatmap_threshold=raster_heatmap_threshold,
        raster_heatmap_invert=raster_heatmap_invert,
        raster_heatmap_colormap=raster_heatmap_colormap,
        inset_x=inset_x,
        inset_y=inset_y,
        inset_width=inset_width,
        inset_height=inset_height,
        inset_size=inset_size,
        inset_heatmap_path=inset_heatmap_path,
        include_inset_heatmap=include_inset_heatmap,
        inset_heatmap_opacity=inset_heatmap_opacity,
        title=title,
        panel_label=panel_label,
        scalebar_um=scalebar_um,
        mpp=mpp,
        background=background,
    )
    output = ensure_parent(out_path)
    fmt = _format_from_path(output, image_format)
    if fmt == "JPEG":
        image.save(output, format=fmt, quality=int(jpeg_quality))
    else:
        image.save(output, format=fmt)
    summary["output_path"] = str(output)
    return summary


def render_figure_to_image(
    slide: Slide,
    center_x: float | None = None,
    center_y: float | None = None,
    window_width: int = 4096,
    window_height: int = 3072,
    main_width: int = 1600,
    main_height: int | None = None,
    raster_heatmap_path: str | Path | None = None,
    raster_heatmap_opacity: float = 0.45,
    max_raster_heatmap_size: int = 4096,
    raster_heatmap_threshold: float | None = None,
    raster_heatmap_invert: bool = False,
    raster_heatmap_colormap: str = "auto",
    inset_x: float | None = None,
    inset_y: float | None = None,
    inset_width: int = 1024,
    inset_height: int = 1024,
    inset_size: int = 360,
    inset_heatmap_path: str | Path | None = None,
    include_inset_heatmap: bool = True,
    inset_heatmap_opacity: float | None = None,
    title: str | None = None,
    panel_label: str | None = None,
    scalebar_um: float | None = None,
    mpp: float | None = None,
    background: str = "white",
) -> tuple[Image.Image, dict[str, Any]]:
    main_width = max(1, int(main_width))
    inset_size = max(64, int(inset_size))
    main_image, main_summary = render_view_to_image(
        slide,
        center_x=center_x,
        center_y=center_y,
        window_width=window_width,
        window_height=window_height,
        out_width=main_width,
        out_height=main_height,
        raster_heatmap_path=raster_heatmap_path,
        raster_heatmap_opacity=raster_heatmap_opacity,
        max_raster_heatmap_size=max_raster_heatmap_size,
        raster_heatmap_threshold=raster_heatmap_threshold,
        raster_heatmap_invert=raster_heatmap_invert,
        raster_heatmap_colormap=raster_heatmap_colormap,
    )

    inset_bbox = _resolve_inset_bbox(slide, inset_x, inset_y, inset_width, inset_height)
    inset_images: list[tuple[str, Image.Image]] = []
    if inset_bbox is not None:
        raw = _render_raw_inset(slide, inset_bbox, inset_size)
        inset_images.append(("Inset patch", raw))
        heatmap_for_inset = inset_heatmap_path if inset_heatmap_path is not None else raster_heatmap_path
        if include_inset_heatmap and heatmap_for_inset is not None:
            heatmap = _render_heatmap_inset(
                slide,
                inset_bbox,
                inset_size,
                heatmap_for_inset,
                opacity=raster_heatmap_opacity if inset_heatmap_opacity is None else inset_heatmap_opacity,
                max_size=max_raster_heatmap_size,
                threshold=raster_heatmap_threshold,
                invert=raster_heatmap_invert,
                colormap=raster_heatmap_colormap,
            )
            inset_images.append(("Inset heatmap", heatmap))

    padding = 36
    gutter = 28
    title_height = 0
    font_title = _font(28)
    font_label = _font(24)
    font_body = _font(15)
    font_small = _font(13)
    if title:
        title_height = 48
    side_width = inset_size if inset_images else 0
    side_height = len(inset_images) * inset_size + max(0, len(inset_images) - 1) * gutter
    canvas_width = padding + main_image.width + (gutter + side_width if inset_images else 0) + padding
    canvas_height = padding + title_height + max(main_image.height, side_height) + padding
    canvas = Image.new("RGB", (canvas_width, canvas_height), _background_color(background))
    draw = ImageDraw.Draw(canvas)

    y = padding
    if title:
        draw.text((padding, y), title, fill=(18, 31, 43), font=font_title)
        y += title_height
    main_origin = (padding, y)
    canvas.paste(main_image, main_origin)
    _draw_border(draw, main_origin, main_image.size, (25, 44, 56), width=2)
    if panel_label:
        _draw_panel_label(draw, main_origin, str(panel_label), font_label)
    if inset_bbox is not None:
        _draw_inset_box(draw, main_origin, main_image.size, main_summary["view_bbox"], inset_bbox)
    scalebar_drawn = False
    if scalebar_um is not None:
        scalebar_drawn = _draw_scalebar(
            draw,
            main_origin,
            main_image.size,
            float(scalebar_um),
            mpp if mpp is not None else _slide_mpp(slide),
            float(main_summary["scale"]),
            font_small,
        )

    inset_origins: list[dict[str, Any]] = []
    if inset_images:
        x = padding + main_image.width + gutter
        inset_y0 = y
        for index, (label, image) in enumerate(inset_images):
            iy = inset_y0 + index * (inset_size + gutter)
            canvas.paste(image, (x, iy))
            _draw_border(draw, (x, iy), image.size, (25, 44, 56), width=2)
            _draw_panel_label(draw, (x, iy), chr(ord("B") + index), font_label)
            draw.text((x, iy + image.height + 6), label, fill=(56, 72, 86), font=font_body)
            inset_origins.append({"label": label, "origin": [x, iy], "size": list(image.size)})

    return canvas, {
        "input_slide": str(slide.path),
        "output_path": None,
        "figure_size": [canvas.width, canvas.height],
        "main_view": main_summary,
        "inset_bbox": list(inset_bbox) if inset_bbox is not None else None,
        "insets": inset_origins,
        "scalebar_um": scalebar_um,
        "scalebar_drawn": scalebar_drawn,
        "title": title,
        "panel_label": panel_label,
    }


def _resolve_inset_bbox(
    slide: Slide,
    inset_x: float | None,
    inset_y: float | None,
    inset_width: int,
    inset_height: int,
) -> tuple[int, int, int, int] | None:
    if inset_x is None and inset_y is None:
        return None
    if inset_x is None or inset_y is None:
        raise ValueError("--inset-x and --inset-y must be provided together.")
    slide_width, slide_height = slide.dimensions
    width = max(1, int(inset_width))
    height = max(1, int(inset_height))
    x0 = int(round(float(inset_x)))
    y0 = int(round(float(inset_y)))
    if x0 >= slide_width or y0 >= slide_height or x0 + width <= 0 or y0 + height <= 0:
        raise ValueError("Inset region is outside the slide bounds.")
    x0 = max(0, min(x0, slide_width - 1))
    y0 = max(0, min(y0, slide_height - 1))
    x1 = max(x0 + 1, min(slide_width, x0 + width))
    y1 = max(y0 + 1, min(slide_height, y0 + height))
    return x0, y0, x1, y1


def _render_raw_inset(slide: Slide, bbox: tuple[int, int, int, int], inset_size: int) -> Image.Image:
    x0, y0, x1, y1 = bbox
    image = ensure_rgb(slide.read_region(x0, y0, x1 - x0, y1 - y0, level=0))
    return _resize_to_square_canvas(image, inset_size)


def _render_heatmap_inset(
    slide: Slide,
    bbox: tuple[int, int, int, int],
    inset_size: int,
    heatmap_path: str | Path,
    opacity: float,
    max_size: int,
    threshold: float | None,
    invert: bool,
    colormap: str,
) -> Image.Image:
    x0, y0, x1, y1 = bbox
    image, _ = render_view_to_image(
        slide,
        center_x=(x0 + x1) / 2,
        center_y=(y0 + y1) / 2,
        window_width=x1 - x0,
        window_height=y1 - y0,
        out_width=inset_size,
        out_height=max(1, int(round(inset_size * (y1 - y0) / float(max(1, x1 - x0))))),
        raster_heatmap_path=heatmap_path,
        raster_heatmap_opacity=opacity,
        max_raster_heatmap_size=max_size,
        raster_heatmap_threshold=threshold,
        raster_heatmap_invert=invert,
        raster_heatmap_colormap=colormap,
    )
    return _resize_to_square_canvas(image, inset_size)


def _resize_to_square_canvas(image: Image.Image, size: int) -> Image.Image:
    image = ensure_rgb(image)
    scale = min(size / float(image.width), size / float(image.height))
    resized = image.resize(
        (max(1, int(round(image.width * scale))), max(1, int(round(image.height * scale)))),
        Image.Resampling.BILINEAR,
    )
    canvas = Image.new("RGB", (size, size), "white")
    canvas.paste(resized, ((size - resized.width) // 2, (size - resized.height) // 2))
    return canvas


def _draw_inset_box(
    draw: ImageDraw.ImageDraw,
    main_origin: tuple[int, int],
    main_size: tuple[int, int],
    view_bbox: list[int],
    inset_bbox: tuple[int, int, int, int],
) -> None:
    vx0, vy0, vx1, vy1 = view_bbox
    if inset_bbox[2] <= vx0 or inset_bbox[0] >= vx1 or inset_bbox[3] <= vy0 or inset_bbox[1] >= vy1:
        return
    scale_x = main_size[0] / float(max(1, vx1 - vx0))
    scale_y = main_size[1] / float(max(1, vy1 - vy0))
    box = (
        main_origin[0] + int(round((inset_bbox[0] - vx0) * scale_x)),
        main_origin[1] + int(round((inset_bbox[1] - vy0) * scale_y)),
        main_origin[0] + int(round((inset_bbox[2] - vx0) * scale_x)),
        main_origin[1] + int(round((inset_bbox[3] - vy0) * scale_y)),
    )
    draw.rectangle(box, outline=(255, 210, 48), width=4)


def _draw_scalebar(
    draw: ImageDraw.ImageDraw,
    main_origin: tuple[int, int],
    main_size: tuple[int, int],
    scalebar_um: float,
    mpp: float | None,
    output_scale: float,
    font: ImageFont.ImageFont,
) -> bool:
    if mpp is None or float(mpp) <= 0:
        raise ValueError("--scalebar-um requires slide mpp metadata or --mpp.")
    length_px = int(round(float(scalebar_um) / float(mpp) * float(output_scale)))
    length_px = max(8, min(length_px, int(main_size[0] * 0.6)))
    x1 = main_origin[0] + main_size[0] - 36
    x0 = x1 - length_px
    y = main_origin[1] + main_size[1] - 36
    label = f"{scalebar_um:g} um"
    bbox = draw.textbbox((0, 0), label, font=font)
    draw.rectangle((x0 - 8, y - 22, x1 + 8, y + 12), fill=(255, 255, 255), outline=(220, 224, 228))
    draw.line((x0, y, x1, y), fill=(15, 23, 31), width=5)
    draw.text((x0 + (length_px - (bbox[2] - bbox[0])) / 2, y - 20), label, fill=(15, 23, 31), font=font)
    return True


def _draw_border(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    size: tuple[int, int],
    color: tuple[int, int, int],
    width: int = 1,
) -> None:
    x0, y0 = origin
    draw.rectangle((x0, y0, x0 + size[0] - 1, y0 + size[1] - 1), outline=color, width=width)


def _draw_panel_label(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    label: str,
    font: ImageFont.ImageFont,
) -> None:
    x, y = origin
    bbox = draw.textbbox((0, 0), label, font=font)
    width = bbox[2] - bbox[0] + 22
    height = bbox[3] - bbox[1] + 16
    draw.rectangle((x + 12, y + 12, x + 12 + width, y + 12 + height), fill=(255, 255, 255), outline=(25, 44, 56))
    draw.text((x + 23, y + 19), label, fill=(15, 23, 31), font=font)


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
    if normalized in {"light", "paper"}:
        return 248, 250, 252
    if normalized.startswith("#") and len(normalized) == 7:
        return int(normalized[1:3], 16), int(normalized[3:5], 16), int(normalized[5:7], 16)
    raise ValueError("--background must be white, paper, or a #RRGGBB color.")


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()
