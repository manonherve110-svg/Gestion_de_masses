const API_BASE = "";

const suggestionsContainer = document.getElementById("suggestions");
const selectedContainer = document.getElementById("selectedSymptoms");
const searchInput = document.getElementById("searchInput");
const searchButton = document.querySelector(".search-button");

let selectedSymptoms = [];
let resultsChartInstance = null;

const LOCALE = "en-US";

function escapeHtml(text) {
  const el = document.createElement("div");
  el.textContent = text;
  return el.innerHTML;
}

function getOperator() {
  return document.querySelector('input[name="mode"]:checked')?.value || "AND";
}

/* ---------- Navigation ---------- */

function initNavigation() {
  document.getElementById("sidebarToggle")?.addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("open");
  });
}

/* ---------- Search (unchanged core) ---------- */

function addSymptom(symptom) {
  const cleanSymptom = String(symptom || "").trim();
  if (cleanSymptom === "") return;
  if (selectedSymptoms.includes(cleanSymptom)) return;
  selectedSymptoms.push(cleanSymptom);
  searchInput.value = "";
  suggestionsContainer.innerHTML = "";
  renderSelectedSymptoms();
}

function removeSymptom(symptom) {
  selectedSymptoms = selectedSymptoms.filter(s => s !== symptom);
  renderSelectedSymptoms();
}

searchInput.addEventListener("keydown", event => {
  if (event.key === "Enter") {
    event.preventDefault();
    const typedSymptom = searchInput.value.trim();
    if (typedSymptom !== "") addSymptom(typedSymptom);
    else showResults();
  }
});

