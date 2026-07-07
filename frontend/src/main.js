const $ = id => document.getElementById(id);

const state = {
  questions: [],
  activeVerdict: null,
};

async function init() {
  try {
    state.questions = await QEApi.fetchQuestions();
    renderQuestionList();
  } catch (err) {
    showError("Could not load questions. Is the API running?");
  }
}

function renderQuestionList() {
  const container = $("question-list");
  container.innerHTML = "";

  state.questions
    .filter(q => !q.is_stub)  // hide TBD stubs in the list
    .forEach((q, i) => {
      const card = document.createElement("div");
      card.className = "question-card" + (q.is_stub ? " is-stub" : "");
      card.innerHTML = `
        <span class="question-text">${q.question}</span>
        <span class="question-meta">${q.source_piece}</span>
      `;
      if (!q.is_stub) {
        card.addEventListener("click", () => loadVerdict(q.id));
      }
      container.appendChild(card);
    });
}

async function loadVerdict(questionId) {
  showVerdictPanel();
  $("verdict-question").textContent = "Loading…";
  $("verdict-text").textContent = "";
  $("key-numbers").innerHTML = "";
  $("chart-title").textContent = "";

  try {
    const verdict = await QEApi.fetchVerdict(questionId);
    renderVerdict(verdict);
  } catch (err) {
    // The API returns a plain-language `detail` for failures; fall back to a
    // friendly message rather than surfacing raw error text.
    const friendly = err.friendlyMessage || err.message ||
      "We couldn't compute this verdict right now — the data source may be unavailable.";
    const banner = document.createElement("div");
    banner.className = "error-banner";
    banner.textContent = friendly;
    $("verdict-text").innerHTML = "";
    $("verdict-text").appendChild(banner);
  }
}

function renderVerdict(v) {
  $("verdict-question").textContent  = v.question;
  $("verdict-scenario").textContent  = v.scenario === "distressed" ? "distressed scenario" : "baseline scenario";
  $("verdict-text").textContent      = v.verdict;
  $("rule-explanation").textContent  = v.rule_explanation;
  $("go-deeper-link").textContent    = `Go deeper: ${v.go_deeper_label} →`;
  $("go-deeper-link").href           = v.go_deeper_link;
  $("chart-title").textContent       = v.chart?.title || "";

  const knContainer = $("key-numbers");
  knContainer.innerHTML = "";
  v.key_numbers.forEach(kn => {
    const el = document.createElement("div");
    el.className = "key-number";
    el.innerHTML = `<span class="kn-value">${kn.value}</span><div class="kn-label">${kn.label}</div>`;
    knContainer.appendChild(el);
  });

  if (v.chart) {
    const svgEl = $("verdict-chart");
    // Give the DOM a tick to size the svg before measuring
    requestAnimationFrame(() => QECharts.renderChart(svgEl, v.chart));
  }
}

function showVerdictPanel() {
  $("question-list").parentElement.hidden = false;
  $("question-list").hidden = true;
  $("verdict-panel").hidden = false;
  $("verdict-panel