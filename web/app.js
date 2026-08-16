const API = {
  projects: "/api/projects",
  projectView: "/api/project-view",
};

const AGENTS = {
  "gap2sku-product-architect": { label: "Leader", short: "L", color: "#0aa78f" },
  "gap2sku-market": { label: "Market", short: "M", color: "#0d9f91" },
  "gap2sku-prototype-designer": { label: "Prototype", short: "P", color: "#7358d8" },
  "gap2sku-supply": { label: "Supply", short: "S", color: "#1677ff" },
  "gap2sku-economics": { label: "Economics", short: "E", color: "#f58a10" },
  "gap2sku-compliance": { label: "Compliance", short: "C", color: "#35a66f" },
  "gap2sku-reviewer": { label: "Reviewer", short: "R", color: "#73808c" },
  "human-manager": { label: "Human Manager", short: "H", color: "#263a4a" },
};

const initialParams = new URLSearchParams(location.search);
const state = {
  status: null, messages: [], events: [], conflicts: [], decision: null, trace: null,
  projects: [], projectKey: initialParams.get("project") || "nap-pillow",
  filter: "run", replay: false, initialRender: true, eventSource: null,
};
const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const css = (agent) => `--agent-color:${(AGENTS[agent] || AGENTS["human-manager"]).color}`;
const agentInfo = (agent) => AGENTS[agent] || { label: agent?.replace("gap2sku-", "") || "System", short: "·", color: "#6f8190" };