let debounceTimeout;
searchInput.addEventListener("input", () => {
  clearTimeout(debounceTimeout);
  const val = searchInput.value.trim();
  if (val.length < 2) {
    suggestionsContainer.innerHTML = "";
    return;
  }
  debounceTimeout = setTimeout(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/suggest?q=${encodeURIComponent(val)}`);
      if (!res.ok) return;
      const suggestions = await res.json();
      suggestionsContainer.innerHTML = "";
      suggestions.forEach(s => {
        const div = document.createElement("div");
        div.className = "suggestion";
        div.textContent = s;
        div.onclick = () => {
          addSymptom(s);
          suggestionsContainer.innerHTML = "";
        };
        suggestionsContainer.appendChild(div);
      });
    } catch (e) {
      console.error("Autocomplete error:", e);
    }
  }, 300);
});

function renderSelectedSymptoms() {
  selectedContainer.innerHTML = "";
  selectedSymptoms.forEach(symptom => {
    const tag = document.createElement("div");
    tag.classList.add("symptom-tag");
    tag.innerHTML = `${escapeHtml(symptom)} <span class="remove-btn">✖</span>`;
    tag.querySelector(".remove-btn").onclick = () => removeSymptom(symptom);
    selectedContainer.appendChild(tag);
  });
  if (document.getElementById("view-search").classList.contains("active")) {
    showResults();
  }
}

searchButton.addEventListener("click", () => {
  const typedSymptom = searchInput.value.trim();
  if (typedSymptom !== "") addSymptom(typedSymptom);
  else showResults();
});

function renderListWithPagination(container, data, renderFn, limit = 5, emptyMsg = "No results found.") {
  container.innerHTML = "";
  if (!data || data.length === 0) {
    container.innerHTML = `<p>${emptyMsg}</p>`;
    return;
  }
  let currentLimit = limit;
  function render() {
    container.innerHTML = "";
    data.slice(0, currentLimit).forEach(item => { container.innerHTML += renderFn(item); });
    if (currentLimit < data.length) {
      const btn = document.createElement("button");
      btn.textContent = `Show more (${data.length - currentLimit} left)`;
      btn.className = "show-more-btn";
      btn.onclick = () => { currentLimit += 10; render(); };
      container.appendChild(btn);
    }
  }
  render();
}

function renderTableWithPagination(tableBody, paginationContainer, data, renderRowFn, limit = 5) {
  tableBody.innerHTML = "";
  paginationContainer.innerHTML = "";
  if (!data || data.length === 0) {
    tableBody.innerHTML = "<tr><td colspan='4'>No treatments found.</td></tr>";
    return;
  }
  let currentLimit = limit;
  function render() {
    tableBody.innerHTML = "";
    data.slice(0, currentLimit).forEach(item => { tableBody.innerHTML += renderRowFn(item); });
    paginationContainer.innerHTML = "";
    if (currentLimit < data.length) {
      const btn = document.createElement("button");
      btn.textContent = `Show more (${data.length - currentLimit} left)`;
      btn.className = "show-more-btn";
      btn.onclick = () => { currentLimit += 10; render(); };
      paginationContainer.appendChild(btn);
    }
  }
  render();
}

function renderResultsChart(summary) {
  const section = document.getElementById("resultsChartsSection");
  const canvas = document.getElementById("resultsChart");
  if (!summary || (summary.diseases === 0 && summary.side_effect_drugs === 0 && summary.treatments === 0)) {
    section.style.display = "none";
    return;
  }
  section.style.display = "block";
  if (resultsChartInstance) resultsChartInstance.destroy();
  resultsChartInstance = new Chart(canvas, {
    type: "bar",
    data: {
      labels: ["Diseases", "Medications (side effects)", "Treatments"],
      datasets: [{
        label: "Result count",
        data: [summary.diseases, summary.side_effect_drugs, summary.treatments],
        backgroundColor: ["#0284c7", "#dc2626", "#16a34a"],
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
    },
  });
}

async function showResults() {
  const maladiesResults = document.getElementById("maladies-results");
  const medicamentsResults = document.getElementById("medicaments-results");
  const tableBody = document.getElementById("diseasesTableBody");
  const treatmentsPagination = document.getElementById("treatmentsPagination");

  if (selectedSymptoms.length === 0) {
    maladiesResults.innerHTML = "<p>Please select at least one symptom.</p>";
    medicamentsResults.innerHTML = "";
    tableBody.innerHTML = "<tr><td colspan='4'>Please select at least one symptom.</td></tr>";
    document.getElementById("resultsChartsSection").style.display = "none";
    return;
  }

  maladiesResults.innerHTML = "<p>Loading...</p>";
  medicamentsResults.innerHTML = "<p>Loading...</p>";
  tableBody.innerHTML = "<tr><td colspan='4'>Loading...</td></tr>";

  try {
    const query = selectedSymptoms.join(" ");
    const operator = getOperator();
    const response = await fetch(
      `${API_BASE}/api/search?q=${encodeURIComponent(query)}&operator=${operator}`
    );
    const data = await response.json();

    if (data.error) {
      maladiesResults.innerHTML = `<p class="error-msg">API error: ${escapeHtml(data.error)}</p>`;
      medicamentsResults.innerHTML = "";
      tableBody.innerHTML = "";
      return;
    }

    renderResultsChart(data.result_summary);

    renderListWithPagination(maladiesResults, data.diseases_causing_symptom, item => `
      <div class="result-item">
        <h4>${escapeHtml(item.disease)}<span class="score-badge">Score: ${item.score}</span></h4>
        <div class="source">Source: ${escapeHtml(item.source)}</div>
      </div>
    `);

    renderListWithPagination(medicamentsResults, data.drugs_causing_symptom_as_side_effect, item => `
      <div class="result-item">
        <h4>${escapeHtml(item.drug_name)}<span class="score-badge">Score: ${item.score}</span></h4>
        <div class="source">Source: ${escapeHtml(item.source)}</div>
      </div>
    `);

    renderTableWithPagination(
      tableBody, treatmentsPagination, data.drugs_treating_symptom_or_disease,
      item => `
        <tr>
          <td class="symptoms-list">${escapeHtml(selectedSymptoms.join(", "))}</td>
          <td class="drugs-list">${escapeHtml(item.drug_name)}
            <span class="score-badge">Score: ${item.score}</span></td>
          <td>${escapeHtml(item.source)}</td>
        </tr>
      `
    );
  } catch (err) {
    console.error(err);
    maladiesResults.innerHTML = `<p class="error-msg">Cannot reach the API. Run: <code>python3 scripts/api.py</code></p>`;
    medicamentsResults.innerHTML = "";
    tableBody.innerHTML = "";
  }
}

/* ---------- Initialization ---------- */

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
});
