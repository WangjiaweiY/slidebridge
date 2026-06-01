from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from PIL import Image, ImageStat

from slidebridge.server.app import create_app
from slidebridge.utils.demo import create_demo_slide

pytestmark = pytest.mark.skipif(
    os.environ.get("SLIDEBRIDGE_RUN_PLAYWRIGHT") != "1",
    reason="Playwright visual tests run only when explicitly enabled.",
)

playwright_sync = pytest.importorskip("playwright.sync_api")


def test_viewer_visual_smoke_and_sidebar_scroll(tmp_path):
    root = tmp_path / "slides"
    root.mkdir()
    for index in range(9):
        create_demo_slide(root / f"demo_{index:02d}.png", width=512, height=384, seed=300 + index)
    patches_path = tmp_path / "coords.csv"
    patches_path.write_text("x,y,width,height,score\n180,120,80,80,0.8\n", encoding="utf-8")
    server, thread, url = _start_viewer_server(root, patches_path=patches_path, recursive=True)

    try:
        with playwright_sync.sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 820}, device_scale_factor=1)
            page.goto(url, wait_until="domcontentloaded")
            _wait_for_viewer_ready(page)

            assert page.locator("#viewer-error").is_hidden()
            assert page.locator("#copy-viewer-url").is_visible()
            assert page.locator("#copy-render-command").is_visible()
            assert page.locator("#download-render-view").is_visible()
            assert page.locator(".zoom-control").is_visible()

            scrollable = page.eval_on_selector(
                "#slide-list",
                "(el) => el.scrollHeight > el.clientHeight",
            )
            assert scrollable is True
            page.locator("#slide-list").hover()
            page.mouse.wheel(0, 700)
            scrolled = page.eval_on_selector("#slide-list", "(el) => el.scrollTop")
            assert scrolled > 0

            screenshot = page.locator("#viewer").screenshot()
            assert _image_has_slide_content(screenshot, tmp_path / "viewer.png")
            browser.close()
    finally:
        _stop_viewer_server(server, thread)


def test_viewer_url_state_restores_panel_and_filters(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=401)
    patches_path = tmp_path / "coords.csv"
    patches_path.write_text("x,y,width,height,score\n180,120,80,80,0.8\n", encoding="utf-8")
    server, thread, url = _start_viewer_server(slide_path, patches_path=patches_path)

    try:
        state_url = (
            f"{url}?slide_id=0&center_x=256&center_y=192&window_width=256&window_height=192"
            "&tab=overlays-tab&overlay=1&score_threshold=0.50&top_k=5&opacity=0.55"
        )
        with playwright_sync.sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 820}, device_scale_factor=1)
            page.goto(state_url, wait_until="domcontentloaded")
            _wait_for_viewer_ready(page)

            assert "tab=overlays-tab" in page.url
            assert page.locator("#overlays-tab").evaluate("(el) => el.classList.contains('active')") is True
            assert page.locator("#score-threshold-value").inner_text() == "0.50"
            assert page.locator("#top-k-input").input_value() == "5"
            assert page.locator("#opacity-slider").input_value() in {"0.55", "0.55000000000000004"}
            browser.close()
    finally:
        _stop_viewer_server(server, thread)


def _start_viewer_server(source: Path, **kwargs):
    app = create_app(source, reader="image", tile_size=128, **kwargs)
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}/"
    deadline = time.time() + 15
    while time.time() < deadline:
        if server.started:
            return server, thread, url
        time.sleep(0.05)
    server.should_exit = True
    raise RuntimeError("Timed out waiting for viewer server to start.")


def _stop_viewer_server(server: uvicorn.Server, thread: threading.Thread) -> None:
    server.should_exit = True
    thread.join(timeout=10)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_viewer_ready(page) -> None:
    page.wait_for_selector("#viewer canvas", timeout=15000)
    page.wait_for_function(
        "() => document.querySelector('#viewer canvas') && "
        "document.querySelector('#snapshot-center') && "
        "document.querySelector('#snapshot-center').textContent !== 'unknown'",
        timeout=15000,
    )
    page.wait_for_timeout(800)


def _image_has_slide_content(screenshot: bytes, output_path: Path) -> bool:
    output_path.write_bytes(screenshot)
    with Image.open(output_path).convert("RGB") as image:
        stat = ImageStat.Stat(image)
        mean = sum(stat.mean) / 3
        extrema = image.getextrema()
        dynamic_range = max(channel[1] - channel[0] for channel in extrema)
    return mean > 35 and dynamic_range > 20
