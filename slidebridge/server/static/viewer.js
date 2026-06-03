    const viewerConfigElement = document.getElementById("slidebridge-viewer-config");
    const viewerConfig = JSON.parse((viewerConfigElement && viewerConfigElement.textContent) || "{}");
    const slideEntries = Array.isArray(viewerConfig.slideEntries) ? viewerConfig.slideEntries : [];
    const tileCacheKey = String(viewerConfig.tileCacheKey || "");
    const initialTileCacheStats = viewerConfig.initialTileCacheStats || {};
    const initialTilePerformanceStats = viewerConfig.initialTilePerformanceStats || {};
    const snapshotOptions = viewerConfig.snapshotOptions || {};
    const defaultHeatmapOpacity = Number.isFinite(Number(viewerConfig.heatmapOpacity)) ? Number(viewerConfig.heatmapOpacity) : 0.45;
    const initialViewerState = parseViewerStateFromUrl();
    let selectedSlideId = initialViewerState.slideId !== null ? initialViewerState.slideId : (slideEntries.length ? slideEntries[0].id : 0);
    const i18n = {
      en: {
        modeLibrary: "Library",
        modeSingle: "Single slide",
        selectedSlide: "selected slide",
        tabLibrary: "Library",
        tabInfo: "Info",
        tabOverlays: "Overlays",
        tabFigure: "Figure",
        slideLibrary: "Slide Library",
        figureDesigner: "Figure Designer",
        setMainView: "Set main from current view",
        figureHeatmapLayer: "heatmap layer",
        mainMode: "main mode",
        overlayOpacity: "overlay opacity",
        mainScalebar: "main scale bar um",
        selectPatchArea: "Select patch area",
        copyFigureSpec: "Copy JSON spec",
        exportFigurePng: "Export PNG",
        filterSlides: "Filter slides",
        session: "Session",
        slideMetadata: "Slide Metadata",
        overlays: "Overlays",
        mode: "mode",
        sourceType: "source type",
        directoryLibrary: "directory library",
        singleSlide: "single slide",
        scanScope: "scan scope",
        rootSubfolders: "root + subfolders",
        rootOnly: "root only",
        sshUser: "ssh user",
        sshHost: "ssh host",
        sshPort: "ssh port",
        remoteRoot: "remote root",
        source: "source",
        selectedPath: "selected path",
        reader: "reader",
        dimensions: "dimensions",
        mpp: "mpp",
        objective: "objective",
        vendor: "vendor",
        warnings: "warnings",
        tileCache: "Tile Cache",
        cacheEnabled: "enabled",
        cacheEntries: "entries",
        cacheMemory: "memory",
        cacheHitsMisses: "hits / misses",
        cacheEvictions: "evictions",
        tileWorkers: "tile workers",
        generatedTiles: "generated tiles",
        cacheServedTiles: "cache served",
        avgTileMs: "avg tile ms",
        p95TileMs: "p95 tile ms",
        viewportSnapshot: "Viewport Snapshot",
        viewportCenter: "center",
        viewportWindow: "window",
        viewportOutput: "output",
        copyViewerUrl: "Copy viewer URL",
        copyRenderCommand: "Copy render-view command",
        downloadViewportPng: "Download PNG",
        viewerUrlCopied: "viewer URL copied.",
        snapshotCopied: "render-view command copied.",
        snapshotDownloaded: "Viewport PNG requested.",
        snapshotUnavailable: "Viewport is not ready yet.",
        modelOverlay: "model/debug overlay",
        rasterHeatmap: "raster heatmap",
        rasterHeatmaps: "raster heatmaps",
        annotationOverlay: "annotation overlay for research/debugging",
        scoreThreshold: "score threshold",
        topK: "top-k patches",
        clearFilters: "Clear filters",
        annotationLabels: "annotation labels",
        allLabels: "All",
        noLabels: "None",
        overlayDetails: "overlay details",
        selectOverlayItem: "Click a patch or annotation in the viewer.",
        filtered: "filtered",
        selected: "selected",
        low: "low",
        high: "high",
        patches: "patches",
        annotations: "annotations",
        shown: "shown",
        canvasDrawn: "canvas drawn",
        none: "none",
        equivalentMagnification: "equiv. magnification",
        fit: "Fit",
        pixelScale: "pixel scale",
        footer: "Coordinates are level-0 pixels. Viewer is for research/debugging only."
      },
      zh: {
        modeLibrary: "切片库",
        modeSingle: "单张切片",
        selectedSlide: "当前切片",
        tabLibrary: "切片库",
        tabInfo: "信息",
        tabOverlays: "叠加层",
        slideLibrary: "切片库",
        filterSlides: "筛选切片",
        session: "会话",
        slideMetadata: "切片元数据",
        overlays: "叠加层",
        mode: "模式",
        sourceType: "来源类型",
        directoryLibrary: "目录切片库",
        singleSlide: "单张切片",
        scanScope: "扫描范围",
        rootSubfolders: "根目录 + 子目录",
        rootOnly: "仅根目录",
        sshUser: "SSH 用户",
        sshHost: "SSH 主机",
        sshPort: "SSH 端口",
        remoteRoot: "远端根目录",
        source: "来源",
        selectedPath: "当前路径",
        reader: "读取器",
        dimensions: "尺寸",
        mpp: "MPP",
        objective: "物镜倍率",
        vendor: "厂商",
        warnings: "警告",
        tileCache: "Tile 缓存",
        cacheEnabled: "启用",
        cacheEntries: "条目",
        cacheMemory: "内存",
        cacheHitsMisses: "命中 / 未命中",
        cacheEvictions: "淘汰",
        tileWorkers: "tile 并发",
        generatedTiles: "生成 tile",
        cacheServedTiles: "缓存返回",
        avgTileMs: "平均 tile 毫秒",
        p95TileMs: "P95 tile 毫秒",
        viewportSnapshot: "视野截图",
        viewportCenter: "中心",
        viewportWindow: "窗口",
        viewportOutput: "输出",
        copyViewerUrl: "复制 viewer URL",
        copyRenderCommand: "复制 render-view 命令",
        downloadViewportPng: "下载 PNG",
        viewerUrlCopied: "已复制 viewer URL。",
        snapshotCopied: "已复制 render-view 命令。",
        snapshotDownloaded: "已请求导出当前视野 PNG。",
        snapshotUnavailable: "视野尚未准备好。",
        modelOverlay: "模型/调试叠加层",
        rasterHeatmap: "整图热图",
        rasterHeatmaps: "整图热图",
        annotationOverlay: "标注叠加层（研究/调试）",
        low: "低",
        high: "高",
        patches: "patch",
        annotations: "标注",
        shown: "已显示",
        none: "无",
        footer: "坐标均为 level-0 像素。本 viewer 仅用于研究和调试。"
      }
    };
    let currentLanguage = localStorage.getItem("slidebridge.viewer.language")
      || (navigator.language && navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en");

    function t(key) {
      return (i18n[currentLanguage] && i18n[currentLanguage][key]) || i18n.en[key] || key;
    }

    function applyLanguage() {
      document.documentElement.lang = currentLanguage === "zh" ? "zh-CN" : "en";
      document.querySelectorAll("[data-i18n]").forEach((element) => {
        element.textContent = t(element.dataset.i18n);
      });
      document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
        element.setAttribute("placeholder", t(element.dataset.i18nPlaceholder));
      });
      const toggle = document.getElementById("language-toggle");
      if (toggle) {
        toggle.textContent = currentLanguage === "zh" ? "EN" : "中文";
        toggle.title = currentLanguage === "zh" ? "Switch to English" : "切换到中文";
      }
    }

    function setupLanguage(onChange) {
      const toggle = document.getElementById("language-toggle");
      if (!toggle) {
        return;
      }
      toggle.addEventListener("click", function () {
        currentLanguage = currentLanguage === "zh" ? "en" : "zh";
        localStorage.setItem("slidebridge.viewer.language", currentLanguage);
        applyLanguage();
        onChange();
      });
    }

    function setupTabs(onChange) {
      const buttons = Array.from(document.querySelectorAll(".tab-button"));
      const panels = Array.from(document.querySelectorAll(".tab-panel"));
      function activateTab(target, emitChange = true) {
        const targetButton = buttons.find((button) => button.dataset.tabTarget === target && !button.classList.contains("hidden"));
        if (!targetButton) {
          return activeTabId();
        }
        buttons.forEach((item) => item.classList.toggle("active", item === targetButton));
        panels.forEach((panel) => panel.classList.toggle("active", panel.id === target));
        if (emitChange && onChange) {
          onChange(target);
        }
        return target;
      }
      buttons.forEach((button) => {
        button.addEventListener("click", function () {
          if (button.classList.contains("hidden")) {
            return;
          }
          activateTab(button.dataset.tabTarget, true);
        });
      });
      return activateTab;
    }

    function activeTabId() {
      const active = document.querySelector(".tab-panel.active");
      return active ? active.id : "";
    }

    function parseViewerStateFromUrl() {
      const params = new URLSearchParams(window.location.search);
      const slideId = parseSlideIdParam(params.get("slide_id") || params.get("slide"));
      const centerX = finiteNumberParam(params.get("center_x") || params.get("cx"));
      const centerY = finiteNumberParam(params.get("center_y") || params.get("cy"));
      const windowWidth = positiveNumberParam(params.get("window_width") || params.get("ww"));
      const windowHeight = positiveNumberParam(params.get("window_height") || params.get("wh"));
      const labelParam = params.get("annotation_labels");
      return {
        slideId,
        centerX,
        centerY,
        windowWidth,
        windowHeight,
        hasViewport: centerX !== null && centerY !== null && windowWidth !== null && windowHeight !== null,
        tab: sanitizeTabParam(params.get("tab")),
        overlay: boolParam(params.get("overlay")),
        annotationOverlay: boolParam(params.get("annotation_overlay")),
        opacity: clampNumberParam(params.get("opacity"), 0, 1),
        annotationOpacity: clampNumberParam(params.get("annotation_opacity"), 0, 1),
        scoreThreshold: clampNumberParam(params.get("score_threshold"), 0, 1),
        topK: nonNegativeIntegerParam(params.get("top_k")),
        annotationLabels: parseAnnotationLabelsParam(labelParam)
      };
    }

    function parseSlideIdParam(value) {
      if (value === null || value === undefined || value === "") {
        return null;
      }
      const numeric = Number(value);
      if (!Number.isInteger(numeric) || numeric < 0) {
        return null;
      }
      return slideEntries.some((entry) => Number(entry.id) === numeric) ? numeric : null;
    }

    function sanitizeTabParam(value) {
      if (!value) {
        return "";
      }
      const normalized = String(value).trim();
      return ["library-tab", "info-tab", "overlays-tab", "figure-tab"].includes(normalized) ? normalized : "";
    }

    function boolParam(value) {
      if (value === null || value === undefined || value === "") {
        return null;
      }
      const normalized = String(value).toLowerCase();
      if (["1", "true", "yes", "on"].includes(normalized)) {
        return true;
      }
      if (["0", "false", "no", "off"].includes(normalized)) {
        return false;
      }
      return null;
    }

    function finiteNumberParam(value) {
      if (value === null || value === undefined || value === "") {
        return null;
      }
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : null;
    }

    function positiveNumberParam(value) {
      const numeric = finiteNumberParam(value);
      return numeric !== null && numeric > 0 ? numeric : null;
    }

    function clampNumberParam(value, minValue, maxValue) {
      const numeric = finiteNumberParam(value);
      if (numeric === null) {
        return null;
      }
      return Math.max(minValue, Math.min(maxValue, numeric));
    }

    function nonNegativeIntegerParam(value) {
      const numeric = finiteNumberParam(value);
      if (numeric === null || numeric < 0) {
        return null;
      }
      return Math.floor(numeric);
    }

    function parseAnnotationLabelsParam(value) {
      if (value === null || value === undefined) {
        return null;
      }
      if (value === "__none__") {
        return [];
      }
      return String(value).split(",").map((item) => item.trim()).filter(Boolean);
    }

    function showViewerLoadError() {
      const element = document.getElementById("viewer-error");
      if (element) {
        element.style.display = "block";
      }
    }

    const osdAssetSources = [
      {
        script: "/static/vendor/openseadragon/openseadragon.min.js",
        prefixUrl: "/static/vendor/openseadragon/images/"
      },
      {
        script: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js",
        prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/"
      }
    ];
    let osdPrefixUrl = osdAssetSources[0].prefixUrl;

    function loadScript(url) {
      return new Promise(function (resolve, reject) {
        const script = document.createElement("script");
        script.src = url;
        script.async = true;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }

    async function loadOpenSeadragon() {
      for (const source of osdAssetSources) {
        osdPrefixUrl = source.prefixUrl;
        try {
          await loadScript(source.script);
          if (window.OpenSeadragon) {
            return;
          }
        } catch (error) {
          console.warn("OpenSeadragon asset failed", source.script, error);
        }
      }
      showViewerLoadError();
      throw new Error("OpenSeadragon failed to load");
    }

    async function initializeViewer() {
      applyLanguage();
      await loadOpenSeadragon();
      const viewer = OpenSeadragon({
        id: "viewer",
        prefixUrl: osdPrefixUrl,
        showNavigationControl: false,
        showNavigator: true,
        navigatorPosition: "TOP_RIGHT",
        navigatorWidth: "260px",
        navigatorHeight: "170px",
        navigatorMaintainSizeRatio: true,
        preserveViewport: false,
        animationTime: 0.15,
        blendTime: 0,
        immediateRender: false,
        imageLoaderLimit: 4,
        maxImageCacheCount: 200,
        maxZoomPixelRatio: 2
      });

      let isOpen = false;
      let patchPayload = null;
      let annotationPayload = null;
      let rasterHeatmapPayload = null;
      let cacheStatsPayload = initialTileCacheStats;
      let performanceStatsPayload = initialTilePerformanceStats;
      const rasterHeatmapElements = new Map();
      const rasterHeatmapLayerState = new Map();
      let currentSlideInfo = null;
      let currentZoomLevels = [];
      const overlayCanvas = document.getElementById("overlay-canvas");
      const overlayContext = overlayCanvas.getContext("2d");
      const overlayTooltip = document.getElementById("overlay-tooltip");
      let overlayHitItems = [];
      let overlayRedrawPending = false;
      let selectedAnnotationLabels = new Set();
      let annotationFilterSignature = "";
      let pendingInitialViewport = initialViewerState.hasViewport;
      let pendingInitialAnnotationLabels = initialViewerState.annotationLabels;
      let urlStateUpdateTimer = null;
      let lastViewerStateUrl = "";
      const activateTab = setupTabs(function () {
        refreshViewerLayout(false);
        scheduleViewerStateUrlUpdate();
      });
      applyInitialControlState();
      if (initialViewerState.tab) {
        activateTab(initialViewerState.tab, false);
      }
      updateCacheStats(cacheStatsPayload);
      updatePerformanceStats(performanceStatsPayload);
      window.setInterval(loadPerformanceStats, 5000);
      setupLanguage(function () {
        if (patchPayload) {
          document.getElementById("patch-count").textContent = patchCountLabel(patchPayload);
        }
        if (annotationPayload) {
          document.getElementById("annotation-count").textContent = annotationCountLabel(annotationPayload);
        }
        if (rasterHeatmapPayload) {
          updateRasterHeatmapHeader(rasterHeatmapPayload, false);
        }
        const infoWarnings = document.getElementById("meta-warnings");
        if (infoWarnings && infoWarnings.dataset.empty === "true") {
          infoWarnings.textContent = t("none");
        }
        renderZoomControl();
        updateZoomReadout();
      });

      viewer.addHandler("open", function () {
        isOpen = true;
        renderZoomControl();
        const restored = restoreInitialViewportIfNeeded();
        renderRasterHeatmap();
        refreshViewerLayout(!restored);
        updateZoomReadout();
        updateSnapshotReadout();
        scheduleViewerStateUrlUpdate();
        scheduleCanvasOverlayRedraw();
      });
      viewer.addHandler("animation", function () {
        updateZoomReadout();
        updateSnapshotReadout();
        scheduleCanvasOverlayRedraw();
      });
      viewer.addHandler("animation-finish", function () {
        updateZoomReadout();
        updateSnapshotReadout();
        scheduleViewerStateUrlUpdate();
        scheduleCanvasOverlayRedraw();
      });
      viewer.addHandler("zoom", function () {
        updateZoomReadout();
        updateSnapshotReadout();
        scheduleCanvasOverlayRedraw();
      });
      viewer.addHandler("pan", function () {
        updateZoomReadout();
        updateSnapshotReadout();
        scheduleCanvasOverlayRedraw();
      });
      viewer.addHandler("resize", function () {
        updateSnapshotReadout();
        scheduleCanvasOverlayRedraw();
      });
      setupCanvasTooltip();
      setupSnapshotControls();

      renderSlideList();
      const search = document.getElementById("slide-search");
      if (search) {
        search.addEventListener("input", renderSlideList);
      }
      exposeSlideBridgeViewerApi();
      await selectSlide(selectedSlideId, {initial: true});
      emitViewerStateChange();
      window.dispatchEvent(new CustomEvent("slidebridge-viewer-ready"));

      async function selectSlide(slideId, options = {}) {
        selectedSlideId = Number(slideId);
        if (!options.initial) {
          pendingInitialViewport = false;
        }
        isOpen = false;
        patchPayload = null;
        annotationPayload = null;
        rasterHeatmapPayload = null;
        clearOverlays();
        clearOverlayDetail();
        setActiveSlideButton();
        document.getElementById("dynamic-warnings").innerHTML = "";
        viewer.open(`/slides/${selectedSlideId}/${tileCacheKey}/dzi.dzi`);
        await Promise.all([loadInfo(), loadPatches(false), loadRasterHeatmap(false), loadAnnotations(false), loadPerformanceStats()]);
        renderRasterHeatmap();
        renderPatches();
        renderAnnotations();
        updateSnapshotReadout();
        scheduleViewerStateUrlUpdate();
        emitViewerStateChange();
      }

      function refreshViewerLayout(goHome) {
        window.requestAnimationFrame(function () {
          viewer.viewport.resize();
          if (goHome) {
            viewer.viewport.goHome(true);
          }
          viewer.forceRedraw();
          renderRasterHeatmap();
          renderPatches();
          renderAnnotations();
        });
      }

      function applyInitialControlState() {
        setCheckedValue("overlay-toggle", initialViewerState.overlay);
        setCheckedValue("annotation-toggle", initialViewerState.annotationOverlay);
        setNumericControlValue("opacity-slider", initialViewerState.opacity);
        setNumericControlValue("annotation-opacity-slider", initialViewerState.annotationOpacity);
        setNumericControlValue("score-threshold-slider", initialViewerState.scoreThreshold);
        if (initialViewerState.topK !== null) {
          const topK = document.getElementById("top-k-input");
          if (topK) {
            topK.value = String(initialViewerState.topK);
          }
        }
        updateScoreThresholdValue();
      }

      function setCheckedValue(id, value) {
        if (value === null) {
          return;
        }
        const element = document.getElementById(id);
        if (element) {
          element.checked = Boolean(value);
        }
      }

      function setNumericControlValue(id, value) {
        if (value === null) {
          return;
        }
        const element = document.getElementById(id);
        if (element) {
          element.value = String(value);
        }
      }

      function restoreInitialViewportIfNeeded() {
        if (!pendingInitialViewport || !initialViewerState.hasViewport || !viewer.viewport) {
          return false;
        }
        pendingInitialViewport = false;
        window.requestAnimationFrame(function () {
          const rect = viewer.viewport.imageToViewportRectangle(
            initialViewerState.centerX - initialViewerState.windowWidth / 2,
            initialViewerState.centerY - initialViewerState.windowHeight / 2,
            initialViewerState.windowWidth,
            initialViewerState.windowHeight
          );
          viewer.viewport.fitBounds(rect, true);
          viewer.forceRedraw();
          updateZoomReadout();
          updateSnapshotReadout();
          scheduleCanvasOverlayRedraw();
          scheduleViewerStateUrlUpdate();
        });
        return true;
      }

      function scheduleViewerStateUrlUpdate() {
        if (urlStateUpdateTimer) {
          window.clearTimeout(urlStateUpdateTimer);
        }
        urlStateUpdateTimer = window.setTimeout(updateViewerStateUrl, 160);
      }

      function updateViewerStateUrl() {
        const url = buildViewerUrl();
        if (!url || url === lastViewerStateUrl || url === window.location.href) {
          lastViewerStateUrl = url || lastViewerStateUrl;
          return;
        }
        window.history.replaceState(null, "", url);
        lastViewerStateUrl = url;
      }

      function buildViewerUrl() {
        const snapshot = currentViewportSnapshot();
        const url = new URL(window.location.href);
        const params = new URLSearchParams();
        params.set("slide_id", String(selectedSlideId));
        if (snapshot) {
          params.set("center_x", String(snapshot.centerX));
          params.set("center_y", String(snapshot.centerY));
          params.set("window_width", String(snapshot.windowWidth));
          params.set("window_height", String(snapshot.windowHeight));
        }
        const tabId = activeTabId();
        if (tabId) {
          params.set("tab", tabId);
        }
        params.set("overlay", document.getElementById("overlay-toggle").checked ? "1" : "0");
        params.set("annotation_overlay", document.getElementById("annotation-toggle").checked ? "1" : "0");
        params.set("opacity", Number(document.getElementById("opacity-slider").value || 0.45).toFixed(2));
        params.set("annotation_opacity", Number(document.getElementById("annotation-opacity-slider").value || 0.35).toFixed(2));
        params.set("score_threshold", scoreThreshold().toFixed(2));
        const topK = topKValue();
        if (topK > 0) {
          params.set("top_k", String(topK));
        }
        const labels = selectedAnnotationLabelList();
        if (labels !== null) {
          params.set("annotation_labels", labels.length ? labels.join(",") : "__none__");
        }
        url.search = params.toString();
        url.hash = "";
        return url.toString();
      }

      function renderSlideList() {
        const list = document.getElementById("slide-list");
        if (!list) {
          return;
        }
        const query = (document.getElementById("slide-search")?.value || "").toLowerCase();
        list.innerHTML = "";
        slideEntries
          .filter((entry) => !query || entry.relative_path.toLowerCase().includes(query) || entry.filename.toLowerCase().includes(query))
          .forEach((entry) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "slide-item";
            button.dataset.slideId = String(entry.id);
            button.title = entry.path || entry.relative_path;
            button.innerHTML = `<strong>${escapeHtml(entry.relative_path)}</strong><span class="slide-folder">${escapeHtml(entryFolder(entry))}</span><span class="slide-size">${formatBytes(entry.size_bytes)}</span>`;
            button.addEventListener("click", () => selectSlide(entry.id));
            list.appendChild(button);
          });
        setActiveSlideButton();
      }

      function setActiveSlideButton() {
        document.querySelectorAll(".slide-item").forEach((button) => {
          button.classList.toggle("active", Number(button.dataset.slideId) === selectedSlideId);
        });
      }

      async function loadInfo() {
        const response = await fetch(apiUrl("info"), {cache: "no-store"});
        const info = await response.json();
        updateInfo(info);
      }

      async function loadPatches(renderNow = true) {
        const response = await fetch(apiUrl("patches"), {cache: "no-store"});
        const payload = await response.json();
        patchPayload = payload;
        updatePatchHeader(payload);
        if (renderNow) {
          renderPatches();
        }
      }

      async function loadRasterHeatmap(renderNow = true) {
        const response = await fetch(apiUrl("raster-heatmaps"), {cache: "no-store"});
        const payload = await response.json();
        rasterHeatmapPayload = payload;
        updateRasterHeatmapHeader(payload);
        emitViewerStateChange();
        if (renderNow) {
          renderRasterHeatmap();
        }
      }

      async function loadAnnotations(renderNow = true) {
        const response = await fetch(apiUrl("annotations"), {cache: "no-store"});
        const payload = await response.json();
        annotationPayload = payload;
        updateAnnotationHeader(payload);
        if (renderNow) {
          renderAnnotations();
        }
      }

      async function loadCacheStats() {
        const response = await fetch(`/api/cache-stats?v=${tileCacheKey}`, {cache: "no-store"});
        const payload = await response.json();
        cacheStatsPayload = payload;
        updateCacheStats(payload);
      }

      async function loadPerformanceStats() {
        const response = await fetch(`/api/performance?v=${tileCacheKey}`, {cache: "no-store"});
        const payload = await response.json();
        cacheStatsPayload = payload.cache;
        performanceStatsPayload = payload.tiles;
        updateCacheStats(payload.cache);
        updatePerformanceStats(payload.tiles);
      }

      function apiUrl(name) {
        return `/api/${name}?slide_id=${selectedSlideId}&v=${tileCacheKey}`;
      }

      function updateInfo(info) {
        document.getElementById("slide-title").textContent = info.filename || "";
        document.title = `SlideBridge Viewer - ${info.filename || ""}`;
        document.getElementById("selected-path-short").textContent = info.relative_path || info.path || info.filename || "";
        document.getElementById("meta-path").textContent = info.path || "";
        document.getElementById("meta-reader").textContent = info.reader || "unknown";
        document.getElementById("meta-dimensions").textContent = `${info.width} x ${info.height}`;
        document.getElementById("meta-mpp").textContent = `${info.mpp_x ?? "unknown"} x ${info.mpp_y ?? "unknown"}`;
        document.getElementById("meta-objective").textContent = info.objective_power ?? "unknown";
        document.getElementById("meta-vendor").textContent = info.vendor ?? "unknown";
        currentSlideInfo = info;
        renderZoomControl();
        updateZoomReadout();
        updateSnapshotReadout();
        const warnings = document.getElementById("meta-warnings");
        if (info.warnings && info.warnings.length) {
          warnings.textContent = info.warnings.join(", ");
          warnings.dataset.empty = "false";
        } else {
          warnings.textContent = t("none");
          warnings.dataset.empty = "true";
        }
      }

      function updateCacheStats(payload) {
        if (!payload) {
          return;
        }
        document.getElementById("cache-enabled").textContent = payload.enabled ? "yes" : "no";
        document.getElementById("cache-entries").textContent = `${payload.entries || 0} / ${payload.max_entries || 0}`;
        document.getElementById("cache-memory").textContent = `${payload.mb || 0} / ${payload.max_mb || 0} MB`;
        document.getElementById("cache-hits-misses").textContent = `${payload.hits || 0} / ${payload.misses || 0}`;
        document.getElementById("cache-evictions").textContent = String(payload.evictions || 0);
        document.getElementById("cache-workers").textContent = String(payload.tile_workers || 0);
      }

      function updatePerformanceStats(payload) {
        if (!payload) {
          return;
        }
        document.getElementById("perf-generated").textContent = String(payload.generated_tiles || 0);
        document.getElementById("perf-cache-served").textContent = String(payload.cache_served_tiles || 0);
        document.getElementById("perf-avg-tile").textContent = metricValue(payload.total_tile_ms, "avg");
        document.getElementById("perf-p95-tile").textContent = metricValue(payload.total_tile_ms, "p95");
      }

      function metricValue(metric, key) {
        if (!metric || metric[key] === null || metric[key] === undefined) {
          return "unknown";
        }
        return `${metric[key]} ms`;
      }

      function renderZoomControl() {
        const bar = document.getElementById("zoom-bar");
        if (!bar) {
          return;
        }
        currentZoomLevels = zoomLevelsFor(currentSlideInfo);
        bar.innerHTML = "";
        currentZoomLevels.forEach((level) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "zoom-button";
          button.textContent = level.fit ? t("fit") : level.label;
          button.title = level.fit ? t("fit") : `${level.label} ${t("equivalentMagnification")}`;
          if (level.fit) {
            button.dataset.fit = "true";
          } else {
            button.dataset.scale = String(level.scale);
          }
          button.addEventListener("click", function () {
            if (level.fit) {
              viewer.viewport.goHome(false);
            } else {
              zoomToImageScale(level.scale);
            }
            window.setTimeout(updateZoomReadout, 50);
          });
          bar.appendChild(button);
        });
        updateZoomReadout();
      }

      function zoomLevelsFor(info) {
        const base = magnificationBase(info);
        if (!base) {
          return [
            {fit: false, label: "2:1", scale: 2},
            {fit: false, label: "1:1", scale: 1},
            {fit: false, label: "1:2", scale: 0.5},
            {fit: false, label: "1:4", scale: 0.25},
            {fit: true, label: t("fit")}
          ];
        }
        const common = [1, 2, 5, 10, 20, 40, 60, 80];
        const levels = common
          .filter((value) => value <= base.value * 1.01)
          .map((value) => ({fit: false, label: `${formatMagnification(value)}`, scale: value / base.value, mag: value}));
        if (!levels.length || Math.abs((levels[levels.length - 1].mag || 0) - base.value) > 0.75) {
          levels.push({fit: false, label: `${formatMagnification(base.value)}`, scale: 1, mag: base.value});
        }
        levels.sort((a, b) => Number(b.mag || 0) - Number(a.mag || 0));
        levels.push({fit: true, label: t("fit")});
        return levels;
      }

      function magnificationBase(info) {
        if (!info) {
          return null;
        }
        const objective = Number(info.objective_power);
        if (Number.isFinite(objective) && objective > 0) {
          return {value: objective, source: "objective"};
        }
        const mppValues = [Number(info.mpp_x), Number(info.mpp_y)].filter((value) => Number.isFinite(value) && value > 0);
        if (mppValues.length) {
          const mpp = mppValues.reduce((sum, value) => sum + value, 0) / mppValues.length;
          return {value: 10 / mpp, source: "mpp"};
        }
        return null;
      }

      function currentImageScale() {
        if (!viewer || !viewer.viewport || !isOpen) {
          return null;
        }
        const sample = Math.max(1, Math.min(1000, Number(currentSlideInfo?.width || 1000)));
        try {
          const p0 = viewer.viewport.imageToViewportCoordinates(0, 0);
          const p1 = viewer.viewport.imageToViewportCoordinates(sample, 0);
          const s0 = viewer.viewport.pixelFromPoint(p0, true);
          const s1 = viewer.viewport.pixelFromPoint(p1, true);
          const scale = Math.abs(Number(s1.x) - Number(s0.x)) / sample;
          return Number.isFinite(scale) && scale > 0 ? scale : null;
        } catch (error) {
          return null;
        }
      }

      function zoomToImageScale(targetScale) {
        const currentScale = currentImageScale();
        const currentZoom = viewer.viewport.getZoom(true);
        const scale = Number(targetScale);
        if (!Number.isFinite(scale) || scale <= 0 || !currentScale || !Number.isFinite(currentZoom) || currentZoom <= 0) {
          return;
        }
        const targetZoom = currentZoom * (scale / currentScale);
        viewer.viewport.zoomTo(targetZoom, viewer.viewport.getCenter(true), false);
      }

      function updateZoomReadout() {
        const value = document.getElementById("zoom-value");
        if (!value) {
          return;
        }
        const scale = currentImageScale();
        if (!scale) {
          value.textContent = t("fit");
          setActiveZoomButton(null);
          return;
        }
        const base = magnificationBase(currentSlideInfo);
        if (base) {
          value.textContent = formatMagnification(base.value * scale);
          const label = document.getElementById("zoom-label");
          if (label) {
            label.textContent = t("equivalentMagnification");
          }
        } else {
          value.textContent = `${scale.toFixed(scale >= 1 ? 1 : 2)}x`;
          const label = document.getElementById("zoom-label");
          if (label) {
            label.textContent = t("pixelScale");
          }
        }
        setActiveZoomButton(scale);
      }

      function setupSnapshotControls() {
        const copyViewerUrlButton = document.getElementById("copy-viewer-url");
        const copyButton = document.getElementById("copy-render-command");
        const downloadButton = document.getElementById("download-render-view");
        if (copyViewerUrlButton) {
          copyViewerUrlButton.addEventListener("click", async function () {
            const url = buildViewerUrl();
            if (!url) {
              setSnapshotStatus(t("snapshotUnavailable"), "error");
              return;
            }
            await copyText(url);
            setSnapshotStatus(t("viewerUrlCopied"), "ok");
          });
        }
        if (copyButton) {
          copyButton.addEventListener("click", async function () {
            const command = buildRenderViewCommand();
            if (!command) {
              setSnapshotStatus(t("snapshotUnavailable"), "error");
              return;
            }
            await copyText(command);
            setSnapshotStatus(t("snapshotCopied"), "ok");
          });
        }
        if (downloadButton) {
          downloadButton.addEventListener("click", function () {
            const url = buildSnapshotDownloadUrl();
            if (!url) {
              setSnapshotStatus(t("snapshotUnavailable"), "error");
              return;
            }
            const link = document.createElement("a");
            link.href = url;
            link.download = snapshotFilename();
            document.body.appendChild(link);
            link.click();
            link.remove();
            setSnapshotStatus(t("snapshotDownloaded"), "ok");
          });
        }
        updateSnapshotReadout();
      }

      function exposeSlideBridgeViewerApi() {
        window.SlideBridgeViewer = {
          getSelectedSlideId: function () {
            return selectedSlideId;
          },
          getCurrentSlideInfo: function () {
            return currentSlideInfo ? {...currentSlideInfo} : null;
          },
          getCurrentViewportBbox: currentViewportBbox,
          getCurrentViewportSnapshot: function () {
            const snapshot = currentViewportSnapshot();
            return snapshot ? {...snapshot} : null;
          },
          getRasterHeatmapLayers: function () {
            return rasterHeatmapLayers(rasterHeatmapPayload).map((layer) => ({...layer}));
          },
          getDefaultOverlayOpacity: function () {
            const slider = document.getElementById("opacity-slider");
            const value = slider ? Number(slider.value) : defaultHeatmapOpacity;
            return Number.isFinite(value) ? value : defaultHeatmapOpacity;
          },
          selectSquareRegion: selectSquareRegion
        };
      }

      function emitViewerStateChange() {
        window.dispatchEvent(new CustomEvent("slidebridge-viewer-state"));
      }

      function currentViewportBbox() {
        const snapshot = currentViewportSnapshot();
        if (!snapshot || !currentSlideInfo) {
          return null;
        }
        const width = Math.max(1, Number(currentSlideInfo.width || 1));
        const height = Math.max(1, Number(currentSlideInfo.height || 1));
        const x0 = Math.max(0, Math.min(width - 1, Math.round(snapshot.centerX - snapshot.windowWidth / 2)));
        const y0 = Math.max(0, Math.min(height - 1, Math.round(snapshot.centerY - snapshot.windowHeight / 2)));
        const x1 = Math.max(x0 + 1, Math.min(width, Math.round(snapshot.centerX + snapshot.windowWidth / 2)));
        const y1 = Math.max(y0 + 1, Math.min(height, Math.round(snapshot.centerY + snapshot.windowHeight / 2)));
        return [x0, y0, x1, y1];
      }

      function selectSquareRegion() {
        if (!isOpen || !currentSlideInfo || !viewer.viewport) {
          return Promise.reject(new Error("Viewer is not ready."));
        }
        const container = document.querySelector("main");
        if (!container) {
          return Promise.reject(new Error("Viewer container is not available."));
        }
        return new Promise(function (resolve, reject) {
          let start = null;
          let active = false;
          let selectionRect = null;
          const box = document.createElement("div");
          box.className = "figure-selection-box";
          box.hidden = true;
          container.appendChild(box);
          container.classList.add("figure-selecting");
          const hadMouseNav = viewer.isMouseNavEnabled ? viewer.isMouseNavEnabled() : true;
          if (viewer.setMouseNavEnabled) {
            viewer.setMouseNavEnabled(false);
          }

          function cleanup() {
            container.classList.remove("figure-selecting");
            box.remove();
            container.removeEventListener("pointerdown", onPointerDown, true);
            window.removeEventListener("pointermove", onPointerMove, true);
            window.removeEventListener("pointerup", onPointerUp, true);
            window.removeEventListener("keydown", onKeyDown, true);
            if (viewer.setMouseNavEnabled) {
              viewer.setMouseNavEnabled(hadMouseNav);
            }
          }

          function finish(result, error) {
            cleanup();
            if (error) {
              reject(error);
              return;
            }
            resolve(result);
          }

          function onPointerDown(event) {
            if (event.target && event.target.closest && event.target.closest(".zoom-control")) {
              return;
            }
            event.preventDefault();
            event.stopPropagation();
            start = containerPointFromEvent(event, container);
            active = true;
            selectionRect = squareSelectionRect(start, start);
            updateSelectionBox(box, selectionRect);
            box.hidden = false;
            window.addEventListener("pointermove", onPointerMove, true);
            window.addEventListener("pointerup", onPointerUp, true);
          }

          function onPointerMove(event) {
            if (!active || !start) {
              return;
            }
            event.preventDefault();
            event.stopPropagation();
            selectionRect = squareSelectionRect(start, containerPointFromEvent(event, container));
            updateSelectionBox(box, selectionRect);
          }

          function onPointerUp(event) {
            if (!active || !start) {
              return;
            }
            event.preventDefault();
            event.stopPropagation();
            active = false;
            selectionRect = squareSelectionRect(start, containerPointFromEvent(event, container));
            if (!selectionRect || selectionRect.width < 8 || selectionRect.height < 8) {
              finish(null, new Error("Selection is too small."));
              return;
            }
            const bbox = selectionRectToBbox(selectionRect, container);
            if (!bbox) {
              finish(null, new Error("Selection is outside the slide."));
              return;
            }
            finish(bbox, null);
          }

          function onKeyDown(event) {
            if (event.key === "Escape") {
              event.preventDefault();
              finish(null, new Error("Selection cancelled."));
            }
          }

          container.addEventListener("pointerdown", onPointerDown, true);
          window.addEventListener("keydown", onKeyDown, true);
        });
      }

      function containerPointFromEvent(event, container) {
        const rect = container.getBoundingClientRect();
        return {
          x: event.clientX - rect.left,
          y: event.clientY - rect.top
        };
      }

      function squareSelectionRect(start, current) {
        const dx = Number(current.x) - Number(start.x);
        const dy = Number(current.y) - Number(start.y);
        const side = Math.max(Math.abs(dx), Math.abs(dy));
        const x = dx < 0 ? Number(start.x) - side : Number(start.x);
        const y = dy < 0 ? Number(start.y) - side : Number(start.y);
        return {x, y, width: side, height: side};
      }

      function updateSelectionBox(box, rect) {
        box.style.left = `${rect.x}px`;
        box.style.top = `${rect.y}px`;
        box.style.width = `${rect.width}px`;
        box.style.height = `${rect.height}px`;
      }

      function selectionRectToBbox(rect, container) {
        const p0 = containerPointToImage(rect.x, rect.y, container);
        const p1 = containerPointToImage(rect.x + rect.width, rect.y + rect.height, container);
        if (!p0 || !p1 || !currentSlideInfo) {
          return null;
        }
        const slideWidth = Math.max(1, Number(currentSlideInfo.width || 1));
        const slideHeight = Math.max(1, Number(currentSlideInfo.height || 1));
        const x0 = Math.max(0, Math.min(slideWidth - 1, Math.round(Math.min(p0.x, p1.x))));
        const y0 = Math.max(0, Math.min(slideHeight - 1, Math.round(Math.min(p0.y, p1.y))));
        const x1 = Math.max(x0 + 1, Math.min(slideWidth, Math.round(Math.max(p0.x, p1.x))));
        const y1 = Math.max(y0 + 1, Math.min(slideHeight, Math.round(Math.max(p0.y, p1.y))));
        return [x0, y0, x1, y1];
      }

      function containerPointToImage(x, y, container) {
        const rect = container.getBoundingClientRect();
        return clientPointToImage(rect.left + Number(x), rect.top + Number(y));
      }

      function clientPointToImage(clientX, clientY) {
        const viewerElement = document.getElementById("viewer");
        if (!viewerElement || !viewer.viewport) {
          return null;
        }
        const rect = viewerElement.getBoundingClientRect();
        const pixel = new OpenSeadragon.Point(Number(clientX) - rect.left, Number(clientY) - rect.top);
        const viewportPoint = viewer.viewport.pointFromPixel(pixel, true);
        const imagePoint = viewer.viewport.viewportToImageCoordinates(viewportPoint);
        return {x: Number(imagePoint.x), y: Number(imagePoint.y)};
      }

      function currentViewportSnapshot() {
        if (!isOpen || !currentSlideInfo || !viewer.viewport) {
          return null;
        }
        const bounds = currentImageBounds(0);
        const windowWidth = Math.max(1, Math.round(bounds[2] - bounds[0]));
        const windowHeight = Math.max(1, Math.round(bounds[3] - bounds[1]));
        const centerX = Math.round(bounds[0] + windowWidth / 2);
        const centerY = Math.round(bounds[1] + windowHeight / 2);
        const output = snapshotOutputSize(windowWidth, windowHeight);
        return {
          centerX,
          centerY,
          windowWidth,
          windowHeight,
          outWidth: output.width,
          outHeight: output.height,
          scale: output.width / windowWidth
        };
      }

      function snapshotOutputSize(windowWidth, windowHeight) {
        const viewerRect = document.getElementById("viewer").getBoundingClientRect();
        const maxSide = 2200;
        const minSide = 256;
        const aspect = Math.max(1, windowHeight) / Math.max(1, windowWidth);
        let width = Math.max(minSide, Math.round(viewerRect.width || 1600));
        let height = Math.max(minSide, Math.round(width * aspect));
        const factor = Math.min(1, maxSide / Math.max(width, height));
        width = Math.max(1, Math.round(width * factor));
        height = Math.max(1, Math.round(height * factor));
        return {width, height};
      }

      function updateSnapshotReadout() {
        const snapshot = currentViewportSnapshot();
        const center = document.getElementById("snapshot-center");
        const windowValue = document.getElementById("snapshot-window");
        const output = document.getElementById("snapshot-output");
        if (!center || !windowValue || !output) {
          return;
        }
        if (!snapshot) {
          center.textContent = "unknown";
          windowValue.textContent = "unknown";
          output.textContent = "unknown";
          return;
        }
        center.textContent = `${snapshot.centerX}, ${snapshot.centerY}`;
        windowValue.textContent = `${snapshot.windowWidth} x ${snapshot.windowHeight}`;
        output.textContent = `${snapshot.outWidth} x ${snapshot.outHeight} (${snapshot.scale.toFixed(3)} px/level-0 px)`;
      }

      function buildSnapshotDownloadUrl() {
        const snapshot = currentViewportSnapshot();
        if (!snapshot) {
          return null;
        }
        const params = new URLSearchParams();
        params.set("slide_id", String(selectedSlideId));
        params.set("center_x", String(snapshot.centerX));
        params.set("center_y", String(snapshot.centerY));
        params.set("window_width", String(snapshot.windowWidth));
        params.set("window_height", String(snapshot.windowHeight));
        params.set("out_width", String(snapshot.outWidth));
        params.set("out_height", String(snapshot.outHeight));
        params.set("include_patches", String(Boolean(snapshotOptions.patches && document.getElementById("overlay-toggle").checked)));
        params.set("include_raster_heatmap", String(Boolean(snapshotOptions.raster_heatmap && document.getElementById("overlay-toggle").checked)));
        params.set("include_annotations", String(Boolean(snapshotOptions.annotations && document.getElementById("annotation-toggle").checked)));
        params.set("score_threshold", String(scoreThreshold()));
        params.set("top_k", String(topKValue()));
        params.set("opacity", String(Number(document.getElementById("opacity-slider").value || 0.45)));
        params.set("annotation_opacity", String(Number(document.getElementById("annotation-opacity-slider").value || 0.35)));
        const labels = selectedAnnotationLabelList();
        if (labels !== null) {
          params.set("annotation_labels", labels.length ? labels.join(",") : "__none__");
        }
        params.set("v", tileCacheKey);
        return `/api/render-view?${params.toString()}`;
      }

      function buildRenderViewCommand() {
        const snapshot = currentViewportSnapshot();
        if (!snapshot || !currentSlideInfo) {
          return null;
        }
        const lines = [`slidebridge render-view ${quoteCommandArg(currentSlideInfo.path || currentSlideInfo.filename || "slide.svs")}`];
        let overlayOpacityAdded = false;
        addCommandArg(lines, "--center-x", snapshot.centerX);
        addCommandArg(lines, "--center-y", snapshot.centerY);
        addCommandArg(lines, "--window-width", snapshot.windowWidth);
        addCommandArg(lines, "--window-height", snapshot.windowHeight);
        addCommandArg(lines, "--out-width", snapshot.outWidth);
        addCommandArg(lines, "--out-height", snapshot.outHeight);
        if (snapshotOptions.patches && document.getElementById("overlay-toggle").checked) {
          addCommandArg(lines, "--patches", snapshotOptions.patches);
          if (snapshotOptions.heatmap) {
            addCommandArg(lines, "--heatmap", snapshotOptions.heatmap);
          }
          addCommandArg(lines, "--score-normalization", snapshotOptions.score_normalization || "minmax");
          addCommandArg(lines, "--opacity", Number(document.getElementById("opacity-slider").value || 0.45).toFixed(2));
          overlayOpacityAdded = true;
        }
        if (snapshotOptions.raster_heatmap && document.getElementById("overlay-toggle").checked) {
          addCommandArg(lines, "--raster-heatmap", snapshotOptions.raster_heatmap);
          if (!overlayOpacityAdded) {
            addCommandArg(lines, "--opacity", Number(document.getElementById("opacity-slider").value || 0.45).toFixed(2));
            overlayOpacityAdded = true;
          }
          if (snapshotOptions.raster_heatmap_threshold !== null && snapshotOptions.raster_heatmap_threshold !== undefined) {
            addCommandArg(lines, "--raster-heatmap-threshold", snapshotOptions.raster_heatmap_threshold);
          }
          if (snapshotOptions.raster_heatmap_invert) {
            lines.push("  --raster-heatmap-invert");
          }
          if (snapshotOptions.raster_heatmap_colormap && snapshotOptions.raster_heatmap_colormap !== "auto") {
            addCommandArg(lines, "--raster-heatmap-colormap", snapshotOptions.raster_heatmap_colormap);
          }
        }
        if (snapshotOptions.annotations && document.getElementById("annotation-toggle").checked) {
          addCommandArg(lines, "--annotations", snapshotOptions.annotations);
          if (snapshotOptions.annotation_format) {
            addCommandArg(lines, "--annotation-format", snapshotOptions.annotation_format);
          }
          const labels = selectedAnnotationLabelList();
          if (labels !== null && labels.length) {
            addCommandArg(lines, "--annotation-labels", labels.join(","));
          }
          addCommandArg(lines, "--annotation-opacity", Number(document.getElementById("annotation-opacity-slider").value || 0.35).toFixed(2));
        }
        if (snapshotOptions.default_patch_size && Number(snapshotOptions.default_patch_size) !== 256) {
          addCommandArg(lines, "--default-patch-size", snapshotOptions.default_patch_size);
        }
        addCommandArg(lines, "--out", "outputs\\view_snapshot.png");
        return lines.join(" `\n");
      }

      function selectedAnnotationLabelList() {
        if (!annotationPayload || !Array.isArray(annotationPayload.labels) || !annotationPayload.labels.length) {
          return null;
        }
        const allLabels = annotationPayload.labels.map((label) => String(label));
        if (selectedAnnotationLabels.size === allLabels.length && allLabels.every((label) => selectedAnnotationLabels.has(label))) {
          return null;
        }
        return Array.from(selectedAnnotationLabels).sort();
      }

      function addCommandArg(lines, option, value) {
        if (value === null || value === undefined || value === "") {
          return;
        }
        const text = typeof value === "number" ? String(value) : quoteCommandArg(value);
        lines.push(`  ${option} ${text}`);
      }

      function quoteCommandArg(value) {
        return `"${String(value).replace(/"/g, "`\"")}"`;
      }

      async function copyText(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text);
          return;
        }
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand("copy");
        textArea.remove();
      }

      function setSnapshotStatus(message, state) {
        const status = document.getElementById("snapshot-status");
        if (!status) {
          return;
        }
        status.textContent = message || "";
        status.dataset.state = state || "";
      }

      function snapshotFilename() {
        const snapshot = currentViewportSnapshot();
        const base = (currentSlideInfo && currentSlideInfo.filename ? currentSlideInfo.filename : "slide").replace(/[^A-Za-z0-9_.-]+/g, "_");
        return snapshot ? `${base}_x${snapshot.centerX}_y${snapshot.centerY}.png` : "slidebridge_view.png";
      }

      function setActiveZoomButton(scale) {
        const buttons = Array.from(document.querySelectorAll(".zoom-button"));
        buttons.forEach((button) => button.classList.remove("active"));
        if (!scale || !currentZoomLevels.length) {
          return;
        }
        const numericLevels = currentZoomLevels.filter((level) => !level.fit && Number.isFinite(Number(level.scale)));
        if (!numericLevels.length) {
          return;
        }
        const minScale = Math.min(...numericLevels.map((level) => Number(level.scale)));
        if (scale < minScale * 0.65) {
          const fitButton = buttons.find((button) => button.dataset.fit === "true");
          if (fitButton) {
            fitButton.classList.add("active");
          }
          return;
        }
        let best = null;
        let bestDistance = Infinity;
        numericLevels.forEach((level) => {
          const distance = Math.abs(Math.log(scale / Number(level.scale)));
          if (distance < bestDistance) {
            bestDistance = distance;
            best = level;
          }
        });
        if (best && bestDistance < 0.28) {
          const button = buttons.find((item) => Number(item.dataset.scale) === Number(best.scale));
          if (button) {
            button.classList.add("active");
          }
        }
      }

      function formatMagnification(value) {
        const mag = Number(value);
        if (!Number.isFinite(mag) || mag <= 0) {
          return "unknown";
        }
        const digits = mag >= 10 ? 0 : mag >= 2 ? 1 : 2;
        return `${mag.toFixed(digits).replace(/\.0+$/, "")}x`;
      }

      function updatePatchHeader(payload) {
        updateScoreFilterControls();
        document.getElementById("patch-count").textContent = patchCountLabel(payload);
        updateScoreLegendVisibility();
        appendWarnings(payload.warnings || []);
      }

      function rasterHeatmapLayers(payload) {
        if (!payload || !payload.available) {
          return [];
        }
        if (Array.isArray(payload.layers)) {
          return payload.layers.filter((layer) => layer && layer.available);
        }
        return [payload];
      }

      function ensureRasterHeatmapLayerState(layers) {
        const baseOpacity = Number(document.getElementById("opacity-slider").value || defaultHeatmapOpacity);
        layers.forEach(function (layer, index) {
          const id = String(layer.id || index);
          if (!rasterHeatmapLayerState.has(id)) {
            rasterHeatmapLayerState.set(id, {
              enabled: index === 0,
              opacity: Math.max(0, Math.min(1, Number.isFinite(baseOpacity) ? baseOpacity : defaultHeatmapOpacity))
            });
          }
        });
      }

      function renderRasterHeatmapLayerControls(payload) {
        const container = document.getElementById("raster-heatmap-layer-list");
        if (!container) {
          return;
        }
        const layers = rasterHeatmapLayers(payload);
        container.hidden = layers.length === 0;
        container.innerHTML = "";
        ensureRasterHeatmapLayerState(layers);
        layers.forEach(function (layer, index) {
          const id = String(layer.id || index);
          const state = rasterHeatmapLayerState.get(id) || {enabled: index === 0, opacity: defaultHeatmapOpacity};
          const row = document.createElement("div");
          row.className = "heatmap-layer-row";
          const label = document.createElement("label");
          label.className = "heatmap-layer-label";
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.checked = Boolean(state.enabled);
          checkbox.addEventListener("change", function () {
            const current = rasterHeatmapLayerState.get(id) || state;
            rasterHeatmapLayerState.set(id, {...current, enabled: checkbox.checked});
            updatePatchOverlayStyle();
          });
          const text = document.createElement("span");
          text.className = "heatmap-layer-name";
          text.textContent = layer.name || rasterHeatmapLabel(layer);
          const meta = document.createElement("span");
          meta.className = "heatmap-layer-meta";
          meta.textContent = rasterHeatmapLayerMeta(layer);
          const warnings = rasterHeatmapLayerWarnings(layer);
          const textWrap = document.createElement("span");
          textWrap.appendChild(text);
          if (meta.textContent) {
            textWrap.appendChild(meta);
          }
          warnings.forEach(function (message) {
            const warning = document.createElement("span");
            warning.className = "heatmap-layer-warning";
            warning.textContent = message;
            textWrap.appendChild(warning);
          });
          label.appendChild(checkbox);
          label.appendChild(textWrap);
          const slider = document.createElement("input");
          slider.type = "range";
          slider.min = "0";
          slider.max = "1";
          slider.step = "0.05";
          slider.value = String(state.opacity);
          slider.addEventListener("input", function () {
            const current = rasterHeatmapLayerState.get(id) || state;
            rasterHeatmapLayerState.set(id, {...current, opacity: Number(slider.value)});
            updatePatchOverlayStyle();
          });
          row.appendChild(label);
          row.appendChild(slider);
          container.appendChild(row);
        });
      }

      function updateRasterHeatmapHeader(payload, appendWarningMessages = true) {
        const element = document.getElementById("raster-heatmap-count");
        if (!element) {
          return;
        }
        const layers = rasterHeatmapLayers(payload);
        element.hidden = !payload.available;
        element.textContent = layers.length > 1 ? `${layers.length} ${t("rasterHeatmaps")}` : rasterHeatmapLabel(layers[0] || payload);
        renderRasterHeatmapLayerControls(payload);
        updateScoreLegendVisibility();
        if (appendWarningMessages) {
          appendWarnings(rasterHeatmapGlobalWarnings(payload));
        }
      }

      function updateAnnotationHeader(payload) {
        updateAnnotationLabelFilter(payload);
        document.getElementById("annotation-count").textContent = annotationCountLabel(payload);
        appendWarnings(payload.warnings || []);
      }

      function updateScoreLegendVisibility() {
        const hasPatchScores = Boolean(patchPayload && patchPayload.has_scores);
        const hasRasterHeatmap = Boolean(rasterHeatmapLayers(rasterHeatmapPayload).length);
        document.getElementById("score-legend").hidden = !(hasPatchScores || hasRasterHeatmap);
      }

      function patchCountLabel(payload) {
        const filteredCount = filteredPatches((payload && payload.patches) || []).length;
        if (payload && payload.returned !== undefined && filteredCount !== Number(payload.returned || 0)) {
          return `${filteredCount} ${t("shown")} / ${payload.returned} ${t("patches")} (${t("filtered")})`;
        }
        return payload.count > payload.returned
          ? `${payload.count} ${t("patches")} (${payload.returned} ${t("shown")})`
          : `${payload.count} ${t("patches")}`;
      }

      function annotationCountLabel(payload) {
        const labels = payload.labels && payload.labels.length ? ` (${payload.labels.join(", ")})` : "";
        const filteredCount = filteredAnnotations((payload && payload.annotations) || []).length;
        if (payload && payload.returned !== undefined && filteredCount !== Number(payload.returned || 0)) {
          return `${filteredCount} ${t("shown")} / ${payload.returned} ${t("annotations")} (${t("filtered")})`;
        }
        return payload.count > payload.returned
          ? `${payload.count} ${t("annotations")} (${payload.returned} ${t("shown")})${labels}`
          : `${payload.count} ${t("annotations")}${labels}`;
      }

      function updateScoreFilterControls() {
        const hasScores = Boolean(patchPayload && patchPayload.has_scores);
        const row = document.getElementById("score-threshold-row");
        const slider = document.getElementById("score-threshold-slider");
        if (row) {
          row.hidden = !hasScores;
        }
        if (slider) {
          slider.disabled = !hasScores;
        }
        updateScoreThresholdValue();
      }

      function updateScoreThresholdValue() {
        const slider = document.getElementById("score-threshold-slider");
        const value = document.getElementById("score-threshold-value");
        if (slider && value) {
          value.textContent = Number(slider.value || 0).toFixed(2);
        }
      }

      function scoreThreshold() {
        const slider = document.getElementById("score-threshold-slider");
        return slider ? Math.max(0, Math.min(1, Number(slider.value || 0))) : 0;
      }

      function topKValue() {
        const input = document.getElementById("top-k-input");
        const value = input ? Number(input.value) : 0;
        return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
      }

      function filteredPatches(patches) {
        const rows = Array.isArray(patches) ? patches.slice() : [];
        const hasScores = Boolean(patchPayload && patchPayload.has_scores);
        let filtered = rows;
        if (hasScores) {
          const minScore = scoreThreshold();
          filtered = rows.filter(function (patch) {
            const score = Number(patch.score);
            return Number.isFinite(score) && score >= minScore;
          });
          filtered.sort((a, b) => Number(b.score) - Number(a.score));
        }
        const topK = topKValue();
        if (topK > 0) {
          filtered = filtered.slice(0, topK);
        }
        return filtered;
      }

      function updateAnnotationLabelFilter(payload) {
        const container = document.getElementById("annotation-label-filter");
        if (!container) {
          return;
        }
        const annotations = (payload && payload.annotations) || [];
        const counts = new Map();
        annotations.forEach(function (annotation) {
          const label = String(annotation.label || "unlabeled");
          counts.set(label, (counts.get(label) || 0) + 1);
        });
        const labels = Array.from(counts.keys()).sort();
        const signature = labels.join("\u001f");
        if (signature !== annotationFilterSignature) {
          annotationFilterSignature = signature;
          if (pendingInitialAnnotationLabels !== null) {
            selectedAnnotationLabels = new Set(pendingInitialAnnotationLabels.filter((label) => labels.includes(label)));
            pendingInitialAnnotationLabels = null;
          } else {
            selectedAnnotationLabels = new Set(labels);
          }
        }
        container.innerHTML = "";
        if (!labels.length) {
          container.textContent = t("none");
          return;
        }
        labels.forEach(function (label) {
          const chip = document.createElement("label");
          chip.className = "label-chip";
          chip.title = `${label} (${counts.get(label) || 0})`;
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.checked = selectedAnnotationLabels.has(label);
          checkbox.addEventListener("change", function () {
            if (checkbox.checked) {
              selectedAnnotationLabels.add(label);
            } else {
              selectedAnnotationLabels.delete(label);
            }
            document.getElementById("annotation-count").textContent = annotationCountLabel(annotationPayload);
            scheduleCanvasOverlayRedraw();
            scheduleViewerStateUrlUpdate();
          });
          const text = document.createElement("span");
          text.textContent = `${label} (${counts.get(label) || 0})`;
          chip.appendChild(checkbox);
          chip.appendChild(text);
          container.appendChild(chip);
        });
      }

      function filteredAnnotations(annotations) {
        const rows = Array.isArray(annotations) ? annotations : [];
        if (!rows.length) {
          return rows;
        }
        const labels = new Set(rows.map((annotation) => String(annotation.label || "unlabeled")));
        if (!labels.size) {
          return rows;
        }
        if (!selectedAnnotationLabels.size) {
          return [];
        }
        return rows.filter((annotation) => selectedAnnotationLabels.has(String(annotation.label || "unlabeled")));
      }

      function refreshOverlayCountsAndCanvas() {
        if (patchPayload) {
          document.getElementById("patch-count").textContent = patchCountLabel(patchPayload);
        }
        if (annotationPayload) {
          document.getElementById("annotation-count").textContent = annotationCountLabel(annotationPayload);
        }
        scheduleCanvasOverlayRedraw();
      }

      function rasterHeatmapLabel(payload) {
        if (!payload || !payload.available) {
          return t("rasterHeatmap");
        }
        if (payload.name) {
          return payload.name;
        }
        const details = [];
        if (payload.mode) {
          details.push(payload.mode);
        }
        if (payload.threshold !== null && payload.threshold !== undefined) {
          details.push(`>=${payload.threshold}`);
        }
        if (payload.invert) {
          details.push("invert");
        }
        return details.length ? `${t("rasterHeatmap")} (${details.join(", ")})` : t("rasterHeatmap");
      }

      function rasterHeatmapLayerMeta(layer) {
        const parts = [];
        if (layer.mode) {
          parts.push(layer.mode);
        }
        if (layer.source_width && layer.source_height && layer.served_width && layer.served_height) {
          if (Number(layer.source_width) !== Number(layer.served_width) || Number(layer.source_height) !== Number(layer.served_height)) {
            parts.push(`${layer.source_width}x${layer.source_height} -> ${layer.served_width}x${layer.served_height}`);
          } else {
            parts.push(`${layer.served_width}x${layer.served_height}`);
          }
        } else if (layer.served_width && layer.served_height) {
          parts.push(`${layer.served_width}x${layer.served_height}`);
        }
        if (layer.threshold !== null && layer.threshold !== undefined) {
          parts.push(`>=${layer.threshold}`);
        }
        if (layer.invert) {
          parts.push("invert");
        }
        return parts.join(" · ");
      }

      function rasterHeatmapLayerWarnings(layer) {
        const raw = Array.isArray(layer && layer.warnings) ? layer.warnings : [];
        const values = raw
          .map((message) => humanizeRasterHeatmapWarning(message))
          .filter((message) => Boolean(message));
        return Array.from(new Set(values));
      }

      function rasterHeatmapGlobalWarnings(payload) {
        const raw = Array.isArray(payload && payload.warnings) ? payload.warnings : [];
        const values = raw
          .filter((message) => !isLayerRasterHeatmapWarning(message))
          .map((message) => humanizeRasterHeatmapWarning(message) || message)
          .filter((message) => Boolean(message));
        return Array.from(new Set(values));
      }

      function isLayerRasterHeatmapWarning(message) {
        const text = String(message || "");
        return text.startsWith("raster_heatmap_resized:")
          || text === "raster_heatmap_aspect_ratio_mismatch"
          || text === "raster_heatmap_no_finite_values"
          || text === "raster_heatmap_constant_values"
          || text === "raster_heatmap_threshold_hides_all_pixels";
      }

      function humanizeRasterHeatmapWarning(message) {
        const text = String(message || "");
        const resizeMatch = text.match(/^raster_heatmap_resized:(\d+x\d+):(\d+x\d+)$/);
        if (resizeMatch) {
          return `resized ${resizeMatch[1]} -> ${resizeMatch[2]}`;
        }
        if (text === "raster_heatmap_aspect_ratio_mismatch") {
          return "aspect ratio differs from slide";
        }
        if (text === "raster_heatmap_no_finite_values") {
          return "no finite score values";
        }
        if (text === "raster_heatmap_constant_values") {
          return "constant score values";
        }
        if (text === "raster_heatmap_threshold_hides_all_pixels") {
          return "threshold hides all pixels";
        }
        return text;
      }

      function appendWarnings(warnings) {
        const target = document.getElementById("dynamic-warnings");
        warnings.forEach((message) => {
          if (!message) {
            return;
          }
          const warning = document.createElement("div");
          warning.className = "warning";
          warning.textContent = message;
          target.appendChild(warning);
        });
      }

      function clearOverlays() {
        rasterHeatmapElements.forEach((element) => viewer.removeOverlay(element));
        rasterHeatmapElements.clear();
        overlayHitItems = [];
        clearCanvasOverlay();
      }

      function renderRasterHeatmap() {
        const layers = rasterHeatmapLayers(rasterHeatmapPayload);
        if (!isOpen || !layers.length || !currentSlideInfo) {
          return;
        }
        ensureRasterHeatmapLayerState(layers);
        const seen = new Set();
        layers.forEach(function (layer, index) {
          const id = String(layer.id || index);
          seen.add(id);
          if (rasterHeatmapElements.has(id)) {
            return;
          }
          const overlay = document.createElement("div");
          overlay.className = "raster-heatmap-overlay";
          overlay.dataset.layerId = id;
          overlay.style.backgroundImage = `url("${layer.url}")`;
          overlay.title = `${rasterHeatmapLabel(layer)}\n${layer.mapping || ""}`;
          viewer.addOverlay({
            element: overlay,
            location: viewer.viewport.imageToViewportRectangle(0, 0, currentSlideInfo.width, currentSlideInfo.height),
            checkResize: false
          });
          rasterHeatmapElements.set(id, overlay);
        });
        rasterHeatmapElements.forEach(function (element, id) {
          if (!seen.has(id)) {
            viewer.removeOverlay(element);
            rasterHeatmapElements.delete(id);
          }
        });
        updatePatchOverlayStyle();
      }

      function renderPatches() {
        scheduleCanvasOverlayRedraw();
      }

      function renderAnnotations() {
        scheduleCanvasOverlayRedraw();
      }

      function scheduleCanvasOverlayRedraw() {
        if (overlayRedrawPending) {
          return;
        }
        overlayRedrawPending = true;
        window.requestAnimationFrame(function () {
          overlayRedrawPending = false;
          drawCanvasOverlays();
        });
      }

      function clearCanvasOverlay() {
        resizeOverlayCanvas();
        overlayContext.clearRect(0, 0, overlayCanvas.clientWidth || 0, overlayCanvas.clientHeight || 0);
        updateOverlayRenderCount(0, 0);
      }

      function resizeOverlayCanvas() {
        const rect = overlayCanvas.getBoundingClientRect();
        const ratio = window.devicePixelRatio || 1;
        const width = Math.max(1, Math.round(rect.width * ratio));
        const height = Math.max(1, Math.round(rect.height * ratio));
        if (overlayCanvas.width !== width || overlayCanvas.height !== height) {
          overlayCanvas.width = width;
          overlayCanvas.height = height;
        }
        overlayContext.setTransform(ratio, 0, 0, ratio, 0, 0);
        return {width: rect.width, height: rect.height};
      }

      function drawCanvasOverlays() {
        const size = resizeOverlayCanvas();
        overlayContext.clearRect(0, 0, size.width, size.height);
        overlayHitItems = [];
        if (!isOpen || !currentSlideInfo) {
          updateOverlayRenderCount(0, 0);
          return;
        }
        const viewBounds = currentImageBounds(0.12);
        let drawn = 0;
        let total = 0;
        if (patchPayload && document.getElementById("overlay-toggle").checked) {
          const patches = filteredPatches(patchPayload.patches || []);
          total += patches.length;
          drawn += drawPatchCanvasOverlays(patches, viewBounds);
        }
        if (annotationPayload && document.getElementById("annotation-toggle").checked) {
          const annotations = filteredAnnotations(annotationPayload.annotations || []);
          total += annotations.length;
          drawn += drawAnnotationCanvasOverlays(annotations, viewBounds);
        }
        updateOverlayRenderCount(drawn, total);
      }

      function drawPatchCanvasOverlays(patches, viewBounds) {
        const opacity = Number(document.getElementById("opacity-slider").value);
        const hasScores = Boolean(patchPayload && patchPayload.has_scores);
        let drawn = 0;
        patches.forEach(function (patch) {
          const bbox = [Number(patch.x), Number(patch.y), Number(patch.x) + Number(patch.width), Number(patch.y) + Number(patch.height)];
          if (!bboxIntersects(bbox, viewBounds)) {
            return;
          }
          const rect = imageRectToScreenRect(bbox);
          if (!rect) {
            return;
          }
          const score = patch.score === undefined || patch.score === null ? null : Number(patch.score);
          overlayContext.save();
          if (hasScores && score !== null && Number.isFinite(score)) {
            overlayContext.fillStyle = scoreColor(score, opacity);
            overlayContext.fillRect(rect.x, rect.y, rect.width, rect.height);
          } else {
            overlayContext.globalAlpha = Math.max(0, Math.min(1, opacity));
            overlayContext.fillStyle = "rgba(255, 80, 80, 0.08)";
            overlayContext.strokeStyle = "rgba(255, 80, 80, 0.95)";
            overlayContext.lineWidth = Math.max(1, Math.min(2, Math.max(rect.width, rect.height) / 64));
            overlayContext.fillRect(rect.x, rect.y, rect.width, rect.height);
            overlayContext.strokeRect(rect.x, rect.y, rect.width, rect.height);
          }
          overlayContext.restore();
          overlayHitItems.push({screen: rect, title: patchTitle(patch, score), kind: "patch", data: patch, bbox});
          drawn += 1;
        });
        return drawn;
      }

      function drawAnnotationCanvasOverlays(annotations, viewBounds) {
        const opacity = Number(document.getElementById("annotation-opacity-slider").value);
        let drawn = 0;
        annotations.forEach(function (annotation) {
          const bbox = normalizedAnnotationBbox(annotation);
          if (!bbox || !bboxIntersects(bbox, viewBounds)) {
            return;
          }
          overlayContext.save();
          overlayContext.globalAlpha = 1;
          const color = annotation.color || "#c2415d";
          overlayContext.strokeStyle = color;
          overlayContext.fillStyle = colorToRgba(color, opacity);
          overlayContext.lineWidth = 2;
          const didDraw = drawAnnotationShape(annotation, bbox, color, opacity);
          overlayContext.restore();
          if (!didDraw) {
            return;
          }
          const rect = annotationScreenHitRect(annotation, bbox);
          if (rect) {
            overlayHitItems.push({screen: rect, title: annotationTitle(annotation), kind: "annotation", data: annotation, bbox});
          }
          drawn += 1;
        });
        return drawn;
      }

      function drawAnnotationShape(annotation, bbox, color, opacity) {
        if (annotation.type === "point") {
          const point = annotation.coordinates || {};
          const screen = imagePointToScreen(Number(point.x), Number(point.y));
          if (!screen) {
            return false;
          }
          overlayContext.beginPath();
          overlayContext.arc(screen.x, screen.y, 5, 0, Math.PI * 2);
          overlayContext.fillStyle = colorToRgba(color, Math.max(opacity, 0.45));
          overlayContext.fill();
          overlayContext.strokeStyle = color;
          overlayContext.stroke();
          return true;
        }
        if (annotation.type === "rectangle") {
          const rect = imageRectToScreenRect(bbox);
          if (!rect) {
            return false;
          }
          overlayContext.fillRect(rect.x, rect.y, rect.width, rect.height);
          overlayContext.strokeRect(rect.x, rect.y, rect.width, rect.height);
          return true;
        }
        if (annotation.type === "line") {
          drawPolyline(annotation.coordinates || [], false);
          return true;
        }
        if (annotation.type === "polygon") {
          drawPolygonRings(annotation.coordinates || []);
          return true;
        }
        if (annotation.type === "multipolygon") {
          (annotation.coordinates || []).forEach((polygon) => drawPolygonRings(polygon || []));
          return true;
        }
        return false;
      }

      function drawPolygonRings(rings) {
        overlayContext.beginPath();
        (rings || []).forEach(function (ring) {
          (ring || []).forEach(function (point, index) {
            const screen = imagePointToScreen(Number(point[0]), Number(point[1]));
            if (!screen) {
              return;
            }
            if (index === 0) {
              overlayContext.moveTo(screen.x, screen.y);
            } else {
              overlayContext.lineTo(screen.x, screen.y);
            }
          });
          overlayContext.closePath();
        });
        overlayContext.fill("evenodd");
        overlayContext.stroke();
      }

      function drawPolyline(points, closePath) {
        overlayContext.beginPath();
        (points || []).forEach(function (point, index) {
          const screen = imagePointToScreen(Number(point[0]), Number(point[1]));
          if (!screen) {
            return;
          }
          if (index === 0) {
            overlayContext.moveTo(screen.x, screen.y);
          } else {
            overlayContext.lineTo(screen.x, screen.y);
          }
        });
        if (closePath) {
          overlayContext.closePath();
        }
        overlayContext.stroke();
      }

      function currentImageBounds(paddingFraction) {
        if (!currentSlideInfo || !viewer.viewport) {
          return [0, 0, 0, 0];
        }
        const bounds = viewer.viewport.getBounds(true);
        const topLeft = viewer.viewport.viewportToImageCoordinates(bounds.x, bounds.y);
        const bottomRight = viewer.viewport.viewportToImageCoordinates(bounds.x + bounds.width, bounds.y + bounds.height);
        const minX = Math.min(topLeft.x, bottomRight.x);
        const minY = Math.min(topLeft.y, bottomRight.y);
        const maxX = Math.max(topLeft.x, bottomRight.x);
        const maxY = Math.max(topLeft.y, bottomRight.y);
        const padX = (maxX - minX) * Number(paddingFraction || 0);
        const padY = (maxY - minY) * Number(paddingFraction || 0);
        return [
          Math.max(0, minX - padX),
          Math.max(0, minY - padY),
          Math.min(Number(currentSlideInfo.width || maxX), maxX + padX),
          Math.min(Number(currentSlideInfo.height || maxY), maxY + padY)
        ];
      }

      function imagePointToScreen(x, y) {
        if (!Number.isFinite(x) || !Number.isFinite(y)) {
          return null;
        }
        const viewportPoint = viewer.viewport.imageToViewportCoordinates(x, y);
        const pixel = viewer.viewport.pixelFromPoint(viewportPoint, true);
        return {x: Number(pixel.x), y: Number(pixel.y)};
      }

      function imageRectToScreenRect(bbox) {
        const p0 = imagePointToScreen(Number(bbox[0]), Number(bbox[1]));
        const p1 = imagePointToScreen(Number(bbox[2]), Number(bbox[3]));
        if (!p0 || !p1) {
          return null;
        }
        const x = Math.min(p0.x, p1.x);
        const y = Math.min(p0.y, p1.y);
        return {
          x,
          y,
          width: Math.max(1, Math.abs(p1.x - p0.x)),
          height: Math.max(1, Math.abs(p1.y - p0.y))
        };
      }

      function bboxIntersects(a, b) {
        return Number(a[0]) <= Number(b[2])
          && Number(a[2]) >= Number(b[0])
          && Number(a[1]) <= Number(b[3])
          && Number(a[3]) >= Number(b[1]);
      }

      function normalizedAnnotationBbox(annotation) {
        const bbox = annotation.bbox || annotationBbox(annotation);
        if (!bbox || bbox.length < 4) {
          return null;
        }
        return [Number(bbox[0]), Number(bbox[1]), Number(bbox[2]), Number(bbox[3])];
      }

      function annotationScreenHitRect(annotation, bbox) {
        if (annotation.type === "point") {
          const point = annotation.coordinates || {};
          const screen = imagePointToScreen(Number(point.x), Number(point.y));
          if (!screen) {
            return null;
          }
          return {x: screen.x - 8, y: screen.y - 8, width: 16, height: 16};
        }
        return imageRectToScreenRect(bbox);
      }

      function colorToRgba(color, opacity) {
        const parsed = parseHexColor(color);
        const alpha = Math.max(0, Math.min(1, Number(opacity)));
        if (!parsed) {
          return `rgba(194, 65, 93, ${alpha})`;
        }
        return `rgba(${parsed.r}, ${parsed.g}, ${parsed.b}, ${alpha})`;
      }

      function parseHexColor(color) {
        const text = String(color || "").trim();
        const match = text.match(/^#?([0-9a-fA-F]{6})$/);
        if (!match) {
          return null;
        }
        const value = match[1];
        return {
          r: parseInt(value.slice(0, 2), 16),
          g: parseInt(value.slice(2, 4), 16),
          b: parseInt(value.slice(4, 6), 16)
        };
      }

      function updateOverlayRenderCount(drawn, total) {
        const element = document.getElementById("overlay-render-count");
        if (!element) {
          return;
        }
        element.textContent = `${t("canvasDrawn")} ${drawn} / ${total}`;
      }

      function setupCanvasTooltip() {
        const container = document.querySelector("main");
        if (!container) {
          return;
        }
        container.addEventListener("mousemove", function (event) {
          if (event.target && event.target.closest && event.target.closest(".zoom-control")) {
            hideOverlayTooltip();
            return;
          }
          const rect = container.getBoundingClientRect();
          const x = event.clientX - rect.left;
          const y = event.clientY - rect.top;
          const item = hitCanvasOverlay(x, y);
          if (!item) {
            hideOverlayTooltip();
            return;
          }
          overlayTooltip.textContent = item.title;
          overlayTooltip.style.left = `${Math.min(x + 14, rect.width - 24)}px`;
          overlayTooltip.style.top = `${Math.min(y + 14, rect.height - 24)}px`;
          overlayTooltip.style.display = "block";
        });
        container.addEventListener("click", function (event) {
          if (event.target && event.target.closest && event.target.closest(".zoom-control")) {
            return;
          }
          const rect = container.getBoundingClientRect();
          const x = event.clientX - rect.left;
          const y = event.clientY - rect.top;
          const item = hitCanvasOverlay(x, y);
          if (item) {
            setOverlayDetail(item);
          } else {
            clearOverlayDetail();
          }
        });
        container.addEventListener("mouseleave", hideOverlayTooltip);
      }

      function hitCanvasOverlay(x, y) {
        for (let index = overlayHitItems.length - 1; index >= 0; index -= 1) {
          const rect = overlayHitItems[index].screen;
          if (x >= rect.x && x <= rect.x + rect.width && y >= rect.y && y <= rect.y + rect.height) {
            return overlayHitItems[index];
          }
        }
        return null;
      }

      function hideOverlayTooltip() {
        overlayTooltip.style.display = "none";
      }

      function setOverlayDetail(item) {
        const detail = document.getElementById("overlay-detail");
        if (!detail || !item) {
          return;
        }
        detail.dataset.empty = "false";
        detail.innerHTML = "";
        const title = document.createElement("span");
        title.className = "overlay-detail-title";
        title.textContent = item.kind === "annotation" ? "annotation" : "patch";
        const body = document.createElement("div");
        body.textContent = item.title;
        const actions = document.createElement("div");
        actions.className = "control-actions";
        actions.style.marginTop = "8px";
        const zoomButton = document.createElement("button");
        zoomButton.className = "small-button";
        zoomButton.type = "button";
        zoomButton.textContent = "Zoom to item";
        zoomButton.addEventListener("click", function () {
          zoomToBbox(item.bbox);
        });
        actions.appendChild(zoomButton);
        detail.appendChild(title);
        detail.appendChild(body);
        if (item.bbox) {
          detail.appendChild(actions);
        }
      }

      function clearOverlayDetail() {
        const detail = document.getElementById("overlay-detail");
        if (!detail) {
          return;
        }
        detail.dataset.empty = "true";
        detail.textContent = t("selectOverlayItem");
      }

      function zoomToBbox(bbox) {
        if (!bbox || bbox.length < 4 || !viewer || !viewer.viewport) {
          return;
        }
        const x = Number(bbox[0]);
        const y = Number(bbox[1]);
        const width = Math.max(1, Number(bbox[2]) - x);
        const height = Math.max(1, Number(bbox[3]) - y);
        const padX = width * 0.25;
        const padY = height * 0.25;
        const rect = viewer.viewport.imageToViewportRectangle(x - padX, y - padY, width + padX * 2, height + padY * 2);
        viewer.viewport.fitBounds(rect, false);
      }

      function patchTitle(patch, score) {
        const parts = [
          `index: ${patch.index ?? ""}`,
          `x/y: ${patch.x}, ${patch.y}`,
          `size: ${patch.width} x ${patch.height}`
        ];
        if (patch.label) {
          parts.push(`label: ${patch.label}`);
        }
        if (score !== null && Number.isFinite(score)) {
          parts.push(`score: ${score.toFixed(3)}`);
        }
        return parts.join("\n");
      }

      function annotationTitle(annotation) {
        const bbox = annotation.bbox || [];
        return [
          `label: ${annotation.label ?? ""}`,
          `type: ${annotation.type ?? ""}`,
          `id: ${annotation.id ?? ""}`,
          `bbox: ${bbox.join(", ")}`
        ].join("\n");
      }

      function annotationElement(annotation) {
        const bbox = annotation.bbox || annotationBbox(annotation);
        if (!bbox) {
          return null;
        }
        let x = Number(bbox[0]);
        let y = Number(bbox[1]);
        let width = Math.max(1, Number(bbox[2]) - x);
        let height = Math.max(1, Number(bbox[3]) - y);
        const color = annotation.color || "#c2415d";
        if (annotation.type === "point") {
          const px = Number(annotation.coordinates.x);
          const py = Number(annotation.coordinates.y);
          x = px - 6;
          y = py - 6;
          width = 12;
          height = 12;
          const point = document.createElement("div");
          point.className = "annotation-overlay annotation-point";
          point.style.color = color;
          point.title = annotationTitle(annotation);
          point.dataset.annotation = "true";
          return {element: point, x, y, width, height};
        }
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("class", "annotation-overlay");
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.setAttribute("preserveAspectRatio", "none");
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = annotationTitle(annotation);
        svg.appendChild(title);
        svg.dataset.annotation = "true";
        if (annotation.type === "polygon") {
          svg.appendChild(polygonPath(annotation.coordinates, x, y, color));
        } else if (annotation.type === "multipolygon") {
          (annotation.coordinates || []).forEach((polygon) => svg.appendChild(polygonPath(polygon, x, y, color)));
        } else if (annotation.type === "rectangle") {
          const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
          rect.setAttribute("x", "0");
          rect.setAttribute("y", "0");
          rect.setAttribute("width", String(width));
          rect.setAttribute("height", String(height));
          rect.setAttribute("fill", color);
          rect.setAttribute("stroke", color);
          rect.setAttribute("stroke-width", "3");
          svg.appendChild(rect);
        } else if (annotation.type === "line") {
          const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
          line.setAttribute("points", (annotation.coordinates || []).map((p) => `${Number(p[0]) - x},${Number(p[1]) - y}`).join(" "));
          line.setAttribute("fill", "none");
          line.setAttribute("stroke", color);
          line.setAttribute("stroke-width", "4");
          svg.appendChild(line);
        } else {
          return null;
        }
        return {element: svg, x, y, width, height};
      }

      function polygonPath(rings, x0, y0, color) {
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        const data = (rings || []).map((ring) => {
          const commands = (ring || []).map((p, index) => `${index === 0 ? "M" : "L"} ${Number(p[0]) - x0} ${Number(p[1]) - y0}`);
          return commands.length ? `${commands.join(" ")} Z` : "";
        }).join(" ");
        path.setAttribute("d", data);
        path.setAttribute("fill", color);
        path.setAttribute("fill-rule", "evenodd");
        path.setAttribute("stroke", color);
        path.setAttribute("stroke-width", "3");
        return path;
      }

      function annotationBbox(annotation) {
        if (annotation.type === "rectangle") {
          const rect = annotation.coordinates;
          return [rect.x, rect.y, rect.x + rect.width, rect.y + rect.height];
        }
        return null;
      }

      function scoreColor(score, opacity) {
        const value = Math.max(0, Math.min(1, Number(score)));
        if (value < 0.5) {
          const t = value / 0.5;
          const r = Math.round(48 + (245 - 48) * t);
          const g = Math.round(112 + (211 - 112) * t);
          const b = Math.round(210 + (84 - 210) * t);
          return `rgba(${r}, ${g}, ${b}, ${opacity})`;
        }
        const t = (value - 0.5) / 0.5;
        const r = Math.round(245 + (220 - 245) * t);
        const g = Math.round(211 + (48 - 211) * t);
        const b = Math.round(84 + (48 - 84) * t);
        return `rgba(${r}, ${g}, ${b}, ${opacity})`;
      }

      function updatePatchOverlayStyle() {
        const toggle = document.getElementById("overlay-toggle");
        const slider = document.getElementById("opacity-slider");
        const opacity = Number(slider.value);
        const visible = Boolean(toggle.checked);
        const rasterLayers = rasterHeatmapLayers(rasterHeatmapPayload);
        const hasMissingRasterLayer = rasterLayers.some((layer, index) => !rasterHeatmapElements.has(String(layer.id || index)));
        if (visible && rasterLayers.length && hasMissingRasterLayer) {
          renderRasterHeatmap();
          return;
        }
        document.querySelectorAll(".raster-heatmap-overlay").forEach(function (element) {
          const layerId = String(element.dataset.layerId || "");
          const layerState = rasterHeatmapLayerState.get(layerId) || {enabled: true, opacity};
          const layerVisible = visible && Boolean(layerState.enabled);
          element.classList.toggle("raster-heatmap-hidden", !layerVisible);
          element.setAttribute("aria-hidden", layerVisible ? "false" : "true");
          element.style.opacity = layerVisible ? String(layerState.opacity) : "0";
        });
        scheduleCanvasOverlayRedraw();
      }

      function updateAnnotationOverlayStyle() {
        scheduleCanvasOverlayRedraw();
      }

      function escapeHtml(value) {
        return String(value)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#039;");
      }

      function entryFolder(entry) {
        const relative = String(entry.relative_path || "");
        const slash = Math.max(relative.lastIndexOf("/"), relative.lastIndexOf("\\"));
        return slash >= 0 ? relative.slice(0, slash) : ".";
      }

      function formatBytes(value) {
        const size = Number(value);
        if (!Number.isFinite(size) || size <= 0) {
          return "";
        }
        const units = ["B", "KB", "MB", "GB", "TB"];
        let current = size;
        let unit = 0;
        while (current >= 1024 && unit < units.length - 1) {
          current /= 1024;
          unit += 1;
        }
        return `${current.toFixed(current >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
      }

      document.getElementById("overlay-toggle").addEventListener("change", function () {
        updatePatchOverlayStyle();
        scheduleViewerStateUrlUpdate();
      });
      document.getElementById("opacity-slider").addEventListener("input", function () {
        updatePatchOverlayStyle();
        scheduleViewerStateUrlUpdate();
        emitViewerStateChange();
      });
      document.getElementById("score-threshold-slider").addEventListener("input", function () {
        updateScoreThresholdValue();
        refreshOverlayCountsAndCanvas();
        scheduleViewerStateUrlUpdate();
      });
      document.getElementById("top-k-input").addEventListener("input", function () {
        refreshOverlayCountsAndCanvas();
        scheduleViewerStateUrlUpdate();
      });
      document.getElementById("clear-overlay-filters").addEventListener("click", function () {
        document.getElementById("score-threshold-slider").value = "0";
        document.getElementById("top-k-input").value = "";
        updateScoreThresholdValue();
        if (annotationPayload) {
          selectedAnnotationLabels = new Set((annotationPayload.annotations || []).map((annotation) => String(annotation.label || "unlabeled")));
          updateAnnotationLabelFilter(annotationPayload);
        }
        refreshOverlayCountsAndCanvas();
        scheduleViewerStateUrlUpdate();
      });
      document.getElementById("select-all-labels").addEventListener("click", function () {
        if (!annotationPayload) {
          return;
        }
        selectedAnnotationLabels = new Set((annotationPayload.annotations || []).map((annotation) => String(annotation.label || "unlabeled")));
        updateAnnotationLabelFilter(annotationPayload);
        refreshOverlayCountsAndCanvas();
        scheduleViewerStateUrlUpdate();
      });
      document.getElementById("select-no-labels").addEventListener("click", function () {
        selectedAnnotationLabels = new Set();
        updateAnnotationLabelFilter(annotationPayload);
        refreshOverlayCountsAndCanvas();
        scheduleViewerStateUrlUpdate();
      });
      document.getElementById("annotation-toggle").addEventListener("change", function () {
        updateAnnotationOverlayStyle();
        scheduleViewerStateUrlUpdate();
      });
      document.getElementById("annotation-opacity-slider").addEventListener("input", function () {
        updateAnnotationOverlayStyle();
        scheduleViewerStateUrlUpdate();
      });
    }

    initializeViewer().catch(function (error) {
      console.error(error);
      showViewerLoadError();
    });
