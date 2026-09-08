let currentAnalysisData = null;

// Run on page load
document.addEventListener("DOMContentLoaded", () => {
  loadDataset("delhivery");
});

// Load analysis for selected dataset
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

// Render analysis data onto the page
function renderAnalysis(data) {
  const factCount = data.facts_extracted_count || (data.facts ? data.facts.length : 0);
  document.getElementById("factCountText").innerText = factCount;

  renderCases(data.cases);
  renderFactsTable(data.facts);
}

// Render the 4 cases in simple basic format
function renderCases(cases) {
  const grid = document.getElementById("casesGrid");
  grid.innerHTML = "";

  const caseConfig = [
    { key: "Case 1: Corroborated Fact", class: "case1", icon: "✅", label: "Case 1: Matching Information Across Documents" },
    { key: "Case 2: Genuine Contradiction", class: "case2", icon: "🚨", label: "Case 2: Conflicting Information (Direct Conflict)" },
    { key: "Case 3: Apparent Contradiction (Reconciled by Context)", class: "case3", icon: "🧩", label: "Case 3: Reconciled by Context (Different Years / Units)" },
    { key: "Case 4: Extraction/Reasoning Failure & Mitigation", class: "case4", icon: "⚠️", label: "Case 4: Footnote / Scope Note Handling" }
  ];

  caseConfig.forEach(cfg => {
    const rels = cases[cfg.key] || [];
    rels.forEach(rel => {
      const card = document.createElement("div");
      card.className = `case-card ${cfg.class}`;

      let docAHTML = "";
      if (rel.fact_a) {
        docAHTML = `
          <div class="doc-box">
            <strong>📄 Document 1:</strong> ${rel.fact_a.evidence.doc_name} (Page ${rel.fact_a.evidence.page_number})<br>
            <strong>Value Extracted:</strong> <span style="color: #2980b9;">${rel.fact_a.metric_name} = ${rel.fact_a.raw_value}</span> (${rel.fact_a.timeframe})
            <div class="quote">"${rel.fact_a.evidence.verbatim_quote}"</div>
          </div>
        `;
      }

      let docBHTML = "";
      if (rel.fact_b) {
        docBHTML = `
          <div class="doc-box">
            <strong>📄 Document 2:</strong> ${rel.fact_b.evidence.doc_name} (Page ${rel.fact_b.evidence.page_number})<br>
            <strong>Value Extracted:</strong> <span style="color: #2980b9;">${rel.fact_b.metric_name} = ${rel.fact_b.raw_value}</span> (${rel.fact_b.timeframe})
            <div class="quote">"${rel.fact_b.evidence.verbatim_quote}"</div>
          </div>
        `;
      }

      let mitigationHTML = "";
      if (rel.handling_strategy) {
        mitigationHTML = `
          <div style="background-color: #fff8e6; border: 1px solid #ffe0b2; padding: 8px 12px; border-radius: 4px; margin-top: 10px; font-size: 13px; color: #b78103;">
            <strong>🔧 How System Fixed It:</strong> ${rel.handling_strategy}
          </div>
        `;
      }

      card.innerHTML = `
        <span class="case-badge">${cfg.icon} ${cfg.label}</span>
        <div class="case-title">${rel.title}</div>
        <div class="case-summary">${rel.summary}</div>
        ${docAHTML}
        ${docBHTML}
        <div class="reasoning">
          <strong>💡 Explanation / Result:</strong> ${rel.reasoning}
        </div>
        ${mitigationHTML}
      `;
      grid.appendChild(card);
    });
  });
}

// Render facts table in simple format
function renderFactsTable(facts) {
  const tbody = document.getElementById("factsTableBody");
  tbody.innerHTML = "";

  if (!facts || facts.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #777;">No facts extracted yet.</td></tr>`;
    return;
  }

  facts.forEach(f => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${f.metric_name}</strong><br><span style="font-size: 12px; color: #666;">(${f.entity})</span></td>
      <td><strong style="color: #2980b9;">${f.raw_value}</strong></td>
      <td>${f.timeframe}</td>
      <td>${f.evidence.doc_name}</td>
      <td>Page ${f.evidence.page_number}</td>
      <td><em>"${f.evidence.verbatim_quote}"</em></td>
    `;
    tbody.appendChild(tr);
  });
}

// Simple search filter for table
function filterFactsTable() {
  const query = document.getElementById("factSearch").value.toLowerCase();
  const rows = document.querySelectorAll("#factsTableBody tr");
  rows.forEach(r => {
    const text = r.innerText.toLowerCase();
    r.style.display = text.includes(query) ? "" : "none";
  });
}

// Handle PDF upload
async function uploadPDF(file) {
  if (!file) return;
  const statusDiv = document.getElementById("uploadStatus");
  statusDiv.innerHTML = `<div style="color: #3498db; font-weight: bold; margin-bottom: 15px;">⏳ Processing ${file.name}... Please wait.</div>`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData
    });
    if (!res.ok) throw new Error(`Server returned error ${res.status}`);
    
    const data = await res.json();
    currentAnalysisData = data;
    renderAnalysis(data);
    statusDiv.innerHTML = `<div style="color: #2ecc71; font-weight: bold; margin-bottom: 15px;">✅ Successfully extracted ${data.facts_extracted_count} facts from ${file.name}!</div>`;
  } catch (err) {
    console.error("Upload error:", err);
    statusDiv.innerHTML = `<div style="color: #e74c3c; font-weight: bold; margin-bottom: 15px;">❌ Upload Failed: ${err.message}</div>`;
  }
}



