export const API_BASE = "/api";

export async function startExam(level = "medium") {
  const res = await fetch(`${API_BASE}/exam`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ level }),
  });
  return res.json();
}

export async function submitExam(payload) {
  const res = await fetch(`${API_BASE}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}
