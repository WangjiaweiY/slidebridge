(function () {
  "use strict";

  const configElement = document.getElementById("slidebridge-app-config");
  const config = JSON.parse((configElement && configElement.textContent) || "{}");
  const state = {
    entries: [],
    sessions: [],
    fileTarget: null
  };
  const els = {};
  const LANGUAGE_STORAGE_KEY = "slidebridge-app-language";
  const DEFAULT_LANGUAGE = "zh-CN";
  let currentLanguage = loadLanguagePreference();
  const translations = {
    "zh-CN": {
      documentTitle: "SlideBridge 启动器",
      appTitle: "Viewer 启动器",
      appSubtitle: "通过 SSH 浏览远端 WSI，并加载 heatmap、patch、annotation 和论文图工作流。",
      sshConnection: "SSH 连接",
      profile: "连接配置",
      manual: "手动填写",
      host: "主机",
      user: "用户",
      sshPort: "SSH 端口",
      remoteRuntime: "远端环境",
      runtimePath: "默认环境",
      runtimeConda: "Conda 环境",
      runtimeCustom: "自定义命令",
      condaCommand: "Conda 可执行文件",
      condaCommandPlaceholder: "/path/to/miniconda3/bin/conda",
      condaEnv: "Conda 环境名",
      customRunner: "自定义命令",
      identityFile: "SSH key 文件",
      remoteWorkdir: "远端工作目录",
      sshOptions: "SSH 额外参数",
      optional: "可选",
      testConnection: "测试 SSH",
      testRuntime: "测试远端环境",
      pickFromBrowser: "从列表选择",
      buildCommand: "生成命令",
      sshHint: "先测试 SSH 并浏览目录；远端环境只在生成命令或启动 viewer 时使用。如果服务器需要密码，密码提示会出现在启动本应用的终端里。",
      viewerInputs: "Viewer 输入",
      remoteDirectory: "远端目录",
      browse: "浏览",
      parentDir: "上级目录",
      slidePath: "切片路径",
      localPort: "本地端口",
      remotePort: "远端端口",
      patches: "Patch 坐标",
      annotations: "Annotation",
      annotationFormat: "Annotation 格式",
      heatmapLayers: "Heatmap 图层",
      addHeatmapLayer: "添加 heatmap 图层",
      language: "语言",
      launchViewer: "启动 viewer",
      remoteFileBrowser: "远端文件浏览器",
      noDirectoryLoaded: "尚未加载目录",
      filterFiles: "筛选文件",
      launchSummary: "启动摘要",
      slide: "切片",
      viewerUrl: "Viewer 地址",
      equivalentCommand: "等价命令",
      copyCommand: "复制命令",
      openViewer: "打开 viewer",
      viewerSessions: "Viewer 会话",
      layerName: "图层名",
      remove: "删除",
      directory: "目录",
      file: "文件",
      slideTag: "切片",
      directoryTag: "目录",
      patchTag: "patch",
      noFilesLoaded: "尚未加载文件。",
      noSessions: "暂无 viewer 会话。",
      notSelected: "未选择",
      none: "无",
      remoteDirectoryFallback: "远端目录",
      profileLoaded: "已加载连接配置：{name}",
      testingSsh: "正在测试 SSH 连接...",
      testingRuntime: "正在测试远端环境...",
      remoteResponded: "SSH 连接可用。",
      remoteFailed: "SSH 连接失败。",
      runtimeResponded: "远端环境可用。",
      runtimeFailed: "远端环境测试失败。",
      loadingRemoteDir: "正在加载远端目录...",
      listingFailed: "远端目录列表获取失败。",
      entriesLoaded: "已加载 {count} 个条目。",
      missingCondaCommand: "请先填写 Conda 可执行文件，或点击“从列表选择”后在文件浏览器里选择 conda。",
      pickCondaHint: "请在远端文件浏览器里打开 conda 所在目录，然后点击 conda 文件。",
      condaSelected: "已选择 Conda 可执行文件：{path}",
      commandReady: "命令已生成。",
      startingViewer: "正在启动 viewer 会话...",
      viewerStarted: "viewer 会话已启动。隧道就绪后打开 viewer。",
      commandCopied: "命令已复制。",
      requestFailed: "请求失败。",
      prepared: "已准备",
      running: "运行中",
      stopped: "已停止",
      open: "打开",
      stop: "停止"
    },
    en: {
      documentTitle: "SlideBridge App",
      appTitle: "Viewer Launcher",
      appSubtitle: "Browse remote WSI over SSH and load heatmaps, patches, annotations, and figure workflows.",
      sshConnection: "SSH connection",
      profile: "Profile",
      manual: "manual",
      host: "Host",
      user: "User",
      sshPort: "SSH port",
      remoteRuntime: "Remote environment",
      runtimePath: "Default environment",
      runtimeConda: "Conda environment",
      runtimeCustom: "Custom command",
      condaCommand: "Conda executable",
      condaCommandPlaceholder: "/path/to/miniconda3/bin/conda",
      condaEnv: "Conda environment",
      customRunner: "Custom command",
      identityFile: "SSH key file",
      remoteWorkdir: "Remote workdir",
      sshOptions: "SSH options",
      optional: "optional",
      testConnection: "Test SSH",
      testRuntime: "Test remote environment",
      pickFromBrowser: "Pick from list",
      buildCommand: "Build command",
      sshHint: "Test SSH and browse directories first. The remote environment is only used when building commands or launching the viewer. Password prompts appear in the terminal that started this app.",
      viewerInputs: "Viewer inputs",
      remoteDirectory: "Remote directory",
      browse: "Browse",
      parentDir: "Parent",
      slidePath: "Slide path",
      localPort: "Local port",
      remotePort: "Remote port",
      patches: "Patch coordinates",
      annotations: "Annotations",
      annotationFormat: "Annotation format",
      heatmapLayers: "Heatmap layers",
      addHeatmapLayer: "Add heatmap layer",
      language: "Language",
      launchViewer: "Launch viewer",
      remoteFileBrowser: "Remote file browser",
      noDirectoryLoaded: "No directory loaded",
      filterFiles: "Filter files",
      launchSummary: "Launch summary",
      slide: "Slide",
      viewerUrl: "Viewer URL",
      equivalentCommand: "Equivalent command",
      copyCommand: "Copy command",
      openViewer: "Open viewer",
      viewerSessions: "Viewer sessions",
      layerName: "name",
      remove: "Remove",
      directory: "directory",
      file: "file",
      slideTag: "slide",
      directoryTag: "dir",
      patchTag: "patches",
      noFilesLoaded: "No files loaded.",
      noSessions: "No viewer sessions yet.",
      notSelected: "not selected",
      none: "none",
      remoteDirectoryFallback: "remote directory",
      profileLoaded: "Profile {name} loaded.",
      testingSsh: "Testing SSH connection...",
      testingRuntime: "Testing remote environment...",
      remoteResponded: "SSH connection is available.",
      remoteFailed: "SSH connection failed.",
      runtimeResponded: "Remote environment is available.",
      runtimeFailed: "Remote environment test failed.",
      loadingRemoteDir: "Loading remote directory...",
      listingFailed: "Remote directory listing failed.",
      entriesLoaded: "{count} entries loaded.",
      missingCondaCommand: "Fill the Conda executable first, or click Pick from list and choose the conda file in the remote file browser.",
      pickCondaHint: "Open the directory that contains conda in the remote file browser, then click the conda file.",
      condaSelected: "Selected Conda executable: {path}",
      commandReady: "Command ready.",
      startingViewer: "Starting viewer session...",
      viewerStarted: "Viewer session started. Open the viewer when the tunnel is ready.",
      commandCopied: "Command copied.",
      requestFailed: "Request failed.",
      prepared: "prepared",
      running: "running",
      stopped: "stopped",
      open: "Open",
      stop: "Stop"
    }
  };

  document.addEventListener("DOMContentLoaded", initialize);

  function initialize() {
    collectElements();
    els.languageSelect.value = currentLanguage;
    els.version.textContent = config.version || "";
    renderProfiles();
    addHeatmapLayer("low", "");
    bindEvents();
    updateRuntimeFields();
    applyLanguage();
    renderSummary();
    refreshSessions();
  }

  function collectElements() {
    Object.assign(els, {
      version: document.getElementById("app-version"),
      status: document.getElementById("status"),
      languageSelect: document.getElementById("language-select"),
      profileSelect: document.getElementById("profile-select"),
      host: document.getElementById("remote-host"),
      user: document.getElementById("remote-user"),
      sshPort: document.getElementById("ssh-port"),
      remoteRuntime: document.getElementById("remote-runtime"),
      condaCommand: document.getElementById("conda-command"),
      condaEnv: document.getElementById("conda-env"),
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
    els.languageSelect.addEventListener("change", changeLanguage);
    els.remoteRuntime.addEventListener("change", onRuntimeChanged);
    els.profileSelect.addEventListener("change", applySelectedProfile);
    document.getElementById("test-connection").addEventListener("click", testConnection);
    document.getElementById("test-runtime").addEventListener("click", testRuntime);
    document.getElementById("pick-conda-command").addEventListener("click", pickCondaCommand);
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
      els.remoteRuntime,
      els.condaCommand,
      els.condaEnv,
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

  function changeLanguage() {
    currentLanguage = normalizeLanguage(els.languageSelect.value);
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, currentLanguage);
    applyLanguage();
  }

  function applyLanguage() {
    document.documentElement.lang = currentLanguage;
    document.title = t("documentTitle");
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      element.textContent = t(element.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
      element.placeholder = t(element.dataset.i18nPlaceholder);
    });
    if (!els.browserPath.dataset.loaded) {
      els.browserPath.textContent = t("noDirectoryLoaded");
    }
    updateGeneratedLanguage();
  }

  function updateGeneratedLanguage() {
    els.heatmapLayers.querySelectorAll(".layer-row").forEach((row) => {
      row.querySelector("[data-layer-name]").placeholder = t("layerName");
      row.querySelector("[data-remove-layer]").textContent = t("remove");
    });
    renderFiles();
    renderSessions();
    renderSummary();
  }

  function onRuntimeChanged() {
    updateRuntimeFields();
    onInputsChanged();
  }

  function updateRuntimeFields() {
    const runtime = els.remoteRuntime.value || "path";
    document.querySelectorAll("[data-runtime-field]").forEach((element) => {
      element.classList.toggle("is-hidden", element.dataset.runtimeField !== runtime);
    });
  }

  function connectionPayload(options) {
    const payload = {
      host: els.host.value.trim(),
      user: els.user.value.trim(),
      ssh_port: els.sshPort.value.trim(),
      remote_workdir: els.remoteWorkdir.value.trim(),
      identity_file: els.identityFile.value.trim(),
      ssh_options: els.sshOptions.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
    };
    if (options && options.includeRuntime) {
      payload.remote_runner = buildRemoteRunner();
    }
    return payload;
  }

  function buildRemoteRunner() {
    const runtime = els.remoteRuntime.value || "path";
    if (runtime === "conda") {
      const condaCommand = els.condaCommand.value.trim();
      if (!condaCommand) {
        throw new Error(t("missingCondaCommand"));
      }
      const condaEnv = els.condaEnv.value.trim() || "slidebridge";
      return `${condaCommand} run -n ${condaEnv} slidebridge`;
    }
    if (runtime === "custom") {
      return els.remoteRunner.value.trim() || "slidebridge";
    }
    return "slidebridge";
  }

  function launchPayload() {
    return {
      ...connectionPayload({includeRuntime: true}),
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
    applyRemoteRunner(profile.remote_runner || "slidebridge");
    els.remoteWorkdir.value = profile.remote_workdir || "";
    els.identityFile.value = profile.identity_file || "";
    els.sshOptions.value = (profile.ssh_options || []).join("\n");
    els.remoteDir.value = profile.root || "";
    els.localPort.value = profile.local_port || "7860";
    els.remotePort.value = profile.remote_port || "7860";
    updateRuntimeFields();
    onInputsChanged();
    setStatus(t("profileLoaded", {name: profileName}), "ok");
  }

  function applyRemoteRunner(remoteRunner) {
    const parsed = parseRemoteRunner(remoteRunner);
    els.remoteRuntime.value = parsed.runtime;
    els.condaCommand.value = parsed.condaCommand || "conda";
    els.condaEnv.value = parsed.condaEnv || "slidebridge";
    els.remoteRunner.value = parsed.customRunner || "slidebridge";
  }

  function parseRemoteRunner(remoteRunner) {
    const runner = String(remoteRunner || "").trim();
    if (!runner || runner === "slidebridge") {
      return {runtime: "path"};
    }
    const condaMatch = runner.match(/^(.*?)\s+run\s+-n\s+(\S+)\s+slidebridge$/);
    if (condaMatch) {
      return {
        runtime: "conda",
        condaCommand: condaMatch[1],
        condaEnv: condaMatch[2]
      };
    }
    return {
      runtime: "custom",
      customRunner: runner
    };
  }

  async function testConnection() {
    setBusy(t("testingSsh"));
    try {
      const result = await postJson("/api/remote/test", connectionPayload());
      setStatus(result.ok ? t("remoteResponded") : (result.stderr || t("remoteFailed")), result.ok ? "ok" : "error");
    } catch (error) {
      setStatus(error.message, "error");
    }
  }

  async function testRuntime() {
    setBusy(t("testingRuntime"));
    try {
      const result = await postJson("/api/remote/runtime-test", connectionPayload({includeRuntime: true}));
      setStatus(result.ok ? t("runtimeResponded") : (result.stderr || t("runtimeFailed")), result.ok ? "ok" : "error");
    } catch (error) {
      setStatus(error.message, "error");
    }
  }

  function pickCondaCommand() {
    state.fileTarget = "conda";
    setStatus(t("pickCondaHint"), "ok");
  }

  async function browseRemote() {
    const payload = {...connectionPayload(), remote_dir: els.remoteDir.value.trim()};
    setBusy(t("loadingRemoteDir"));
    try {
      const result = await postJson("/api/remote/list", payload);
      if (!result.ok) {
        setStatus(result.stderr || t("listingFailed"), "error");
        return;
      }
      state.entries = result.entries || [];
      els.browserPath.dataset.loaded = "true";
      els.browserPath.textContent = payload.remote_dir || t("remoteDirectoryFallback");
      renderFiles();
      setStatus(t("entriesLoaded", {count: state.entries.length}), "ok");
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
      empty.textContent = t("noFilesLoaded");
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
        `<span>${escapeHtml(formatKind(entry.kind))}</span>`,
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
      return [t("directoryTag")];
    }
    const tags = [];
    if (entry.is_slide) tags.push(t("slideTag"));
    if (entry.is_heatmap) tags.push("heatmap");
    if (entry.is_patches) tags.push(t("patchTag"));
    if (entry.is_annotation) tags.push("annotation");
    return tags;
  }

  function formatKind(kind) {
    if (kind === "directory") return t("directory");
    if (kind === "file") return t("file");
    return kind || "";
  }

  function selectEntry(entry) {
    if (entry.kind === "directory") {
      els.remoteDir.value = entry.path;
      browseRemote();
      return;
    }
    if (state.fileTarget === "conda") {
      els.condaCommand.value = entry.path;
      state.fileTarget = null;
      setStatus(t("condaSelected", {path: entry.path}), "ok");
      onInputsChanged();
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
      `<input data-layer-name placeholder="${escapeAttribute(t("layerName"))}" value="${escapeAttribute(name || "")}">`,
      `<input data-layer-path placeholder="/data/heatmaps/case.png" value="${escapeAttribute(path || "")}">`,
      `<button type="button" data-remove-layer>${escapeHtml(t("remove"))}</button>`
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
      setStatus(t("commandReady"), "ok");
    } catch (error) {
      setStatus(error.message, "error");
    }
  }

  async function launchViewer() {
    setBusy(t("startingViewer"));
    try {
      const result = await postJson("/api/session/launch", launchPayload());
      updateCommand(result);
      await refreshSessions();
      setStatus(t("viewerStarted"), "ok");
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
      els.sessionList.textContent = t("noSessions");
      return;
    }
    state.sessions.forEach((session) => {
      const row = document.createElement("div");
      row.className = "session-row";
      row.innerHTML = [
        `<div><strong>${escapeHtml(session.id)}</strong><br><span>${escapeHtml(formatStatus(session.status))} - ${escapeHtml(session.slide || "")}</span></div>`,
        `<div class="action-row"><a href="${escapeAttribute(session.viewer_url)}" target="_blank" rel="noreferrer">${escapeHtml(t("open"))}</a><button type="button" data-stop="${escapeAttribute(session.id)}">${escapeHtml(t("stop"))}</button></div>`
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
    els.summarySlide.textContent = els.remotePath.value.trim() || t("notSelected");
    els.summaryHeatmaps.textContent = layers.length ? layers.map((layer) => layer.name || layer.path).join(", ") : t("none");
    els.summaryPatches.textContent = els.patches.value.trim() || t("none");
    els.summaryAnnotations.textContent = els.annotations.value.trim() || t("none");
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
      setStatus(t("commandCopied"), "ok");
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
      throw new Error(payload.detail || response.statusText || t("requestFailed"));
    }
    return payload;
  }

  function formatStatus(status) {
    if (status === "prepared") return t("prepared");
    if (status === "running") return t("running");
    if (status === "stopped") return t("stopped");
    return status || "";
  }

  function t(key, values) {
    const table = translations[currentLanguage] || translations[DEFAULT_LANGUAGE];
    const fallback = translations[DEFAULT_LANGUAGE][key] || key;
    let text = table[key] || fallback;
    Object.entries(values || {}).forEach(([name, value]) => {
      text = text.replaceAll(`{${name}}`, String(value));
    });
    return text;
  }

  function loadLanguagePreference() {
    try {
      return normalizeLanguage(window.localStorage.getItem(LANGUAGE_STORAGE_KEY));
    } catch (error) {
      return DEFAULT_LANGUAGE;
    }
  }

  function normalizeLanguage(language) {
    return language === "en" ? "en" : DEFAULT_LANGUAGE;
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
