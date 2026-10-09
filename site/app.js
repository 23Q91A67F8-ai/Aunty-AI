// aunty.ai web client

const $ = (id) => document.getElementById(id);
const els = {
  sidebar: $("sidebar"), sessions: $("sessions"), newChat: $("newChat"),
  folderInput: $("folderInput"), wsName: $("wsName"), wsMeta: $("wsMeta"), clearWs: $("clearWs"),
  includeContext: $("includeContext"), modelSelect: $("modelSelect"), voiceToggle: $("voiceToggle"),
  chatTitle: $("chatTitle"), messages: $("messages"), welcome: $("welcome"),
  composer: $("composer"), prompt: $("prompt"), sendBtn: $("sendBtn"), stopBtn: $("stopBtn"),
  imageInput: $("imageInput"), attachments: $("attachments"), status: $("status"),
};

const IGNORE_DIRS = new Set([".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".netlify", ".idea", ".vscode"]);
const IGNORE_EXTS = new Set(["exe", "dll", "so", "png", "jpg", "jpeg", "gif", "webp", "ico", "pdf", "pyc", "zip", "tar", "gz", "mp3", "mp4", "woff", "woff2", "ttf", "lock", "db", "sqlite"]);
const MAX_FILE_BYTES = 500 * 1024;
const MAX_CONTEXT_CHARS = 400_000;

const clientId = localStorage.getItem("aunty.clientId") || crypto.randomUUID();
localStorage.setItem("aunty.clientId", clientId);

const state = {
  sessions: [],
  currentId: null,
  models: [],
  workspace: null, // { name, files: [{ path, content }], context }
  images: [], // data URLs
  controller: null,
};

// ---------- API ----------

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", "x-client-id": clientId, ...(options.headers || {}) },
  });
  if (!res.ok && res.status !== 204) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

// ---------- Markdown ----------

const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function inline(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}

function renderMarkdown(src) {
  const out = [];
  const lines = src.split("\n");
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const fence = line.match(/^```\s*([\w+-]*)/);
    if (fence) {
      const code = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) code.push(lines[i++]);
      i++;
      out.push(`<div class="code"><div class="code-head"><span>${escapeHtml(fence[1] || "code")}</span><button class="copy">Copy</button></div><pre><code>${escapeHtml(code.join("\n"))}</code></pre></div>`);
      continue;
    }
    const heading = line.match(/^(#{1,4})\s+(.*)/);
    if (heading) {
      const level = Math.min(heading[1].length + 2, 6);
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      i++;
      continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const items = [];
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
        items.push(`<li>${inline(lines[i].replace(/^\s*([-*]|\d+\.)\s+/, ""))}</li>`);
        i++;
      }
      out.push(ordered ? `<ol>${items.join("")}</ol>` : `<ul>${items.join("")}</ul>`);
      continue;
    }
    if (/^>\s?/.test(line)) {
      const quote = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) quote.push(lines[i++].replace(/^>\s?/, ""));
      out.push(`<blockquote>${inline(quote.join(" "))}</blockquote>`);
      continue;
    }
    if (!line.trim()) {
      i++;
      continue;
    }
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^(```|#{1,4}\s|>\s?|\s*([-*]|\d+\.)\s+)/.test(lines[i])) para.push(lines[i++]);
    out.push(`<p>${inline(para.join("\n")).replace(/\n/g, "<br>")}</p>`);
  }
  return out.join("");
}

// ---------- Rendering ----------

function setStatus(text, isError = false) {
  els.status.textContent = text;
  els.status.classList.toggle("error", isError);
}

function renderSessions() {
  els.sessions.innerHTML = "";
  if (!state.sessions.length) {
    els.sessions.innerHTML = '<li class="empty">No chats yet</li>';
    return;
  }
  for (const s of state.sessions) {
    const li = document.createElement("li");
    li.className = s.id === state.currentId ? "active" : "";
    li.innerHTML = `<button class="session-open"></button><button class="session-del" title="Delete chat" aria-label="Delete chat">✕</button>`;
    li.querySelector(".session-open").textContent = s.title;
    li.querySelector(".session-open").onclick = () => openSession(s.id);
    li.querySelector(".session-del").onclick = () => deleteSession(s.id);
    els.sessions.appendChild(li);
  }
}

function addMessage(role, content) {
  els.welcome.hidden = true;
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = `<div class="who">${role === "user" ? "You" : "aunty"}</div><div class="body"></div>`;
  const body = div.querySelector(".body");
  setBody(body, role, content);
  els.messages.appendChild(div);
  scrollDown();
  return body;
}

function setBody(body, role, content) {
  if (role === "user") body.innerHTML = renderMarkdown(content);
  else body.innerHTML = content ? renderMarkdown(content) : '<span class="typing"><i></i><i></i><i></i></span>';
}

function scrollDown() {
  els.messages.scrollTop = els.messages.scrollHeight;
}

function clearMessages() {
  els.messages.querySelectorAll(".msg").forEach((m) => m.remove());
  els.welcome.hidden = false;
}

