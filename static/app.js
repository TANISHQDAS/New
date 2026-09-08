let currentAnalysisData = null;

document.addEventListener("DOMContentLoaded", () => {
  loadDataset("delhivery");
});

function switchTab(tabId, el) {
  document.querySelectorAll(".aws-tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.style.display = "none");
  
  if (el) el.classList.add("active");
  const target = document.getElementById(`tab-${tabId}`);
  if (target) target.style.display = "block";
}

async function loadDataset(datasetId) {
  try {
    const response = await fetch(`/api/analysis/${datasetId}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    currentAnalysisData = data;
    renderAnalysis(data);
  } catch (err) {
    console.error("Error loading dataset:", err);
  }
}

function renderAnalysis(data) {
  // Update stats & tab badges
  const factCount = data.facts_extracted_count || (data.facts ? data.facts.length : 0);
  document.getElementById("statFactCount").innerText = factCount;
  document.getElementById("badgeFacts").innerText = factCount;
  
  const docName = data.dataset_id.includes("delhivery") 
    ? "3 PDFs (Delhivery)" 
    : (data.dataset_id.includes("macroeconomy") ? "3 PDFs (Macroeconomy)" : `Uploaded PDF`);
  document.getElementById("statDocCount").innerText = docName;

  // Render 4 Cases Grid
  renderCases(data.cases);

  // Render Facts Table
  renderFactsTable(data.facts);

  // Render Reconciliation Matrix
  renderMatrix(data.cases);
}

function renderCases(cases) {
  const grid = document.getElementById("casesGrid");
  grid.innerHTML = "";

  const caseConfig = [
    { key: "Case 1: Corroborated Fact", class: "case1", icon: "✅", title: "Case 1: Corroborated Fact Across Documents" },
    { key: "Case 2: Genuine Contradiction", class: "case2", icon: "🚨", title: "Case 2: Genuine or Likely Contradiction" },
    { key: "Case 3: Apparent Contradiction (Reconciled by Context)", class: "case3", icon: "🧩", title: "Case 3: Apparent Contradiction Reconciled by Context" },
    { key: "Case 4: Extraction/Reasoning Failure & Mitigation", class: "case4", icon: "⚠️", title: "Case 4: Extraction / Reasoning Failure & Handling" }
  ];

  let cardIndex = 0;

  caseConfig.forEach(cfg => {
    const rels = cases[cfg.key] || [];
    rels.forEach(rel => {
      cardIndex++;
      const card = document.createElement("div");
      card.className = `case-card ${cfg.class}`;

      let docAHTML = "";
      if (rel.fact_a) {
        docAHTML = `
          <div class="evidence-panel">
            <div class="evidence-panel-header">
              <span class="doc-tag">📄 Doc A: ${rel.fact_a.evidence.doc_name}</span>
              <span class="pill-badge">Page ${rel.fact_a.evidence.page_number}</span>
            </div>
            <div class="metric-highlight">
              <strong>${rel.fact_a.metric_name}:</strong> 
              <span class="metric-val">${rel.fact_a.raw_value}</span>
              <span style="font-size: 12px; color: var(--text-muted);">(${rel.fact_a.timeframe})</span>
            </div>
            <div class="quote-block">"${rel.fact_a.evidence.verbatim_quote}"</div>
          </div>
        `;
      }

      let docBHTML = "";
      if (rel.fact_b) {
        docBHTML = `
          <div class="evidence-panel">
            <div class="evidence-panel-header">
              <span class="doc-tag">📄 Doc B: ${rel.fact_b.evidence.doc_name}</span>
              <span class="pill-badge">Page ${rel.fact_b.evidence.page_number}</span>
            </div>
            <div class="metric-highlight">
              <strong>${rel.fact_b.metric_name}:</strong> 
              <span class="metric-val">${rel.fact_b.raw_value}</span>
              <span style="font-size: 12px; color: var(--text-muted);">(${rel.fact_b.timeframe})</span>
            </div>
            <div class="quote-block">"${rel.fact_b.evidence.verbatim_quote}"</div>
          </div>
        `;
      }

      let mitigationHTML = "";
      if (rel.handling_strategy) {
        mitigationHTML = `
          <div style="background-color: var(--case4-bg); border: 1px solid var(--case4-border); padding: 12px 16px; border-radius: var(--radius-sm); margin-top: 12px; color: var(--case4-color);">
            <strong>🛠️ Mitigation Strategy & Automated Handling:</strong><br>
            ${rel.handling_strategy}
          </div>
        `;
      }

      const reasoningId = `reasoning-${cardIndex}`;

      card.innerHTML = `
        <div class="case-card-header">
          <span class="case-title-text">${rel.title}</span>
          <span class="case-badge">${cfg.icon} ${rel.case_type}</span>
        </div>
        <div class="case-card-body">
          <div class="case-summary">${rel.summary}</div>
          <div class="comparison-grid">
            ${docAHTML}
            ${docBHTML}
          </div>
          <div class="reasoning-toggle" onclick="toggleReasoning('${reasoningId}')">
            <span>🧠 System Reasoning & Grounded Reconciliation</span>
            <span id="icon-${reasoningId}">▼</span>
          </div>
          <div class="reasoning-content" id="${reasoningId}" style="display: none;">
            ${rel.reasoning}
          </div>
          ${mitigationHTML}
        </div>
      `;
      grid.appendChild(card);
    });
  });
}

function toggleReasoning(id) {
  const content = document.getElementById(id);
  const icon = document.getElementById(`icon-${id}`);
  if (content.style.display === "none") {
    content.style.display = "block";
    if (icon) icon.innerText = "▲";
  } else {
    content.style.display = "none";
    if (icon) icon.innerText = "▼";
  }
}

function renderFactsTable(facts) {
  const tbody = document.getElementById("factsTableBody");
  tbody.innerHTML = "";

  if (!facts || facts.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">No facts extracted yet.</td></tr>`;
    return;
  }

  facts.forEach(f => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${f.entity}</strong></td>
      <td><span style="font-weight: 600; color: var(--accent-blue);">${f.metric_name}</span></td>
      <td><span class="pill-badge" style="background-color: var(--accent-blue-light); color: var(--accent-blue); font-size: 13px;">${f.raw_value}</span></td>
      <td><span class="pill-badge">${f.timeframe}</span></td>
      <td><span style="font-size: 12.5px; color: var(--text-muted);">${f.scope || 'Consolidated'}</span></td>
      <td><span style="font-size: 12px; font-family: var(--font-mono); color: var(--primary-navy);">${f.evidence.doc_name}</span></td>
      <td><strong>P. ${f.evidence.page_number}</strong></td>
      <td><span class="quote-block" style="font-size: 12px; padding: 6px 10px; margin: 0; display: block;">"${f.evidence.verbatim_quote}"</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function filterFactsTable() {
  const query = document.getElementById("factSearch").value.toLowerCase();
  const rows = document.querySelectorAll("#factsTableBody tr");
  rows.forEach(r => {
    const text = r.innerText.toLowerCase();
    r.style.display = text.includes(query) ? "" : "none";
  });
}

function renderMatrix(cases) {
  const container = document.getElementById("reconciliationMatrix");
  container.innerHTML = "";

  const allRels = [];
  Object.values(cases).forEach(arr => allRels.push(...arr));

  if (allRels.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 24px;">No reconciliation pairs available.</div>`;
    return;
  }

  const tableWrapper = document.createElement("div");
  tableWrapper.className = "table-wrapper";

  const table = document.createElement("table");
  table.className = "aws-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>Case Classification</th>
        <th>Fact Pair Title</th>
        <th>Source Document A</th>
        <th>Source Document B</th>
        <th>Key Reconciliation Factors</th>
        <th>Confidence</th>
      </tr>
    </thead>
    <tbody>
      ${allRels.map(r => `
        <tr>
          <td><span class="pill-badge" style="font-weight: 700;">${r.case_type}</span></td>
          <td><strong>${r.title}</strong></td>
          <td><span style="font-size: 12px; font-family: var(--font-mono);">${r.source_documents[0] || 'N/A'}</span></td>
          <td><span style="font-size: 12px; font-family: var(--font-mono);">${r.source_documents[1] || 'N/A'}</span></td>
          <td>${(r.reconciliation_factors || []).join(" &bull; ")}</td>
          <td><span style="color: var(--case1-color); font-weight: 800;">${Math.round((r.confidence || 0.9) * 100)}%</span></td>
        </tr>
      `).join('')}
    </tbody>
  `;
  tableWrapper.appendChild(table);
  container.appendChild(tableWrapper);
}

async function uploadPDF(file) {
  if (!file) return;
  const statusDiv = document.getElementById("uploadStatus");
  statusDiv.innerHTML = `<div style="color: var(--accent-blue); font-weight: 600; padding: 12px; background: var(--accent-blue-light); border-radius: var(--radius-sm);">⏳ Processing & extracting facts from ${file.name}... Please wait.</div>`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData
    });
    if (!res.ok) {
      throw new Error(`Server returned status code ${res.status}`);
    }
    const data = await res.json();
    currentAnalysisData = data;
    renderAnalysis(data);
    statusDiv.innerHTML = `<div style="color: var(--case1-color); font-weight: 700; padding: 12px; background: var(--case1-bg); border-radius: var(--radius-sm);">✅ Successfully processed ${file.name}! Extracted ${data.facts_extracted_count} facts.</div>`;
    switchTab("showcase", document.querySelectorAll(".aws-tab")[0]);
  } catch (err) {
    console.error("Upload error:", err);
    statusDiv.innerHTML = `<div style="color: var(--case2-color); font-weight: 700; padding: 12px; background: var(--case2-bg); border-radius: var(--radius-sm);">❌ Upload Error: ${err.message}.</div>`;
  }
}