async function jsonFetch(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function animateIn() {
  if (!window.Motion || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  window.Motion.animate(".panel", { opacity: [0, 1], y: [12, 0] }, { duration: .45, delay: window.Motion.stagger(.07), easing: "ease-out" });
  window.Motion.animate(".agent-card", { opacity: [0, 1], x: [-8, 0] }, { duration: .32, delay: window.Motion.stagger(.035, {startDelay:.12}) });
  window.Motion.animate(".conflict-card", { opacity: [0, 1], x: [10, 0] }, { duration: .35, delay: window.Motion.stagger(.055, {startDelay:.18}) });
  window.Motion.animate(".message-item", { opacity: [0, 1], y: [8, 0] }, { duration: .3, delay: window.Motion.stagger(.028) });
}

function roleFromMessage(message) {
  return message.sender_role || Object.keys(AGENTS).find((key) => message.sender_id?.includes(key.replace("gap2sku-", ""))) || "human-manager";
}

function renderRoster() {
  const source = [...(state.status?.agents || []), {id:"human-manager", status:"online"}];
  $("#agent-roster").innerHTML = source.map((agent) => {
    const info = agentInfo(agent.id);
    return `<div class="agent-card status-${esc(agent.status)}" style="${css(agent.id)}" title="${esc(agent.id)} · ${esc(agent.status)}">
      <span class="agent-avatar">${esc(info.short)}</span><span class="agent-dot"></span><span class="agent-label">${esc(info.label)}</span>
    </div>`;
  }).join("");
}

function mergedStream() {
  const messages = new Map(state.messages.map((message) => [message.message_id, message]));
  return state.events.map((event) => ({ event, message: messages.get(event.matrix_message_id) })).filter((item) => {
    if (state.replay) return true;
    if (state.filter === "run") {
      const runId = state.status?.active_run_id;
      return !runId || item.event.task_id?.includes(runId);
    }
    if (state.filter === "all") return true;
    if (state.filter === "decision") return ["DECISION_RECORD", "HUMAN_DECISION", "REVIEW_FINDING"].includes(item.event.event_type);
    if (state.filter === "risk") return item.event.status === "blocked" || ["RISK_ALERT", "NEEDS_EVIDENCE", "REVIEW_FINDING"].includes(item.event.event_type);
    if (state.filter === "artifact") return item.event.artifact_refs?.length;
    return true;
  });
}

function conciseSummary(value, limit = 230) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  const firstBreak = text.slice(88, limit + 1).search(/[。；]/);
  const cut = firstBreak >= 0 ? firstBreak + 89 : limit;
  return `${text.slice(0, cut).trim()}…`;
}

function toolLabel(event) {
  if (event.event_type === "USER_REQUEST") return "task.create_suggestion";
  if (event.requested_action === "review_handoff") return "collaboration.submit_handoff";
  return event.requested_action || "artifact.commit";
}

function setStreamStatus(connected = true) {
  const live = state.status?.collaboration_mode === "AGENTTEAMS_LIVE";
  const projectReplay = state.status?.read_only_replay;
  if (state.status?.review_mode) {
    $("#stream-status").className = "";
    $("#stream-status").innerHTML = "<i></i> 审核快照 · 版本化事件";
    return;
  }
  $("#stream-status").className = connected ? "" : "disconnected";
  $("#stream-status").innerHTML = `<i></i> ${connected ? (live ? "Matrix + SSE · 实时" : projectReplay ? "版本化项目回放" : "本地回放 + SSE") : "SSE 重连中"}`;
}

function renderStream() {
  let items = mergedStream();
  if (state.replay) items = items.slice(0, Number($("#replay-range").value));
  if (!items.length) {
    $("#message-stream").innerHTML = `<div class="loading-state"><span>当前筛选暂无结构化协作事件</span></div>`;
    return;
  }
  $("#message-stream").innerHTML = items.map(({event, message}) => {
    const agent = event.sender || roleFromMessage(message || {});
    const info = agentInfo(agent);
    const isConflict = event.status === "blocked" || ["RISK_ALERT", "REVIEW_FINDING", "NEEDS_EVIDENCE"].includes(event.event_type);
    const stamp = message?.origin_server_ts ? new Date(message.origin_server_ts) : new Date(event.created_at);
    const refs = event.artifact_refs || [];
    const chips = refs.slice(0, 4).map((ref) => `<button class="artifact-chip" data-artifact="${esc(ref)}" type="button">${esc(ref)} · 查看</button>`).join("") + (refs.length > 4 ? `<button class="artifact-chip artifact-more" data-event="${esc(event.event_id)}" type="button">+${refs.length - 4} 个产物</button>` : "");
    const fullSummary = String(event.summary || "").replace(/\s+/g, " ").trim();
    const summary = conciseSummary(fullSummary);
    const expandable = summary !== fullSummary;
    const provenance = message?.raw_event?.replay
      ? "REPLAY"
      : message?.raw_event?.source === "LOCAL_REPLAY_ONLY"
        ? "LOCAL"
        : message ? "MATRIX" : "PROJECT";
    return `<article class="message-item ${isConflict ? "conflict" : ""}" style="${css(agent)}">
      <div class="message-avatar">${esc(info.short)}</div>
      <div>
        <div class="message-top"><span class="message-role">${esc(info.label)}</span><time class="message-time">${stamp.toLocaleTimeString("zh-CN", {hour:"2-digit", minute:"2-digit"})}</time><span class="message-type">${esc(event.event_type)}</span></div>
        <p class="message-body">${esc(summary)}</p>
        <div class="execution-row"><span class="tool-call"><b>TOOL</b>${esc(toolLabel(event))}</span><span class="task-ref">${esc(event.task_id)}</span>${expandable ? `<button class="message-expand" data-event="${esc(event.event_id)}" type="button">展开原文</button>` : ""}</div>
        ${chips ? `<div class="artifact-chips">${chips}</div>` : ""}
        <span class="event-status ${esc(event.status)}"><i></i>${esc(event.status)} · r${esc(event.revision)} · ${esc(event.data_mode)} · ${provenance}</span>
      </div>
    </article>`;
  }).join("");
  document.querySelectorAll("[data-artifact]").forEach((button) => button.addEventListener("click", () => openArtifact(button.dataset.artifact)));
  document.querySelectorAll("[data-event]").forEach((button) => button.addEventListener("click", () => openEvent(button.dataset.event)));
  if (window.Motion && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const last = document.querySelector(".message-item:last-child");
    if (last) window.Motion.animate(last, {opacity:[0,1], y:[7,0]}, {duration:.28, easing:"ease-out"});
  }
  if (!state.replay) {
    $("#message-stream").scrollTop = state.initialRender ? 0 : $("#message-stream").scrollHeight;
    state.initialRender = false;
  }
}

function renderConflicts() {
  const rows = (state.conflicts || []).filter((artifact) => !String(artifact.payload?.status || "").startsWith("RESOLVED"));
  $("#conflict-count").textContent = `${rows.length} 项`;
  $("#conflict-summary").textContent = rows.length ? "用户价值、制造可行性、成本与合规证据仍有跨角色冲突。" : "当前没有未解决冲突。";
  $("#conflict-list").innerHTML = rows.slice(0, 5).map((artifact, index) => {
    const payload = artifact.payload || {};
    const owner = ["gap2sku-market", "gap2sku-supply", "gap2sku-economics", "gap2sku-compliance"][index % 4];
    const info = agentInfo(owner);
    const gap = (payload.unresolved_gaps || [])[0] || (payload.claims || [])[0] || "等待证据闭环";
    return `<button class="conflict-card" style="${css(owner)}" data-artifact="${esc(artifact.artifact_id)}" type="button">
      <span class="conflict-icon">${esc(info.short)}</span><span><strong>${esc(payload.title || artifact.artifact_id)}</strong><p>${esc(gap)}</p></span><span class="severity">${esc(payload.severity || payload.status || "OPEN")}</span>
    </button>`;
  }).join("");
  document.querySelectorAll(".conflict-card").forEach((button) => button.addEventListener("click", () => openArtifact(button.dataset.artifact)));
}

function latest(list) { return list?.length ? list[list.length - 1] : null; }
function renderDecision() {
  const brief = latest(state.decision?.decisionBrief)?.payload || state.status?.run?.decision_brief || {};
  const review = latest(state.decision?.reviewResult)?.payload || {};
  const recommendation = brief.recommendation || state.status?.run?.recommendation || "REVISE";
  $("#recommendation-inline").textContent = recommendation;
  $("#recommendation-inline").className = `recommendation-inline ${recommendation.toLowerCase()}`;
  $("#review-state").textContent = `REVIEW ${review.review_result || state.status?.run?.review_result || "—"}`;
  document.querySelectorAll("#decision-selector div").forEach((item) => item.classList.toggle("active", item.dataset.value === recommendation));
  const reasons = brief.risk_summary || brief.pending_confirmations || [];
  $("#decision-reason").innerHTML = reasons.length ? `<ul>${reasons.slice(0, 4).map((reason) => `<li>${esc(reason)}</li>`).join("")}</ul>` : "确定性规则已通过，仍需人工审批绑定当前规格与政策版本。";
  const canApprove = review.review_result === "PASS" && !state.status?.read_only_replay;
  $("#approval-button").disabled = !canApprove;
  $("#approval-button").textContent = canApprove
    ? "提交人工审批"
    : state.status?.review_mode ? "审核快照 · 不提交审批"
      : state.status?.read_only_replay ? "回放项目 · 不重复审批" : "Reviewer 未通过 · 禁止覆盖";
}

function openDrawer(title, eyebrow, html) {
  $("#drawer-title").textContent = title;
  $("#drawer-eyebrow").textContent = eyebrow;
  $("#drawer-body").innerHTML = html;
  $("#drawer-backdrop").hidden = false;
  $("#drawer").classList.add("open");
  $("#drawer").setAttribute("aria-hidden", "false");
}

function closeDrawer() {
  $("#drawer").classList.remove("open");
  $("#drawer").setAttribute("aria-hidden", "true");
  setTimeout(() => { $("#drawer-backdrop").hidden = true; }, 280);
}

async function openArtifact(id) {
  try {
    const artifact = await jsonFetch(`/api/project-artifacts/${encodeURIComponent(id)}?project=${encodeURIComponent(state.projectKey)}`);
    openDrawer(artifact.artifact_id, `${artifact.artifact_type} · V${artifact.artifact_version}`, `<div class="detail-card"><strong>审计元数据</strong><p>producer ${esc(artifact.producer_agent)} · ${esc(artifact.status)} · ${esc(artifact.data_mode)}</p><p>${esc(artifact.content_hash)}</p></div><pre class="raw">${esc(JSON.stringify(artifact.payload, null, 2))}</pre>`);
  } catch (error) { openDrawer("Artifact 不可用", "ERROR", `<div class="detail-card"><p>${esc(error.message)}</p></div>`); }
}

function openEvent(id) {
  const event = state.events.find((row) => row.event_id === id);
  const message = event ? state.messages.find((row) => row.message_id === event.matrix_message_id) : null;
  if (!event) return;
  openDrawer(
    `${agentInfo(event.sender).label} · ${event.event_type}`,
    `${event.task_id} · REVISION ${event.revision}`,
    `<div class="detail-card"><strong>结构化协作事件</strong><p>${esc(event.summary)}</p></div>
     <div class="detail-card"><strong>状态事实</strong><p>${esc(event.status)} · ${esc(event.data_mode)} · ${esc(toolLabel(event))}</p><p>聊天内容不直接推进业务状态；Task、Artifact、规则与审批才是事实源。</p></div>
     ${message ? `<details class="raw-message"><summary>查看 Matrix 原始消息</summary><pre class="raw">${esc(message.body)}</pre></details>` : ""}`,
  );
}

function applyProjectView(payload) {
  const status = payload.status;
  state.status = status;
  state.messages = payload.messages || [];
  state.events = payload.events || [];
  state.conflicts = payload.conflicts || [];
  state.decision = payload.decision || {};
  state.trace = payload.trace || {metrics:{}, events:[]};
  state.replay = false;
  state.initialRender = true;
  $("#replay-bar").hidden = true;
  document.body.classList.toggle("review-mode", Boolean(status.review_mode));
  $("#project-name").textContent = status.project_name;
  $("#policy-badge").textContent = `POLICY ${status.policy_version}`;
  const mode = status.data_mode || status.run?.data_mode || "REAL";
  $("#data-mode").textContent = mode;
  $("#data-mode").className = `top-badge mode ${String(mode).toLowerCase()}`;
  const constraints = status.display_constraints || {};
  $("#constraint-price").textContent = constraints.target_price || "待确认";
  $("#constraint-cost").textContent = constraints.cost || "待 RFQ";
  $("#constraint-margin").textContent = constraints.target_margin || "待确认";
  $(".story-link").href = status.story_url || `/story?project=${encodeURIComponent(state.projectKey)}`;
  const isLive = status.collaboration_mode === "AGENTTEAMS_LIVE";
  $("#live-toggle span").textContent = status.review_mode ? "REVIEW SNAPSHOT" : isLive ? "LIVE" : "LOCAL REPLAY";
  $("#live-toggle").classList.toggle("offline", !isLive);
  $("#stream-status").dataset.runtime = isLive ? "live" : "replay";
  const completed = status.active_run_progress?.completed || 0;
  const total = status.active_run_progress?.total || 7;
  $("#run-progress").innerHTML = `<i></i><b>${status.end_to_end_verified ? "本轮完成" : "分析中"}</b><small>${completed}/${total}</small>`;
  $(".composer-notice").innerHTML = status.review_mode
    ? `<span>i</span> 审核快照：页面仅展示已生成的版本化结果`
    : status.read_only_replay
      ? `<span>i</span> 回放项目：消息只保存为本项目建议，不会伪装成实时 AgentTeams`
      : `<span>i</span> 消息只创建建议任务，不会直接修改业务状态`;
  setStreamStatus(true);
  renderRoster(); renderStream(); renderConflicts(); renderDecision(); setupReplay(); animateIn();
}

async function loadProject(projectKey, updateUrl = true) {
  try {
    const payload = await jsonFetch(`${API.projectView}?project=${encodeURIComponent(projectKey)}`);
    state.projectKey = projectKey;
    if (updateUrl) {
      const next = new URL(location.href);
      next.searchParams.set("project", projectKey);
      history.replaceState({}, "", next);
    }
    applyProjectView(payload);
    connectStream();
  } catch (error) {
    $("#message-stream").innerHTML = `<div class="loading-state"><span>无法读取项目：${esc(error.message)}<br>请先运行对应的 make demo-* 命令</span></div>`;
  }
}

async function loadInitial() {
  try {
    const catalog = await jsonFetch(API.projects);
    state.projects = catalog.projects || [];
    const selected = state.projects.find((project) => project.key === state.projectKey && project.available);
    if (!selected) state.projectKey = catalog.default_project || "nap-pillow";
    await loadProject(state.projectKey, true);
  } catch (error) {
    $("#message-stream").innerHTML = `<div class="loading-state"><span>无法读取运行数据：${esc(error.message)}<br>请先运行 make demo-real</span></div>`;
  }
}

function setupReplay() {
  const max = Math.max(1, mergedStream().length);
  $("#replay-range").max = String(max);
  $("#replay-range").value = String(max);
  $("#replay-label").textContent = `${max} / ${max}`;
}

function connectStream() {
  if (state.eventSource) state.eventSource.close();
  state.eventSource = null;
  if (state.projectKey !== "nap-pillow") {
    setStreamStatus(true);
    return;
  }
  if (state.status?.review_mode) {
    setStreamStatus(true);
    return;
  }
  const source = new EventSource("/api/collaboration/stream");
  state.eventSource = source;
  source.addEventListener("collaboration", async () => {
    if (state.replay) return;
    const payload = await jsonFetch(`${API.projectView}?project=nap-pillow`);
    state.messages = payload.messages || [];
    state.events = payload.events || [];
    setupReplay(); renderStream();
  });
  source.onopen = () => {
    setStreamStatus(true);
  };
  source.onerror = () => setStreamStatus(false);
}

$("#filter-pills").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-filter]");
  if (!button) return;
  state.filter = button.dataset.filter;
  document.querySelectorAll("#filter-pills button").forEach((item) => item.classList.toggle("active", item === button));
  setupReplay(); renderStream();
});

