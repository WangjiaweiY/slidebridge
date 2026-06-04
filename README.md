# SlideBridge Core

[![CI](https://github.com/WangjiaweiY/slidebridge/actions/workflows/ci.yml/badge.svg)](https://github.com/WangjiaweiY/slidebridge/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

[English README](README.en.md)

SlideBridge Core 是一个面向计算病理 / 病理 AI 的 WSI inspection、model-output debugging 和论文图生成工具箱。

Debug whole-slide images like a developer.

![SlideBridge remote WSI heatmap viewer](docs/assets/readme_remote_heatmap_viewer.png)

> 在本地浏览器查看远端 WSI，并叠加模型 heatmap、patch 和 annotation 调试结果。

当前版本：`0.3.0`

## 这是什么？

SlideBridge Core 让计算病理研究者和 AI 工程师可以在同一个轻量工具里完成 WSI inspection、远端切片浏览、模型输出检查、annotation/patch debugging 和论文图导出。它的重点不是临床诊断，而是把算法调试过程中最常见的“看图、对齐、定位、复现、导出”做得足够直接。

## 核心亮点

### 1. 本地直接看远端切片

v0.3.0 新增 `slidebridge app` 网页启动器，可以在浏览器里填写 SSH、选择远端切片、选择 heatmap/patch/annotation，然后启动 viewer。底层仍然使用 `remote-view`：远端服务器读取 WSI，本地通过 SSH tunnel 打开浏览器 viewer。切片不需要复制到本地，适合在工作站或服务器上调试大规模 cohort、TCGA/CPTAC/internal research slides 等场景。它使用本机 `ssh` 客户端连接远端：推荐 SSH key；如果服务器允许密码登录，也可以在终端按 SSH 提示输入密码。

![SlideBridge remote viewer info panel](docs/assets/readme_remote_info_panel.png)

```cmd
slidebridge app
```

```cmd
slidebridge remote-view user@server:/data/slides/case.svs --remote-runner "conda run -n slidebridge slidebridge"
```

也可以传远端目录，在本地浏览器左侧选择切片：

```cmd
slidebridge remote-view user@server:/data/slides --recursive --max-slides 500 --remote-runner "conda run -n slidebridge slidebridge"
```

### 2. 热图 / attention 调试

支持 patch score/attention，也支持整图 PNG/JPG raster heatmap。Viewer 内可以切换多层 heatmap、调节透明度、设置 threshold，并和 WSI level-0 坐标对齐。

```cmd
slidebridge view outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --open-browser
```

```cmd
slidebridge view outputs\demo_slide.png --raster-heatmap-layer low=outputs\heatmap_low.png --raster-heatmap-layer high=outputs\heatmap_high.png --open-browser
```

### 3. Patch / annotation debugging

Viewer 可以叠加 patch 坐标、score threshold、top-k patch、annotation labels，并支持 QuPath GeoJSON、ASAP XML 和 SlideBridge JSON。常见用途是检查 patch/attention/annotation 是否和 WSI 坐标系统对齐。

```cmd
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.csv --annotations outputs\demo_annotations.geojson --open-browser
```

### 4. 论文/汇报图设计与导出

Figure Designer 让用户在网页里设计 `main + patch panels` 论文图布局；导出时不使用浏览器截图，而是由后端按 level-0 坐标重新渲染高分辨率 PNG，便于复现。

![SlideBridge figure designer](docs/assets/readme_figure_designer.png)

## 重要声明

- 仅用于 research 和 algorithm development。
- 不用于临床诊断。
- 本项目不包含任何厂商私有 SDK。
- 本项目不包含任何厂商私有格式实现。
- 特定 reader 应在单独授权的私有插件中实现。
- 本项目不隶属于、不代表、不背书任何扫描仪厂商。

## 安装与命令调用

### 从 GitHub 安装

```powershell
pip install git+https://github.com/WangjiaweiY/slidebridge.git
```

安装后先确认命令可用：

```cmd
slidebridge version
```

如果当前终端找不到 `slidebridge`，请改用 Python module 形式。README 里后续所有 `slidebridge ...` 命令都可以这样替换：

```cmd
python -m slidebridge.cli version
python -m slidebridge.cli view outputs\demo_slide.png --open-browser
```

在 Windows / Anaconda 环境里，也可以直接使用环境里的 Python：

```cmd
%CONDA_PREFIX%\python.exe -m slidebridge.cli version
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

### Windows 终端注意事项

PowerShell 的多行续行符是反引号 `` ` ``：

```powershell
slidebridge view outputs\demo_slide.png `
  --raster-heatmap outputs\demo_heatmap.png `
  --open-browser
```

Anaconda Prompt / cmd 不能使用 PowerShell 的反引号。建议在 Anaconda Prompt 里使用单行命令：

```cmd
slidebridge view outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --open-browser
```

如果 `slidebridge` 命令不可用，把前缀替换成 `python -m slidebridge.cli`：

```cmd
python -m slidebridge.cli view outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --open-browser
```

## 快速开始

本地 synthetic demo：

```powershell
slidebridge create-demo --out outputs\demo_slide.png
slidebridge create-demo-heatmap --out outputs\demo_heatmap.png --slide outputs\demo_slide.png
slidebridge create-demo-annotations --out outputs\demo_annotations.geojson
slidebridge view outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --annotations outputs\demo_annotations.geojson --open-browser
```

远端 WSI viewer：

```cmd
slidebridge app
```

或直接使用命令行：

```cmd
slidebridge remote-view user@server:/data/slides/case.svs --remote-runner "conda run -n slidebridge slidebridge"
```

## 网页启动器

`slidebridge app` 会启动一个本地 Web App，用于管理 SSH 连接、浏览远端目录、选择 WSI、添加多层 raster heatmap、填写 patch/annotation 路径，并启动 viewer session。它适合不想手写长命令的日常调试流程。

```cmd
slidebridge app
```

如果 `slidebridge` 命令不可用，可以使用：

```cmd
python -m slidebridge.cli app
```

Launcher 会调用本机 `ssh`。SSH key、`ssh-agent`、`~/.ssh/config` alias 和密码登录都由本机 SSH 客户端处理；如果服务器要求密码，密码提示会出现在启动 `slidebridge app` 的终端里。

## 通过 SSH 浏览服务器上的切片

这是 SlideBridge 的核心使用场景：切片文件保留在服务器上，SlideBridge 在远端读取 WSI，本地浏览器通过 SSH tunnel 访问 viewer。`remote-view` 使用本机 `ssh`，因此 SSH key、密码登录、非 22 端口和 `~/.ssh/config` alias 都取决于用户自己的 SSH 配置。

SSH key 登录和密码登录使用同一条命令；如果服务器要求密码，终端会显示 SSH password prompt：

```cmd
slidebridge remote-view user@server:/data/slides/case.svs --remote-runner "conda run -n slidebridge slidebridge"
```

非 22 端口：

```cmd
slidebridge remote-view user@server:/data/slides/case.svs --ssh-port 2222 --remote-runner "conda run -n slidebridge slidebridge"
```

也可以传远端目录，在浏览器左侧选择切片：

```cmd
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

## 常用命令

```cmd
slidebridge version
slidebridge app
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

Multiple full-slide heatmaps can be compared in the viewer:

```powershell
slidebridge view outputs\demo_slide.png `
  --raster-heatmap-layer low=outputs\heatmap_low.png `
  --raster-heatmap-layer high=outputs\heatmap_high.png `
  --port 7860 --open-browser
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

## 论文/汇报图导出

`render-figure` 可以导出主视野 + inset patch + inset heatmap + 标尺/标题的组合图，适合把模型调试结果整理成报告图。

```powershell
slidebridge render-figure outputs\demo_slide.png `
  --raster-heatmap outputs\demo_heatmap.png `
  --center-x 2048 --center-y 1536 `
  --window-width 1600 --window-height 1200 `
  --inset-x 1800 --inset-y 1300 `
  --inset-width 512 --inset-height 512 `
  --title "Model output overview" `
  --panel-label A `
  --scalebar-um 500 `
  --mpp 0.25 `
  --out outputs\demo_figure.png
```

详见 [Figure Rendering](docs/FIGURES.md)。

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
- [Figure Rendering](docs/FIGURES.md)
- [Coordinates](docs/COORDINATES.md)
- [Viewer](docs/VIEWER.md)
- [Issues and Improvements](docs/ISSUES_AND_IMPROVEMENTS.md)

## Roadmap

v0.3.0:

- `slidebridge app` 本地网页启动器
- 在网页里配置 SSH、浏览远端目录、选择 WSI/heatmap/patch/annotation
- 预览等价 `remote-view` 命令并启动/停止 viewer session

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

v0.2.21:

- viewer Figure Designer custom layout editing with draggable/resizable panels
- add/delete up to 12 patch panels and export custom `2400x1800` PNG figures through `/api/render-figure`
- legacy bottom `2x3` figure specs remain supported

v0.2.20:

- viewer Figure tab for main heatmap plus bottom `2x3` patch figure design
- copy JSON specs and export fixed `2400x1800` PNG figures through `/api/render-figure`

v0.2.19:

- `render-figure` 论文/汇报图导出
- 主视野 + inset patch + inset heatmap + 标尺/标题

v0.2.x:

- viewer 交互体验继续打磨
- heatmap / annotation 对齐诊断
- 更好的远端 viewer 生命周期管理

v0.3:

- plugin template

## License

Apache-2.0
