const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const conceptImages = {"concept-a":"/static/assets/concepts/concept-a.png","concept-b":"/static/assets/concepts/concept-b.png","concept-c":"/static/assets/concepts/concept-c.png"};
let currentView = "internal";
const storyParams = new URLSearchParams(location.search);
let currentProject = storyParams.get("project") || "nap-pillow";

function resultClass(result) { return String(result || "").toLowerCase().replaceAll("-", "_"); }
function fill(root, field, value) { const node = $(`[data-field="${field}"]`, root); if (node) node.textContent = value ?? "—"; }
function money(value) { return typeof value === "number" ? `¥${value.toFixed(2)}` : "待确认"; }

function render(data) {
  const fragment = $("#story-template").content.cloneNode(true);
  const root = $(".product-story", fragment);
  const sections = data.sections || {};
  const concepts = sections.concepts?.concepts || [];
  const selected = concepts.find((item) => item.concept_id === sections.concepts?.selected_concept_id) || sections.overview?.selected_concept || concepts[0] || {};
  const spec = sections.sample_spec || {};
  const rfq = sections.supplier_rfq || {};
  const review = sections.review || {};
  const recommendation = data.recommendation || "REVISE";
  const renderAssets = sections.render_assets || {};
  const conceptImage = (conceptId) => renderAssets[conceptId] || conceptImages[conceptId] || null;

  fill(root,"version",`V${data.version || 1}`); fill(root,"title",data.title); fill(root,"subtitle",data.subtitle);
  fill(root,"policy-version",review.policy_version || "policy-v3.0.0");
  const painLabels = {
    height_adjustment:"高度与角度难匹配",
    arm_channel:"手臂受压与摆放受限",
    odor_material:"异味与材料担忧",
    durability:"调节结构耐久反馈",
  };
  const rfqLabels = {AWAITING_REAL_SUPPLIER_RESPONSE:"等待真实响应", AWAITING_MATCHED_SPEC_RESPONSE:"等待同规格响应", RESPONDED_SYNTHETIC:"合成响应", MISSING:"尚未发起", READY:"可发出", RESPONDED:"已收到响应"};
  const specStatus = spec.locked_by?.includes("demo") ? `${spec.lock_status || "LOCKED"} · DEMO CHECKPOINT` : (spec.lock_status || "DRAFT");
  fill(root,"recommendation",recommendation); fill(root,"data-mode",data.data_mode); fill(root,"spec-status",specStatus);
  fill(root,"evidence-count",sections.evidence?.review_count || 0); fill(root,"rfq-status",rfqLabels[rfq.status] || rfq.status || "尚未发起"); fill(root,"review-result",review.review_result || "—"); fill(root,"review-verdict",recommendation);
  const isSyntheticGo = recommendation === "GO" && data.data_mode === "SYNTHETIC";
  fill(root,"verdict-copy",recommendation === "REVISE" ? "方向可继续，但真实 RFQ、BOM、耐久与材料证据未闭环；进入补证与打样 revision。" : isSyntheticGo ? "合成证据门禁与 exact-hash 演示审批已通过；只证明流程可达，不形成真实商业结论。" : recommendation === "GO" ? "确定性规则已通过，等待与当前规格和政策绑定的人工批准。" : "关键风险不可接受，当前方案停止立项。" );
  fill(root,"review-heading",recommendation === "GO" ? "为什么当前可以进入打样" : recommendation === "NO-GO" ? "为什么当前方案应停止" : "为什么当前还不能 GO");
  fill(root,"review-subtitle",recommendation === "GO" ? "Reviewer 门禁已通过；GO 仍受当前规格、政策版本和数据模式约束。" : "Reviewer 不能被 Leader、LLM 或人工说明绕过。");
  fill(root,"review-next",recommendation === "GO" ? (isSyntheticGo ? "仅批准 SYNTHETIC 回归；不得替代真实报价、测试或商业立项。" : "人工审批只绑定当前 spec_hash 与 policy version。") : recommendation === "NO-GO" ? "停止当前方案；若重启立项必须创建新的概念和版本链。" : "补证后创建新 revision，历史版本保持不可变。");
  fill(root,"spec-hash",`spec_hash ${spec.spec_hash || sections.overview?.spec_hash || "—"}`);
  const hero = $("[data-field='hero-image']",root);
  hero.src = data.hero_render_ref || conceptImage(selected.concept_id) || conceptImages["concept-a"];
  const annotated = $("[data-field='annotated-image']", root);
  annotated.src = hero.src;
  const overall = spec.dimensions?.expanded_mm || spec.dimensions?.overall_mm || [];
  const folded = spec.dimensions?.folded_mm || [];
  fill(root,"dimension-1", overall[0] ? `${overall[0]} mm` : "LOCKED SPEC");
  fill(root,"dimension-2", overall[1] ? `${overall[1]} mm` : "HASH BOUND");
  fill(root,"dimension-3", overall[2] ? `${overall[2]} mm MAX` : (spec.parameters?.rated_load_kg ? `${spec.parameters.rated_load_kg} kg` : "TEST FIRST"));

  $("[data-field='pain-points']",root).innerHTML = (sections.evidence?.pain_points || []).slice(0,4).map((pain,index) => `<article class="pain-card"><i>${String(index+1).padStart(2,"0")}</i><h3>${esc(pain.title || pain.label || painLabels[pain.pain_point_id] || pain.pain_point_id)}</h3><p>${esc(pain.summary || pain.description || (pain.match_count || pain.count ? `形成 ${pain.match_count || pain.count} 条行级证据；频率不代表总体发生率。` : "已形成可回溯的行级证据簇；仍需结合制造与测试证据判断。"))}</p></article>`).join("");
  $("[data-field='evidence-limitations']",root).textContent = `证据边界：${(sections.evidence?.limitations || []).join("；") || "评论只证明用户表达，不证明供应能力与法规结论。"}`;
  $("[data-field='concepts']",root).innerHTML = concepts.map((concept) => {
    const image = conceptImage(concept.concept_id);
    const media = image ? `<div class="concept-image"><img src="${esc(image)}" alt="${esc(concept.title)} 概念效果图"><span>SYNTHETIC_CONCEPT</span></div>` : "";
    return `<article class="concept-card ${concept.concept_id === selected.concept_id ? "selected" : ""}">${media}<div class="concept-body"><div class="concept-top"><h3>${esc(concept.title)}</h3><b>${esc(concept.strategy)}</b></div><p>${esc(concept.tradeoffs?.join("；") || "等待工程取舍")}</p><ul>${(concept.differentiators || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul></div></article>`;
  }).join("");

  const specRows = [
    ["选中概念", spec.selected_concept_ref], ["关键尺寸", overall.length ? overall.join(" × ") + " mm" : "—"], ["收纳尺寸", folded.length ? folded.join(" × ") + " mm" : "—"], ["结构方式", spec.parameters?.adjustment || spec.parameters?.installation || "—"], ["材料", (spec.materials || []).map((m) => `${m.component}: ${m.material} (${m.status})`).join("；")], ["尺寸公差", `±${spec.tolerances?.dimension_mm || "—"} mm`], ["测试要求", (spec.test_requirements || []).join("；")], ["spec_hash", spec.spec_hash],
  ];
  $("[data-field='sample-spec']",root).innerHTML = specRows.map(([label,value], index) => `<div class="spec-row ${index === specRows.length-1 ? "hash-row" : ""}"><span>${esc(label)}</span><b>${esc(value)}</b></div>`).join("");

  $("[data-field='rfq']",root).innerHTML = `<div class="rfq-facts"><div><small>样品数量</small><b>${esc(rfq.quantity || 0)} 件</b></div><div><small>目标 MOQ</small><b>${esc(rfq.target_moq || "—")}</b></div><div><small>目标交期</small><b>${esc(rfq.target_lead_days || "—")} 天</b></div></div><div class="rfq-questions"><strong>必须逐项响应</strong><p>${esc((rfq.questions || []).join(" · "))}</p><p>包装：${esc((rfq.packaging_requirements || []).join(" · "))}</p></div>`;
  const economics = sections.economics || {};
  const targetPrice = economics.target_retail_cny || economics.target_price_cny;
  const targetLabel = Array.isArray(targetPrice) ? `¥${targetPrice.join("–")}` : (typeof targetPrice === "number" ? `¥${targetPrice.toFixed(0)}` : "待确认");
  const margin = economics.verified_profit?.contribution_margin ?? economics.gross_margin;
  const economicCards = [
    ["目标售价", targetLabel, "用户硬约束，不是市场事实", ""], ["工厂成本", money(economics.factory_cost_cny), "需真实 RFQ 与 BOM", economics.factory_cost_cny == null ? "warning" : ""], ["贡献毛利", margin == null ? "未验证" : `${Math.round(margin*100)}%`, "估算不得升级为验证利润", margin == null ? "warning" : ""], ["数据状态", economics.data_mode || data.data_mode, economics.warning || "版本化模型", ""],
  ];
  $("[data-field='economics']",root).innerHTML = economicCards.map(([label,value,copy,klass]) => `<div class="economics-card ${klass}"><small>${esc(label)}</small><strong>${esc(value)}</strong><p>${esc(copy)}</p></div>`).join("");
  const compliance = sections.compliance || {};
  $("[data-field='compliance']",root).innerHTML = (compliance.checks || []).map((check) => `<div class="check-item"><div><h3>${esc(check.title)}</h3><p>${esc((check.remediation || []).join("；"))}</p></div><span class="result-chip ${resultClass(check.result)}">${esc(check.result)}</span></div>`).join("");
  $("[data-field='tests']",root).innerHTML = (sections.tests?.tests || []).map((test) => `<div class="test-item"><div><h3>${esc(test.name)}</h3><p>${esc(test.method)} · n=${esc(test.sample_size)} · ${esc(test.acceptance_criteria)}</p></div><span class="result-chip ${resultClass(test.status)}">${esc(test.status)}</span></div>`).join("");
  $("[data-field='findings']",root).innerHTML = (review.findings || []).map((finding) => `<div class="finding"><b>${esc(finding.rule_id)}</b><div><h3>${esc(finding.result)}</h3><p>${esc(finding.message)}</p></div></div>`).join("") || `<div class="finding"><b>PASS</b><div><h3>Reviewer 未发现阻断项</h3><p>仍需人工审批绑定当前 spec_hash 和 policy version。</p></div></div>`;
  $("[data-field='artifact-refs']",root).innerHTML = (data.artifact_refs || []).map((ref) => `<span>${esc(ref)}</span>`).join("");

  const availableSections = new Set(Object.keys(sections));
  $$('[data-section]', root).forEach((section) => { if (!availableSections.has(section.dataset.section)) section.remove(); });
  $("#story-root").replaceChildren(fragment);
  $("#story-mode").textContent = `${data.data_mode} · ${String(data.view || currentView).toUpperCase()}`;
  if (window.Motion && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    window.Motion.animate(".hero-copy > *", {opacity:[0,1], y:[14,0]}, {duration:.5, delay:window.Motion.stagger(.055), easing:"ease-out"});
    window.Motion.animate(".hero-visual img", {opacity:[0,1], scale:[.96,1], y:[18,0]}, {duration:.7, easing:"ease-out"});
    window.Motion.inView(".section", (element) => {
      const targets = element.querySelectorAll(".section-head, .pain-card, .concept-card, .spec-layout, .commerce-grid, .economics-card, .safety-layout, .review-layout, .artifact-list");
      window.Motion.animate(targets, {opacity:[0,1], y:[18,0]}, {duration:.48, delay:window.Motion.stagger(.035), easing:"ease-out"});
    }, {margin:"0px 0px -16% 0px"});
  }
}

async function load(view) {
  currentView = view;
  $$(".view-tabs button").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  try {
    const response = await fetch(`/api/story?view=${encodeURIComponent(view)}&project=${encodeURIComponent(currentProject)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    render(data);
  } catch (error) { $("#story-root").innerHTML = `<div class="story-error"><h2>Product Story 尚未生成</h2><p>${esc(error.message)}</p><p>先在项目目录运行 <code>make demo-real</code>。</p></div>`; }
}

$$(".view-tabs button").forEach((button) => button.addEventListener("click", () => load(button.dataset.view)));
const projectSelect = $("#story-project");
projectSelect.value = currentProject;
projectSelect.addEventListener("change", () => {
  currentProject = projectSelect.value;
  const next = new URL(location.href);
  next.searchParams.set("project", currentProject);
  history.replaceState({}, "", next);
  load(currentView);
});
$("#print-button").addEventListener("click", () => window.print());
load(currentView);