$("#replay-button").addEventListener("click", () => {
  state.replay = true;
  state.initialRender = true;
  setupReplay();
  $("#replay-bar").hidden = false;
  $("#live-toggle span").textContent = "HISTORY";
  $("#replay-range").value = String(Math.max(1, Math.ceil(mergedStream().length * .55)));
  $("#replay-range").dispatchEvent(new Event("input"));
});
$("#replay-exit").addEventListener("click", () => {
  state.replay = false; $("#replay-bar").hidden = true;
  state.initialRender = true;
  setupReplay();
  $("#live-toggle span").textContent = state.status?.collaboration_mode === "AGENTTEAMS_LIVE" ? "LIVE" : "LOCAL REPLAY";
  renderStream();
});
$("#live-toggle").addEventListener("click", () => state.replay ? $("#replay-exit").click() : $("#replay-button").click());
$("#replay-range").addEventListener("input", (event) => { $("#replay-label").textContent = `${event.target.value} / ${event.target.max}`; renderStream(); });

$("#message-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#message-input");
  const body = input.value.trim();
  if (!body) return;
  const submit = event.currentTarget.querySelector("button");
  submit.disabled = true; submit.textContent = "发送中";
  try {
    await jsonFetch(`/api/project-messages?project=${encodeURIComponent(state.projectKey)}`, {method:"POST", headers:{"content-type":"application/json"}, body:JSON.stringify({body})});
    input.value = "";
    await loadProject(state.projectKey, false);
  } catch (error) { openDrawer("消息未发送", "ERROR", `<div class="detail-card"><p>${esc(error.message)}</p></div>`); }
  finally { submit.disabled = false; submit.textContent = "发送"; }
});

