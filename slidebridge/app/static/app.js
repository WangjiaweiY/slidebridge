(function () {
  "use strict";

  const configElement = document.getElementById("slidebridge-app-config");
  const config = JSON.parse((configElement && configElement.textContent) || "{}");
  const LANGUAGE_STORAGE_KEY = "slidebridge-app-language";
  const DEFAULT_LANGUAGE = "zh-CN";
  const state = {
    remoteHome: ""
  };
  const els = {};
  let currentLanguage = loadLanguagePreference();

  const translations = {
    "zh-CN": {
      documentTitle: "SlideBridge 启动器",
      appTitle: "Viewer 启动器",
      appSubtitle: "先连接远端 SSH 和 Python 环境，再进入 viewer 浏览目录、选择切片、加载热图和标注。",
      sshConnection: "SSH 连接",
      profile: "连接配置",
      manual: "手动填写",
      host: "主机",
      user: "用户",
      sshPort: "SSH 端口",
      identityFile: "SSH key 文件",
      sshOptions: "SSH 额外参数",
      optional: "可选",
      testConnection: "测试 SSH",
      sshHint: "支持 SSH key、ssh-agent、ssh config alias。若服务器需要密码，密码提示会出现在启动本应用的终端里。",
      runtimeSection: "远端环境",
      remoteRuntime: "运行方式",
      runtimePath: "默认 slidebridge",
      runtimeConda: "Conda 环境路径",
      runtimeCustom: "自定义命令",
      condaEnvPath: "Conda 环境路径",
      condaEnvPathPlaceholder: "/home/user/miniconda3/envs/slidebridge",
      browseRemoteDirectory: "浏览",
      remoteDirectoryBrowser: "远端目录选择",
      browserCurrentDirectory: "当前目录",
      openDirectory: "打开",
      parentDirectory: "上级目录",
      refreshDirectory: "刷新",
      chooseDirectory: "选择",
      enterDirectory: "进入",
      chooseCurrentDirectory: "选择当前目录",
      loadingDirectory: "正在加载远端目录...",
      directoryLoaded: "已加载 {count} 个文件夹。",
      noDirectories: "该目录下没有可显示的文件夹。",
      directorySelected: "已选择远端目录。",
      remoteBrowserHint: "只显示远端文件夹。选择 Conda 环境目录，例如 /home/user/miniconda3/envs/slidebridge。",
      customRunner: "自定义命令",
      remoteWorkdir: "远端工作目录",
      remoteWorkdirHint: "可选。仅在远端命令需要先 cd 到某个目录时填写；通常留空。",
      localPort: "本地端口",
      remotePort: "远端端口",
      testRuntime: "测试远端环境",
      buildCommand: "生成命令",
      runtimeHint: "Conda 环境路径会自动转换为该环境里的 python 命令，不依赖远端 PATH 中存在 conda。",
      language: "语言",
      launchViewer: "启动 viewer",
      launchSummary: "启动摘要",
      sshTarget: "SSH",
      remoteHome: "远端 home",
      runtime: "环境",
      viewerUrl: "Viewer 地址",
      equivalentCommand: "等价命令",
      copyCommand: "复制命令",
      notConfigured: "未填写",
      notTested: "未测试",
      profileLoaded: "已加载连接配置：{name}",
      testingSsh: "正在测试 SSH 连接...",
      testingRuntime: "正在测试远端环境...",
      remoteResponded: "SSH 连接可用。",
      remoteFailed: "SSH 连接失败。",
      runtimeResponded: "远端环境可用。",
      runtimeFailed: "远端环境测试失败。",
      missingCondaEnvPath: "请填写 Conda 环境路径，例如 /home/user/miniconda3/envs/slidebridge。",
      commandReady: "命令已生成。",
      startingViewer: "正在启动 viewer，并等待服务就绪...",
      viewerStarted: "viewer 已就绪，正在打开...",
      commandCopied: "命令已复制。",
      requestFailed: "请求失败。",
      prepared: "已准备",
      running: "运行中",
      stopped: "已停止"
    },
    en: {
      documentTitle: "SlideBridge Launcher",
      appTitle: "Viewer Launcher",
      appSubtitle: "Connect SSH and the remote Python runtime first, then browse directories, choose slides, and load heatmaps or annotations in the viewer.",
      sshConnection: "SSH connection",
      profile: "Profile",
      manual: "manual",
      host: "Host",
      user: "User",
      sshPort: "SSH port",
      identityFile: "SSH key file",
      sshOptions: "SSH options",
      optional: "optional",
      testConnection: "Test SSH",
      sshHint: "Supports SSH keys, ssh-agent, and ssh config aliases. Password prompts appear in the terminal that started this app.",
      runtimeSection: "Remote runtime",
      remoteRuntime: "Run with",
      runtimePath: "Default slidebridge",
      runtimeConda: "Conda env path",
      runtimeCustom: "Custom command",
      condaEnvPath: "Conda env path",
      condaEnvPathPlaceholder: "/home/user/miniconda3/envs/slidebridge",
      browseRemoteDirectory: "Browse",
      remoteDirectoryBrowser: "Remote directory picker",
      browserCurrentDirectory: "Current directory",
      openDirectory: "Open",
      parentDirectory: "Parent",
      refreshDirectory: "Refresh",
      chooseDirectory: "Choose",
      enterDirectory: "Enter",
      chooseCurrentDirectory: "Choose current directory",
      loadingDirectory: "Loading remote directory...",
      directoryLoaded: "{count} folders loaded.",
      noDirectories: "No visible folders in this directory.",
      directorySelected: "Remote directory selected.",
      remoteBrowserHint: "Only remote folders are shown. Choose the Conda env directory, for example /home/user/miniconda3/envs/slidebridge.",
      customRunner: "Custom command",
      remoteWorkdir: "Remote workdir",
      remoteWorkdirHint: "Optional. Fill this only when the remote command must cd into a directory first; usually leave it empty.",
      localPort: "Local port",
      remotePort: "Remote port",
      testRuntime: "Test runtime",
      buildCommand: "Build command",
      runtimeHint: "The Conda env path is converted to that environment's python command; it does not require conda on the remote PATH.",
      language: "Language",
      launchViewer: "Launch viewer",
      launchSummary: "Launch summary",
      sshTarget: "SSH",
      remoteHome: "Remote home",
      runtime: "Runtime",
      viewerUrl: "Viewer URL",
      equivalentCommand: "Equivalent command",
      copyCommand: "Copy command",
      notConfigured: "not configured",
      notTested: "not tested",
      profileLoaded: "Profile {name} loaded.",
      testingSsh: "Testing SSH connection...",
      testingRuntime: "Testing remote runtime...",
      remoteResponded: "SSH connection is available.",
      remoteFailed: "SSH connection failed.",
      runtimeResponded: "Remote runtime is available.",
      runtimeFailed: "Remote runtime test failed.",
      missingCondaEnvPath: "Fill the Conda env path, for example /home/user/miniconda3/envs/slidebridge.",
      commandReady: "Command ready.",
      startingViewer: "Starting viewer and waiting until it is ready...",
      viewerStarted: "Viewer is ready. Opening...",
      commandCopied: "Command copied.",
      requestFailed: "Request failed.",
      prepared: "prepared",
      running: "running",
      stopped: "stopped"
    }
  };

  document.addEventListener("DOMContentLoaded", initialize);

  function initialize() {
    collectElements();
    els.languageSelect.value = currentLanguage;
    els.version.textContent = config.version || "";
    renderProfiles();
    bindEvents();
    updateRuntimeFields();
    applyLanguage();
    renderSummary();
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
      identityFile: document.getElementById("identity-file"),
      sshOptions: document.getElementById("ssh-options"),
      remoteRuntime: document.getElementById("remote-runtime"),
      condaEnvPath: document.getElementById("conda-env-path"),
      remoteRunner: document.getElementById("remote-runner"),
      remoteWorkdir: document.getElementById("remote-workdir"),
      localPort: document.getElementById("local-port"),
      remotePort: document.getElementById("remote-port"),
      launchViewer: document.getElementById("launch-viewer"),
      commandOutput: document.getElementById("command-output"),
      summaryTarget: document.getElementById("summary-target"),
      summaryHome: document.getElementById("summary-home"),
      summaryRuntime: document.getElementById("summary-runtime"),
      summaryUrl: document.getElementById("summary-url"),
      remoteBrowserModal: document.getElementById("remote-browser-modal"),
      remoteBrowserPath: document.getElementById("remote-browser-path"),
      remoteBrowserList: document.getElementById("remote-browser-list"),
      remoteBrowserStatus: document.getElementById("remote-browser-status")
    });
  }

  function bindEvents() {
    els.languageSelect.addEventListener("change", changeLanguage);
    els.remoteRuntime.addEventListener("change", onRuntimeChanged);
    els.profileSelect.addEventListener("change", applySelectedProfile);
    document.getElementById("test-connection").addEventListener("click", testConnection);
    document.getElementById("test-runtime").addEventListener("click", testRuntime);
    document.getElementById("build-command").addEventListener("click", buildCommand);
    els.launchViewer.addEventListener("click", launchViewer);
    document.getElementById("copy-command").addEventListener("click", copyCommand);
    document.getElementById("browse-conda-env-path").addEventListener("click", openRemoteDirectoryBrowser);
    document.getElementById("remote-browser-close").addEventListener("click", closeRemoteDirectoryBrowser);
    document.getElementById("remote-browser-open-path").addEventListener("click", function () {
      loadRemoteBrowserDirectory(els.remoteBrowserPath.value.trim());
    });
    document.getElementById("remote-browser-parent").addEventListener("click", function () {
      loadRemoteBrowserDirectory(parentDirectory(els.remoteBrowserPath.value.trim()));
    });
    document.getElementById("remote-browser-refresh").addEventListener("click", function () {
      loadRemoteBrowserDirectory(els.remoteBrowserPath.value.trim());
    });
    document.getElementById("remote-browser-select-current").addEventListener("click", function () {
      chooseRemoteDirectory(els.remoteBrowserPath.value.trim());
    });
    els.remoteBrowserModal.addEventListener("click", function (event) {
      if (event.target === els.remoteBrowserModal) {
        closeRemoteDirectoryBrowser();
      }
    });
    window.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !els.remoteBrowserModal.hidden) {
        closeRemoteDirectoryBrowser();
      }
    });
    [
      els.host,
      els.user,
      els.sshPort,
      els.identityFile,
      els.sshOptions,
      els.remoteRuntime,
      els.condaEnvPath,
      els.remoteRunner,
      els.remoteWorkdir,
      els.localPort,
      els.remotePort
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
      identity_file: els.identityFile.value.trim(),
      ssh_options: els.sshOptions.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean),
      remote_workdir: els.remoteWorkdir.value.trim()
    };
    if (options && options.includeRuntime) {
      Object.assign(payload, runtimePayload());
    }
    return payload;
  }

  function runtimePayload() {
    const runtime = els.remoteRuntime.value || "path";
    if (runtime === "conda") {
      const envPath = els.condaEnvPath.value.trim();
      if (!envPath) {
        throw new Error(t("missingCondaEnvPath"));
      }
      return {conda_env_path: envPath};
    }
    if (runtime === "custom") {
      return {remote_runner: els.remoteRunner.value.trim() || "slidebridge"};
    }
    return {};
  }

  function launchPayload() {
    return {
      ...connectionPayload({includeRuntime: true}),
      remote_home: state.remoteHome || "",
      local_host: "127.0.0.1",
      local_port: els.localPort.value.trim() || "7860",
      remote_host: "127.0.0.1",
      remote_port: els.remotePort.value.trim() || "7860",
      max_slides: 500
    };
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
    els.identityFile.value = profile.identity_file || "";
    els.sshOptions.value = (profile.ssh_options || []).join("\n");
    els.remoteWorkdir.value = profile.remote_workdir || "";
    els.localPort.value = profile.local_port || "7860";
    els.remotePort.value = profile.remote_port || "7860";
    applyRemoteRunner(profile.remote_runner || "slidebridge");
    updateRuntimeFields();
    onInputsChanged();
    setStatus(t("profileLoaded", {name: profileName}), "ok");
  }

  function applyRemoteRunner(remoteRunner) {
    const parsed = parseRemoteRunner(remoteRunner);
    els.remoteRuntime.value = parsed.runtime;
    els.condaEnvPath.value = parsed.condaEnvPath || "";
    els.remoteRunner.value = parsed.customRunner || "slidebridge";
  }

  function parseRemoteRunner(remoteRunner) {
    const runner = String(remoteRunner || "").trim();
    if (!runner || runner === "slidebridge") {
      return {runtime: "path"};
    }
    const pythonMatch = runner.match(/^(.+?)\/bin\/python\s+-m\s+slidebridge\.cli$/);
    if (pythonMatch) {
      return {runtime: "conda", condaEnvPath: pythonMatch[1]};
    }
    return {runtime: "custom", customRunner: runner};
  }

  function openRemoteDirectoryBrowser() {
    els.remoteBrowserModal.hidden = false;
    const initialPath = initialRemoteBrowserPath();
    els.remoteBrowserPath.value = initialPath;
    loadRemoteBrowserDirectory(initialPath);
  }

  function closeRemoteDirectoryBrowser() {
    els.remoteBrowserModal.hidden = true;
  }

  function initialRemoteBrowserPath() {
    const currentValue = els.condaEnvPath.value.trim();
    if (currentValue.startsWith("/") || currentValue.startsWith("~")) {
      return currentValue;
    }
    return state.remoteHome || "~";
  }

  async function loadRemoteBrowserDirectory(path) {
    const directory = String(path || "").trim() || "~";
    els.remoteBrowserPath.value = directory;
    setRemoteBrowserStatus(t("loadingDirectory"), "");
    try {
      const payload = await postJson("/api/remote/list", {
        ...connectionPayload(),
        remote_dir: directory,
        limit: 1000
      });
      if (!payload.ok) {
        renderRemoteDirectoryEntries([]);
        setRemoteBrowserStatus(payload.stderr || t("remoteFailed"), "error");
        return;
      }
      const entries = (payload.entries || [])
        .filter((entry) => entry.kind === "directory")
        .filter((entry) => !String(entry.name || "").startsWith("."));
      renderRemoteDirectoryEntries(entries);
      setRemoteBrowserStatus(t("directoryLoaded", {count: entries.length}), "ok");
    } catch (error) {
      renderRemoteDirectoryEntries([]);
      setRemoteBrowserStatus(error.message, "error");
    }
  }

  function renderRemoteDirectoryEntries(entries) {
    els.remoteBrowserList.innerHTML = "";
    if (!entries.length) {
      const empty = document.createElement("div");
      empty.className = "directory-row empty";
      empty.textContent = t("noDirectories");
      els.remoteBrowserList.appendChild(empty);
      return;
    }
    entries.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "directory-row";

      const name = document.createElement("div");
      name.className = "directory-name";
      const strong = document.createElement("strong");
      strong.textContent = entry.name || entry.path || "";
      const span = document.createElement("span");
      span.textContent = entry.path || "";
      name.appendChild(strong);
      name.appendChild(span);

      const enterButton = document.createElement("button");
      enterButton.type = "button";
      enterButton.textContent = t("enterDirectory");
      enterButton.addEventListener("click", function () {
        loadRemoteBrowserDirectory(entry.path || "");
      });

      const chooseButton = document.createElement("button");
      chooseButton.type = "button";
      chooseButton.textContent = t("chooseDirectory");
      chooseButton.addEventListener("click", function () {
        chooseRemoteDirectory(entry.path || "");
      });

      row.appendChild(name);
      row.appendChild(enterButton);
      row.appendChild(chooseButton);
      els.remoteBrowserList.appendChild(row);
    });
  }

  function chooseRemoteDirectory(path) {
    const directory = String(path || "").trim();
    if (!directory) {
      return;
    }
    els.condaEnvPath.value = directory;
    closeRemoteDirectoryBrowser();
    onInputsChanged();
    setStatus(t("directorySelected"), "ok");
  }

  function setRemoteBrowserStatus(message, stateName) {
    els.remoteBrowserStatus.textContent = message || "";
    els.remoteBrowserStatus.dataset.state = stateName || "";
  }

  function parentDirectory(path) {
    const value = String(path || "").trim().replace(/\/+$/, "");
    if (!value || value === "/" || value === "~") {
      return value || "~";
    }
    if (value.startsWith("~/")) {
      const rest = value.slice(2);
      const index = rest.lastIndexOf("/");
      return index < 0 ? "~" : `~/${rest.slice(0, index)}`;
    }
    const index = value.lastIndexOf("/");
    return index <= 0 ? "/" : value.slice(0, index);
  }

  async function testConnection() {
    setBusy(t("testingSsh"));
    try {
      const result = await postJson("/api/remote/test", connectionPayload());
      if (result.ok) {
        state.remoteHome = result.remote_home || state.remoteHome || "";
      }
      setStatus(result.ok ? t("remoteResponded") : (result.stderr || t("remoteFailed")), result.ok ? "ok" : "error");
      renderSummary();
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
    if (els.launchViewer) {
      els.launchViewer.disabled = true;
    }
    try {
      const result = await postJson("/api/session/launch", launchPayload());
      updateCommand(result);
      setStatus(t("viewerStarted"), "ok");
      window.location.assign(result.viewer_url || viewerUrl());
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      if (els.launchViewer) {
        els.launchViewer.disabled = false;
      }
    }
  }

  function updateCommand(session) {
    els.commandOutput.value = session.command || "";
    els.summaryUrl.textContent = session.viewer_url || viewerUrl();
    renderSummary();
  }

  function renderSummary() {
    if (!els.summaryTarget) {
      return;
    }
    const user = els.user.value.trim();
    const host = els.host.value.trim();
    els.summaryTarget.textContent = host ? `${user ? `${user}@` : ""}${host}` : t("notConfigured");
    els.summaryHome.textContent = state.remoteHome || t("notTested");
    els.summaryRuntime.textContent = runtimeSummary();
    els.summaryUrl.textContent = viewerUrl();
  }

  function runtimeSummary() {
    const runtime = els.remoteRuntime.value || "path";
    if (runtime === "conda") {
      return els.condaEnvPath.value.trim() || t("runtimeConda");
    }
    if (runtime === "custom") {
      return els.remoteRunner.value.trim() || "slidebridge";
    }
    return "slidebridge";
  }

  function viewerUrl() {
    return `http://127.0.0.1:${els.localPort.value.trim() || "7860"}`;
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
