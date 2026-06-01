# Remote WSI Viewing

SlideBridge can view remote WSIs by running the tile server on the remote
machine and forwarding it to the local browser over SSH.

```text
Local Windows browser
  -> http://127.0.0.1:7860
  -> SSH tunnel
  -> remote slidebridge view
  -> remote WSI file
```

## What Stays Remote

- The WSI stays on the remote server.
- SlideBridge does not automatically download the slide.
- The remote command reads the slide from the server local filesystem.
- The remote machine must already have SlideBridge installed.
- The workflow is for research/debugging only, not clinical diagnosis.

## Prerequisites

1. The local machine has an OpenSSH client.
2. The remote machine has an SSH server.
3. You can SSH into the remote server.
4. The remote machine has Python and SlideBridge installed.
5. Your remote account has read permission for the remote slide path.

## Install SlideBridge on the Remote Machine

```bash
pip install git+https://github.com/WangjiaweiY/slidebridge.git
```

If the remote machine uses conda:

```bash
conda create -n slidebridge python=3.11 -y
conda activate slidebridge
pip install git+https://github.com/WangjiaweiY/slidebridge.git
```

When `slidebridge` is not on the default non-interactive SSH `PATH`, pass a
runner explicitly:

```powershell
--remote-runner "conda run -n slidebridge slidebridge"
```

`--remote-runner` is trusted user input and is executed on the remote machine.
Do not paste commands from untrusted sources.

## Commands

Check remote environment:

```powershell
slidebridge remote-check user@server --remote-runner "conda run -n slidebridge slidebridge"
```

List likely slide files without reading them:

```powershell
slidebridge remote-ls user@server:/data/slides
```

Inspect a remote slide:

```powershell
slidebridge remote-inspect user@server:/data/slides/case.svs --remote-runner "conda run -n slidebridge slidebridge"
```

Start a remote viewer and open it locally:

```powershell
slidebridge remote-view user@server:/data/slides/case.svs --remote-runner "conda run -n slidebridge slidebridge" --local-port 7860 --remote-port 7860
```

For slower links or heavily loaded servers, tune the remote tile cache and tile
generation concurrency:

```powershell
slidebridge remote-view user@server:/data/slides/case.svs `
  --remote-runner "conda run -n slidebridge slidebridge" `
  --tile-cache-size 512 `
  --tile-workers 4
```

The tile cache stays on the remote process. SlideBridge still does not download
the slide to the local machine.

To browse a remote folder and select slides in the browser:

```powershell
slidebridge remote-view user@server:/data/slides --recursive --max-slides 500 --remote-runner "conda run -n slidebridge slidebridge"
```

With remote patch coordinates and annotations:

```powershell
slidebridge remote-view user@server:/data/slides/case.svs `
  --patches /data/features/case_coords.h5 `
  --annotations /data/annotations/case.geojson `
  --remote-runner "conda run -n slidebridge slidebridge"
```

With a remote full-slide raster heatmap:

```powershell
slidebridge remote-view user@server:/data/slides/case.svs `
  --raster-heatmap /data/model_outputs/case_heatmap.png `
  --remote-runner "conda run -n slidebridge slidebridge"
```

Preview commands without connecting:

```powershell
slidebridge remote-view user@server:/data/slides/case.svs --remote-runner "conda run -n slidebridge slidebridge" --dry-run
```

## Troubleshooting

- `ssh not found`: install or enable OpenSSH Client on Windows.
- `Permission denied`: confirm your SSH key, username, host, and `--ssh-port`.
- `remote slidebridge not found`: install SlideBridge remotely or pass `--remote-runner`.
- `remote port already in use`: choose another `--remote-port`.
- `local port already in use`: choose another `--local-port`.
- Empty slide library: add `--recursive` or check that the directory contains supported slide/image suffixes.
- Viewer opens but tiles fail: check the remote terminal output and slide read permissions.
- Remote server cannot read slide: confirm the server-side slide path and file permissions.
- `conda` not found in non-interactive shell: use an absolute runner or `conda run -n ...`.

## Security Notes

- The remote viewer binds to `127.0.0.1` by default.
- The local SSH tunnel binds to `127.0.0.1` by default.
- Do not use `0.0.0.0` unless you understand the network exposure risk.
- Do not share patient-identifiable URLs, screenshots, or paths in public issues.
- Do not upload proprietary SDKs, vendor binaries, private data, or patient data.
