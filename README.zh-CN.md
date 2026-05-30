# SlideBridge Core

[English README](README.md)

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

当前版本：`0.2.1`

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

## 功能

- 统一 slide reader 接口
- TiffSlide / OpenSlide / Pillow image reader
- metadata inspection
- thumbnail export
- browser viewer
- 本地打包的 OpenSeadragon viewer asset，带 CDN fallback
- patch coordinate overlay
- score / attention heatmap overlay
- doctor QC report
- patch export
- static overlay rendering
- environment / reader diagnostics
- synthetic demo image
- annotation overlay
- annotation conversion
- annotation-based patch labeling

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

## 从 Annotation 给 Patch 打标签

```powershell
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 200 --with-scores
slidebridge label-patches outputs\demo_coords.csv --annotations outputs\demo_annotations.geojson --out outputs\demo_coords_labeled.csv
```

`label-patches` 是 debugging / weak-labeling helper，不是 gold-standard labeling 工作流。

## Patch 和 Heatmap

Patch 坐标默认使用 level-0 pixel coordinate。

支持的 patch coordinate 格式：

- CSV
- NPY
- H5 / HDF5
- JSON
- PT / PTH，可选，需要 PyTorch

支持从 `score` / `attention` 列或单独 score 文件渲染 model/debug score overlay。
这些 overlay 只用于模型调试和结果检查，不是诊断输出。

## 坐标约定

- `x` / `y` 是 level-0 pixel coordinate。
- patch `width` / `height` 默认也是 level-0 pixel size。
- annotation 坐标也使用 level-0 pixel coordinate。
- `read_region` 的 `x` / `y` 使用 level-0 坐标。
- viewer overlay 按 level-0 coordinate space 对齐。

CSV 示例：

```csv
x,y,width,height,score
10000,20000,512,512,0.82
```

## 插件机制

公开 core 只定义 reader interface 和 registry。私有 reader 应放在单独的私有包中，
并通过 `slidebridge.core.registry.register_reader` 注册。

SlideBridge Core 不包含任何私有 reader。

## Roadmap

v0.2.1:

- annotation overlay
- QuPath GeoJSON overlay
- ASAP XML overlay
- annotation conversion
- patch labeling from annotations

v0.3:

- canvas overlay performance
- spatial culling for large overlays
- plugin template

## License

Apache-2.0
