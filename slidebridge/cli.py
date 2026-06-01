from __future__ import annotations

import csv
import json
import platform
import random
import subprocess
import sys
import time
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
from slidebridge.remote.commands import build_find_command, build_remote_slidebridge_command, quote_remote_arg
from slidebridge.remote.diagnostics import REMOTE_INSTALL_HINT, RemoteCommandResult, run_ssh_command
from slidebridge.remote.spec import RemotePath, is_remote_spec, parse_remote_path
from slidebridge.remote.ssh import build_ssh_base_command, require_ssh_available
from slidebridge.remote.tunnel import build_tunnel_command, is_local_port_available, wait_for_http
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
    open_browser: bool = typer.Option(False, "--open-browser/--no-open-browser", help="Open the browser."),
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
    recursive: bool = typer.Option(False, "--recursive/--no-recursive", help="When PATH is a directory, include nested slide files."),
    max_slides: int = typer.Option(500, "--max-slides", help="Maximum slide files listed in directory viewer mode."),
    viewer_context: str = typer.Option("local", "--viewer-context", help="Viewer display context: local or remote."),
    viewer_remote_user: Optional[str] = typer.Option(None, "--viewer-remote-user", help="Remote SSH user shown in the viewer."),
    viewer_remote_host: Optional[str] = typer.Option(None, "--viewer-remote-host", help="Remote SSH host shown in the viewer."),
    viewer_remote_ssh_port: Optional[int] = typer.Option(None, "--viewer-remote-ssh-port", help="Remote SSH port shown in the viewer."),
    viewer_source: Optional[str] = typer.Option(None, "--viewer-source", help="Source path shown in the viewer session panel."),
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
            recursive=recursive,
            max_slides=max_slides,
            viewer_context=viewer_context,
            viewer_remote_user=viewer_remote_user,
            viewer_remote_host=viewer_remote_host,
            viewer_remote_ssh_port=viewer_remote_ssh_port,
            viewer_source=viewer_source,
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


