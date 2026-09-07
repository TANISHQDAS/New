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
    const data = await response.json();
    currentAnalysisData = data;
    renderAnalysis(data);
  } catch (err) {
    console.error("Error loading dataset:", err);
  }
}

function renderAnalysis(data) {
  // Update stats
  document.getElementById("statFactCount").innerText = data.facts_extracted_count || 0;
  document.getElementById("statDocCount").innerText = data.dataset_id.includes("delhivery") ? "3 PDFs (Delhivery)" : (data.dataset_id.includes("macroeconomy") ? "3 PDFs (Macroeconomy)" : "Uploaded PDF");

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

  caseConfig.forEach(cfg => {
    const rels = cases[cfg.key] || [];
    rels.forEach(rel => {
      const card = document.createElement("div");
      card.className = `case-card ${cfg.class}`;

      let evidenceHTML = "";
      if (rel.fact_a) {
        evidenceHTML += `
          <div class="evidence-box">
            <div class="evidence-title">📄 Document A: ${rel.fact_a.evidence.doc_name} (Page ${rel.fact_a.evidence.page_number})</div>
            <div><strong>Extracted Metric:</strong> ${rel.fact_a.metric_name} = <span style="color: var(--aws-blue); font-weight: 700;">${rel.fact_a.raw_value}</span> (${rel.fact_a.timeframe})</div>
            <div class="quote-block">"${rel.fact_a.evidence.verbatim_quote}"</div>
          </div>
        `;
      }

      if (rel.fact_b) {
        evidenceHTML += `
          <div class="evidence-box">
            <div class="evidence-title">📄 Document B: ${rel.fact_b.evidence.doc_name} (Page ${rel.fact_b.evidence.page_number})</div>
            <div><strong>Extracted Metric:</strong> ${rel.fact_b.metric_name} = <span style="color: var(--aws-blue); font-weight: 700;">${rel.fact_b.raw_value}</span> (${rel.fact_b.timeframe})</div>
            <div class="quote-block">"${rel.fact_b.evidence.verbatim_quote}"</div>
          </div>
        `;
      }

      let mitigationHTML = "";
      if (rel.handling_strategy) {
        mitigationHTML = `
          <div style="background-color: var(--case4-bg); border: 1px solid #ffe0b2; padding: 12px; border-radius: 6px; margin-top: 10px; color: var(--case4-amber);">
            <strong>🛠️ Mitigation Strategy & Automated Handling:</strong><br>
            ${rel.handling_strategy}
          </div>
        `;
      }

      card.innerHTML = `
        <span class="case-badge">${cfg.icon} ${rel.case_type}</span>
        <div class="case-title">${rel.title}</div>
        <div class="case-summary">${rel.summary}</div>
        ${evidenceHTML}
        <div class="reasoning-box">
          <strong>🧠 System Reasoning & Grounded Reconciliation:</strong><br>
          ${rel.reasoning}
        </div>
        ${mitigationHTML}
      `;
      grid.appendChild(card);
    });
  });
}

function renderFactsTable(facts) {
  const tbody = document.getElementById("factsTableBody");
  tbody.innerHTML = "";

  if (!facts || facts.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--aws-text-muted);">No facts extracted yet.</td></tr>`;
    return;
  }

  facts.forEach(f => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${f.entity}</strong></td>
      <td><span style="font-weight: 600; color: var(--aws-blue);">${f.metric_name}</span></td>
      <td><strong>${f.raw_value}</strong></td>
      <td><span class="aws-user-badge" style="padding: 2px 8px; font-size: 11px;">${f.timeframe}</span></td>
      <td>${f.scope || 'Consolidated'}</td>
      <td><span style="font-size: 12px; font-family: monospace;">${f.evidence.doc_name}</span></td>
      <td><strong>Page ${f.evidence.page_number}</strong></td>
      <td><span class="quote-block" style="font-size: 11.5px; padding: 4px 8px; display: block; margin: 0;">"${f.evidence.verbatim_quote}"</span></td>
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
    container.innerHTML = `<div style="text-align: center; color: var(--aws-text-muted);">No reconciliation pairs available.</div>`;
    return;
  }

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
          <td><span class="case-badge">${r.case_type}</span></td>
          <td><strong>${r.title}</strong></td>
          <td>${r.source_documents[0] || 'N/A'}</td>
          <td>${r.source_documents[1] || 'N/A'}</td>
          <td>${(r.reconciliation_factors || []).join(" &bull; ")}</td>
          <td><span style="color: var(--case1-green); font-weight: 700;">${Math.round((r.confidence || 0.9) * 100)}%</span></td>
        </tr>
      `).join('')}
    </tbody>
  `;
  container.appendChild(table);
}

async function uploadPDF(file) {
  if (!file) return;
  const statusDiv = document.getElementById("uploadStatus");
  statusDiv.innerHTML = `<div style="color: var(--aws-blue); font-weight: 600;">⏳ Processing & extracting facts from ${file.name}... Please wait.</div>`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    currentAnalysisData = data;
    renderAnalysis(data);
    statusDiv.innerHTML = `<div style="color: var(--case1-green); font-weight: 700;">✅ Successfully processed ${file.name}! Extracted ${data.facts_extracted_count} facts.</div>`;
    switchTab("showcase", document.querySelectorAll(".aws-tab")[0]);
  } catch (err) {
    console.error("Upload error:", err);
    statusDiv.innerHTML = `<div style="color: var(--case2-red); font-weight: 700;">❌ Error processing PDF file.</div>`;
  }
}
