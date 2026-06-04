(function () {
  "use strict";

  const configElement = document.getElementById("slidebridge-app-config");
  const config = JSON.parse((configElement && configElement.textContent) || "{}");
  const state = {
    entries: [],
    sessions: []
  };
  const els = {};

  document.addEventListener("DOMContentLoaded", initialize);

  function initialize() {
    collectElements();
    els.version.textContent = config.version || "";
    renderProfiles();
    addHeatmapLayer("low", "");
    bindEvents();
    renderSummary();
    refreshSessions();
  }

  function collectElements() {
    Object.assign(els, {
      version: document.getElementById("app-version"),
      status: document.getElementById("status"),
      profileSelect: document.getElementById("profile-select"),
      host: document.getElementById("remote-host"),
      user: document.getElementById("remote-user"),
      sshPort: document.getElementById("ssh-port"),
      remoteRunner: document.getElementById("remote-runner"),
      remoteWorkdir: document.getElementById("remote-workdir"),
      identityFile: document.getElementById("identity-file"),
      sshOptions: document.getElementById("ssh-options"),
      remoteDir: document.getElementById("remote-dir"),
      remotePath: document.getElementById("remote-path"),
      localPort: document.getElementById("local-port"),
      remotePort: document.getElementById("remote-port"),
      patches: document.getElementById("patches-path"),
      annotations: document.getElementById("annotations-path"),
      annotationFormat: document.getElementById("annotation-format"),
      heatmapLayers: document.getElementById("heatmap-layers"),
      fileTable: document.getElementById("file-table"),
      browserPath: document.getElementById("browser-path"),
      fileFilter: document.getElementById("file-filter"),
      commandOutput: document.getElementById("command-output"),
      openViewer: document.getElementById("open-viewer"),
      sessionList: document.getElementById("session-list"),
      summarySlide: document.getElementById("summary-slide"),
      summaryHeatmaps: document.getElementById("summary-heatmaps"),
      summaryPatches: document.getElementById("summary-patches"),
      summaryAnnotations: document.getElementById("summary-annotations"),
      summaryUrl: document.getElementById("summary-url")
    });
  }

  function bindEvents() {
    els.profileSelect.addEventListener("change", applySelectedProfile);
    document.getElementById("test-connection").addEventListener("click", testConnection);
    document.getElementById("browse-remote").addEventListener("click", browseRemote);
    document.getElementById("parent-dir").addEventListener("click", browseParent);
    document.getElementById("build-command").addEventListener("click", buildCommand);
    document.getElementById("launch-viewer").addEventListener("click", launchViewer);
    document.getElementById("add-heatmap-layer").addEventListener("click", function () {
      addHeatmapLayer("", "");
      renderSummary();
    });
    document.getElementById("copy-command").addEventListener("click", copyCommand);
    els.fileFilter.addEventListener("input", renderFiles);
    [
      els.host,
      els.user,
      els.sshPort,
      els.remoteRunner,
      els.remoteWorkdir,
      els.identityFile,
      els.sshOptions,
      els.remoteDir,
      els.remotePath,
      els.localPort,
      els.remotePort,
      els.patches,
      els.annotations,
      els.annotationFormat
    ].forEach((element) => element.addEventListener("input", debounce(onInputsChanged, 150)));
  }

  function connectionPayload() {
    return {
      host: els.host.value.trim(),
      user: els.user.value.trim(),
      ssh_port: els.sshPort.value.trim(),
      remote_runner: els.remoteRunner.value.trim() || "slidebridge",
      remote_workdir: els.remoteWorkdir.value.trim(),
      identity_file: els.identityFile.value.trim(),
      ssh_options: els.sshOptions.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
    };
  }

  function launchPayload() {
    return {
      ...connectionPayload(),
      remote_path: els.remotePath.value.trim(),
      remote_dir: els.remoteDir.value.trim(),
      local_host: "127.0.0.1",
      local_port: els.localPort.value.trim() || "7860",
      remote_host: "127.0.0.1",
      remote_port: els.remotePort.value.trim() || "7860",
      patches: els.patches.value.trim(),
      annotations: els.annotations.value.trim(),
      annotation_format: els.annotationFormat.value,
      raster_heatmap_layers: heatmapLayerPayload()
    };
  }

  function heatmapLayerPayload() {
    return Array.from(els.heatmapLayers.querySelectorAll(".layer-row"))
      .map((row) => ({
        name: row.querySelector("[data-layer-name]").value.trim(),
        path: row.querySelector("[data-layer-path]").value.trim()
      }))
      .filter((layer) => layer.path);
  }

  function renderProfiles() {
    const profiles = Array.isArray(config.profiles) ? config.profiles : [];
    profiles.forEach((profile) => {
      const option = document.createElement("option");
      option.value = profile.name || "";
      option.textContent = profile.name || profile.host || "profile";
      els.profileSelect.appendChild(option);
    });
  }

  function applySelectedProfile() {
    const profileName = els.profileSelect.value;
    const profile = (config.profiles || []).find((item) => item.name === profileName);
    if (!profile) {
      return;
    }
    els.host.value = profile.host || "";
    els.user.value = profile.user || "";
    els.sshPort.value = profile.ssh_port || "";
    els.remoteRunner.value = profile.remote_runner || "slidebridge";
    els.remoteWorkdir.value = profile.remote_workdir || "";
    els.identityFile.value = profile.identity_file || "";
    els.sshOptions.value = (profile.ssh_options || []).join("\n");
    els.remoteDir.value = profile.root || "";
    els.localPort.value = profile.local_port || "7860";
    els.remotePort.value = profile.remote_port || "7860";
    onInputsChanged();
    setStatus(`Profile ${profileName} loaded.`, "ok");
  }

  async function testConnection() {
    setBusy("Testing SSH connection...");
    try {
      const result = await postJson("/api/remote/test", connectionPayload());
      setStatus(result.ok ? "Remote SlideBridge responded." : (result.stderr || "Remote test failed."), result.ok ? "ok" : "error");
    } catch (error) {
      setStatus(error.message, "error");
    }
  }

  async function browseRemote() {
    const payload = {...connectionPayload(), remote_dir: els.remoteDir.value.trim()};
    setBusy("Loading remote directory...");
    try {
      const result = await postJson("/api/remote/list", payload);
      if (!result.ok) {
        setStatus(result.stderr || "Remote directory listing failed.", "error");
        return;
      }
      state.entries = result.entries || [];
      els.browserPath.textContent = payload.remote_dir || "remote directory";
      renderFiles();
      setStatus(`${state.entries.length} entries loaded.`, "ok");
    } catch (error) {
      setStatus(error.message, "error");
    }
  }

  function browseParent() {
    const current = els.remoteDir.value.trim().replace(/\/+$/, "");
    if (!current || current === "/") {
      els.remoteDir.value = "/";
    } else {
      const index = current.lastIndexOf("/");
      els.remoteDir.value = index <= 0 ? "/" : current.slice(0, index);
    }
    browseRemote();
  }

  function renderFiles() {
    const filter = els.fileFilter.value.trim().toLowerCase();
    const entries = state.entries.filter((entry) => !filter || entry.path.toLowerCase().includes(filter));
    els.fileTable.innerHTML = "";
    if (!entries.length) {
      const empty = document.createElement("div");
      empty.className = "file-row";
      empty.textContent = "No files loaded.";
      els.fileTable.appendChild(empty);
      return;
    }
    entries.forEach((entry) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "file-row";
      row.dataset.kind = entry.kind;
      row.title = entry.path;
      row.innerHTML = [
        `<span>${escapeHtml(entry.kind)}</span>`,
        `<span class="file-name">${escapeHtml(entry.name)}</span>`,
        `<span class="file-size">${entry.size === null || entry.size === undefined ? "" : escapeHtml(String(entry.size))}</span>`,
        `<span class="file-modified">${escapeHtml(entry.modified || "")}</span>`
      ].join("");
      const tags = document.createElement("span");
      tags.className = "file-tags";
      fileTags(entry).forEach((tag) => {
        const chip = document.createElement("span");
        chip.className = "tag";
        chip.textContent = tag;
        tags.appendChild(chip);
      });
      row.querySelector(".file-name").appendChild(tags);
      row.addEventListener("click", function () {
        selectEntry(entry);
      });
      els.fileTable.appendChild(row);
    });
  }

  function fileTags(entry) {
    if (entry.kind === "directory") {
      return ["dir"];
    }
    const tags = [];
    if (entry.is_slide) tags.push("slide");
    if (entry.is_heatmap) tags.push("heatmap");
    if (entry.is_patches) tags.push("patches");
    if (entry.is_annotation) tags.push("annotation");
    return tags;
  }

  function selectEntry(entry) {
    if (entry.kind === "directory") {
      els.remoteDir.value = entry.path;
      browseRemote();
      return;
    }
    if (entry.is_slide && (!entry.is_heatmap || !els.remotePath.value.trim())) {
      els.remotePath.value = entry.path;
    } else if (entry.is_heatmap) {
      fillFirstEmptyHeatmap(entry.path);
    } else if (entry.is_annotation) {
      els.annotations.value = entry.path;
    } else if (entry.is_patches) {
      els.patches.value = entry.path;
    } else {
      els.remotePath.value = entry.path;
    }
    onInputsChanged();
  }

  function fillFirstEmptyHeatmap(path) {
    const rows = Array.from(els.heatmapLayers.querySelectorAll(".layer-row"));
    const row = rows.find((item) => !item.querySelector("[data-layer-path]").value.trim()) || addHeatmapLayer("", "");
    row.querySelector("[data-layer-path]").value = path;
    if (!row.querySelector("[data-layer-name]").value.trim()) {
      row.querySelector("[data-layer-name]").value = `layer${rows.length + 1}`;
    }
  }

  function addHeatmapLayer(name, path) {
    const row = document.createElement("div");
    row.className = "layer-row";
    row.innerHTML = [
      `<input data-layer-name placeholder="name" value="${escapeAttribute(name || "")}">`,
      `<input data-layer-path placeholder="/data/heatmaps/case.png" value="${escapeAttribute(path || "")}">`,
      `<button type="button" data-remove-layer>Remove</button>`
    ].join("");
    row.querySelector("[data-remove-layer]").addEventListener("click", function () {
      row.remove();
      onInputsChanged();
    });
    row.querySelectorAll("input").forEach((input) => input.addEventListener("input", debounce(onInputsChanged, 150)));
    els.heatmapLayers.appendChild(row);
    return row;
  }

  async function buildCommand() {
    try {
      const result = await postJson("/api/session/command", launchPayload());
      updateCommand(result);
      setStatus("Command ready.", "ok");
    } catch (error) {
      setStatus(error.message, "error");
    }
  }

  async function launchViewer() {
    setBusy("Starting viewer session...");
    try {
      const result = await postJson("/api/session/launch", launchPayload());
      updateCommand(result);
      await refreshSessions();
      setStatus("Viewer session started. Open the viewer when the tunnel is ready.", "ok");
    } catch (error) {
      setStatus(error.message, "error");
    }
  }

  async function refreshSessions() {
    const result = await fetchJson("/api/session/list");
    state.sessions = result.sessions || [];
    renderSessions();
  }

  function renderSessions() {
    els.sessionList.innerHTML = "";
    if (!state.sessions.length) {
      els.sessionList.textContent = "No viewer sessions yet.";
      return;
    }
    state.sessions.forEach((session) => {
      const row = document.createElement("div");
      row.className = "session-row";
      row.innerHTML = [
        `<div><strong>${escapeHtml(session.id)}</strong><br><span>${escapeHtml(session.status)} - ${escapeHtml(session.slide || "")}</span></div>`,
        `<div class="action-row"><a href="${escapeAttribute(session.viewer_url)}" target="_blank" rel="noreferrer">Open</a><button type="button" data-stop="${escapeAttribute(session.id)}">Stop</button></div>`
      ].join("");
      row.querySelector("[data-stop]").addEventListener("click", async function () {
        await postJson(`/api/session/${encodeURIComponent(session.id)}/stop`, {});
        await refreshSessions();
      });
      els.sessionList.appendChild(row);
    });
  }

  function updateCommand(session) {
    els.commandOutput.value = session.command || "";
    els.openViewer.href = session.viewer_url || "http://127.0.0.1:7860";
    els.summaryUrl.textContent = session.viewer_url || "http://127.0.0.1:7860";
    renderSummary();
  }

  function renderSummary() {
    const layers = heatmapLayerPayload();
    els.summarySlide.textContent = els.remotePath.value.trim() || "not selected";
    els.summaryHeatmaps.textContent = layers.length ? layers.map((layer) => layer.name || layer.path).join(", ") : "none";
    els.summaryPatches.textContent = els.patches.value.trim() || "none";
    els.summaryAnnotations.textContent = els.annotations.value.trim() || "none";
  }

  function onInputsChanged() {
    renderSummary();
  }

  async function copyCommand() {
    if (!els.commandOutput.value.trim()) {
      await buildCommand();
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(els.commandOutput.value);
      setStatus("Command copied.", "ok");
    }
  }

  async function fetchJson(url) {
    const response = await fetch(url, {cache: "no-store"});
    return parseResponse(response);
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    return parseResponse(response);
  }

  async function parseResponse(response) {
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || response.statusText || "Request failed.");
    }
    return payload;
  }

  function setBusy(message) {
    setStatus(message, "");
  }

  function setStatus(message, stateName) {
    els.status.textContent = message || "";
    els.status.dataset.state = stateName || "";
  }

  function debounce(fn, delay) {
    let timeout = null;
    return function () {
      window.clearTimeout(timeout);
      timeout = window.setTimeout(fn, delay);
    };
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replaceAll("'", "&#39;");
  }
})();