$("#message-input").addEventListener("input", (event) => {
  event.target.style.height = "auto";
  event.target.style.height = `${Math.min(event.target.scrollHeight, 92)}px`;
  const match = event.target.value.match(/(?:^|\s)@([A-Za-z-]*)$/);
  const menu = $("#mention-menu");
  if (!match) { menu.hidden = true; return; }
  const query = match[1].toLowerCase();
  const entries = Object.entries(AGENTS).filter(([id]) => id !== "human-manager" && (id.includes(query) || AGENTS[id].label.toLowerCase().includes(query)));
  menu.innerHTML = entries.map(([id, info]) => `<button type="button" data-mention="${esc(info.label)}"><span style="${css(id)}">${esc(info.short)}</span>${esc(info.label)}</button>`).join("");
  menu.hidden = !entries.length;
  menu.querySelectorAll("[data-mention]").forEach((button) => button.addEventListener("click", () => {
    event.target.value = event.target.value.replace(/@([A-Za-z-]*)$/, `@${button.dataset.mention} `);
    menu.hidden = true; event.target.focus();
  }));
});

function openIntake() {
  openDrawer("新品决策入口", "CATEGORY-AGNOSTIC INTAKE", `
    <p class="conflict-summary">午睡枕只是当前演示项目。这里可以预览任意品类的 CategoryProfile 与 ResearchPlan；未知品类在人工确认政策前禁止 GO。</p>
    <form id="intake-form" class="intake-form">
      <label>入口模式<select name="mode"><option value="OPPORTUNITY_DISCOVERY">Opportunity Discovery · 发现机会</option><option value="NEW_CONCEPT">New Concept · 验证构思</option><option value="EXISTING_SKU_UPGRADE">Existing SKU Upgrade · 现有 SKU 改款</option></select></label>
      <label>项目名称<input name="title" value="新产品立项评估" required></label>
      <label>品类提示<input name="category_hint" placeholder="例如：露营灯、宠物饮水机、厨房收纳" required></label>
      <label>目标市场<input name="target_market" value="US" required></label>
      <label>目标用户<input name="target_users" placeholder="例如：adult outdoor users" required></label>
      <label>构思 / 问题<textarea name="idea_or_problem" rows="3" placeholder="要发现或验证什么？" required></textarea></label>
      <div class="intake-grid"><label>目标价格下限<input name="price_min" type="number" value="20"></label><label>目标价格上限<input name="price_max" type="number" value="50"></label></div>
      <button class="primary-button" type="submit">生成品类与研究计划</button>
    </form><div id="intake-result"></div>`);
  $("#intake-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const projectId = `preview-${Date.now()}`;
    const payload = {
      project_id: projectId, mode: data.get("mode"), title: data.get("title"),
      target_market: data.get("target_market"), target_users: [data.get("target_users")],
      category_hint: data.get("category_hint"), idea_or_problem: data.get("idea_or_problem"),
      hard_constraints: {target_price: [Number(data.get("price_min")), Number(data.get("price_max"))]},
    };
    const button = event.currentTarget.querySelector("button[type=submit]");
    button.disabled = true; button.textContent = "分析中";
    try {
      const result = await jsonFetch("/api/intake/preview", {method:"POST", headers:{"content-type":"application/json"}, body:JSON.stringify(payload)});
      const profile = result.category_profile;
      $("#intake-result").innerHTML = `<div class="detail-card intake-result"><strong>${esc(profile.category_name)} · ${esc(profile.status)}</strong><p>风险级别 ${esc(profile.risk_tier)} · GO eligible: ${esc(result.go_eligible)}</p><p>${esc(result.notice)}</p></div><pre class="raw">${esc(JSON.stringify(result.research_plan, null, 2))}</pre>`;
    } catch (error) { $("#intake-result").innerHTML = `<div class="detail-card"><p>${esc(error.message)}</p></div>`; }
    finally { button.disabled = false; button.textContent = "生成品类与研究计划"; }
  });
}

