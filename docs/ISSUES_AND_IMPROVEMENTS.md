# Issues and Improvements

Last updated: 2026-06-01

This document tracks engineering issues found during local and remote
SlideBridge development, plus the current fix and the next improvement path.
It is intentionally written without real slide paths, server addresses,
patient data, proprietary SDK details, or private reader implementation notes.

SlideBridge Core remains a research and algorithm debugging tool. These notes
do not describe clinical diagnosis workflows.

## Current Issue Log

| Area | Symptom | Root Cause | Current Fix | Follow-Up |
| --- | --- | --- | --- | --- |
| Remote viewer lifecycle | After closing `remote-view`, the next run may report that the remote port is already in use. | `ssh` termination did not always stop the remote `slidebridge view` process when it was launched through a wrapper such as `conda run`. | Remote cleanup now checks the remote listening port with `ss`, extracts the listener PID, and also falls back to matching the `slidebridge view --port` command line. | Add a more explicit remote session supervisor or shutdown endpoint for cleaner lifecycle control. |
| Tile cache contamination | The viewer can show a mix of old and new slide tiles after restarting on the same localhost port. | Tile URLs were reused across viewer runs, and tile responses were cacheable for one hour. | Each viewer app now generates a per-run tile cache key. DZI and tile URLs include that key. HTML and DZI responses are `no-store`; stale tile keys return 404. | Add browser regression tests that switch slides and verify no stale tile reuse. |
| Overlay API cache | Heatmap or annotation overlays may not appear until a hard refresh. | Overlay JSON endpoints reused stable URLs such as `/api/patches?slide_id=0`. | API JSON responses now use `Cache-Control: no-store`, and frontend fetches include the per-run cache key plus `cache: "no-store"`. | Consider adding visible cache/session diagnostics in the viewer debug panel. |
| Sidebar scrolling | The slide library list could show a scrollbar but fail to scroll reliably. | Custom wheel handling and fragile height calculations conflicted with OpenSeadragon and flex layout behavior. | The sidebar now uses native flexbox scrolling with constrained panel height and no custom wheel interception. | Add Playwright-based layout tests for directory mode. |
| Sidebar layout shifts | Collapsing or switching panels could slightly resize the slide viewport. | Sidebar content height changes triggered viewer resize behavior at awkward times. | The sidebar uses tabbed panels and a controlled viewer resize/redraw path. | Keep viewer controls in fixed-size areas and avoid layout-dependent viewport changes. |
| Directory viewer context | It was unclear whether the viewer was showing a single slide or a remote directory library. | The viewer did not show enough session/source context. | The sidebar now displays local/remote mode, source type, SSH user/host/port when remote, root path, and selected slide path. | Add a compact breadcrumb for nested directory libraries. |
| OpenSeadragon asset loading | CDN loading can be slow or unavailable. | The first implementation depended on a public CDN. | A bundled local OpenSeadragon asset is used first, with CDN as fallback. | Keep bundled asset version documented and upgrade deliberately. |
| Magnification controls | Users needed visible magnification state and direct magnification jumps. | OpenSeadragon default buttons only expose generic zoom. | A custom magnification panel shows equivalent magnification and supports 1x/2x/5x/10x/20x/40x/Fit controls. | Improve calibration when objective power or MPP is missing. |
| Heatmap examples | Users may not have ready model attention files while testing the viewer. | Real model outputs vary by project and are often unavailable during UI testing. | Synthetic CSV/H5/NPY patch-score examples can be generated on a remote or local machine for visual debugging. Raster PNG/JPG heatmaps are also supported as full-slide overlays. | Add a first-class command for synthetic heatmap fixtures. |
| Tile request pressure | Fast zooming and panning can send many tile requests and repeatedly read/encode the same regions. | OpenSeadragon requests visible tiles aggressively, and the server previously regenerated repeated tile URLs. | The viewer now has an in-memory LRU tile cache, byte-aware cache limits, `/api/cache-stats`, `/api/performance`, and a tile generation concurrency limit. | Use the timing metrics to decide whether the next bottleneck is reading, resizing, JPEG encoding, network, or overlays. |
| Remote command length | Repeated remote viewing commands can become long and error-prone. | SSH port, remote runner, root path, and viewer ports were passed manually on every command. | `remote-profile` stores reusable local SSH viewer settings, and remote commands accept `--profile` plus profile-relative paths. | Add optional profile import/export once the profile format stabilizes. |
| Local shell noise | Some PowerShell sessions may print stale conda initialization errors. | The user shell profile may reference an old conda installation. | Development commands use the known Python executable or environment-specific `slidebridge.exe` directly. | Document shell-profile cleanup in Windows troubleshooting. |

## Improvement Backlog

### Viewer Robustness

- Add Playwright smoke tests for the viewer page, including:
  - initial tile load;
  - switching slides in directory mode;
  - patch overlay visibility;
  - annotation overlay visibility;
  - magnification control behavior.
- Add a small viewer debug panel showing:
  - current slide id;
  - tile cache key;
  - patch count loaded from API;
  - annotation count loaded from API;
  - selected DZI URL.

### Overlay Performance

- Replace large DOM patch overlays with a canvas overlay.
- Add spatial culling so only visible overlays are drawn at the current viewport.
- Keep DOM/SVG overlays for small annotation counts where hover and click behavior
  are useful.
- Add a configurable threshold where the viewer switches from DOM overlays to
  canvas rendering.

### Heatmap Interoperability

- Support raster heatmaps such as PNG/JPG in addition to patch-score tables.
- Require explicit coordinate metadata for raster heatmaps, for example:
  - full-slide level-0 size;
  - thumbnail/downsample factor;
  - origin and extent;
  - value normalization.
- Keep raster heatmaps as algorithm-debug visualization only.
- Do not infer clinical meaning from heatmap colors.

### Remote Viewing

- Add profile import/export for sharing non-sensitive template settings.
- Add a remote session id to startup logs and viewer metadata.
- Improve remote cleanup by starting the remote viewer in a process group when
  possible.
- Add clearer recovery commands when remote port cleanup fails.
- Keep the default bind address as `127.0.0.1` on both local and remote sides.

### Tile Performance

- Add timing metrics for reader level selection and downstream response transfer.
- Consider a lower default JPEG quality only after measuring visual impact.
- Keep correctness and predictable cache behavior ahead of aggressive caching.

### Annotation Validation

- Test QuPath GeoJSON and ASAP XML loaders against more synthetic fixtures.
- Add render-overlay regression fixtures for polygons, rectangles, points, and
  mixed annotation labels.
- Add warnings for annotation coordinate ranges that are far outside slide bounds.

## Maintenance Rule

When a new issue is discovered, add a row to the issue log with:

1. area;
2. symptom;
3. root cause;
4. current fix or workaround;
5. follow-up improvement.

If the issue involves real local paths, private infrastructure, or real patient
data, describe it generically before committing it to the public repository.