function setBusy(busy) {
  els.sendBtn.hidden = busy;
  els.stopBtn.hidden = !busy;
  els.prompt.disabled = busy;
}

// ---------- Sessions ----------

async function loadSessions() {
  state.sessions = await api("/api/sessions");
  renderSessions();
}

async function openSession(id) {
  closeSidebar();
  const data = await api(`/api/sessions/${id}`);
  state.currentId = id;
  localStorage.setItem("aunty.lastSession", id);
  els.chatTitle.textContent = data.session.title;
  if (state.models.some((m) => m.id === data.session.model)) els.modelSelect.value = data.session.model;
  clearMessages();
  for (const m of data.messages) addMessage(m.role, m.content);
  renderSessions();
}

function newChat() {
  closeSidebar();
  state.currentId = null;
  localStorage.removeItem("aunty.lastSession");
  els.chatTitle.textContent = "New chat";
  clearMessages();
  renderSessions();
  els.prompt.focus();
}

async function deleteSession(id) {
  if (!confirm("Delete this chat?")) return;
  await api(`/api/sessions/${id}`, { method: "DELETE" });
  state.sessions = state.sessions.filter((s) => s.id !== id);
  if (state.currentId === id) newChat();
  else renderSessions();
}

// ---------- Workspace ----------

async function loadFolder(fileList) {
  const files = [...fileList].filter((f) => {
    const parts = (f.webkitRelativePath || f.name).split("/");
    if (parts.slice(0, -1).some((p) => IGNORE_DIRS.has(p))) return false;
    const ext = f.name.includes(".") ? f.name.split(".").pop().toLowerCase() : "";
    return !IGNORE_EXTS.has(ext) && f.size <= MAX_FILE_BYTES;
  });
  if (!files.length) {
    setStatus("No readable text files found in that folder.", true);
    return;
  }
  setStatus(`Reading ${files.length} files…`);
  const read = await Promise.all(
    files.map(async (f) => {
      const content = await f.text();
      // Skip files that look binary
      if (content.includes("\u0000")) return null;
      const path = (f.webkitRelativePath || f.name).split("/").slice(1).join("/") || f.name;
      return { path, content };
    }),
  );
  const good = read.filter(Boolean).sort((a, b) => a.path.localeCompare(b.path));
  const name = (files[0].webkitRelativePath || "").split("/")[0] || "Project";

  const blocks = ["# Project Codebase Context\n"];
  let size = 0;
  let included = 0;
  for (const f of good) {
    const block = `## File: \`${f.path}\`\n\`\`\`\n${f.content}\n\`\`\`\n`;
    if (size + block.length > MAX_CONTEXT_CHARS) break;
    blocks.push(block);
    size += block.length;
    included++;
  }
  state.workspace = { name, files: good, context: blocks.join("\n"), included };
  renderWorkspace();
  setStatus("");
}

function renderWorkspace() {
  const ws = state.workspace;
  els.clearWs.hidden = !ws;
  els.includeContext.disabled = !ws;
  if (!ws) {
    els.wsName.textContent = "No folder open";
    els.wsMeta.textContent = "Open a project folder to give aunty its code as context. Files stay in your browser until you send a message.";
    return;
  }
  const kb = Math.round(ws.context.length / 1024);
  els.wsName.textContent = `📁 ${ws.name}`;
  els.wsMeta.textContent =
    ws.included < ws.files.length
      ? `${ws.included} of ${ws.files.length} files fit in context (${kb} KB). Large projects are trimmed.`
      : `${ws.files.length} files loaded (${kb} KB).`;
}

// ---------- Images ----------

