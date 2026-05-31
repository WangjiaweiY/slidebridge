from __future__ import annotations

import csv
import json
import platform
import random
import sys
import webbrowser
from pathlib import Path
from typing import Optional

import numpy as np
import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from slidebridge import __version__
from slidebridge.annotations.demo import create_demo_annotations as create_synthetic_annotations
from slidebridge.annotations.io import load_annotation_table, save_annotation_table
from slidebridge.annotations.label_patches import label_patch_table, save_labeled_patches
from slidebridge.core.diagnostics import environment_report, reader_statuses
from slidebridge.core.metadata import summary
from slidebridge.core.registry import SlideOpenError, get_registered_readers, open_slide
from slidebridge.export.patches import export_patches as export_patch_images
from slidebridge.overlays.patches import load_patch_table
from slidebridge.qc.blur import blur_score
from slidebridge.qc.report import generate_html_report, generate_json_report
from slidebridge.qc.tissue import estimate_tissue_percent
from slidebridge.render.overlay import render_overlay
from slidebridge.server.app import create_app
from slidebridge.utils.demo import create_demo_slide
from slidebridge.utils.image import ensure_rgb, image_to_base64_jpeg
from slidebridge.utils.paths import ensure_parent, iter_slide_paths

app = typer.Typer(no_args_is_help=True, help="SlideBridge Core WSI inspection tools.")
console = Console()


@app.callback(invoke_without_command=True)
def main(
    version_flag: bool = typer.Option(
        False,
        "--version",
        help="Show SlideBridge Core version and exit.",
        is_eager=True,
    ),
) -> None:
    if version_flag:
        print(f"SlideBridge Core {__version__}")
        raise typer.Exit()


@app.command("version")
def version_command() -> None:
    """Show SlideBridge Core and Python runtime version information."""

    console.print(f"SlideBridge Core version: {__version__}")
    console.print(f"Python version: {sys.version.replace(chr(10), ' ')}")
    console.print(f"Platform: {platform.platform()}")
    console.print(f"Executable: {sys.executable}")


@app.command("env")
def env_command() -> None:
    """Show dependency and runtime diagnostics."""

    report = environment_report()
    console.print(f"Python executable: {report['python_executable']}")
    console.print(f"Python version: {report['python_version']}")
    console.print(f"Platform: {report['platform']}")
    console.print(f"Current working directory: {report['cwd']}")
    console.print(f"TiffSlide available: {'yes' if report['tiffslide_available'] else 'no'}")
    console.print(f"OpenSlide available: {'yes' if report['openslide_available'] else 'no'}")

    table = Table(title="Package Diagnostics")
    table.add_column("Package")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Notes")
    for package in report["packages"]:
        table.add_row(
            package["name"],
            str(package["version"] or "unknown"),
            package["status"],
            package["notes"],
        )
    console.print(table)


@app.command("readers")
def readers_command() -> None:
    """List registered readers and dependency availability."""

    statuses = reader_statuses()
    table = Table(title="Registered Readers")
    table.add_column("name")
    table.add_column("priority")
    table.add_column("available")
    table.add_column("notes")
    for reader in get_registered_readers():
        status = statuses.get(reader.name, {})
        table.add_row(
            reader.name,
            str(reader.priority),
            "yes" if status.get("available") else "no",
            str(status.get("notes") or "no diagnostics available"),
        )
    console.print(table)


