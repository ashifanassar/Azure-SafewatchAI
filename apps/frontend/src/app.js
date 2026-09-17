const DEFAULT_API = "https://safewatch-api.victoriousflower-c9f9a1d0.uaenorth.azurecontainerapps.io";
const APP_VERSION = "ui-v23-audit-trail";

const state = {
  latest: null,
  history: JSON.parse(localStorage.getItem("safewatch.history") || "[]"),
  auditTrail: JSON.parse(localStorage.getItem("safewatch.auditTrail") || "[]"),
  api: localStorage.getItem("safewatch.api") || DEFAULT_API,
  selectedIncidentId: null,
};

const apiUrl = requireElement("apiUrl");
const requestPreview = requireElement("requestPreview");
const emptyResult = requireElement("emptyResult");
const summaryCards = requireElement("summaryCards");
const findings = requireElement("findings");
const citations = requireElement("citations");
const queue = requireElement("queue");
const decisionDetail = requireElement("decisionDetail");
const configGrid = requireElement("configGrid");
const apiStatus = requireElement("apiStatus");
const uploadStatus = requireElement("uploadStatus");
const auditTrail = requireElement("auditTrail");

apiUrl.value = state.api;

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

requireElement("saveApi").addEventListener("click", () => {
  state.api = apiUrl.value.trim().replace(/\/$/, "");
  localStorage.setItem("safewatch.api", state.api);
  checkStatus();
});

requireElement("refreshStatus").addEventListener("click", checkStatus);
requireElement("runAnalysis").addEventListener("click", runAnalysis);

[
  "incidentId",
  "siteId",
  "zoneId",
  "workType",
  "contractorId",
  "createdBy",
].forEach((id) => {
  requireElement(id).addEventListener("input", updatePreview);
});

["permitFile", "imageFile"].forEach((id) => {
  requireElement(id).addEventListener("change", updatePreview);
});

seedIncidentId();
updatePreview();
renderQueue();
renderAuditTrail();
checkStatus();

function switchView(viewName) {
  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === viewName);
  });
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("is-visible", view.id === viewName);
  });
  const titles = {
    operations: "Operations Console",
    governance: "Governance Dashboard",
    modelops: "Model Ops",
  };
  requireElement("viewTitle").textContent = titles[viewName];
}

function seedIncidentId() {
  const stamp = new Date().toISOString().slice(11, 19).replaceAll(":", "");
  requireElement("incidentId").value = `inc-work-start-${stamp}`;
}

function buildPreviewPayload() {
  return {
    incident_id: valueOf("incidentId"),
    site_id: valueOf("siteId"),
    zone_id: valueOf("zoneId"),
    work_type: valueOf("workType"),
    contractor_id: valueOf("contractorId"),
    created_by: valueOf("createdBy"),
    evidence: buildEvidencePreview(),
  };
}

function buildEvidencePreview() {
  const evidence = [];
  const permitFile = fileOf("permitFile");
  const imageFile = fileOf("imageFile");

  if (permitFile) {
    evidence.push({
      evidence_id: "permit-upload",
      uri: `upload://${permitFile.name}`,
      kind: "permit",
      metadata: {},
    });
  }

  if (imageFile) {
    evidence.push({
      evidence_id: "image-upload",
      uri: `upload://${imageFile.name}`,
      kind: "image",
      metadata: {},
    });
  }

  return evidence;
}

async function buildPayloadWithUploads() {
  const evidence = [];
  const permitFile = fileOf("permitFile");
  const imageFile = fileOf("imageFile");

  if (!permitFile) {
    throw new Error("Upload the work permit PDF before running the workflow.");
  }

  if (!imageFile) {
    throw new Error("Upload the site safety image before running the workflow.");
  }

  const incidentId = valueOf("incidentId") || `inc-work-start-${Date.now()}`;

  uploadStatus.textContent = `Uploading work permit PDF: ${permitFile.name} (${formatFileSize(permitFile.size)})...`;
  evidence.push(await uploadEvidence("permit", `permit-${incidentId}`, permitFile, {}));

  uploadStatus.textContent = `Uploading site safety image: ${imageFile.name} (${formatFileSize(imageFile.size)})...`;
  evidence.push(await uploadEvidence("image", `image-${incidentId}`, imageFile, {}));

  return {
    incident_id: incidentId,
    site_id: valueOf("siteId"),
    zone_id: valueOf("zoneId"),
    work_type: valueOf("workType"),
    contractor_id: valueOf("contractorId"),
    created_by: valueOf("createdBy"),
    evidence,
  };
}

