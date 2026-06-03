(function () {
  const SLOT_COUNT = 6;
  const SLOT_LABELS = ["B", "C", "D", "E", "F", "G"];
  const CANVAS = {width: 2400, height: 1800, background: "white"};

  const state = {
    activeSlot: 0,
    heatmapLayerId: "",
    overlayOpacity: 0.45,
    opacityTouched: false,
    mainBbox: null,
    mainMode: "overlay",
    scalebarUm: null,
    slots: SLOT_LABELS.map(function (label, slot) {
      return {slot, label, bbox: null, mode: slot === 0 ? "raw" : "overlay"};
    })
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
    if (!elements.root) {
      return;
    }
    initialized = true;
    buildPreview();
    buildSlotRows();
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
      mainPreview: document.getElementById("figure-preview-main"),
      gridPreview: document.getElementById("figure-preview-grid"),
      setMain: document.getElementById("figure-set-main"),
      layer: document.getElementById("figure-heatmap-layer"),
      mainMode: document.getElementById("figure-main-mode"),
      opacity: document.getElementById("figure-opacity"),
      opacityValue: document.getElementById("figure-opacity-value"),
      scalebar: document.getElementById("figure-scalebar"),
      slotList: document.getElementById("figure-slot-list"),
      selectPatch: document.getElementById("figure-select-patch"),
      copySpec: document.getElementById("figure-copy-spec"),
      exportPng: document.getElementById("figure-export"),
      status: document.getElementById("figure-status")
    };
  }

  function buildPreview() {
    elements.gridPreview.innerHTML = "";
    state.slots.forEach(function (slot) {
      const item = document.createElement("div");
      item.className = "figure-preview-slot";
      item.dataset.slot = String(slot.slot);
      item.textContent = slot.label;
      elements.gridPreview.appendChild(item);
    });
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
        state.activeSlot = slot.slot;
        render();
      });

      row.addEventListener("click", function (event) {
        if (event.target === mode) {
          return;
        }
        state.activeSlot = slot.slot;
        render();
      });
      row.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
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
      const bbox = window.SlideBridgeViewer.getCurrentViewportBbox();
      if (!bbox) {
        setStatus("Viewport is not ready.", "error");
        return;
      }
      state.mainBbox = bbox;
      setStatus("Main panel set from current view.", "ok");
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

    elements.selectPatch.addEventListener("click", async function () {
      try {
        setStatus("Selection mode active.", "");
        const bbox = await window.SlideBridgeViewer.selectSquareRegion();
        const slot = state.slots[state.activeSlot];
        slot.bbox = bbox;
        const nextEmpty = state.slots.find((item) => !item.bbox && item.slot > slot.slot)
          || state.slots.find((item) => !item.bbox);
        if (nextEmpty) {
          state.activeSlot = nextEmpty.slot;
        }
        setStatus(`Slot ${slot.label} set.`, "ok");
      } catch (error) {
        setStatus(error && error.message ? error.message : "Selection failed.", "error");
      }
      render();
    });

    elements.copySpec.addEventListener("click", async function () {
      try {
        const spec = buildSpec();
        await copyText(JSON.stringify(spec, null, 2));
        setStatus("Figure spec copied.", "ok");
      } catch (error) {
        setStatus(error && error.message ? error.message : "Spec is not ready.", "error");
      }
    });

    elements.exportPng.addEventListener("click", exportPng);
  }

  function refreshFromViewer() {
    const api = window.SlideBridgeViewer;
    const layers = api.getRasterHeatmapLayers();
    const previous = state.heatmapLayerId;
    elements.layer.innerHTML = "";
    if (!layers.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No raster heatmap";
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
    renderPreview();
    renderSlots();
    renderActions();
  }

  function renderModes(overlayAvailable) {
    elements.mainMode.value = state.mainMode;
    setOverlayOptionDisabled(elements.mainMode, !overlayAvailable);
    Array.from(elements.slotList.querySelectorAll("[data-slot-mode]")).forEach(function (select) {
      const slot = state.slots[Number(select.dataset.slotMode)];
      select.value = slot.mode;
      setOverlayOptionDisabled(select, !overlayAvailable);
    });
  }

  function setOverlayOptionDisabled(select, disabled) {
    Array.from(select.options).forEach(function (option) {
      if (option.value === "overlay") {
        option.disabled = disabled;
      }
    });
  }

  function renderPreview() {
    elements.mainPreview.dataset.ready = state.mainBbox ? "true" : "false";
    elements.mainPreview.textContent = state.mainBbox ? "A" : "A";
    Array.from(elements.gridPreview.querySelectorAll(".figure-preview-slot")).forEach(function (item) {
      const slot = state.slots[Number(item.dataset.slot)];
      item.dataset.ready = slot.bbox ? "true" : "false";
    });
  }

  function renderSlots() {
    Array.from(elements.slotList.querySelectorAll(".figure-slot-row")).forEach(function (row) {
      const slot = state.slots[Number(row.dataset.slot)];
      const summary = row.querySelector(".figure-slot-summary");
      row.classList.toggle("active", slot.slot === state.activeSlot);
      row.dataset.ready = slot.bbox ? "true" : "false";
      summary.textContent = slot.bbox ? `${slot.bbox.join(", ")} | ${slot.mode}` : "empty";
    });
  }

  function renderActions() {
    const hasMain = Boolean(state.mainBbox);
    elements.copySpec.disabled = !hasMain;
    elements.exportPng.disabled = !hasMain;
    elements.selectPatch.disabled = !window.SlideBridgeViewer || !window.SlideBridgeViewer.selectSquareRegion;
  }

  function renderOpacity() {
    elements.opacityValue.textContent = Number(state.overlayOpacity).toFixed(2);
  }

  function buildSpec() {
    if (!state.mainBbox) {
      throw new Error("Main panel is not set.");
    }
    return {
      slide_id: window.SlideBridgeViewer.getSelectedSlideId(),
      canvas: {...CANVAS},
      heatmap_layer_id: state.heatmapLayerId,
      overlay_opacity: Number(state.overlayOpacity),
      main: {
        bbox: state.mainBbox.slice(),
        mode: state.mainMode,
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
    setStatus("Exporting PNG.", "");
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
      setStatus("PNG export requested.", "ok");
    } catch (error) {
      setStatus(error && error.message ? error.message : "Export failed.", "error");
    }
    renderActions();
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