@app.command("remote-check")
def remote_check(
    remote: str = typer.Argument(..., help="Remote host, user@host, or user@host:/server/path. Server-side paths are not uploaded."),
    ssh_port: Optional[int] = typer.Option(None, "--ssh-port", help="SSH port."),
    identity_file: Optional[Path] = typer.Option(None, "--identity-file", help="SSH identity file."),
    ssh_option: list[str] = typer.Option([], "--ssh-option", help="Extra SSH option, e.g. '-J bastion'. May be repeated."),
    remote_runner: str = typer.Option("slidebridge", "--remote-runner", help="Remote SlideBridge command."),
    remote_workdir: Optional[str] = typer.Option(None, "--remote-workdir", help="Optional remote working directory."),
    slide: Optional[str] = typer.Option(None, "--slide", help="Optional remote slide path when REMOTE has no path."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON summary."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print commands without connecting over SSH."),
) -> None:
    """Check remote SSH access, SlideBridge availability, readers, and optional slide inspection."""

    try:
        remote_path, slide_path = _remote_from_target(remote, slide=slide, ssh_port=ssh_port)
        checks = [
            ("version", ["version"]),
            ("env", ["env"]),
            ("readers", ["readers"]),
        ]
        if slide_path:
            checks.append(("inspect", ["inspect", slide_path]))
        commands = [
            (
                name,
                build_remote_slidebridge_command(remote_runner, args, remote_workdir=remote_workdir),
            )
            for name, args in checks
        ]
        ssh_commands = [
            (name, _ssh_command_for_remote(remote_path, command, ssh_port, identity_file, ssh_option))
            for name, command in commands
        ]
        if dry_run:
            _print_remote_dry_run(None, commands, ssh_commands)
            return
        require_ssh_available()
        results = []
        for name, ssh_command in ssh_commands:
            result = run_ssh_command(ssh_command, timeout=60)
            if not json_output:
                console.print(f"\n[bold]remote {name}[/bold]")
                _print_remote_result(result)
            results.append({"name": name, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if any(result["returncode"] != 0 for result in results) and not json_output:
            console.print(f"[yellow]{REMOTE_INSTALL_HINT}[/yellow]")
        if json_output:
            print(json.dumps({"target": remote_path.target, "slide": slide_path, "results": results}, ensure_ascii=False, indent=2))
    except Exception as exc:
        _fail(exc)


@app.command("remote-ls")
def remote_ls(
    remote_dir: str = typer.Argument(..., help="Remote directory as user@host:/server/path or host:/server/path. No files are downloaded."),
    ssh_port: Optional[int] = typer.Option(None, "--ssh-port", help="SSH port."),
    identity_file: Optional[Path] = typer.Option(None, "--identity-file", help="SSH identity file."),
    ssh_option: list[str] = typer.Option([], "--ssh-option", help="Extra SSH option, e.g. '-J bastion'. May be repeated."),
    remote_workdir: Optional[str] = typer.Option(None, "--remote-workdir", help="Optional remote working directory."),
    patterns: str = typer.Option("*.svs,*.tif,*.tiff,*.ndpi,*.mrxs,*.scn", "--patterns", help="Comma-separated find patterns."),
    max_depth: int = typer.Option(2, "--max-depth", help="find maxdepth on the remote Linux/POSIX server."),
    limit: int = typer.Option(100, "--limit", help="Maximum rows to print."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print command without connecting over SSH."),
) -> None:
    """List likely slide files on a remote Linux/POSIX server without reading them."""

    try:
        remote_path = parse_remote_path(remote_dir)
        remote_path = RemotePath(remote_path.user, remote_path.host, remote_path.path, ssh_port)
        find_command = build_find_command(remote_path.path, _split_csv(patterns), max_depth=max_depth, limit=limit)
        remote_command = f"cd {quote_remote_arg(remote_workdir)} && {find_command}" if remote_workdir else find_command
        ssh_command = _ssh_command_for_remote(remote_path, remote_command, ssh_port, identity_file, ssh_option)
        if dry_run:
            _print_remote_dry_run(None, [("find", remote_command)], [("find", ssh_command)])
            return
        require_ssh_available()
        result = run_ssh_command(ssh_command, timeout=120)
        if result.returncode != 0:
            _print_remote_result(result)
            raise RuntimeError("remote-ls failed. The remote server must provide a Linux/POSIX find command.")
        rows = _parse_remote_ls(result.stdout)
        if json_output:
            print(json.dumps({"target": remote_path.target, "remote_dir": remote_path.path, "files": rows}, ensure_ascii=False, indent=2))
        else:
            table = Table(title="Remote Slide Files")
            table.add_column("path")
            table.add_column("size")
            table.add_column("modified")
            for row in rows:
                table.add_row(row["path"], str(row["size"]), row["modified"])
            console.print(table)
    except Exception as exc:
        _fail(exc)


@app.command("remote-inspect")
def remote_inspect(
    remote_slide: str = typer.Argument(..., help="Remote slide as user@host:/server/path or host:/server/path. The slide remains remote."),
    ssh_port: Optional[int] = typer.Option(None, "--ssh-port", help="SSH port."),
    identity_file: Optional[Path] = typer.Option(None, "--identity-file", help="SSH identity file."),
    ssh_option: list[str] = typer.Option([], "--ssh-option", help="Extra SSH option, e.g. '-J bastion'. May be repeated."),
    remote_runner: str = typer.Option("slidebridge", "--remote-runner", help="Remote SlideBridge command."),
    remote_workdir: Optional[str] = typer.Option(None, "--remote-workdir", help="Optional remote working directory."),
    json_output: bool = typer.Option(False, "--json", help="Run remote inspect with --json and print raw JSON."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print command without connecting over SSH."),
) -> None:
    """Run slidebridge inspect on a remote server-side slide path over SSH."""

    try:
        remote_path = parse_remote_path(remote_slide)
        args = ["inspect", remote_path.path] + (["--json"] if json_output else [])
        remote_command = build_remote_slidebridge_command(remote_runner, args, remote_workdir=remote_workdir)
        ssh_command = _ssh_command_for_remote(remote_path, remote_command, ssh_port, identity_file, ssh_option)
        if dry_run:
            _print_remote_dry_run(None, [("inspect", remote_command)], [("inspect", ssh_command)])
            return
        require_ssh_available()
        result = run_ssh_command(ssh_command, timeout=120)
        if result.returncode != 0:
            _print_remote_result(result)
            console.print(f"[yellow]{REMOTE_INSTALL_HINT}[/yellow]")
            raise RuntimeError("remote-inspect failed")
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    except Exception as exc:
        _fail(exc)


@app.command("remote-view")
def remote_view(
    remote_slide: str = typer.Argument(..., help="Remote slide or directory as user@host:/server/path or host:/server/path. Files remain remote."),
    ssh_port: Optional[int] = typer.Option(None, "--ssh-port", help="SSH port."),
    identity_file: Optional[Path] = typer.Option(None, "--identity-file", help="SSH identity file."),
    ssh_option: list[str] = typer.Option([], "--ssh-option", help="Extra SSH option, e.g. '-J bastion'. May be repeated."),
    remote_runner: str = typer.Option("slidebridge", "--remote-runner", help="Remote SlideBridge command."),
    remote_workdir: Optional[str] = typer.Option(None, "--remote-workdir", help="Optional remote working directory."),
    local_host: str = typer.Option("127.0.0.1", "--local-host", help="Local tunnel bind host. Defaults to localhost."),
    local_port: int = typer.Option(7860, "--local-port", help="Local tunnel port."),
    remote_host: str = typer.Option("127.0.0.1", "--remote-host", help="Remote viewer bind host. Defaults to localhost."),
    remote_port: int = typer.Option(7860, "--remote-port", help="Remote viewer port."),
    open_browser: bool = typer.Option(True, "--open-browser/--no-open-browser", help="Open local browser after tunnel is ready."),
    wait_timeout: float = typer.Option(30.0, "--wait-timeout", help="Seconds to wait for the forwarded viewer."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print commands without connecting over SSH."),
    verbose: bool = typer.Option(False, "--verbose", help="Print extra command details."),
    patches: Optional[str] = typer.Option(None, "--patches", help="Remote patch coordinate path."),
    heatmap: Optional[str] = typer.Option(None, "--heatmap", help="Remote heatmap/score path."),
    annotations: Optional[str] = typer.Option(None, "--annotations", help="Remote annotation path."),
    annotation_format: Optional[str] = typer.Option(None, "--annotation-format", help="Annotation format override."),
    default_patch_size: int = typer.Option(256, "--default-patch-size", help="Default patch size for remote coordinate files."),
    heatmap_opacity: float = typer.Option(0.45, "--heatmap-opacity", min=0.0, max=1.0, help="Heatmap opacity."),
    annotation_opacity: float = typer.Option(0.35, "--annotation-opacity", min=0.0, max=1.0, help="Annotation opacity."),
    max_overlay_patches: int = typer.Option(50_000, "--max-overlay-patches", help="Maximum patch overlays returned by remote viewer."),
    max_annotations: int = typer.Option(10_000, "--max-annotations", help="Maximum annotations returned by remote viewer."),
    recursive: bool = typer.Option(False, "--recursive/--no-recursive", help="When REMOTE_SLIDE is a directory, include nested slide files."),
    max_slides: int = typer.Option(500, "--max-slides", help="Maximum slide files listed by the remote directory viewer."),
) -> None:
    """View a remote server-side WSI or slide directory through an SSH localhost tunnel."""

    try:
        remote_path = parse_remote_path(remote_slide)
        remote_command = build_remote_slidebridge_command(
            remote_runner,
            _remote_view_args(
                remote_path.path,
                remote_host,
                remote_port,
                patches=patches,
                heatmap=heatmap,
                annotations=annotations,
                annotation_format=annotation_format,
                default_patch_size=default_patch_size,
                heatmap_opacity=heatmap_opacity,
                annotation_opacity=annotation_opacity,
                max_overlay_patches=max_overlay_patches,
                max_annotations=max_annotations,
                recursive=recursive,
                max_slides=max_slides,
                viewer_context="remote",
                viewer_remote_user=remote_path.user,
                viewer_remote_host=remote_path.host,
                viewer_remote_ssh_port=ssh_port or remote_path.ssh_port,
                viewer_source=remote_path.path,
            ),
            remote_workdir=remote_workdir,
        )
        ssh_command = build_tunnel_command(
            remote_path,
            remote_command,
            local_host=local_host,
            local_port=local_port,
            remote_host=remote_host,
            remote_port=remote_port,
            ssh_port=ssh_port,
            identity_file=str(identity_file) if identity_file else None,
            ssh_options=ssh_option,
        )
        local_url = _local_url(local_host, local_port)
        _warn_if_public_bind(local_host, "local")
        _warn_if_public_bind(remote_host, "remote")
        if dry_run:
            _print_remote_dry_run(local_url, [("view", remote_command)], [("tunnel", ssh_command)])
            return
        require_ssh_available()
        if not is_local_port_available("127.0.0.1" if local_host == "0.0.0.0" else local_host, local_port):
            raise RuntimeError(f"Local port {local_port} is already in use. Choose another --local-port.")
        _ensure_remote_port_available(remote_path, remote_port, ssh_port, identity_file, ssh_option)
        if verbose:
            _print_remote_dry_run(local_url, [("view", remote_command)], [("tunnel", ssh_command)])
        console.print(f"Starting remote SlideBridge viewer through SSH: {local_url}")
        process = subprocess.Popen(ssh_command)
        try:
            if wait_for_http(f"{local_url}/api/info", timeout=wait_timeout):
                console.print(f"Remote viewer ready: {local_url}")
                if open_browser:
                    webbrowser.open(local_url)
            else:
                raise RuntimeError(f"Viewer did not become reachable at {local_url} within {wait_timeout} seconds.")
            returncode = process.wait()
            if returncode != 0:
                _cleanup_remote_viewer(remote_path, remote_port, ssh_port, identity_file, ssh_option)
        except KeyboardInterrupt:
            console.print("Stopping SSH tunnel...")
            _stop_process(process)
            _cleanup_remote_viewer(remote_path, remote_port, ssh_port, identity_file, ssh_option)
        except Exception:
            _stop_process(process)
            _cleanup_remote_viewer(remote_path, remote_port, ssh_port, identity_file, ssh_option)
            raise
    except Exception as exc:
        _fail(exc)


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


def _remote_from_target(remote: str, slide: Optional[str] = None, ssh_port: Optional[int] = None) -> tuple[RemotePath, str | None]:
    if is_remote_spec(remote):
        parsed = parse_remote_path(remote)
        return RemotePath(parsed.user, parsed.host, parsed.path, ssh_port), parsed.path
    text = str(remote or "").strip()
    if not text or "/" in text or "\\" in text:
        raise ValueError("REMOTE must be a host, user@host, or [user@]host:/server/path.")
    user = None
    host = text
    if "@" in text:
        user, host = text.split("@", 1)
    if not host:
        raise ValueError("Remote host is empty.")
    return RemotePath(user=user or None, host=host, path=slide or "", ssh_port=ssh_port), slide


def _ssh_command_for_remote(
    remote: RemotePath,
    remote_command: str,
    ssh_port: Optional[int],
    identity_file: Optional[Path],
    ssh_options: list[str],
) -> list[str]:
    command = build_ssh_base_command(
        remote.host,
        user=remote.user,
        port=ssh_port or remote.ssh_port,
        identity_file=identity_file,
        ssh_options=ssh_options,
    )
    command.append(remote_command)
    return command


def _remote_port_check_command(port: int) -> str:
    checked_port = int(port)
    return (
        "if command -v ss >/dev/null 2>&1; then "
        f"ss -ltn 'sport = :{checked_port}' 2>/dev/null | grep -q LISTEN; "
        "elif command -v netstat >/dev/null 2>&1; then "
        "netstat -ltn 2>/dev/null | awk '{print $4}' | "
        f"grep -Eq '(^|[.:]){checked_port}$'; "
        "else "
        "exit 2; "
        "fi"
    )


def _ensure_remote_port_available(
    remote: RemotePath,
    remote_port: int,
    ssh_port: Optional[int],
    identity_file: Optional[Path],
    ssh_options: list[str],
) -> None:
    command = _ssh_command_for_remote(
        remote,
        _remote_port_check_command(remote_port),
        ssh_port,
        identity_file,
        ssh_options,
    )
    result = run_ssh_command(command, timeout=15)
    if result.returncode == 0:
        raise RuntimeError(
            f"Remote port {int(remote_port)} on {remote.target} is already in use. "
            "A previous SlideBridge viewer may still be running. Stop it on the remote server "
            "or choose another --remote-port."
        )
    if result.returncode == 1:
        return
    if result.returncode == 2:
        console.print(
            "[yellow]Could not verify the remote port because neither ss nor netstat was found. "
            "Continuing with viewer startup.[/yellow]"
        )
        return
    _print_remote_result(result)
    raise RuntimeError("Remote port preflight check failed before starting the viewer.")


def _remote_port_is_listening(
    remote: RemotePath,
    remote_port: int,
    ssh_port: Optional[int],
    identity_file: Optional[Path],
    ssh_options: list[str],
) -> bool | None:
    command = _ssh_command_for_remote(
        remote,
        _remote_port_check_command(remote_port),
        ssh_port,
        identity_file,
        ssh_options,
    )
    result = run_ssh_command(command, timeout=15)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    return None


def _remote_view_cleanup_command(port: int) -> str:
    checked_port = int(port)
    return (
        "self=$$; "
        "user_name=$(id -un 2>/dev/null || whoami); "
        "pids=''; "
        "if command -v ss >/dev/null 2>&1; then "
        f"pids=$(ss -ltnp 'sport = :{checked_port}' 2>/dev/null | "
        "sed -n 's/.*pid=\\([0-9][0-9]*\\).*/\\1/p' | sort -u); "
        "fi; "
        "extra=$(ps -u \"$user_name\" -o pid=,args= 2>/dev/null | "
        f"awk -v port='--port {checked_port}' -v self=\"$self\" "
        "'$1 != self && index($0, port) && "
        "(index($0, \"slidebridge view\") || index($0, \"conda run\")) {print $1}'); "
        "pids=$(printf '%s\\n%s\\n' \"$pids\" \"$extra\" | awk 'NF && $1 != 1 {print $1}' | sort -u); "
        "if [ -n \"$pids\" ]; then "
        "kill $pids 2>/dev/null || true; "
        "sleep 1; "
        "kill -9 $pids 2>/dev/null || true; "
        "fi"
    )


def _cleanup_remote_viewer(
    remote: RemotePath,
    remote_port: int,
    ssh_port: Optional[int],
    identity_file: Optional[Path],
    ssh_options: list[str],
) -> None:
    console.print(f"Stopping remote SlideBridge viewer on port {int(remote_port)}...")
    command = _ssh_command_for_remote(
        remote,
        _remote_view_cleanup_command(remote_port),
        ssh_port,
        identity_file,
        ssh_options,
    )
    result = run_ssh_command(command, timeout=20)
    for _ in range(5):
        listening = _remote_port_is_listening(remote, remote_port, ssh_port, identity_file, ssh_options)
        if listening is False:
            console.print("Remote viewer stopped.")
            return
        if listening is None:
            break
        time.sleep(0.5)
    if result.returncode != 0:
        _print_remote_result(result)
    console.print(
        "[yellow]Remote cleanup could not confirm that the viewer stopped. If the remote port is still occupied, run "
        f"`pkill -f 'slidebridge view .*--port {int(remote_port)}'` on the remote server.[/yellow]"
    )


def _stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def _remote_view_args(
    remote_slide: str,
    remote_host: str,
    remote_port: int,
    patches: Optional[str] = None,
    heatmap: Optional[str] = None,
    annotations: Optional[str] = None,
    annotation_format: Optional[str] = None,
    default_patch_size: int = 256,
    heatmap_opacity: float = 0.45,
    annotation_opacity: float = 0.35,
    max_overlay_patches: int = 50_000,
    max_annotations: int = 10_000,
    recursive: bool = False,
    max_slides: int = 500,
    viewer_context: str = "local",
    viewer_remote_user: Optional[str] = None,
    viewer_remote_host: Optional[str] = None,
    viewer_remote_ssh_port: Optional[int] = None,
    viewer_source: Optional[str] = None,
) -> list[str]:
    args = [
        "view",
        remote_slide,
        "--host",
        remote_host,
        "--port",
        str(int(remote_port)),
        "--no-open-browser",
        "--default-patch-size",
        str(int(default_patch_size)),
        "--heatmap-opacity",
        str(float(heatmap_opacity)),
        "--annotation-opacity",
        str(float(annotation_opacity)),
        "--max-overlay-patches",
        str(int(max_overlay_patches)),
        "--max-annotations",
        str(int(max_annotations)),
        "--max-slides",
        str(int(max_slides)),
        "--viewer-context",
        viewer_context,
    ]
    if viewer_remote_user:
        args.extend(["--viewer-remote-user", viewer_remote_user])
    if viewer_remote_host:
        args.extend(["--viewer-remote-host", viewer_remote_host])
    if viewer_remote_ssh_port is not None:
        args.extend(["--viewer-remote-ssh-port", str(int(viewer_remote_ssh_port))])
    if viewer_source:
        args.extend(["--viewer-source", viewer_source])
    if recursive:
        args.append("--recursive")
    if patches:
        args.extend(["--patches", patches])
    if heatmap:
        args.extend(["--heatmap", heatmap])
    if annotations:
        args.extend(["--annotations", annotations])
    if annotation_format:
        args.extend(["--annotation-format", annotation_format])
    return args


def _print_remote_dry_run(
    local_url: Optional[str],
    remote_commands: list[tuple[str, str]],
    ssh_commands: list[tuple[str, list[str]]],
) -> None:
    if local_url:
        console.print("[bold]Local URL:[/bold]")
        console.print(local_url)
    console.print("[bold]Remote command:[/bold]")
    for name, command in remote_commands:
        console.print(f"{name}: {command}")
    console.print("[bold]SSH command:[/bold]")
    for name, command in ssh_commands:
        console.print(f"{name}: {_format_command(command)}")


def _print_remote_result(result: RemoteCommandResult) -> None:
    if result.stdout:
        console.print(result.stdout.rstrip())
    if result.stderr:
        console.print(f"[yellow]{result.stderr.rstrip()}[/yellow]")
    if result.returncode != 0:
        console.print(f"[red]Remote command exited with code {result.returncode}[/red]")


def _format_command(command: list[str]) -> str:
    return subprocess.list2cmdline([str(part) for part in command])


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _parse_remote_ls(output: str) -> list[dict[str, str | int]]:
    rows = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        try:
            size: str | int = int(parts[1])
        except ValueError:
            size = parts[1]
        rows.append({"path": parts[0], "size": size, "modified": parts[2]})
    return rows


def _warn_if_public_bind(host: str, side: str) -> None:
    if host == "0.0.0.0":
        console.print(
            f"[yellow]Binding {side} host to 0.0.0.0 may expose the viewer on your network. "
            "Use only in trusted environments.[/yellow]"
        )


def _local_url(local_host: str, local_port: int) -> str:
    browser_host = "127.0.0.1" if local_host == "0.0.0.0" else local_host
    return f"http://{browser_host}:{int(local_port)}"


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