function valueOf(id) {
  return requireElement(id).value.trim();
}

function fileOf(id) {
  return requireElement(id).files?.[0] || null;
}

function requireElement(id) {
  const element = document.querySelector(`#${id}`);
  if (!element) {
    throw new Error(`UI field missing: ${id}. Hard refresh the page and try again.`);
  }
  return element;
}

function updatePreview() {
  requestPreview.textContent = JSON.stringify(buildPreviewPayload(), null, 2);
}

async function checkStatus() {
  setStatus("Checking", "neutral");
  try {
    const config = await getJson("/config/status");
    setStatus("Connected", "ok");
    renderConfig(config);
  } catch (error) {
    setStatus("Offline", "danger");
    renderConfig({ error: error.message });
  }
}

function setStatus(text, tone) {
  apiStatus.textContent = text;
  apiStatus.style.background = tone === "ok" ? "#15803d" : tone === "danger" ? "#b91c1c" : "#334d48";
}

async function runAnalysis() {
  const button = requireElement("runAnalysis");
  button.disabled = true;
  button.textContent = "Running agents...";
  uploadStatus.textContent = "Preparing evidence package...";
  let stage = "preparing the evidence package";
  try {
    stage = "uploading evidence files";
    const payload = await buildPayloadWithUploads();
    requestPreview.textContent = JSON.stringify(payload, null, 2);
    stage = "calling the LangGraph analyze endpoint";
    uploadStatus.textContent = "Evidence ready. Running LangGraph workflow...";
    const result = await postJson("/incidents/analyze", payload);
    state.latest = result;
    state.history = [result, ...state.history.filter((item) => item.incident.incident_id !== result.incident.incident_id)].slice(0, 12);
    localStorage.setItem("safewatch.history", JSON.stringify(state.history));
    uploadStatus.textContent = "Analysis complete. Reviewer packet created.";
    renderResult(result);
    renderQueue();
    switchView("operations");
  } catch (error) {
    uploadStatus.textContent = "";
    emptyResult.classList.remove("hidden");
    emptyResult.textContent = `Request failed while ${stage}: ${error.message}`;
    summaryCards.classList.add("hidden");
    findings.classList.add("hidden");
    citations.classList.add("hidden");
  } finally {
    button.disabled = false;
    button.textContent = "Analyze Work Start";
  }
}

async function uploadEvidence(kind, evidenceId, file, metadata) {
  const form = new FormData();
  form.append("kind", kind);
  form.append("evidence_id", evidenceId);
  form.append("file", file);

  const url = `${apiBase()}/evidence/upload`;
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      body: form,
    });
  } catch (error) {
    throw new Error(
      `Browser could not reach ${url} for ${kind} file "${file.name}". ${networkHint(error)}`,
    );
  }
  if (!response.ok) throw new Error(await errorBody(response));
  const uploaded = await response.json();
  return {
    evidence_id: uploaded.evidence_id,
    uri: uploaded.uri,
    kind: uploaded.kind,
    metadata,
  };
}

async function getJson(path) {
  const url = `${apiBase()}${path}`;
  let response;
  try {
    response = await fetch(url);
  } catch (error) {
    throw new Error(`Browser could not reach ${url}. ${networkHint(error)}`);
  }
  if (!response.ok) throw new Error(await errorBody(response));
  return response.json();
}

async function postJson(path, payload) {
  const url = `${apiBase()}${path}`;
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    throw new Error(`Browser could not reach ${url}. ${networkHint(error)}`);
  }
  if (!response.ok) throw new Error(await errorBody(response));
  return response.json();
}

