const API_BASE = "/api";

async function fetchQuestions() {
  const res = await fetch(`${API_BASE}/questions`);
  if (!res.ok) throw new Error(`Failed to load questions: ${res.status}`);
  return res.json();
}

async function fetchVerdict(questionId) {
  const res = await fetch(`${API_BASE}/verdict/${questionId}`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to load verdict");
  }
  return res.json();
}

window.QEApi = { fetchQuestions, fetchVerdict };