@app.command()
def inspect(
    path: Path = typer.Argument(..., help="Path to a WSI or image."),
    reader: Optional[str] = typer.Option(None, "--reader", help="Specify a reader by name."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Show more properties."),
) -> None:
    slide = None
    try:
        slide = open_slide(path, reader=reader)
        info = summary(slide)
        if verbose:
            info["properties"] = slide.properties
        if json_output:
            print(json.dumps(info, ensure_ascii=False, indent=2))
            return
        _print_summary(info)
        if verbose and slide.properties:
            console.print("\n[bold]Properties[/bold]")
            console.print(json.dumps(slide.properties, ensure_ascii=False, indent=2))
    except Exception as exc:
        _fail(exc)
    finally:
        if slide is not None:
            slide.close()


@app.command()
def thumbnail(
    path: Path = typer.Argument(..., help="Path to a WSI or image."),
    out: Path = typer.Option(..., "--out", help="Output image path."),
    max_size: int = typer.Option(1024, "--max-size", help="Maximum thumbnail side length."),
    reader: Optional[str] = typer.Option(None, "--reader", help="Specify a reader by name."),
) -> None:
    slide = None
    try:
        slide = open_slide(path, reader=reader)
        image = ensure_rgb(slide.get_thumbnail(max_size=max_size))
        output = ensure_parent(out)
        image.save(output)
        console.print(f"Saved thumbnail: {output}")
    except Exception as exc:
        _fail(exc)
    finally:
        if slide is not None:
            slide.close()


@app.command()
def doctor(
    path_or_dir: Path = typer.Argument(..., help="Path to a WSI or directory."),
    out: Path = typer.Option(..., "--out", help="Output HTML report path."),
    json_out: Optional[Path] = typer.Option(None, "--json-out", help="Optional JSON report path."),
    recursive: bool = typer.Option(False, "--recursive", help="Search directories recursively."),
    workers: int = typer.Option(1, "--workers", help="Reserved for future parallel processing."),
    reader: Optional[str] = typer.Option(None, "--reader", help="Specify a reader by name."),
) -> None:
    del workers
    try:
        paths = iter_slide_paths(path_or_dir, recursive=recursive)
        if not paths:
            raise ValueError(f"No supported slide files found under: {path_or_dir}")
        results = [_doctor_one(path, reader=reader) for path in paths]
        output = generate_html_report(results, out)
        console.print(f"Saved QC report: {output}")
        if json_out is not None:
            json_output = generate_json_report(results, json_out)
            console.print(f"Saved QC JSON report: {json_output}")
    except Exception as exc:
        _fail(exc)


@app.command("sample-patches")
def sample_patches(
    path: Path = typer.Argument(..., help="Path to a WSI or image."),
    out: Path = typer.Option(..., "--out", help="Output coordinate path."),
    patch_size: int = typer.Option(512, "--patch-size", help="Patch width and height."),
    count: int = typer.Option(100, "--count", help="Number of patches."),
    seed: int = typer.Option(42, "--seed", help="Random seed."),
    reader: Optional[str] = typer.Option(None, "--reader", help="Specify a reader by name."),
    output_format: str = typer.Option("csv", "--format", help="Output format: csv, npy, h5, json."),
    with_scores: bool = typer.Option(True, "--with-scores/--no-scores", help="Include random scores."),
) -> None:
    slide = None
    try:
        slide = open_slide(path, reader=reader)
        width, height = slide.dimensions
        rng = random.Random(seed)
        output = ensure_parent(out)
        patch_w = max(1, min(int(patch_size), int(width)))
        patch_h = max(1, min(int(patch_size), int(height)))
        max_x = max(0, int(width) - patch_w)
        max_y = max(0, int(height) - patch_h)
        records = []
        for _ in range(max(0, int(count))):
            item = {
                "x": rng.randint(0, max_x) if max_x else 0,
                "y": rng.randint(0, max_y) if max_y else 0,
                "width": patch_w,
                "height": patch_h,
            }
            if with_scores:
                item["score"] = round(rng.random(), 3)
            records.append(item)
        _write_sample_patches(output, records, output_format.lower(), patch_size=patch_w, with_scores=with_scores)
        console.print(f"Saved patch coordinates: {output}")
    except Exception as exc:
        _fail(exc)
    finally:
        if slide is not None:
            slide.close()


@app.command("inspect-patches")
def inspect_patches(
    patches: Path = typer.Argument(..., help="Patch coordinate file."),
    slide_path: Optional[Path] = typer.Option(None, "--slide", help="Optional slide for bounds validation."),
    default_patch_size: int = typer.Option(256, "--default-patch-size", help="Default patch size."),
    reader: Optional[str] = typer.Option(None, "--reader", help="Specify a slide reader by name."),
) -> None:
    slide = None
    try:
        table = load_patch_table(patches, default_patch_size=default_patch_size)
        if slide_path is not None:
            slide = open_slide(slide_path, reader=reader)
            table = table.validate(slide.dimensions[0], slide.dimensions[1], mode="warn")
        _print_patch_summary(table.summary())
    except Exception as exc:
        _fail(exc)
    finally:
        if slide is not None:
            slide.close()


@app.command("create-demo")
def create_demo(
    out: Path = typer.Option(Path("outputs/demo_slide.png"), "--out", help="Output PNG path."),
    width: int = typer.Option(4096, "--width", help="Image width in pixels."),
    height: int = typer.Option(3072, "--height", help="Image height in pixels."),
    seed: int = typer.Option(42, "--seed", help="Random seed."),
) -> None:
    """Create a synthetic H&E-like demo image."""

    try:
        output = create_demo_slide(out, width=width, height=height, seed=seed)
        console.print(f"Saved demo slide: {output}")
    except Exception as exc:
        _fail(exc)


@app.command("create-demo-annotations")
def create_demo_annotations_command(
    out: Path = typer.Option(Path("outputs/demo_annotations.geojson"), "--out", help="Output annotation path."),
    width: int = typer.Option(4096, "--width", help="Coordinate-space width."),
    height: int = typer.Option(3072, "--height", help="Coordinate-space height."),
    seed: int = typer.Option(42, "--seed", help="Random seed."),
    output_format: str = typer.Option("geojson", "--format", help="Output format: geojson, slidebridge-json, asap-xml."),
    count: int = typer.Option(6, "--count", help="Number of synthetic annotations."),
    labels: str = typer.Option("Tumor,Stroma,Necrosis", "--labels", help="Comma-separated synthetic labels."),
) -> None:
    """Create synthetic annotation files for demos and tests."""

    try:
        output = create_synthetic_annotations(
            out,
            width=width,
            height=height,
            seed=seed,
            count=count,
            labels=_split_labels(labels),
            output_format=output_format.lower(),
        )
        console.print(f"Saved demo annotations: {output}")
    except Exception as exc:
        _fail(exc)


@app.command("inspect-annotations")
def inspect_annotations(
    annotations: Path = typer.Argument(..., help="Annotation file."),
    annotation_format: Optional[str] = typer.Option(None, "--format", help="Annotation format override."),
    slide_path: Optional[Path] = typer.Option(None, "--slide", help="Optional slide for bounds validation."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    labels_only: bool = typer.Option(False, "--labels", help="Only list labels."),
    verbose: bool = typer.Option(False, "--verbose", help="Include examples in console output."),
    max_examples: int = typer.Option(5, "--max-examples", help="Maximum example records to display."),
    reader: Optional[str] = typer.Option(None, "--reader", help="Specify a slide reader by name."),
) -> None:
    """Inspect an annotation file and optional slide alignment."""

    slide = None
    try:
        table = load_annotation_table(annotations, format=annotation_format).compute_bboxes().normalize_colors()
        slide_dimensions = None
        if slide_path is not None:
            slide = open_slide(slide_path, reader=reader)
            slide_dimensions = slide.dimensions
            table = table.validate(slide.dimensions[0], slide.dimensions[1], mode="warn")
        info = table.summary()
        if slide_dimensions is not None:
            info["slide_dimensions"] = list(slide_dimensions)
        if labels_only:
            if json_output:
                print(json.dumps({"labels": table.labels()}, ensure_ascii=False, indent=2))
            else:
                for label in table.labels():
                    console.print(label)
            return
        if json_output:
            payload = dict(info)
            payload["examples"] = table.to_list()[: max(0, int(max_examples))]
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        _print_annotation_summary(info)
        if verbose:
            console.print(json.dumps(table.to_list()[: max(0, int(max_examples))], ensure_ascii=False, indent=2))
    except Exception as exc:
        _fail(exc)
    finally:
        if slide is not None:
            slide.close()


@app.command("convert-annotations")
def convert_annotations(
    input_path: Path = typer.Argument(..., help="Input annotation file."),
    out: Path = typer.Option(..., "--out", help="Output annotation file."),
    input_format: Optional[str] = typer.Option(None, "--input-format", help="Input format override."),
    output_format: Optional[str] = typer.Option(None, "--output-format", help="slidebridge-json or geojson."),
    labels: Optional[str] = typer.Option(None, "--labels", help="Comma-separated labels to export."),
    pretty: bool = typer.Option(True, "--pretty/--compact", help="Pretty-print JSON output."),
) -> None:
    """Convert public annotation formats to SlideBridge JSON or GeoJSON."""

    try:
        table = load_annotation_table(input_path, format=input_format)
        if labels:
            table = table.filter_labels(_split_labels(labels))
        output = save_annotation_table(table, out, format=output_format, pretty=pretty)
        console.print(f"Saved converted annotations: {output}")
    except Exception as exc:
        _fail(exc)


@app.command()
def view(
    path: Path = typer.Argument(..., help="Path to a WSI or image."),
    patches: Optional[Path] = typer.Option(None, "--patches", help="Patch coordinate CSV."),
    host: str = typer.Option("127.0.0.1", "--host", help="Server host."),
    port: int = typer.Option(7860, "--port", help="Server port."),
    open_browser: bool = typer.Option(False, "--open-browser", help="Open the browser."),
    reader: Optional[str] = typer.Option(None, "--reader", help="Specify a reader by name."),
    tile_size: int = typer.Option(256, "--tile-size", min=64, max=1024, help="Deep Zoom tile size."),
    jpeg_quality: int = typer.Option(85, "--jpeg-quality", min=1, max=100, help="JPEG tile quality."),
    heatmap: Optional[Path] = typer.Option(None, "--heatmap", help="Optional score/attention file."),
    default_patch_size: int = typer.Option(256, "--default-patch-size", help="Default patch size for coordinate files."),
    heatmap_opacity: float = typer.Option(0.45, "--heatmap-opacity", min=0.0, max=1.0, help="Heatmap opacity."),
    score_normalization: str = typer.Option("minmax", "--score-normalization", help="minmax, percentile, or none."),
    max_overlay_patches: int = typer.Option(50_000, "--max-overlay-patches", help="Maximum overlays returned to the browser."),
    annotations: Optional[Path] = typer.Option(None, "--annotations", help="Optional annotation file."),
    annotation_format: Optional[str] = typer.Option(None, "--annotation-format", help="Annotation format override."),
    annotation_opacity: float = typer.Option(0.35, "--annotation-opacity", min=0.0, max=1.0, help="Annotation overlay opacity."),
    max_annotations: int = typer.Option(10_000, "--max-annotations", help="Maximum annotations returned to the browser."),
    annotation_labels: Optional[str] = typer.Option(None, "--annotation-labels", help="Comma-separated annotation label filter."),
) -> None:
    try:
        viewer_app = create_app(
            path,
            patches_path=patches,
            reader=reader,
            tile_size=tile_size,
            jpeg_quality=jpeg_quality,
            heatmap_path=heatmap,
            default_patch_size=default_patch_size,
            heatmap_opacity=heatmap_opacity,
            score_normalization=score_normalization,
            max_overlay_patches=max_overlay_patches,
            annotations_path=annotations,
            annotation_format=annotation_format,
            annotation_opacity=annotation_opacity,
            max_annotations=max_annotations,
            annotation_labels=_split_labels(annotation_labels),
        )
        url = f"http://{host}:{port}"
        console.print(f"Starting SlideBridge viewer: {url}")
        if open_browser:
            webbrowser.open(url)
        uvicorn.run(viewer_app, host=host, port=port)
    except Exception as exc:
        _fail(exc)


@app.command("export-patches")
def export_patches_command(
    slide_path: Path = typer.Argument(..., help="Path to a WSI or image."),
    patches: Path = typer.Option(..., "--patches", help="Patch coordinate file."),
    out: Path = typer.Option(..., "--out", help="Output directory."),
    reader: Optional[str] = typer.Option(None, "--reader", help="Specify a reader by name."),
    default_patch_size: int = typer.Option(256, "--default-patch-size", help="Default patch size."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum patches to export."),
    image_format: str = typer.Option("jpg", "--format", help="Output image format: jpg or png."),
    jpeg_quality: int = typer.Option(90, "--jpeg-quality", min=1, max=100, help="JPEG quality."),
    prefix: str = typer.Option("patch", "--prefix", help="Output filename prefix."),
    overwrite: bool = typer.Option(False, "--overwrite/--skip-existing", help="Overwrite existing patch images."),
    manifest: str = typer.Option("manifest.csv", "--manifest", help="Reserved manifest filename option."),
    workers: int = typer.Option(1, "--workers", help="Reserved for future parallel processing."),
) -> None:
    del workers
    slide = None
    try:
        slide = open_slide(slide_path, reader=reader)
        table = load_patch_table(patches, default_patch_size=default_patch_size)
        result = export_patch_images(
            slide,
            table,
            out,
            image_format=image_format,
            jpeg_quality=jpeg_quality,
            limit=limit,
            prefix=prefix,
            overwrite=overwrite,
            manifest_filename=manifest,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        _fail(exc)
    finally:
        if slide is not None:
            slide.close()


@app.command("label-patches")
def label_patches_command(
    patches: Path = typer.Argument(..., help="Patch coordinate file."),
    annotations: Path = typer.Option(..., "--annotations", help="Annotation file."),
    out: Path = typer.Option(..., "--out", help="Output labeled coordinate file."),
    slide_path: Optional[Path] = typer.Option(None, "--slide", help="Optional slide for patch bounds validation."),
    annotation_format: Optional[str] = typer.Option(None, "--annotation-format", help="Annotation format override."),
    default_patch_size: int = typer.Option(256, "--default-patch-size", help="Default patch size."),
    method: str = typer.Option("center", "--method", help="center or bbox."),
    labels: Optional[str] = typer.Option(None, "--labels", help="Comma-separated annotation labels to consider."),
    background_label: str = typer.Option("background", "--background-label", help="Label for unmatched patches."),
    multi_label: bool = typer.Option(False, "--multi-label/--single-label", help="Allow multiple matched labels."),
    output_format: Optional[str] = typer.Option(None, "--output-format", help="csv, json, or h5. Defaults to output suffix."),
    include_score: bool = typer.Option(True, "--include-score/--no-include-score", help="Include patch score in output."),
    reader: Optional[str] = typer.Option(None, "--reader", help="Specify a slide reader by name."),
) -> None:
    """Assign annotation-derived labels to patch coordinates for debugging."""

    slide = None
    try:
        table = load_patch_table(patches, default_patch_size=default_patch_size)
        if slide_path is not None:
            slide = open_slide(slide_path, reader=reader)
            table = table.validate(slide.dimensions[0], slide.dimensions[1], mode="clip")
        annotation_table = load_annotation_table(annotations, format=annotation_format)
        if labels:
            annotation_table = annotation_table.filter_labels(_split_labels(labels))
        labeled, info = label_patch_table(
            table,
            annotation_table,
            method=method.lower(),  # type: ignore[arg-type]
            background_label=background_label,
            multi_label=multi_label,
        )
        output = save_labeled_patches(labeled, out, output_format=output_format, include_score=include_score)
        info["output"] = str(output)
        print(json.dumps(info, ensure_ascii=False, indent=2))
    except Exception as exc:
        _fail(exc)
    finally:
        if slide is not None:
            slide.close()


@app.command("render-overlay")
def render_overlay_command(
    slide_path: Path = typer.Argument(..., help="Path to a WSI or image."),
    patches: Optional[Path] = typer.Option(None, "--patches", help="Patch coordinate file."),
    out: Path = typer.Option(..., "--out", help="Output PNG/JPG path."),
    heatmap: Optional[Path] = typer.Option(None, "--heatmap", help="Optional score/attention file."),
    reader: Optional[str] = typer.Option(None, "--reader", help="Specify a reader by name."),
    default_patch_size: int = typer.Option(256, "--default-patch-size", help="Default patch size."),
    max_size: int = typer.Option(1600, "--max-size", help="Maximum rendered image side length."),
    opacity: float = typer.Option(0.45, "--opacity", min=0.0, max=1.0, help="Overlay opacity."),
    score_normalization: str = typer.Option("minmax", "--score-normalization", help="minmax, percentile, or none."),
    show_labels: bool = typer.Option(False, "--show-labels/--no-labels", help="Draw patch labels or indices."),
    image_format: Optional[str] = typer.Option(None, "--format", help="Output format: png or jpg. Defaults to output suffix."),
    annotations: Optional[Path] = typer.Option(None, "--annotations", help="Optional annotation file."),
    annotation_format: Optional[str] = typer.Option(None, "--annotation-format", help="Annotation format override."),
    annotation_opacity: float = typer.Option(0.35, "--annotation-opacity", min=0.0, max=1.0, help="Annotation opacity."),
    annotation_labels: Optional[str] = typer.Option(None, "--annotation-labels", help="Comma-separated annotation label filter."),
    draw_annotation_labels: bool = typer.Option(False, "--draw-annotation-labels/--no-draw-annotation-labels", help="Draw annotation labels."),
) -> None:
    slide = None
    try:
        if score_normalization not in {"minmax", "percentile", "none"}:
            raise ValueError("--score-normalization must be one of: minmax, percentile, none")
        if patches is None and annotations is None:
            raise ValueError("render-overlay requires --patches, --annotations, or both")
        slide = open_slide(slide_path, reader=reader)
        table = None
        if patches is not None:
            table = load_patch_table(patches, default_patch_size=default_patch_size, score_path=heatmap)
            table = table.validate(slide.dimensions[0], slide.dimensions[1], mode="clip")
        elif heatmap is not None:
            raise ValueError("--heatmap requires --patches")
        if table is not None and score_normalization != "none":
            table = table.normalize_scores(score_normalization)  # type: ignore[arg-type]
        annotation_table = None
        if annotations is not None:
            annotation_table = load_annotation_table(annotations, format=annotation_format).compute_bboxes().normalize_colors()
            if annotation_labels:
                annotation_table = annotation_table.filter_labels(_split_labels(annotation_labels))
            annotation_table = annotation_table.validate(slide.dimensions[0], slide.dimensions[1], mode="warn")
        result = render_overlay(
            slide,
            table,
            out,
            annotation_table=annotation_table,
            max_size=max_size,
            opacity=opacity,
            show_labels=show_labels,
            annotation_opacity=annotation_opacity,
            draw_annotation_labels=draw_annotation_labels,
            image_format=image_format,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        _fail(exc)
    finally:
        if slide is not None:
            slide.close()


def _doctor_one(path: Path, reader: Optional[str] = None) -> dict:
    slide = None
    try:
        slide = open_slide(path, reader=reader)
        info = summary(slide)
        thumbnail_image = slide.get_thumbnail(max_size=512)
        info["thumbnail_b64"] = image_to_base64_jpeg(thumbnail_image)
        info["tissue_percent"] = estimate_tissue_percent(thumbnail_image)
        info["blur_score"] = blur_score(thumbnail_image)
        return info
    except Exception as exc:
        return {
            "path": str(path),
            "filename": path.name,
            "error": str(exc),
        }
    finally:
        if slide is not None:
            slide.close()


def _print_summary(info: dict) -> None:
    table = Table(title="SlideBridge Inspect")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("path", str(info["path"]))
    table.add_row("reader", str(info["reader"]))
    table.add_row("dimensions", f"{info['width']} x {info['height']}")
    table.add_row("level_count", str(info["level_count"]))
    table.add_row("level_dimensions", json.dumps(info["level_dimensions"]))
    table.add_row("level_downsamples", json.dumps(info["level_downsamples"]))
    table.add_row("mpp", f"{info['mpp_x']} x {info['mpp_y']}")
    table.add_row("objective_power", str(info["objective_power"]))
    table.add_row("vendor", str(info["vendor"]))
    table.add_row("warnings", ", ".join(info["warnings"]) if info["warnings"] else "none")
    console.print(table)


def _print_patch_summary(info: dict) -> None:
    table = Table(title="PatchTable Inspect")
    table.add_column("Field")
    table.add_column("Value")
    for key in [
        "count",
        "source",
        "coordinate_space",
        "default_patch_size",
        "x_min",
        "x_max",
        "y_min",
        "y_max",
        "width_min",
        "width_max",
        "height_min",
        "height_max",
        "has_scores",
        "score_min",
        "score_max",
        "score_mean",
        "warnings",
    ]:
        if key in info:
            value = info[key]
            table.add_row(key, json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value))
    console.print(table)


def _print_annotation_summary(info: dict) -> None:
    table = Table(title="AnnotationTable Inspect")
    table.add_column("Field")
    table.add_column("Value")
    for key in [
        "count",
        "source",
        "source_format",
        "coordinate_space",
        "type_counts",
        "label_counts",
        "labels",
        "global_bbox",
        "colors_present",
        "slide_dimensions",
        "warnings",
    ]:
        if key in info:
            value = info[key]
            table.add_row(key, json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value))
    console.print(table)


def _split_labels(labels: Optional[str]) -> list[str]:
    if not labels:
        return []
    return [item.strip() for item in labels.split(",") if item.strip()]


def _write_sample_patches(
    output: Path,
    records: list[dict[str, float | int]],
    output_format: str,
    patch_size: int,
    with_scores: bool,
) -> None:
    if output_format not in {"csv", "npy", "h5", "json"}:
        raise ValueError("--format must be one of: csv, npy, h5, json")
    if output_format == "csv":
        fieldnames = ["x", "y", "width", "height"] + (["score"] if with_scores else [])
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        return
    if output_format == "json":
        output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    coords = np.array([[item["x"], item["y"], item["width"], item["height"]] for item in records], dtype=np.float32)
    if output_format == "npy":
        if with_scores:
            scores = np.array([[item.get("score", 0.0)] for item in records], dtype=np.float32)
            coords = np.concatenate([coords, scores], axis=1)
        np.save(output, coords)
        return
    try:
        import h5py
    except Exception as exc:
        raise RuntimeError("Writing H5 patch files requires h5py. Please install h5py.") from exc
    with h5py.File(output, "w") as handle:
        handle.create_dataset("coords", data=coords.astype(np.int64))
        if with_scores:
            handle.create_dataset("scores", data=np.array([item.get("score", 0.0) for item in records], dtype=np.float32))
        handle.attrs["patch_size"] = int(patch_size)


def _fail(exc: Exception) -> None:
    message = str(exc)
    if isinstance(exc, SlideOpenError):
        message = str(exc)
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