function apiBase() {
  const value = state.api.trim().replace(/\/$/, "");
  if (!value) {
    throw new Error("Backend API URL is empty.");
  }
  if (!value.startsWith("https://")) {
    throw new Error(`Backend API URL must start with https://. Current value: ${value}`);
  }
  return value;
}

function networkHint(error) {
  const message = error instanceof Error ? error.message : String(error);
  return `${message}. Check the Backend API field, then hard refresh the UI.`;
}

async function errorBody(response) {
  const text = await response.text();
  return `${response.status} ${response.statusText}${text ? `: ${text}` : ""}`;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function renderResult(result) {
  emptyResult.classList.add("hidden");
  summaryCards.classList.remove("hidden");
  findings.classList.remove("hidden");
  citations.classList.remove("hidden");

  summaryCards.innerHTML = [
    metric("Risk Score", `${result.risk.risk_score}`, result.risk.risk_band),
    metric("Approval", result.governance.approval_level, result.governance.approval_level),
    metric("Status", result.incident.status, result.incident.status),
  ].join("");

  findings.innerHTML = [
    sectionLine("Incident", `${result.incident.incident_id} at ${result.incident.site_id} / ${result.incident.zone_id || "no zone"}`),
    sectionLine("Risk Explanation", result.risk.explanation),
    sectionLine("Governance Rules", result.governance.triggered_rules.join(", ") || "none"),
    sectionLine("Hard Overrides", result.governance.hard_overrides.join(", ") || "none"),
    ...result.reviewer_packet.key_findings.map((item) => sectionLine("Finding", item)),
  ].join("");

  citations.innerHTML = `<h3>Citations</h3>${result.citations.map(renderCitation).join("")}`;
  decisionDetail.innerHTML = renderDecision(result);
}

function metric(label, value, tone) {
  return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><div class="badge ${badgeTone(tone)}">${escapeHtml(tone)}</div></div>`;
}

function sectionLine(label, value) {
  return `<div class="finding"><strong>${escapeHtml(label)}</strong><p>${escapeHtml(value)}</p></div>`;
}

function renderCitation(citation) {
  return `<article class="citation">
    <h4>${escapeHtml(citation.source)} ${escapeHtml(citation.clause_id)} - ${escapeHtml(citation.title)}</h4>
    <p>${escapeHtml(citation.excerpt)}</p>
    <span class="badge">score ${escapeHtml(String(citation.relevance_score))}</span>
  </article>`;
}

function renderQueue() {
  const pending = state.history.filter((result) => isPendingHumanReview(result));
  if (!pending.length) {
    queue.innerHTML = `<div class="empty-state">No incidents are waiting for human review.</div>`;
    decisionDetail.innerHTML = `<div class="empty-state">Select a pending review incident after running a medium or high risk case.</div>`;
    return;
  }
  if (!state.selectedIncidentId || !pending.some((result) => result.incident.incident_id === state.selectedIncidentId)) {
    state.selectedIncidentId = pending[0].incident.incident_id;
  }
  queue.innerHTML = pending
    .map(
      (result) => `<button class="queue-item ${result.incident.incident_id === state.selectedIncidentId ? "is-selected" : ""}" data-incident="${result.incident.incident_id}">
        <h4>${escapeHtml(result.incident.incident_id)}</h4>
        <p>${escapeHtml(result.governance.approval_level)} - risk ${escapeHtml(String(result.risk.risk_score))} - ${escapeHtml(result.incident.status)}</p>
      </button>`,
    )
    .join("");
  queue.querySelectorAll(".queue-item").forEach((button) => {
    button.addEventListener("click", () => {
      queue.querySelectorAll(".queue-item").forEach((item) => item.classList.remove("is-selected"));
      button.classList.add("is-selected");
      state.selectedIncidentId = button.dataset.incident;
      const result = state.history.find((item) => item.incident.incident_id === state.selectedIncidentId);
      decisionDetail.innerHTML = result ? renderDecision(result) : "No incident selected.";
    });
  });
  decisionDetail.innerHTML = renderDecision(pending.find((item) => item.incident.incident_id === state.selectedIncidentId));
}

function renderDecision(result) {
  if (!result) return `<div class="empty-state">No incident selected.</div>`;
  const canReview = isPendingHumanReview(result);
  return `<div class="decision-detail">
    ${sectionLine("Summary", result.reviewer_packet.summary)}
    ${sectionLine("Required Approval", result.reviewer_packet.required_approval)}
    ${sectionLine("Human Review Required", String(result.governance.human_review_required))}
    ${sectionLine("Blocked Actions", result.governance.blocked_actions.join(", ") || "none")}
    ${
      canReview
        ? `<div class="review-actions">
            <button class="approve-action" data-action="approve" data-incident="${escapeHtml(result.incident.incident_id)}">Approve</button>
            <button class="reject-action" data-action="reject" data-incident="${escapeHtml(result.incident.incident_id)}">Reject</button>
          </div>`
        : sectionLine("Review Outcome", result.incident.status)
    }
    <div class="citations">${result.citations.slice(0, 3).map(renderCitation).join("")}</div>
  </div>`;
}

function isPendingHumanReview(result) {
  return result?.governance?.human_review_required === true && result?.incident?.status === "pending_review";
}

async function reviewIncident(incidentId, action) {
  const result = state.history.find((item) => item.incident.incident_id === incidentId);
  if (!result) return;
  const reviewerId = valueOf("createdBy") || "ashifa";
  const comment = action === "approve" ? "Approved after HSE review." : "Rejected after HSE review.";
  try {
    const response = await postJson(`/incidents/${encodeURIComponent(incidentId)}/review`, {
      action,
      reviewer_id: reviewerId,
      comment,
    });
    result.incident.status = response.status;
    recordAuditEvent({
      incident_id: incidentId,
      event_type: `incident_${response.status}`,
      actor_id: reviewerId,
      comment,
      created_at: new Date().toISOString(),
    });
  } catch (error) {
    decisionDetail.insertAdjacentHTML(
      "afterbegin",
      `<div class="review-error">Review action failed: ${escapeHtml(error.message)}</div>`,
    );
    return;
  }
  state.history = state.history.map((item) => (item.incident.incident_id === incidentId ? result : item));
  localStorage.setItem("safewatch.history", JSON.stringify(state.history));
  renderQueue();
  if (state.latest?.incident?.incident_id === incidentId) {
    state.latest = result;
    renderResult(result);
  }
}

function recordAuditEvent(event) {
  state.auditTrail = [event, ...state.auditTrail].slice(0, 20);
  localStorage.setItem("safewatch.auditTrail", JSON.stringify(state.auditTrail));
  renderAuditTrail();
}

function renderAuditTrail() {
  if (!state.auditTrail.length) {
    auditTrail.innerHTML = `<div class="empty-state">No approval or rejection actions in this browser session yet.</div>`;
    return;
  }
  auditTrail.innerHTML = state.auditTrail
    .map(
      (event) => `<article class="audit-item">
        <strong>${escapeHtml(event.event_type)}</strong>
        <p>${escapeHtml(event.incident_id)} by ${escapeHtml(event.actor_id)} at ${escapeHtml(new Date(event.created_at).toLocaleString())}</p>
        <p>${escapeHtml(event.comment || "No comment")}</p>
      </article>`,
    )
    .join("");
}

decisionDetail.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  button.disabled = true;
  button.textContent = button.dataset.action === "approve" ? "Approving..." : "Rejecting...";
  await reviewIncident(button.dataset.incident, button.dataset.action);
});

function renderConfig(config) {
  configGrid.innerHTML = Object.entries({ app_version: APP_VERSION, ...config })
    .map(([key, value]) => `<div class="config-item"><span>${escapeHtml(key)}</span><strong>${escapeHtml(String(value))}</strong></div>`)
    .join("");
}

function badgeTone(value) {
  const text = String(value).toLowerCase();
  if (text.includes("high") || text.includes("critical") || text.includes("escalation")) return "high";
  if (text.includes("medium") || text.includes("hse")) return "medium";
  if (text.includes("low") || text.includes("auto")) return "low";
  return "";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