function openProjectMenu() {
  const cards = state.projects.map((project) => {
    const active = project.key === state.projectKey;
    const verdictClass = String(project.recommendation || "").toLowerCase();
    return `<button class="project-option ${active ? "active" : ""}" data-project="${esc(project.key)}" type="button" ${project.available ? "" : "disabled"}>
      <span><strong>${esc(project.project_name)}</strong><p>${esc(project.entry_mode)} · ${project.available ? "已生成，可切换" : "尚未生成演示数据"}</p></span>
      <span class="project-option-meta"><span>${esc(project.data_mode)}</span><b class="${esc(verdictClass)}">${esc(project.recommendation || "—")}</b></span>
    </button>`;
  }).join("");
  openDrawer("切换项目", "PROJECT WORKSPACE", `
    <p class="conflict-summary project-menu-intro">切换只改变当前查看的项目、Artifact、协作回放和 Product Story，不会改写任何历史版本。</p>
    <div class="project-menu-grid">${cards}</div>
    <div class="project-menu-actions">${state.status?.review_mode
      ? `<p class="review-menu-note">审核快照仅支持浏览已生成项目与历史事件。</p>`
      : `<button class="new-project-action" id="new-project-action" type="button">＋ 新建立项预览</button>`}<a href="/guide">查看完整使用指南</a></div>`);
  document.querySelectorAll("[data-project]").forEach((button) => button.addEventListener("click", async () => {
    if (button.dataset.project === state.projectKey) { closeDrawer(); return; }
    button.disabled = true;
    await loadProject(button.dataset.project, true);
    closeDrawer();
  }));
  $("#new-project-action")?.addEventListener("click", openIntake);
}

