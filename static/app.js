// Simple JavaScript for PDF Fact Extractor

document.addEventListener("DOMContentLoaded", () => {
  loadDataset("delhivery");
});

const DATASET_INFO = {
  delhivery: {
    name: "Delhivery Filings",
    description: "Three company documents covering corporate, operational, and financial facts.",
    path: "starter-datasets/delhivery/"
  },
  "india-macroeconomy": {
    name: "India Macroeconomy",
    description: "Three institutional reports covering overlapping facts about the Indian economy.",
    path: "starter-datasets/india-macroeconomy/"
  }
};

// Load sample dataset
async function loadDataset(datasetId) {
  const datasetInfo = document.getElementById("datasetInfo");
  datasetInfo.innerText = `Loading ${DATASET_INFO[datasetId]?.name || datasetId}...`;
  document.getElementById("casesGrid").innerHTML = "";
  document.getElementById("factsTableBody").innerHTML = "";
  document.getElementById("factCountText").innerText = "...";

  try {
    const response = await fetch(`/api/analysis/${datasetId}?t=${Date.now()}`, {
      cache: "no-store"
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Dataset could not be loaded");
    renderDatasetInfo(datasetId, data);
    renderAnalysis(data);
  } catch (err) {
    console.error("Error loading sample data:", err);
    document.getElementById("datasetInfo").innerText = `Could not load ${datasetId}: ${err.message}`;
  }
}

function renderDatasetInfo(datasetId, data) {
  const info = DATASET_INFO[datasetId] || { name: datasetId, description: "", path: "" };
  document.getElementById("datasetInfo").innerHTML = `
    <strong>${info.name}</strong>
    <span>${info.description}</span>
    <code>${info.path}</code>
    <span>${data.facts_extracted_count || 0} facts loaded</span>
  `;
}

// Display analysis results
function renderAnalysis(data) {
  const factCount = data.facts_extracted_count || (data.facts ? data.facts.length : 0);
  document.getElementById("factCountText").innerText = factCount;

  renderCases(data.cases);
  renderFactsTable(data.facts);
}

// Display 4 Cases
function renderCases(cases) {
  const grid = document.getElementById("casesGrid");
  grid.innerHTML = "";
  const maxCardsPerCase = 24;

  const caseConfig = [
    { key: "Case 1: Corroborated Fact", class: "case1", icon: "✅", label: "Case 1: Matching Fact" },
    { key: "Case 2: Genuine Contradiction", class: "case2", icon: "🚨", label: "Case 2: Conflicting Fact" },
    { key: "Case 3: Apparent Contradiction (Reconciled by Context)", class: "case3", icon: "🧩", label: "Case 3: Reconciled by Context" },
    { key: "Case 4: Extraction/Reasoning Failure & Mitigation", class: "case4", icon: "⚠️", label: "Case 4: Special Note / Failure" }
  ];

  caseConfig.forEach(cfg => {
    const allRels = cases[cfg.key] || [];
    const rels = allRels.slice(0, maxCardsPerCase);
    rels.forEach(rel => {
      const card = document.createElement("div");
      card.className = `case-card ${cfg.class}`;

      let docAHTML = "";
      if (rel.fact_a) {
        docAHTML = `
          <div class="doc-box">
            <strong>Source A</strong> — ${rel.fact_a.metric_name}: <strong>${rel.fact_a.raw_value}</strong> (${rel.fact_a.timeframe}, Page ${rel.fact_a.evidence.page_number})
          </div>
        `;
      }

      let docBHTML = "";
      if (rel.fact_b) {
        docBHTML = `
          <div class="doc-box">
            <strong>Source B</strong> — ${rel.fact_b.metric_name}: <strong>${rel.fact_b.raw_value}</strong> (${rel.fact_b.timeframe}, Page ${rel.fact_b.evidence.page_number})
          </div>
        `;
      }

      let fixHTML = "";
      if (rel.handling_strategy) {
        fixHTML = `<p class="fix-text"><strong>Fix / Strategy:</strong> ${rel.handling_strategy}</p>`;
      }

      card.innerHTML = `
        <span class="case-badge">${cfg.icon} ${cfg.label}</span>
        <div class="case-title">${rel.title}</div>
        ${docAHTML}
        ${docBHTML}
        <p class="result-text"><strong>Explanation:</strong> ${rel.reasoning}</p>
        ${fixHTML}
      `;
      grid.appendChild(card);
    });

    if (allRels.length > maxCardsPerCase) {
      const note = document.createElement("p");
      note.className = "result-text";
      note.textContent = `Showing ${maxCardsPerCase} of ${allRels.length} ${cfg.label.toLowerCase()} entries.`;
      grid.appendChild(note);
    }
  });
}

// Display Extracted Facts Table
function renderFactsTable(facts) {
  const tbody = document.getElementById("factsTableBody");
  tbody.innerHTML = "";

  if (!facts || facts.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #777;">No facts found in this document.</td></tr>`;
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

// Search facts table
function filterFactsTable() {
  const query = document.getElementById("factSearch").value.toLowerCase();
  const rows = document.querySelectorAll("#factsTableBody tr");
  rows.forEach(r => {
    r.style.display = r.innerText.toLowerCase().includes(query) ? "" : "none";
  });
}

// Upload PDF file
async function uploadPDF(file) {
  if (!file) return;
  const statusDiv = document.getElementById("uploadStatus");
  statusDiv.innerHTML = `<div style="color: #3498db; font-weight: bold; margin-bottom: 10px;">Extracting facts from ${file.name}...</div>`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData
    });
    if (!res.ok) throw new Error(`Upload failed (${res.status})`);
    
    const data = await res.json();
    renderAnalysis(data);
    statusDiv.innerHTML = `<div style="color: #2ecc71; font-weight: bold; margin-bottom: 10px;">Successfully extracted ${data.facts_extracted_count} facts from ${file.name}!</div>`;
  } catch (err) {
    console.error("Upload error:", err);
    statusDiv.innerHTML = `<div style="color: #e74c3c; font-weight: bold; margin-bottom: 10px;">Could not extract facts: ${err.message}</div>`;
  }
}
