const API_BASE = "";
const LOCALE = "en-US";

let cachedStats = null;
let distributionChart = null;
let entityChart = null;

const FALLBACK_STATS = {
  sources: {
    HPO: { symptom_terms: 12299, synonyms: 15904 },
    OMIM: { indexed_diseases: 23952, onto_label_cui_pairs: 23947 },
    SIDER: { distinct_cuis: 1430, indication_rows: 77647, side_effect_rows: 309849 },
    DrugBank: { indexed_drugs: 10562, indexed_drugs_with_indications: 9287 },
    STITCH: { compound_aliases: 387496, compound_ids: 6833 }
  }
};

function escapeHtml(text) {
  const el = document.createElement("div");
  el.textContent = text;
  return el.innerHTML;
}

function renderDatabaseDistribution(stats) {
  try {
    const canvasElement = document.getElementById("distributionChart");
    if (!canvasElement) return;
    
    if (distributionChart) distributionChart.destroy();

    const labels = ["HPO", "OMIM", "DrugBank", "SIDER", "STITCH"];
    const data = [
      stats.HPO.symptom_terms,
      stats.OMIM.indexed_diseases,
      stats.DrugBank.indexed_drugs,
      stats.SIDER.distinct_cuis,
      stats.STITCH.compound_ids
    ];
    
    const colors = [
      "rgba(244, 67, 54, 0.7)",      // Red
      "rgba(156, 39, 176, 0.7)",     // Purple
      "rgba(66, 133, 244, 0.7)",     // Blue
      "rgba(255, 152, 0, 0.7)",      // Orange
      "rgba(76, 175, 80, 0.7)"       // Green
    ];
    
    const borderColors = [
      "rgba(244, 67, 54, 1)",
      "rgba(156, 39, 176, 1)",
      "rgba(66, 133, 244, 1)",
      "rgba(255, 152, 0, 1)",
      "rgba(76, 175, 80, 1)"
    ];

    const total = data.reduce((a, b) => a + b, 0);

    distributionChart = new Chart(canvasElement, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: colors,
          borderColor: borderColors,
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: 20 },
        plugins: {
          legend: { position: "bottom", labels: { padding: 15, font: { size: 14 } } },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.label || "";
                const value = context.parsed || 0;
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value.toLocaleString(LOCALE)} (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  } catch (e) {
    console.error("Error rendering database distribution:", e);
  }
}

function renderEntityDistribution(stats) {
  try {
    const canvasElement = document.getElementById("entityChart");
    if (!canvasElement) return;
    
    if (entityChart) entityChart.destroy();

    const labels = ["Symptoms", "Diseases", "Drugs"];
    const data = [
      stats.HPO.symptom_terms,
      stats.OMIM.indexed_diseases,
      stats.DrugBank.indexed_drugs
    ];
    
    const colors = [
      "rgba(244, 67, 54, 0.7)",  // Red (Symptoms)
      "rgba(156, 39, 176, 0.7)", // Purple (Diseases)
      "rgba(66, 133, 244, 0.7)"  // Blue (Drugs)
    ];
    
    const borderColors = [
      "rgba(244, 67, 54, 1)",
      "rgba(156, 39, 176, 1)",
      "rgba(66, 133, 244, 1)"
    ];

    const total = data.reduce((a, b) => a + b, 0);

    entityChart = new Chart(canvasElement, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: colors,
          borderColor: borderColors,
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: 20 },
        plugins: {
          legend: { position: "bottom", labels: { padding: 15, font: { size: 14 } } },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.label || "";
                const value = context.parsed || 0;
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value.toLocaleString(LOCALE)} (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  } catch (e) {
    console.error("Error rendering entity distribution:", e);
  }
}

function renderStatCard(title, lines) {
  return `
    <div class="stat-card">
      <h3>${escapeHtml(title)}</h3>
      <ul>${lines.map(l => `<li>${l}</li>`).join("")}</ul>
    </div>
  `;
}

async function loadSourceStatistics() {
  const loading = document.getElementById("sourcesLoading");
  const content = document.getElementById("sourcesContent");
  const statsGrid = document.getElementById("statsGrid");

  loading.hidden = false;
  content.hidden = true;

  try {
    let s = null;
    if (!cachedStats) {
      try {
        const res = await fetch(`${API_BASE}/api/stats`);
        if (res.ok) {
          cachedStats = await res.json();
          s = cachedStats.sources;
        } else {
          throw new Error("API not available");
        }
      } catch (e) {
        console.warn("API not available, using fallback data");
        cachedStats = FALLBACK_STATS;
        s = FALLBACK_STATS.sources;
      }
    } else {
      s = cachedStats.sources;
    }

    if (s) {
      // 1. Dessiner les graphiques
      renderDatabaseDistribution(s);
      renderEntityDistribution(s);

      // 2. Injecter les cartes
      if (statsGrid) {
        let html = `
          <div class="cards-row">
            ${renderStatCard("HPO", [
              `<strong>${s.HPO.symptom_terms.toLocaleString(LOCALE)}</strong> unique symptoms`,
              `<strong>${s.HPO.synonyms.toLocaleString(LOCALE)}</strong> synonyms`,
            ])}
            ${renderStatCard("OMIM", [
              `<strong>${s.OMIM.indexed_diseases.toLocaleString(LOCALE)}</strong> genetic diseases`,
              `<strong>${s.OMIM.onto_label_cui_pairs.toLocaleString(LOCALE)}</strong> associated symptoms`
            ])}
            ${renderStatCard("SIDER", [
              `<strong>${s.SIDER.distinct_cuis.toLocaleString(LOCALE)}</strong> medications`,
              `<strong>${s.SIDER.indication_rows.toLocaleString(LOCALE)}</strong> indications`,
              `<strong>${s.SIDER.side_effect_rows.toLocaleString(LOCALE)}</strong> side effects`,
            ])}
            ${renderStatCard("DrugBank", [
              `<strong>${s.DrugBank.indexed_drugs.toLocaleString(LOCALE)}</strong> medications`,
              `<strong>${s.DrugBank.indexed_drugs_with_indications.toLocaleString(LOCALE)}</strong> with indications`,
            ])}
            ${renderStatCard("STITCH & ATC", [
              `<strong>${s.STITCH.compound_aliases.toLocaleString(LOCALE)}</strong> successful mappings`,
              `<strong>${s.STITCH.compound_ids.toLocaleString(LOCALE)}</strong> total compounds`,
            ])}
          </div>
        `;
        statsGrid.innerHTML = html;
        statsGrid.className = "";
      }
    }

    loading.hidden = true;
    content.hidden = false;
  } catch (e) {
    console.error("Error loading statistics:", e);
    loading.innerHTML = `<p class='error-msg'>Failed to load statistics: ${e.message}</p>`;
  }
}

function initSidebar() {
  document.getElementById("sidebarToggle")?.addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("open");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initSidebar();
  loadSourceStatistics();
});