const PRESETS = {
  valid: [
    { name: "Eleanor Vance", email: "eleanor.vance@example.com", metadata: { grade: "Distinction" } },
    { name: "Marcus Holloway", email: "marcus.h@example.com", metadata: { grade: "A+" } },
    { name: "Dr. Sarah Chen", email: "chen.sarah@research.org" },
    { name: "Aarav Patel", email: "aarav.patel@example.com" },
    { name: "Beatriz Morales", email: "beatriz.m@example.com", metadata: { grade: "Honors" } }
  ],
  mixed: [
    { name: "Jonathan Reed", email: "jonathan.reed@example.com" },
    { name: "Sophia Taylor", email: "sophia.t@example.com" },
    { name: "   ", email: "bad_name@example.com" }, // Blank name -> Will fail validation
    { name: "Liam O'Connor", email: "invalid-email-address" }, // Invalid email -> Will fail validation
    { name: "Elena Rostova", email: "elena.rostova@example.com", metadata: { grade: "Top Graduate" } }
  ],
  large: Array.from({ length: 20 }, (_, i) => ({
    name: `Participant ${i + 1} Alverez`,
    email: `participant.${i + 1}@example.com`,
    metadata: { cohort: "2026-Q3", score: 85 + (i % 15) }
  }))
};

let currentJobId = null;
let pollInterval = null;

// DOM Elements
const jobForm = document.getElementById("jobForm");
const recipientsInput = document.getElementById("recipientsInput");
const submitBtn = document.getElementById("submitBtn");
const recipientCountBadge = document.getElementById("recipientCountBadge");

const btnPresetValid = document.getElementById("btnPresetValid");
const btnPresetMixed = document.getElementById("btnPresetMixed");
const btnPresetLarge = document.getElementById("btnPresetLarge");

const noJobPlaceholder = document.getElementById("noJobPlaceholder");
const jobDetailsContainer = document.getElementById("jobDetailsContainer");
const displayJobTitle = document.getElementById("displayJobTitle");
const displayJobId = document.getElementById("displayJobId");
const displayJobStatus = document.getElementById("displayJobStatus");
const progressText = document.getElementById("progressText");
const progressCounts = document.getElementById("progressCounts");
const progressBarFill = document.getElementById("progressBarFill");
const statTotal = document.getElementById("statTotal");
const statProcessed = document.getElementById("statProcessed");
const statSuccess = document.getElementById("statSuccess");
const statFailed = document.getElementById("statFailed");
const zipDownloadArea = document.getElementById("zipDownloadArea");
const btnDownloadZip = document.getElementById("btnDownloadZip");
const recipientsTableBody = document.getElementById("recipientsTableBody");

const previewModal = document.getElementById("previewModal");
const pdfFrame = document.getElementById("pdfFrame");
const modalCertTitle = document.getElementById("modalCertTitle");
const modalCloseBtn = document.getElementById("modalCloseBtn");

const modeJsonBtn = document.getElementById("modeJsonBtn");
const modeCsvBtn = document.getElementById("modeCsvBtn");
const jsonInputArea = document.getElementById("jsonInputArea");
const csvInputArea = document.getElementById("csvInputArea");
const csvFileInput = document.getElementById("csvFileInput");
let currentMode = "json";

modeJsonBtn.addEventListener("click", () => {
  currentMode = "json";
  jsonInputArea.style.display = "block";
  csvInputArea.style.display = "none";
  modeJsonBtn.style.borderColor = "#3B82F6";
  modeJsonBtn.style.color = "#fff";
  modeCsvBtn.style.borderColor = "var(--card-border)";
  modeCsvBtn.style.color = "var(--text-muted)";
});

modeCsvBtn.addEventListener("click", () => {
  currentMode = "csv";
  jsonInputArea.style.display = "none";
  csvInputArea.style.display = "block";
  modeCsvBtn.style.borderColor = "#3B82F6";
  modeCsvBtn.style.color = "#fff";
  modeJsonBtn.style.borderColor = "var(--card-border)";
  modeJsonBtn.style.color = "var(--text-muted)";
});

function loadPreset(presetKey) {
  const data = PRESETS[presetKey] || PRESETS.valid;
  recipientsInput.value = JSON.stringify(data, null, 2);
  updateBadge();
}

function updateBadge() {
  try {
    const parsed = JSON.parse(recipientsInput.value);
    if (Array.isArray(parsed)) {
      recipientCountBadge.textContent = `${parsed.length} recipients loaded`;
      return;
    }
  } catch (e) {
    recipientCountBadge.textContent = "Invalid JSON syntax";
  }
}

recipientsInput.addEventListener("input", updateBadge);
btnPresetValid.addEventListener("click", () => loadPreset("valid"));
btnPresetMixed.addEventListener("click", () => loadPreset("mixed"));
btnPresetLarge.addEventListener("click", () => loadPreset("large"));

jobForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const titleVal = document.getElementById("eventTitle").value.trim();
  const issuerVal = document.getElementById("issuerName").value.trim();
  const dateVal = document.getElementById("issueDate").value.trim();
  const descVal = document.getElementById("description").value.trim() || null;

  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span>Submitting Job...</span>`;

  try {
    let res;
    if (currentMode === "csv") {
      if (!csvFileInput.files || csvFileInput.files.length === 0) {
        alert("Please select a .csv file to upload.");
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>Submit Generation Job</span>`;
        return;
      }
      const formData = new FormData();
      formData.append("file", csvFileInput.files[0]);
      formData.append("title", titleVal);
      formData.append("issuer_name", issuerVal);
      formData.append("issue_date", dateVal);
      if (descVal) formData.append("description", descVal);

      res = await fetch("/api/v1/jobs/upload-csv", {
        method: "POST",
        body: formData
      });
    } else {
      let recipients = [];
      try {
        recipients = JSON.parse(recipientsInput.value);
        if (!Array.isArray(recipients) || recipients.length === 0) {
          alert("Please provide a non-empty array of recipient objects.");
          submitBtn.disabled = false;
          submitBtn.innerHTML = `<span>Submit Generation Job</span>`;
          return;
        }
      } catch (err) {
        alert("Invalid JSON format in recipients field. Please check your syntax.");
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>Submit Generation Job</span>`;
        return;
      }

      const payload = {
        title: titleVal,
        issuer_name: issuerVal,
        issue_date: dateVal,
        description: descVal,
        recipients: recipients
      };

      res = await fetch("/api/v1/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    }

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || "Failed to submit job.");
    }

    const data = await res.json();
    currentJobId = data.job_id;

    noJobPlaceholder.style.display = "none";
    jobDetailsContainer.style.display = "flex";
    displayJobTitle.textContent = payload.title;
    displayJobId.textContent = `Job ID: ${currentJobId}`;

    startPolling(currentJobId);
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span>Submit Generation Job</span>`;
  }
});

function startPolling(jobId) {
  if (pollInterval) clearInterval(pollInterval);
  fetchJobStatus(jobId);
  pollInterval = setInterval(() => fetchJobStatus(jobId), 700);
}

async function fetchJobStatus(jobId) {
  try {
    const res = await fetch(`/api/v1/jobs/${jobId}`);
    if (!res.ok) return;

    const job = await res.json();
    updateJobUI(job);

    if (["COMPLETED", "PARTIAL_SUCCESS", "FAILED"].includes(job.status)) {
      clearInterval(pollInterval);
    }
  } catch (err) {
    console.error("Polling error:", err);
  }
}

function updateJobUI(job) {
  displayJobTitle.textContent = job.title;
  displayJobStatus.textContent = job.status;
  displayJobStatus.className = `badge badge-${job.status}`;

  statTotal.textContent = job.total_count;
  statProcessed.textContent = job.processed_count;
  statSuccess.textContent = job.success_count;
  statFailed.textContent = job.failed_count;

  const pct = job.progress_percentage || 0;
  progressText.textContent = `Progress: ${pct}%`;
  progressCounts.textContent = `${job.processed_count} / ${job.total_count} processed`;
  progressBarFill.style.width = `${pct}%`;

  if (job.zip_download_url) {
    btnDownloadZip.href = job.zip_download_url;
    zipDownloadArea.style.display = "block";
  } else {
    zipDownloadArea.style.display = "none";
  }

  recipientsTableBody.innerHTML = "";
  (job.certificates || []).forEach((c) => {
    const tr = document.createElement("tr");

    let statusBadge = `<span class="badge badge-${c.status}">${c.status}</span>`;
    let actions = "";

    if (c.status === "SUCCESS") {
      actions = `
        <div style="display: flex; gap: 6px;">
          <a href="${c.download_url}" class="action-btn" download title="Download PDF">PDF</a>
          <button class="action-btn" onclick="openPreview('${c.preview_url}', '${c.recipient_name}')" title="Preview PDF">View</button>
        </div>
      `;
    } else if (c.status === "FAILED") {
      actions = `<span style="font-size: 0.75rem; color: #EF4444;" title="${c.failure_reason || ''}">${c.failure_reason || 'Generation failed'}</span>`;
    } else {
      actions = `<span style="font-size: 0.75rem; color: var(--text-muted);">Queued...</span>`;
    }

    tr.innerHTML = `
      <td>
        <div style="font-weight: 500;">${escapeHtml(c.recipient_name)}</div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(c.recipient_email || 'No email')}</div>
      </td>
      <td>${statusBadge}</td>
      <td style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;">${escapeHtml(c.certificate_number)}</td>
      <td>${actions}</td>
    `;
    recipientsTableBody.appendChild(tr);
  });
}

function openPreview(url, name) {
  modalCertTitle.textContent = `Certificate: ${name}`;
  pdfFrame.src = url;
  previewModal.style.display = "flex";
}

modalCloseBtn.addEventListener("click", () => {
  previewModal.style.display = "none";
  pdfFrame.src = "";
});

window.addEventListener("click", (e) => {
  if (e.target === previewModal) {
    previewModal.style.display = "none";
    pdfFrame.src = "";
  }
});

function escapeHtml(text) {
  if (!text) return "";
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

loadPreset("valid");
