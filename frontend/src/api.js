const API_BASE = "/api";

async function fetchQuestions() {
  const res = await fetch(`${API_BASE}/questions`);
  if (!res.ok) throw new Error(`Failed to load questions: ${res.status}`);
  return res.json();
}

const FRIENDLY_UNAVAILABLE =
  "We couldn't compute this verdict right now — the data source may be unavailable.";

async function fetchVerdict(questionId) {
  const res = await fetch(`${API_BASE}/verdict/${questionId}`, { method: "POST" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // Use the API's plain-language detail when present; never surface raw
    // status text or stack traces to the user.
    const error = new Error(body.detail || FRIENDLY_UNAVAILABLE);
    error.friendlyMessage = body.detail || FRIENDLY_UNAVAILABLE;
    throw error;
  }
  return res.json();
}

window.QEApi = { fetchQuestions, fetchVerdict };
