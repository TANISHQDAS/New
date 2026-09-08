let currentAnalysisData = null;

document.addEventListener("DOMContentLoaded", () => {
  loadDataset("delhivery");
});

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
  const factCount = data.facts_extracted_count || (data.facts ? data.facts.length : 0);
  document.getElementById("factCountText").innerText = factCount;

  renderCases(data.cases);
  renderFactsTable(data.facts);
}

function renderCases(cases) {
  const grid = document.getElementById("casesGrid");
  grid.innerHTML = "";

  const caseConfig = [
    { key: "Case 1: Corroborated Fact", class: "case1", icon: "✅", label: "Case 1: Matching Fact" },
    { key: "Case 2: Genuine Contradiction", class: "case2", icon: "🚨", label: "Case 2: Contradiction" },
    { key: "Case 3: Apparent Contradiction (Reconciled by Context)", class: "case3", icon: "🧩", label: "Case 3: Reconciled Context" },
    { key: "Case 4: Extraction/Reasoning Failure & Mitigation", class: "case4", icon: "⚠️", label: "Case 4: Footnote Note" }
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
            <strong>Doc A</strong> — ${rel.fact_a.metric_name}: <strong>${rel.fact_a.raw_value}</strong> (${rel.fact_a.timeframe}, Page ${rel.fact_a.evidence.page_number})
          </div>
        `;
      }

      let docBHTML = "";
      if (rel.fact_b) {
        docBHTML = `
          <div class="doc-box">
            <strong>Doc B</strong> — ${rel.fact_b.metric_name}: <strong>${rel.fact_b.raw_value}</strong> (${rel.fact_b.timeframe}, Page ${rel.fact_b.evidence.page_number})
          </div>
        `;
      }

      let mitigationHTML = "";
      if (rel.handling_strategy) {
        const shortFix = rel.handling_strategy.split(".")[0] + ".";
        mitigationHTML = `<p class="fix-text"><strong>Fix:</strong> ${shortFix}</p>`;
      }

      const shortResult = rel.reasoning ? rel.reasoning.split(".")[0] + "." : "";

      card.innerHTML = `
        <span class="case-badge">${cfg.icon} ${cfg.label}</span>
        <div class="case-title">${rel.title}</div>
        ${docAHTML}
        ${docBHTML}
        <p class="result-text"><strong>Result:</strong> ${shortResult}</p>
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
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #777;">No facts.</td></tr>`;
    return;
  }

  facts.forEach(f => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${f.metric_name}</strong></td>
      <td><strong>${f.raw_value}</strong></td>
      <td>${f.timeframe}</td>
      <td>${f.evidence.doc_name}</td>
      <td>Page ${f.evidence.page_number}</td>
      <td><em>"${f.evidence.verbatim_quote}"</em></td>
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

async function uploadPDF(file) {
  if (!file) return;
  const statusDiv = document.getElementById("uploadStatus");
  statusDiv.innerHTML = `<div style="color: #3498db; font-weight: bold; margin-bottom: 10px;">Uploading ${file.name}...</div>`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData
    });
    if (!res.ok) throw new Error(`Error ${res.status}`);
    
    const data = await res.json();
    currentAnalysisData = data;
    renderAnalysis(data);
    statusDiv.innerHTML = `<div style="color: #2ecc71; font-weight: bold; margin-bottom: 10px;">Uploaded ${file.name} successfully!</div>`;
  } catch (err) {
    console.error("Upload error:", err);
    statusDiv.innerHTML = `<div style="color: #e74c3c; font-weight: bold; margin-bottom: 10px;">Upload failed: ${err.message}</div>`;
  }
}