function compressImage(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, 1568 / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(img.src);
      resolve(canvas.toDataURL("image/jpeg", 0.85));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

async function addImages(files) {
  for (const f of [...files].slice(0, 4 - state.images.length)) {
    state.images.push(await compressImage(f));
  }
  renderAttachments();
}

function renderAttachments() {
  els.attachments.hidden = !state.images.length;
  els.attachments.innerHTML = "";
  state.images.forEach((src, idx) => {
    const wrap = document.createElement("div");
    wrap.className = "thumb";
    wrap.innerHTML = `<img alt="Attachment ${idx + 1}"><button type="button" aria-label="Remove image">✕</button>`;
    wrap.querySelector("img").src = src;
    wrap.querySelector("button").onclick = () => {
      state.images.splice(idx, 1);
      renderAttachments();
    };
    els.attachments.appendChild(wrap);
  });
}

// ---------- Voice ----------

function speak(text) {
  if (!els.voiceToggle.checked || !("speechSynthesis" in window)) return;
  const plain = text.replace(/```[\s\S]*?```/g, " code block omitted. ").replace(/[`*#>_]/g, "");
  speechSynthesis.cancel();
  speechSynthesis.speak(new SpeechSynthesisUtterance(plain.slice(0, 4000)));
}

// ---------- Chat ----------

async function send(text) {
  text = text.trim();
  if ((!text && !state.images.length) || state.controller) return;
  setStatus("");

  try {
    if (!state.currentId) {
      const session = await api("/api/sessions", { method: "POST", body: JSON.stringify({ model: els.modelSelect.value }) });
      state.currentId = session.id;
      localStorage.setItem("aunty.lastSession", session.id);
      state.sessions.unshift(session);
    }
  } catch (err) {
    setStatus(err.message, true);
    return;
  }

  const images = state.images;
  const shown = images.length ? `${text || "(see attached image)"}\n\n_[${images.length} image(s) attached]_` : text;
  addMessage("user", shown);
  els.prompt.value = "";
  autoGrow();
  state.images = [];
  renderAttachments();

  const body = addMessage("assistant", "");
  state.controller = new AbortController();
  setBusy(true);
  let reply = "";

  try {
    const useContext = state.workspace && els.includeContext.checked;
    const res = await fetch("/api/chat", {
      method: "POST",
      signal: state.controller.signal,
      headers: { "Content-Type": "application/json", "x-client-id": clientId },
      body: JSON.stringify({
        sessionId: state.currentId,
        model: els.modelSelect.value,
        message: text,
        images,
        context: useContext ? state.workspace.context : "",
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Request failed (${res.status})`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      reply += decoder.decode(value, { stream: true });
      setBody(body, "assistant", reply);
      scrollDown();
    }
    speak(reply);
  } catch (err) {
    if (err.name === "AbortError") {
      reply += reply ? "\n\n_Stopped._" : "_Stopped._";
    } else {
      reply += `\n\n**Error:** ${err.message}`;
      setStatus(err.message, true);
    }
    setBody(body, "assistant", reply);
  } finally {
    state.controller = null;
    setBusy(false);
    els.prompt.focus();
    loadSessions()
      .then(() => {
        const s = state.sessions.find((x) => x.id === state.currentId);
        if (s) els.chatTitle.textContent = s.title;
      })
      .catch(() => {});
  }
}

// ---------- Misc UI ----------

function autoGrow() {
  els.prompt.style.height = "auto";
  els.prompt.style.height = Math.min(els.prompt.scrollHeight, 240) + "px";
}

const closeSidebar = () => els.sidebar.classList.remove("open");

els.composer.addEventListener("submit", (e) => {
  e.preventDefault();
  send(els.prompt.value);
});
els.prompt.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    send(els.prompt.value);
  }
});
els.prompt.addEventListener("input", autoGrow);
els.prompt.addEventListener("paste", (e) => {
  const imgs = [...e.clipboardData.files].filter((f) => f.type.startsWith("image/"));
  if (imgs.length) addImages(imgs);
});
els.stopBtn.onclick = () => state.controller?.abort();
els.newChat.onclick = newChat;
els.imageInput.onchange = (e) => {
  addImages(e.target.files);
  e.target.value = "";
};
els.folderInput.onchange = (e) => {
  loadFolder(e.target.files);
  e.target.value = "";
};
els.clearWs.onclick = () => {
  state.workspace = null;
  renderWorkspace();
};
els.modelSelect.onchange = () => {
  localStorage.setItem("aunty.model", els.modelSelect.value);
  if (state.currentId) api(`/api/sessions/${state.currentId}`, { method: "PATCH", body: JSON.stringify({ model: els.modelSelect.value }) }).catch(() => {});
};
els.voiceToggle.onchange = () => {
  localStorage.setItem("aunty.voice", els.voiceToggle.checked ? "1" : "");
  if (!els.voiceToggle.checked && "speechSynthesis" in window) speechSynthesis.cancel();
};
$("openSidebar").onclick = () => els.sidebar.classList.add("open");
$("closeSidebar").onclick = closeSidebar;
document.querySelectorAll(".suggestions button").forEach((b) => (b.onclick = () => send(b.dataset.prompt)));
els.messages.addEventListener("click", (e) => {
  if (!e.target.classList.contains("copy")) return;
  const code = e.target.closest(".code").querySelector("code").textContent;
  navigator.clipboard.writeText(code).then(() => {
    e.target.textContent = "Copied";
    setTimeout(() => (e.target.textContent = "Copy"), 1500);
  });
});

// ---------- Init ----------

async function init() {
  els.voiceToggle.checked = !!localStorage.getItem("aunty.voice");
  try {
    const { models, default: def } = await api("/api/models");
    state.models = models;
    els.modelSelect.innerHTML = models.map((m) => `<option value="${m.id}">${escapeHtml(m.name)}</option>`).join("");
    const saved = localStorage.getItem("aunty.model");
    els.modelSelect.value = models.some((m) => m.id === saved) ? saved : def;
  } catch {
    setStatus("Couldn't load models. Please refresh the page.", true);
  }
  try {
    await loadSessions();
    const last = localStorage.getItem("aunty.lastSession");
    if (last && state.sessions.some((s) => s.id === last)) await openSession(last);
  } catch (err) {
    setStatus(`Couldn't load your chats: ${err.message}`, true);
  }
  els.prompt.focus();
}

init();
