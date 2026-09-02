const API_BASE = "/api/v1";
const TOKEN_KEY = "taxaura_access_token";

export function getToken() { return sessionStorage.getItem(TOKEN_KEY); }
export function setSession(data) { sessionStorage.setItem(TOKEN_KEY, data.access_token); }
export function clearSession() { sessionStorage.removeItem(TOKEN_KEY); }
export function requireSession() { if (!getToken()) window.location.replace("/app/login.html"); }

function errorMessage(payload, fallback) {
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) return payload.detail.map((item) => item.msg).join("; ");
  return fallback;
}

export async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData) && !(options.body instanceof URLSearchParams)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE}${path}`, {...options, headers});
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/")) {
      clearSession();
      window.location.replace("/app/login.html");
    }
    throw new Error(errorMessage(payload, `Request failed (${response.status})`));
  }
  return payload;
}

export function showMessage(element, message, success = false) {
  element.textContent = message;
  element.classList.toggle("success", success);
  element.hidden = false;
}

export function setBusy(button, busy, busyLabel = "Please wait…") {
  if (!button.dataset.label) button.dataset.label = button.textContent;
  button.disabled = busy;
  button.textContent = busy ? busyLabel : button.dataset.label;
}

export function logout() {
  clearSession();
  window.location.replace("/app/login.html");
}