$("#project-switcher").addEventListener("click", openProjectMenu);

$("#approval-button").addEventListener("click", async () => {
  const spec = latest(state.decision?.productSpec)?.payload;
  const review = latest(state.decision?.reviewResult)?.payload;
  if (!spec || !review) return;
  try {
    const result = await jsonFetch("/api/decision/approve", {method:"POST", headers:{"content-type":"application/json"}, body:JSON.stringify({spec_hash:spec.spec_hash, policy_version:review.policy_version, approver:"local-human-manager", reason:"确认当前 SampleSpec 与政策版本", decision:"APPROVE"})});
    $("#approval-result").textContent = result.accepted ? "审批已绑定当前 spec_hash 与 policy version" : "审批未生效";
  } catch (error) { $("#approval-result").textContent = error.message; }
});

$("#raw-drawer-button").addEventListener("click", () => openDrawer("Matrix 原始消息", "READ-ONLY OBSERVER", `<p class="conflict-summary">原始消息用于审计与回放；业务状态以 Task / Artifact Store 为准。</p>${state.messages.map((message) => `<div class="detail-card"><strong>${esc(message.sender_id)}</strong><p>${esc(message.body)}</p><button data-raw="${esc(message.message_id)}">查看 raw event</button></div>`).join("")}`));
$("#artifact-browser").addEventListener("click", () => {
  const rows = state.status?.artifacts || [];
  openDrawer("Artifact 浏览器", `${rows.length} VERSIONED ARTIFACTS`, rows.slice().reverse().map((artifact) => `<div class="detail-card"><strong>${esc(artifact.artifact_type)} · ${esc(artifact.artifact_id)}</strong><p>${esc(artifact.producer_agent)} · ${esc(artifact.status)} · ${esc(artifact.data_mode)}</p><button data-open-artifact="${esc(artifact.artifact_id)}">查看 payload</button></div>`).join(""));
  document.querySelectorAll("[data-open-artifact]").forEach((button) => button.addEventListener("click", () => openArtifact(button.dataset.openArtifact)));
});
$("#audit-button").addEventListener("click", async () => {
  const trace = state.trace || {metrics:{}, events:[]};
  openDrawer("审计记录", `${trace.events?.length || 0} TRACE EVENTS`, `<pre class="raw">${esc(JSON.stringify({metrics:trace.metrics, events:trace.events}, null, 2))}</pre>`);
});
$("#conflict-count").addEventListener("click", () => $("#conflict-list").scrollIntoView({behavior:"smooth"}));
$("#drawer-close").addEventListener("click", closeDrawer);
$("#drawer-backdrop").addEventListener("click", closeDrawer);
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeDrawer(); });
document.querySelector(".story-link").addEventListener("click", (event) => {
  if (!document.startViewTransition) return;
  event.preventDefault();
  const href = event.currentTarget.href;
  document.startViewTransition(() => { window.location.href = href; });
});

loadInitial();
