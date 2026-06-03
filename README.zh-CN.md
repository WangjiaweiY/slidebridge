# SlideBridge Core

[![CI](https://github.com/WangjiaweiY/slidebridge/actions/workflows/ci.yml/badge.svg)](https://github.com/WangjiaweiY/slidebridge/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

[English README](README.en.md)

SlideBridge Core 是一个面向计算病理和病理 AI 的轻量 WSI 检查、调试和可视化工具箱。

Debug whole-slide images like a developer.

![SlideBridge demo overlay](docs/assets/demo_overlay.png)

> 上图是 synthetic demo，不包含任何患者数据。

当前版本：`0.2.15`

## 这是什么？

SlideBridge Core 帮助计算病理研究者和 AI 工程师完成常见调试任务：

- 检查 WSI metadata、尺寸、level、MPP、objective 和 reader。
- 导出缩略图和 QC 报告。
- 在本地浏览器中查看 slide。
- 叠加 patch 坐标、score/attention heatmap 和 annotation。
- 从 annotation 给 patch 生成调试标签。
- 导出 patch 图像和 manifest。
- 通过 SSH tunnel 浏览远端服务器上的 WSI。
- 生成静态 overlay 图和指定视野截图，便于报告和复现。

## 重要声明

- 仅用于 research 和 algorithm development。
- 不用于临床诊断。
- 本项目不包含任何厂商私有 SDK。
- 本项目不包含任何厂商私有格式实现。
- 特定 reader 应在单独授权的私有插件中实现。
- 本项目不隶属于、不代表、不背书任何扫描仪厂商。
- 示例图片、坐标和 annotation 均为 synthetic demo，不包含患者数据。

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

Windows 上如果需要 OpenSlide 运行时，可以安装：

```powershell
pip install tiffslide openslide-python openslide-bin pillow numpy pandas fastapi uvicorn typer rich jinja2 pytest h5py
```

如果 OpenSlide 不可用，SlideBridge 仍可通过 TiffSlide 或普通 image reader 运行部分工作流。

## 30 秒 Demo

```powershell
slidebridge create-demo --out outputs\demo_slide.png
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 200 --with-scores
slidebridge render-overlay outputs\demo_slide.png --patches outputs\demo_coords.csv --out outputs\demo_overlay.png
slidebridge render-view outputs\demo_slide.png --patches outputs\demo_coords.csv --center-x 2048 --center-y 1536 --window-width 1200 --window-height 900 --out outputs\demo_view.png
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.csv --port 7860 --open-browser
```

## 常用命令

```powershell
slidebridge version
slidebridge env
slidebridge readers

slidebridge inspect outputs\demo_slide.png
slidebridge thumbnail outputs\demo_slide.png --out outputs\demo_thumbnail.jpg
slidebridge doctor outputs\demo_slide.png --out outputs\demo_report.html --json-out outputs\demo_report.json

slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 200 --with-scores
slidebridge inspect-patches outputs\demo_coords.csv --slide outputs\demo_slide.png
slidebridge export-patches outputs\demo_slide.png --patches outputs\demo_coords.csv --out outputs\patches --limit 20
```

## Heatmap 调试

Patch score / attention:

```powershell
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.h5 --format h5 --count 200 --with-scores
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.h5 --port 7860 --open-browser
```

整图 PNG/JPG heatmap:

```powershell
slidebridge create-demo-heatmap --out outputs\demo_heatmap.png
slidebridge inspect-heatmap outputs\demo_heatmap.png --slide outputs\demo_slide.png
slidebridge view outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --port 7860 --open-browser
slidebridge render-overlay outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --out outputs\demo_raster_heatmap.png
```

这些 heatmap 只用于 model/debug visualization，不是诊断结果。

## 静态视野截图

`render-view` 可以在不打开浏览器的情况下，导出某个 level-0 中心点附近的固定视野，适合保存模型输出、annotation 和 patch 对齐结果。

```powershell
slidebridge render-view outputs\demo_slide.png `
  --patches outputs\demo_coords.csv `
  --raster-heatmap outputs\demo_heatmap.png `
  --center-x 2048 --center-y 1536 `
  --window-width 1200 --window-height 900 `
  --out outputs\demo_view.png
```

## Annotation Debugging

```powershell
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

## 从 Annotation 给 Patch 打标签

```powershell
slidebridge label-patches outputs\demo_coords.csv --annotations outputs\demo_annotations.geojson --out outputs\demo_coords_labeled.csv
```

`label-patches` 是 debugging / weak-labeling helper，不是 gold-standard labeling 工作流。

## 通过 SSH 浏览服务器上的切片

切片文件保留在服务器上，SlideBridge 在服务器上读取切片，本地浏览器通过 SSH tunnel 访问 viewer。

```powershell
slidebridge remote-view user@server:/data/slides/case.svs --remote-runner "conda run -n slidebridge slidebridge"
```

也可以传远端目录，在浏览器左侧选择切片：

```powershell
slidebridge remote-view user@server:/data/slides --recursive --max-slides 500 --remote-runner "conda run -n slidebridge slidebridge"
```

如果经常连接同一台服务器，可以保存本地 profile：

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

```powershell
slidebridge view outputs\demo_slide.png --tile-cache-size 512 --tile-cache-mb 256 --tile-workers 4
slidebridge remote-view user@server:/data/slides/case.svs --tile-cache-size 512 --tile-cache-mb 256 --tile-workers 4
```

`--tile-cache-size 0` 可以关闭服务端 tile cache。Viewer 信息页会显示 cache entries、内存占用、hits、misses、evictions、生成 tile 数、缓存返回数、平均 tile 耗时和 p95 tile 耗时。

## 坐标约定

- `x` / `y` 是 level-0 pixel coordinate。
- patch `width` / `height` 默认也是 level-0 pixel size。
- annotation 坐标也使用 level-0 pixel coordinate。
- `read_region` 的 `x` / `y` 使用 level-0 坐标。
- viewer overlay 按 level-0 coordinate space 对齐。

## 插件机制

公开 core 只定义 reader interface 和 registry。私有 reader 应放在单独的私有包中，并通过 `slidebridge.core.registry.register_reader` 注册。SlideBridge Core 不包含任何私有 reader。

## 文档

- [Remote WSI Viewing](docs/REMOTE_VIEWING.md)
- [Annotations](docs/ANNOTATIONS.md)
- [Heatmaps](docs/HEATMAPS.md)
- [Coordinates](docs/COORDINATES.md)
- [Viewer](docs/VIEWER.md)
- [Issues and Improvements](docs/ISSUES_AND_IMPROVEMENTS.md)

## Roadmap

v0.2.10:

- `render-view` 静态视野截图
- viewport-level patch / heatmap / annotation overlay 导出

v0.2.11:

- viewer 内复制当前视野的 `render-view` 命令
- viewer 内直接下载当前视野 PNG

v0.2.12:

- viewer URL 记录当前切片、视野、tab 和 overlay 过滤状态
- 刷新页面后恢复当前 viewer 状态
- viewer 内复制可复现的 viewer URL

v0.2.13:

- viewer 玻璃拟态视觉优化
- Playwright viewer 视觉/交互回归测试

v0.2.x:

- viewer 交互体验继续打磨
- heatmap / annotation 对齐诊断
- 更好的远端 viewer 生命周期管理

v0.3:

- plugin template

## License

Apache-2.0
