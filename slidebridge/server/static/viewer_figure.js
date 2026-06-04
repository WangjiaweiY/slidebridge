(function () {
  const MAX_PATCH_SLOTS = 12;
  const DEFAULT_PATCH_SLOTS = 6;
  const CANVAS = {width: 2400, height: 1800, background: "white"};
  const SNAP_STEP = 20;
  const MIN_MAIN_SIZE = {width: 180, height: 120};
  const MIN_PATCH_SIZE = 80;

  const state = {
    activeRole: "patch",
    activeSlot: 0,
    slideId: null,
    heatmapLayerId: "",
    overlayOpacity: 0.45,
    opacityTouched: false,
    mainBbox: null,
    mainMode: "overlay",
    mainPanel: null,
    scalebarUm: null,
    showLabels: true,
    snapToGrid: true,
    isExporting: false,
    slots: []
  };

  let elements = null;
  let initialized = false;

  function initializeWhenReady() {
    if (window.SlideBridgeViewer) {
      initialize();
      return;
    }
    window.addEventListener("slidebridge-viewer-ready", initialize, {once: true});
  }

  function initialize() {
    if (initialized || !window.SlideBridgeViewer) {
      return;
    }
    elements = collectElements();
    if (!elements.root || !elements.preview) {
      return;
    }
    initialized = true;
    resetLayout(false);
    buildPreview();
    bindControls();
    refreshFromViewer();
    render();
    window.addEventListener("slidebridge-viewer-state", function () {
      refreshFromViewer();
      render();
    });
  }

  function collectElements() {
    return {
      root: document.getElementById("figure-tab"),
      preview: document.getElementById("figure-preview"),
      setMain: document.getElementById("figure-set-main"),
      addPatch: document.getElementById("figure-add-patch"),
      deletePatch: document.getElementById("figure-delete-patch"),
      resetLayout: document.getElementById("figure-reset-layout"),
      snapToggle: document.getElementById("figure-snap-toggle"),
      layer: document.getElementById("figure-heatmap-layer"),
      mainMode: document.getElementById("figure-main-mode"),
      opacity: document.getElementById("figure-opacity"),
      opacityValue: document.getElementById("figure-opacity-value"),
      scalebar: document.getElementById("figure-scalebar"),
      labelToggle: document.getElementById("figure-label-toggle"),
      slotList: document.getElementById("figure-slot-list"),
      selectPatch: document.getElementById("figure-select-patch"),
      copySpec: document.getElementById("figure-copy-spec"),
      exportPng: document.getElementById("figure-export"),
      status: document.getElementById("figure-status")
    };
  }

  function resetLayout(preserveSelections) {
    const previous = new Map((state.slots || []).map((slot) => [slot.slot, slot]));
    state.mainPanel = defaultLayoutForMainBbox(state.mainBbox).main;
    state.slots = [];
    defaultLayoutForMainBbox(state.mainBbox).patches.forEach(function (rect, slot) {
      const existing = preserveSelections ? previous.get(slot) : null;
      state.slots.push({
        slot,
        label: slotLabel(slot),
        bbox: existing ? existing.bbox : null,
        mode: existing ? existing.mode : (slot === 0 ? "raw" : "overlay"),
        rect
      });
    });
    state.activeRole = "patch";
    state.activeSlot = 0;
  }

  function defaultLayoutForMainBbox(bbox) {
    const aspect = bbox && bbox.length === 4
      ? Math.max(1, Number(bbox[2]) - Number(bbox[0])) / Math.max(1, Number(bbox[3]) - Number(bbox[1]))
      : 4 / 3;
    const top = 80;
    const bottomMargin = 80;
    const mainPatchGap = 32;
    const rowGap = 32;
    const availableHeight = CANVAS.height - top - bottomMargin - mainPatchGap - rowGap;
    const maxMainWidth = 2240;
    const maxMainHeight = 980;
    const maxMainHeightByLayout = Math.min(
      maxMainHeight,
      maxMainWidth / aspect,
      availableHeight / (1 + 2 * aspect / 3)
    );
    let slotSize = Math.max(1, Math.floor((maxMainHeightByLayout * aspect) / 3));
    while (slotSize > 1) {
      const mainWidth = slotSize * 3;
      const mainHeight = Math.max(1, Math.round(mainWidth / aspect));
      const totalHeight = top + mainHeight + mainPatchGap + slotSize * 2 + rowGap + bottomMargin;
      if (mainWidth <= maxMainWidth && mainHeight <= maxMainHeight && totalHeight <= CANVAS.height) {
        break;
      }
      slotSize -= 1;
    }
    const mainWidth = slotSize * 3;
    const mainHeight = Math.max(1, Math.round(mainWidth / aspect));
    const mainX = Math.round((CANVAS.width - mainWidth) / 2);
    const main = [mainX, top, mainWidth, mainHeight];
    const patches = [];
    for (let slot = 0; slot < DEFAULT_PATCH_SLOTS; slot += 1) {
      const col = slot % 3;
      const row = Math.floor(slot / 3);
      patches.push([
        mainX + col * slotSize,
        top + mainHeight + mainPatchGap + row * (slotSize + rowGap),
        slotSize,
        slotSize
      ]);
    }
    return {main, patches};
  }

  function buildPreview() {
    elements.preview.innerHTML = "";
    const canvas = document.createElement("div");
    canvas.className = "figure-layout-canvas";
    canvas.id = "figure-layout-canvas";
    elements.preview.appendChild(canvas);
    elements.canvas = canvas;
  }

  function buildSlotRows() {
    elements.slotList.innerHTML = "";
    state.slots.forEach(function (slot) {
      const row = document.createElement("div");
      row.className = "figure-slot-row";
      row.dataset.slot = String(slot.slot);
      row.tabIndex = 0;
      row.setAttribute("role", "button");

      const label = document.createElement("div");
      label.className = "figure-slot-label";
      label.textContent = slot.label;

      const summary = document.createElement("div");
      summary.className = "figure-slot-summary";

      const mode = document.createElement("select");
      mode.className = "inline-input figure-slot-mode";
      mode.dataset.slotMode = String(slot.slot);
      addModeOptions(mode);
      mode.addEventListener("change", function () {
        slot.mode = mode.value;
        state.activeRole = "patch";
        state.activeSlot = slot.slot;
        render();
      });

      row.addEventListener("click", function (event) {
        if (event.target === mode) {
          return;
        }
        state.activeRole = "patch";
        state.activeSlot = slot.slot;
        render();
      });
      row.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          state.activeRole = "patch";
          state.activeSlot = slot.slot;
          render();
        }
      });

      row.appendChild(label);
      row.appendChild(summary);
      row.appendChild(mode);
      elements.slotList.appendChild(row);
    });
  }

  function addModeOptions(select) {
    ["raw", "overlay"].forEach(function (mode) {
      const option = document.createElement("option");
      option.value = mode;
      option.textContent = mode;
      select.appendChild(option);
    });
  }

  function bindControls() {
    elements.setMain.addEventListener("click", function () {
      const bbox = fullSlideBbox();
      if (!bbox) {
        setStatus(tr("snapshotUnavailable"), "error");
        return;
      }
      state.mainBbox = bbox;
      state.mainPanel = defaultLayoutForMainBbox(bbox).main;
      setStatus(tr("figureMainFullSet"), "ok");
      render();
    });

    elements.addPatch.addEventListener("click", function () {
      const slot = firstAvailableSlot();
      if (slot === null) {
        setStatus(tr("figurePatchLimit"), "error");
        return;
      }
      state.slots.push({
        slot,
        label: slotLabel(slot),
        bbox: null,
        mode: state.heatmapLayerId ? "overlay" : "raw",
        rect: defaultPatchRect(slot)
      });
      state.activeRole = "patch";
      state.activeSlot = slot;
      setStatus(tr("figurePatchAdded").replace("{label}", slotLabel(slot)), "ok");
      render();
    });

    elements.deletePatch.addEventListener("click", function () {
      if (state.activeRole !== "patch") {
        return;
      }
      if (state.slots.length <= 1) {
        setStatus(tr("figurePatchMinimum"), "error");
        return;
      }
      const label = slotLabel(state.activeSlot);
      state.slots = state.slots.filter((slot) => slot.slot !== state.activeSlot);
      const next = state.slots[0];
      state.activeSlot = next ? next.slot : 0;
      state.activeRole = next ? "patch" : "main";
      setStatus(tr("figurePatchDeleted").replace("{label}", label), "ok");
      render();
    });

    elements.resetLayout.addEventListener("click", function () {
      resetLayout(true);
      setStatus(tr("figureLayoutReset"), "ok");
      render();
    });

    elements.snapToggle.addEventListener("change", function () {
      state.snapToGrid = Boolean(elements.snapToggle.checked);
      render();
    });

    elements.layer.addEventListener("change", function () {
      state.heatmapLayerId = elements.layer.value;
      render();
    });

    elements.mainMode.addEventListener("change", function () {
      state.mainMode = elements.mainMode.value;
      render();
    });

    elements.opacity.addEventListener("input", function () {
      state.opacityTouched = true;
      state.overlayOpacity = boundedNumber(elements.opacity.value, 0, 1, 0.45);
      renderOpacity();
    });

    elements.scalebar.addEventListener("input", function () {
      const value = Number(elements.scalebar.value);
      state.scalebarUm = Number.isFinite(value) && value > 0 ? value : null;
      render();
    });

    elements.labelToggle.addEventListener("change", function () {
      state.showLabels = Boolean(elements.labelToggle.checked);
      render();
    });

    elements.selectPatch.addEventListener("click", async function () {
      if (state.activeRole !== "patch") {
        setStatus(tr("figurePatchSlotRequired"), "error");
        return;
      }
      try {
        setStatus(tr("figureSelectionActive"), "busy");
        const bbox = await window.SlideBridgeViewer.selectSquareRegion();
        const slot = activeSlot();
        slot.bbox = bbox;
        const nextEmpty = state.slots.find((item) => !item.bbox && item.slot > slot.slot)
          || state.slots.find((item) => !item.bbox);
        if (nextEmpty) {
          state.activeRole = "patch";
          state.activeSlot = nextEmpty.slot;
        }
        setStatus(tr("figureSlotSet").replace("{label}", slot.label), "ok");
      } catch (error) {
        setStatus(error && error.message ? error.message : "Selection failed.", "error");
      }
      render();
    });

    elements.copySpec.addEventListener("click", async function () {
      try {
        const spec = buildSpec();
        await copyText(JSON.stringify(spec, null, 2));
        setStatus(tr("figureSpecCopied"), "ok");
      } catch (error) {
        setStatus(error && error.message ? error.message : tr("figureMainUnset"), "error");
      }
    });

    elements.exportPng.addEventListener("click", exportPng);
  }

  function refreshFromViewer() {
    const api = window.SlideBridgeViewer;
    const selectedSlideId = api.getSelectedSlideId();
    if (state.slideId !== selectedSlideId) {
      state.slideId = selectedSlideId;
      state.mainBbox = fullSlideBbox();
      resetLayout(true);
    } else if (!state.mainBbox) {
      state.mainBbox = fullSlideBbox();
    }
    const layers = api.getRasterHeatmapLayers();
    const previous = state.heatmapLayerId;
    elements.layer.innerHTML = "";
    if (!layers.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = tr("noRasterHeatmap");
      elements.layer.appendChild(option);
      elements.layer.disabled = true;
      state.heatmapLayerId = "";
    } else {
      elements.layer.disabled = false;
      layers.forEach(function (layer, index) {
        const id = String(layer.id || index);
        const option = document.createElement("option");
        option.value = id;
        option.textContent = layer.name ? `${layer.name} (${id})` : id;
        elements.layer.appendChild(option);
      });
      state.heatmapLayerId = layers.some((layer, index) => String(layer.id || index) === previous)
        ? previous
        : String(layers[0].id || 0);
    }
    elements.layer.value = state.heatmapLayerId;
    if (!state.opacityTouched) {
      state.overlayOpacity = boundedNumber(api.getDefaultOverlayOpacity(), 0, 1, 0.45);
      elements.opacity.value = String(state.overlayOpacity);
    }
    renderOpacity();
  }

  function render() {
    const overlayAvailable = Boolean(state.heatmapLayerId);
    if (!overlayAvailable && state.mainMode === "overlay") {
      state.mainMode = "raw";
    }
    state.slots.forEach(function (slot) {
      if (!overlayAvailable && slot.mode === "overlay") {
        slot.mode = "raw";
      }
    });
    renderModes(overlayAvailable);
    elements.labelToggle.checked = Boolean(state.showLabels);
    elements.snapToggle.checked = Boolean(state.snapToGrid);
    renderPreview();
    buildSlotRows();
    renderSlots();
    renderActions();
  }

  function renderModes(overlayAvailable) {
    elements.mainMode.value = state.mainMode;
    setOverlayOptionDisabled(elements.mainMode, !overlayAvailable);
  }

  function setOverlayOptionDisabled(select, disabled) {
    Array.from(select.options).forEach(function (option) {
      if (option.value === "overlay") {
        option.disabled = disabled;
      }
    });
  }

  function renderPreview() {
    elements.canvas.innerHTML = "";
    const mainPanel = createPanelElement("main", null, "A", state.mainPanel, Boolean(state.mainBbox));
    elements.canvas.appendChild(mainPanel);
    state.slots.forEach(function (slot) {
      const item = createPanelElement("patch", slot.slot, slot.label, slot.rect, Boolean(slot.bbox));
      elements.canvas.appendChild(item);
    });
  }

  function createPanelElement(role, slot, label, rect, ready) {
    const item = document.createElement("div");
    item.className = role === "main" ? "figure-layout-panel figure-layout-main" : "figure-layout-panel figure-layout-patch";
    item.dataset.role = role;
    item.dataset.ready = ready ? "true" : "false";
    item.dataset.active = isActive(role, slot) ? "true" : "false";
    if (slot !== null && slot !== undefined) {
      item.dataset.slot = String(slot);
    }
    item.textContent = label;
    applyPanelRect(item, rect);
    const handle = document.createElement("span");
    handle.className = "figure-panel-resize";
    handle.setAttribute("aria-hidden", "true");
    item.appendChild(handle);
    item.addEventListener("pointerdown", function (event) {
      beginPanelEdit(event, role, slot, event.target === handle ? "resize" : "drag");
    });
    return item;
  }

  function applyPanelRect(element, rect) {
    element.style.left = `${rect[0] / CANVAS.width * 100}%`;
    element.style.top = `${rect[1] / CANVAS.height * 100}%`;
    element.style.width = `${rect[2] / CANVAS.width * 100}%`;
    element.style.height = `${rect[3] / CANVAS.height * 100}%`;
  }

  function beginPanelEdit(event, role, slot, mode) {
    event.preventDefault();
    event.stopPropagation();
    state.activeRole = role;
    state.activeSlot = slot === null || slot === undefined ? state.activeSlot : slot;
    const panel = role === "main" ? {rect: state.mainPanel} : activeSlot();
    if (!panel) {
      return;
    }
    const startRect = panel.rect.slice();
    const canvasBox = elements.canvas.getBoundingClientRect();
    const startX = event.clientX;
    const startY = event.clientY;
    const scaleX = CANVAS.width / Math.max(1, canvasBox.width);
    const scaleY = CANVAS.height / Math.max(1, canvasBox.height);

    function onPointerMove(moveEvent) {
      moveEvent.preventDefault();
      const dx = (moveEvent.clientX - startX) * scaleX;
      const dy = (moveEvent.clientY - startY) * scaleY;
      if (mode === "resize") {
        panel.rect = resizedRect(startRect, dx, dy, role);
      } else {
        panel.rect = movedRect(startRect, dx, dy);
      }
      if (role === "main") {
        state.mainPanel = panel.rect;
      }
      renderPreview();
    }

    function onPointerUp() {
      window.removeEventListener("pointermove", onPointerMove, true);
      window.removeEventListener("pointerup", onPointerUp, true);
      render();
    }

    window.addEventListener("pointermove", onPointerMove, true);
    window.addEventListener("pointerup", onPointerUp, true);
    render();
  }

  function movedRect(rect, dx, dy) {
    const width = rect[2];
    const height = rect[3];
    return [
      clamp(snap(rect[0] + dx), 0, CANVAS.width - width),
      clamp(snap(rect[1] + dy), 0, CANVAS.height - height),
      width,
      height
    ];
  }

  function resizedRect(rect, dx, dy, role) {
    if (role === "patch") {
      const size = snap(Math.max(MIN_PATCH_SIZE, rect[2] + Math.max(dx, dy)));
      const bounded = Math.max(MIN_PATCH_SIZE, Math.min(size, CANVAS.width - rect[0], CANVAS.height - rect[1]));
      return [rect[0], rect[1], bounded, bounded];
    }
    const width = snap(Math.max(MIN_MAIN_SIZE.width, rect[2] + dx));
    const height = snap(Math.max(MIN_MAIN_SIZE.height, rect[3] + dy));
    return [
      rect[0],
      rect[1],
      Math.max(MIN_MAIN_SIZE.width, Math.min(width, CANVAS.width - rect[0])),
      Math.max(MIN_MAIN_SIZE.height, Math.min(height, CANVAS.height - rect[1]))
    ];
  }

  function renderSlots() {
    Array.from(elements.slotList.querySelectorAll(".figure-slot-row")).forEach(function (row) {
      const slot = state.slots.find((item) => item.slot === Number(row.dataset.slot));
      if (!slot) {
        return;
      }
      const summary = row.querySelector(".figure-slot-summary");
      const mode = row.querySelector("[data-slot-mode]");
      row.classList.toggle("active", isActive("patch", slot.slot));
      row.dataset.ready = slot.bbox ? "true" : "false";
      summary.textContent = slot.bbox
        ? `${slot.bbox.join(", ")} | ${slot.mode} | ${slot.rect.join(", ")}`
        : `${tr("empty")} | ${slot.rect.join(", ")}`;
      mode.value = slot.mode;
      setOverlayOptionDisabled(mode, !state.heatmapLayerId);
    });
  }

  function renderActions() {
    const hasMain = Boolean(state.mainBbox);
    elements.addPatch.disabled = state.isExporting || state.slots.length >= MAX_PATCH_SLOTS;
    elements.deletePatch.disabled = state.isExporting || state.activeRole !== "patch" || state.slots.length <= 1;
    elements.resetLayout.disabled = state.isExporting;
    elements.copySpec.disabled = state.isExporting || !hasMain;
    elements.exportPng.disabled = !hasMain || state.isExporting;
    elements.exportPng.textContent = state.isExporting ? tr("figureExporting") : tr("exportFigurePng");
    elements.selectPatch.disabled = state.isExporting
      || state.activeRole !== "patch"
      || !window.SlideBridgeViewer
      || !window.SlideBridgeViewer.selectSquareRegion;
    elements.setMain.disabled = state.isExporting;
  }

  function renderOpacity() {
    elements.opacityValue.textContent = Number(state.overlayOpacity).toFixed(2);
  }

  function buildSpec() {
    if (!state.mainBbox) {
      throw new Error(tr("figureMainUnset"));
    }
    return {
      slide_id: window.SlideBridgeViewer.getSelectedSlideId(),
      canvas: {...CANVAS},
      heatmap_layer_id: state.heatmapLayerId,
      overlay_opacity: Number(state.overlayOpacity),
      show_labels: Boolean(state.showLabels),
      layout: {
        template: "custom",
        panels: [
          {id: "A", role: "main", rect: state.mainPanel.slice()},
          ...state.slots.map(function (slot) {
            return {id: slot.label, role: "patch", slot: slot.slot, rect: slot.rect.slice()};
          })
        ]
      },
      main: {
        bbox: state.mainBbox.slice(),
        mode: state.mainMode,
        fit: "contain",
        label: "A",
        scalebar_um: state.scalebarUm
      },
      patches: state.slots
        .filter((slot) => Boolean(slot.bbox))
        .map(function (slot) {
          return {
            slot: slot.slot,
            bbox: slot.bbox.slice(),
            mode: slot.mode,
            label: slot.label
          };
        })
    };
  }

  async function exportPng() {
    let spec = null;
    try {
      spec = buildSpec();
    } catch (error) {
      setStatus(error && error.message ? error.message : "Spec is not ready.", "error");
      return;
    }
    elements.exportPng.disabled = true;
    state.isExporting = true;
    renderActions();
    setStatus(tr("figureExporting"), "busy");
    try {
      const response = await fetch("/api/render-figure", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(spec)
      });
      if (!response.ok) {
        throw new Error(await responseError(response));
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "slidebridge_figure.png";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(function () {
        URL.revokeObjectURL(url);
      }, 2000);
      setStatus(tr("figureExportComplete"), "ok");
    } catch (error) {
      setStatus(error && error.message ? error.message : "Export failed.", "error");
    }
    state.isExporting = false;
    renderActions();
  }

  function defaultPatchRect(slot) {
    const size = 260;
    const col = slot % 6;
    const row = Math.floor(slot / 6);
    return [80 + col * 280, 1180 + row * 280, size, size];
  }

  function firstAvailableSlot() {
    const used = new Set(state.slots.map((slot) => slot.slot));
    for (let slot = 0; slot < MAX_PATCH_SLOTS; slot += 1) {
      if (!used.has(slot)) {
        return slot;
      }
    }
    return null;
  }

  function activeSlot() {
    return state.slots.find((slot) => slot.slot === state.activeSlot) || state.slots[0] || null;
  }

  function isActive(role, slot) {
    if (role !== state.activeRole) {
      return false;
    }
    return role === "main" || Number(slot) === Number(state.activeSlot);
  }

  function slotLabel(slot) {
    return String.fromCharCode("B".charCodeAt(0) + Number(slot));
  }

  function snap(value) {
    const numeric = Math.round(Number(value));
    return state.snapToGrid ? Math.round(numeric / SNAP_STEP) * SNAP_STEP : numeric;
  }

  function clamp(value, minValue, maxValue) {
    return Math.max(minValue, Math.min(maxValue, value));
  }

  async function responseError(response) {
    try {
      const payload = await response.json();
      return payload.detail || response.statusText || "Export failed.";
    } catch (error) {
      return response.statusText || "Export failed.";
    }
  }

  function setStatus(message, stateName) {
    elements.status.textContent = message || "";
    elements.status.dataset.state = stateName || "";
  }

  function fullSlideBbox() {
    if (!window.SlideBridgeViewer || !window.SlideBridgeViewer.getCurrentSlideInfo) {
      return null;
    }
    const info = window.SlideBridgeViewer.getCurrentSlideInfo();
    const width = info ? Number(info.width) : 0;
    const height = info ? Number(info.height) : 0;
    if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
      return null;
    }
    return [0, 0, Math.round(width), Math.round(height)];
  }

  function tr(key) {
    const api = window.SlideBridgeViewer;
    if (api && api.translate) {
      return api.translate(key);
    }
    return key;
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

  function boundedNumber(value, minValue, maxValue, fallback) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return fallback;
    }
    return Math.max(minValue, Math.min(maxValue, numeric));
  }

  initializeWhenReady();
}());
