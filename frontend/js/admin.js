import {apiFetch, logout, requireSession, setBusy, showMessage} from "/app/js/api.js";

requireSession();
const message = document.querySelector("#global-message");
document.querySelector("#logout-button").addEventListener("click", logout);

async function requireAdmin() {
  const user = await apiFetch("/users/me");
  if (user.role !== "ADMIN") window.location.replace("/app/dashboard.html");
}

document.querySelector("#rule-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; const button = form.querySelector("button"); setBusy(button, true, "Ingesting…");
  const sourceUrl = document.querySelector("#source-url").value.trim();
  try {
    const result = await apiFetch("/knowledge/rules", {method: "POST", body: JSON.stringify({source_name: document.querySelector("#source-name").value.trim(), source_url: sourceUrl || null, content: document.querySelector("#source-content").value.trim()})});
    showMessage(message, `${result.chunks_created} verified knowledge chunks created.`, true); form.reset();
  } catch (error) { showMessage(message, error.message); }
  finally { setBusy(button, false); }
});

requireAdmin().catch((error) => showMessage(message, error.message));
