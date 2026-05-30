# Promotion Draft

## Chinese Short Post

我开源了一个计算病理 / 病理 AI 调试小工具：SlideBridge Core。

它可以做 WSI 元数据检查、缩略图导出、patch 坐标可视化、模型 score /
attention overlay、简单 QC 报告和 patch 导出。仓库自带 synthetic demo，不需要
真实切片也能快速跑起来。

项目定位是 research / algorithm debugging only，不用于临床诊断。

GitHub: [WangjiaweiY/slidebridge](https://github.com/WangjiaweiY/slidebridge)

## English Open Source Post

I just published SlideBridge Core, a lightweight toolkit for computational
pathology and pathology AI debugging.

It focuses on practical WSI inspection workflows:

- metadata inspection
- thumbnail export
- local browser viewer
- patch coordinate debugging
- score / attention overlay
- lightweight QC report
- patch export
- synthetic demo data for quick start

The goal is to make model-output debugging and patch-level inspection easier
without requiring any private data for the demo.

Research and algorithm debugging only. Not for clinical diagnosis.

GitHub: [WangjiaweiY/slidebridge](https://github.com/WangjiaweiY/slidebridge)

## Chinese Technical Note For Lab / Classmates

我整理了一个轻量的 WSI 调试工具 SlideBridge Core，主要解决病理 AI 开发里几个
常见问题：

- 快速确认切片尺寸、level、MPP、objective、reader 和 metadata。
- 把 patch 坐标 CSV / NPY / H5 / JSON 叠到本地 viewer 上检查是否对齐。
- 把模型 score / attention 做成 overlay，方便 debug 采样和预测结果。
- 从坐标表导出 patch 图像和 manifest，方便复现实验。

可以不用真实切片，先跑 synthetic demo：

```powershell
slidebridge create-demo --out outputs\demo_slide.png
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 100 --with-scores
slidebridge render-overlay outputs\demo_slide.png --patches outputs\demo_coords.csv --out outputs\demo_overlay.png
```

如果你们在做 WSI / MIL / patch-level 模型调试，欢迎试用和提 issue。

GitHub: [WangjiaweiY/slidebridge](https://github.com/WangjiaweiY/slidebridge)
