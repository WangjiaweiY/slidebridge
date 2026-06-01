# SlideBridge Core

[![CI](https://github.com/WangjiaweiY/slidebridge/actions/workflows/ci.yml/badge.svg)](https://github.com/WangjiaweiY/slidebridge/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

[English README](README.en.md)

SlideBridge Core 是一个面向计算病理和病理 AI 的轻量 WSI 检查、调试和可视化工具箱。

Debug whole-slide images like a developer.

![SlideBridge demo overlay](docs/assets/demo_overlay.png)

> 上图是 synthetic demo，不包含任何患者数据。

## 这是什么？

SlideBridge Core 帮助计算病理研究者和 AI 工程师完成常见调试任务：

- 检查 WSI metadata、尺寸、level、MPP、objective 和 reader。
- 导出缩略图。
- 在本地浏览器里查看 slide。
- 叠加 patch 坐标。
- 可视化模型 score / attention。
- 生成轻量 QC 报告。
- 根据坐标导出 patch 图像和 manifest。
- 加载、转换和可视化 annotation 文件。
- 根据 annotation 给 patch 打调试标签。
- 通过 SSH tunnel 浏览远端服务器上的 WSI。

当前版本：`0.2.9`

## 30 秒 Demo

```powershell
git clone https://github.com/WangjiaweiY/slidebridge.git
cd slidebridge
pip install -e .
slidebridge create-demo --out outputs\demo_slide.png
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 200 --with-scores
slidebridge render-overlay outputs\demo_slide.png --patches outputs\demo_coords.csv --out outputs\demo_overlay.png
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.csv --port 7860 --open-browser
```

## 重要声明

- 仅用于 research 和 algorithm development。
- 不用于临床诊断。
- 本项目不包含任何厂商私有 SDK。
- 本项目不包含任何厂商私有格式实现。
- 如需特定 reader，应在单独授权的私有插件中实现。
- 本项目不隶属于、不代表、不背书任何扫描仪厂商。

## 安装

### 从 GitHub 安装

```powershell
pip install git+https://github.com/WangjiaweiY/slidebridge.git
```

### 开发安装

```powershell
git clone https://github.com/WangjiaweiY/slidebridge.git
cd slidebridge
pip install -e .[dev]
```

### Windows 说明

```powershell
conda create -n slidebridge python=3.11 -y
conda activate slidebridge
pip install tiffslide openslide-python openslide-bin pillow numpy pandas `
  fastapi uvicorn typer rich jinja2 pytest h5py
pip install -e .
```

`openslide-bin` 可以在 Windows 上补齐 `openslide-python` 需要的 OpenSlide
运行时。即使 OpenSlide 不可用，SlideBridge 仍可通过 TiffSlide 或普通 image
reader 运行部分工作流。

## 常用命令

```powershell
slidebridge version
slidebridge env
slidebridge readers
```

```powershell
slidebridge inspect outputs\demo_slide.png
slidebridge thumbnail outputs\demo_slide.png --out outputs\demo_thumbnail.jpg
slidebridge doctor outputs\demo_slide.png --out outputs\demo_report.html
```

```powershell
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 100 --with-scores
slidebridge inspect-patches outputs\demo_coords.csv --slide outputs\demo_slide.png
slidebridge render-overlay outputs\demo_slide.png --patches outputs\demo_coords.csv --out outputs\demo_overlay.png
slidebridge export-patches outputs\demo_slide.png --patches outputs\demo_coords.csv --out outputs\patches --limit 20
```

```powershell
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.csv --port 7860 --open-browser
```

## 整图 Heatmap PNG/JPG

如果模型输出的是一整张 PNG/JPG 热图，可以直接作为 full-slide overlay 查看：

```powershell
slidebridge create-demo-heatmap --out outputs\demo_heatmap.png
slidebridge view outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --port 7860 --open-browser
slidebridge inspect-heatmap outputs\demo_heatmap.png --slide outputs\demo_slide.png
```

也可以用 `--heatmap` 自动识别图片热图：

```powershell
slidebridge render-overlay outputs\demo_slide.png --heatmap outputs\demo_heatmap.png --out outputs\demo_raster_heatmap.png
```

当前 raster heatmap 默认覆盖整张 slide，并拉伸到 level-0 全图坐标系。它只用于
model/debug visualization，不是诊断结果。

## Annotation Debugging

```powershell
slidebridge create-demo --out outputs\demo_slide.png
slidebridge create-demo-annotations --out outputs\demo_annotations.geojson
slidebridge inspect-annotations outputs\demo_annotations.geojson --slide outputs\demo_slide.png
slidebridge render-overlay outputs\demo_slide.png --annotations outputs\demo_annotations.geojson --out outputs\demo_annotation_overlay.png
slidebridge view outputs\demo_slide.png --annotations outputs\demo_annotations.geojson --port 7860 --open-browser
```

支持的公开 annotation 输入：

- QuPath GeoJSON
- ASAP XML
- SlideBridge JSON

这些 annotation 只用于 research/debugging，不是临床诊断结果。

## 通过 SSH 浏览服务器上的切片

切片文件保留在服务器上，SlideBridge 在服务器上读取切片，本地浏览器通过 SSH
tunnel 访问 viewer。

```powershell
slidebridge remote-view user@server:/data/slides/case.svs --remote-runner "conda run -n slidebridge slidebridge"
```

也可以传远端目录，在浏览器左侧选择要看的切片：

```powershell
slidebridge remote-view user@server:/data/slides --recursive --max-slides 500 --remote-runner "conda run -n slidebridge slidebridge"
```

带远端 patch 和 annotation：

```powershell
slidebridge remote-view user@server:/data/slides/case.svs `
  --patches /data/features/case_coords.h5 `
  --annotations /data/annotations/case.geojson `
  --remote-runner "conda run -n slidebridge slidebridge"
```

先用 `--dry-run` 检查 SSH tunnel 和远端命令：

```powershell
slidebridge remote-view user@server:/data/slides/case.svs --remote-runner "conda run -n slidebridge slidebridge" --dry-run
```

如果经常连接同一台服务器，可以先保存一个本地 profile，后续命令就不用反复输入 SSH 端口和
`--remote-runner`：

```powershell
slidebridge remote-profile add lab `
  --host server.example.org `
  --user user `
  --ssh-port 22 `
  --remote-runner "conda run -n slidebridge slidebridge" `
  --root /data/slides

slidebridge remote-view lab:case.svs
slidebridge remote-view lab:cohort-a/ --recursive
slidebridge remote-ls lab:
```

## Viewer 性能参数

Viewer 默认启用进程内 tile cache，并限制同时生成 tile 的数量，减少重复缩放和平移时的服务端压力：

```powershell
slidebridge view outputs\demo_slide.png --tile-cache-size 512 --tile-cache-mb 256 --tile-workers 4
slidebridge remote-view user@server:/data/slides/case.svs --tile-cache-size 512 --tile-cache-mb 256 --tile-workers 4
```

`--tile-cache-size 0` 可以关闭服务端 tile cache。Viewer 信息页会显示 cache entries、内存占用、hits、misses、evictions、生成 tile 数、缓存返回数、平均 tile 耗时和 p95 tile 耗时。

## 从 Annotation 给 Patch 打标签

```powershell
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 200 --with-scores
slidebridge label-patches outputs\demo_coords.csv --annotations outputs\demo_annotations.geojson --out outputs\demo_coords_labeled.csv
```

`label-patches` 是 debugging / weak-labeling helper，不是 gold-standard labeling 工作流。

## 工程记录

已知问题、修复方案和后续优化方向会持续记录在
[Issues and Improvements](docs/ISSUES_AND_IMPROVEMENTS.md)。

## 坐标约定

- `x` / `y` 是 level-0 pixel coordinate。
- patch `width` / `height` 默认也是 level-0 pixel size。
- annotation 坐标也使用 level-0 pixel coordinate。
- `read_region` 的 `x` / `y` 使用 level-0 坐标。
- viewer overlay 按 level-0 coordinate space 对齐。

## 插件机制

公开 core 只定义 reader interface 和 registry。私有 reader 应放在单独的私有包中，
并通过 `slidebridge.core.registry.register_reader` 注册。

SlideBridge Core 不包含任何私有 reader。

## Roadmap

v0.2.2:

- remote WSI viewing over SSH tunnel
- remote-check / remote-ls / remote-inspect / remote-view
- 本地和远端目录阅片模式

v0.2.3:

- PNG/JPG 整图 heatmap overlay
- `view` / `remote-view` / `render-overlay` 支持 `--raster-heatmap`
- viewer tile/API cache 加固

v0.2.4:

- 内存 LRU tile cache
- tile 生成并发限制
- viewer cache stats 诊断

v0.2.5:

- `--tile-cache-mb` 按内存大小限制 tile cache
- `/api/performance` tile 性能诊断
- read / resize / JPEG / total tile 生成耗时统计

v0.2.6:

- `remote-profile` 保存常用 SSH viewer 配置
- 支持 profile-relative 远端路径，减少重复命令参数

v0.2.7:

- canvas overlay rendering
- viewport culling for large patch / annotation overlays
- overlay draw count and canvas tooltip

v0.2.8:

- heatmap inspection command
- raster heatmap threshold / invert / colormap controls
- slide-aspect synthetic heatmap generation

v0.2.9:

- viewer-side score threshold and top-k patch filters
- annotation label filters
- click-to-inspect overlay details and zoom-to-item

v0.3:

- plugin template

## License

Apache-2.0
