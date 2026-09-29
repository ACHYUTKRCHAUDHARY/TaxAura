import {apiFetch, logout, requireSession, setBusy, showMessage} from "/app/js/api.js";

requireSession();
const globalMessage = document.querySelector("#global-message");
let documents = [];

function activateSection(sectionId) {
  document.querySelectorAll(".dashboard-section").forEach((section) => section.classList.toggle("active-section", section.id === sectionId));
  document.querySelectorAll(".nav-item[data-section]").forEach((item) => item.classList.toggle("active", item.dataset.section === sectionId));
}

document.querySelectorAll("[data-section]").forEach((item) => item.addEventListener("click", () => activateSection(item.dataset.section)));
document.querySelector("#logout-button").addEventListener("click", logout);

async function loadUser() {
  const user = await apiFetch("/users/me");
  document.querySelector("#welcome-title").textContent = `Welcome, ${user.full_name.split(" ")[0]}`;
  document.querySelector("#user-name").textContent = user.full_name;
  document.querySelector("#user-role").textContent = user.role;
  document.querySelector("#user-initial").textContent = user.full_name.charAt(0).toUpperCase();
  document.querySelector("#admin-link").hidden = user.role !== "ADMIN";
}

function statusClass(status) { return status.toLowerCase() === "completed" ? "completed" : status.toLowerCase() === "failed" ? "failed" : ""; }

function renderDocuments() {
  const table = document.querySelector("#document-table");
  table.replaceChildren();
  if (!documents.length) {
    const row = document.createElement("tr"); const cell = document.createElement("td");
    cell.colSpan = 5; cell.className = "empty-state"; cell.textContent = "No documents uploaded yet.";
    row.append(cell); table.append(row);
  } else {
    documents.forEach((documentItem) => {
      const row = document.createElement("tr");
      [documentItem.filename, documentItem.mime_type].forEach((value) => { const cell = document.createElement("td"); cell.textContent = value; row.append(cell); });
      const statusCell = document.createElement("td"); const status = document.createElement("span");
      status.className = `document-status ${statusClass(documentItem.processing_status)}`; status.textContent = documentItem.processing_status; statusCell.append(status); row.append(statusCell);
      const dateCell = document.createElement("td"); dateCell.textContent = new Date(documentItem.created_at).toLocaleString(); row.append(dateCell);
      const actions = document.createElement("td");
      const addAction = (label, handler) => {
        const button = document.createElement("button"); button.className = "button button-secondary";
        button.textContent = label;
        button.addEventListener("click", async () => {
          setBusy(button, true);
          try { await handler(); } catch (error) { showMessage(globalMessage, error.message); }
          finally { setBusy(button, false); }
        });
        actions.append(button);
      };
      if (documentItem.processing_status === "COMPLETED") addAction("View text", async () => {
        const data = await apiFetch(`/documents/${documentItem.id}/text`);
        document.querySelector("#preview-title").textContent = data.filename;
        document.querySelector("#preview-text").textContent = data.text;
        document.querySelector("#document-preview").showModal();
      });
      if (documentItem.processing_status === "FAILED") {
        status.title = documentItem.processing_error || "Processing failed";
        addAction("Retry", async () => { await apiFetch(`/documents/${documentItem.id}/retry`, {method: "POST"}); await loadDocuments(); });
      }
      addAction("Delete", async () => {
        if (!window.confirm(`Delete ${documentItem.filename} and its extracted text?`)) return;
        await apiFetch(`/documents/${documentItem.id}`, {method: "DELETE"}); await loadDocuments();
      });
      row.append(actions); table.append(row);
    });
  }
  document.querySelector("#document-count").textContent = String(documents.length);
  document.querySelector("#processed-count").textContent = `${documents.filter((item) => item.processing_status === "COMPLETED").length} ready`;
}

async function loadDocuments() { documents = await apiFetch("/documents"); renderDocuments(); }

async function uploadFile(file, button) {
  const body = new FormData(); body.append("file", file); setBusy(button, true, "Uploading…");
  try { await apiFetch("/documents/upload", {method: "POST", body}); showMessage(globalMessage, "Document uploaded and queued for processing.", true); await loadDocuments(); }
  catch (error) { showMessage(globalMessage, error.message); }
  finally { setBusy(button, false); }
}

document.querySelectorAll("#quick-upload-form, #document-upload-form").forEach((form) => form.addEventListener("submit", async (event) => {
  event.preventDefault(); const file = form.querySelector("input[type='file']").files[0]; if (!file) return;
  await uploadFile(file, form.querySelector("button")); form.reset();
}));

const currency = new Intl.NumberFormat("en-IN", {style: "currency", currency: "INR", maximumFractionDigits: 0});
document.querySelector("#tax-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; const button = form.querySelector("button"); setBusy(button, true, "Calculating…");
  try {
    const result = await apiFetch("/tax/compare", {method: "POST", body: JSON.stringify({annual_salary: Number(document.querySelector("#annual-salary").value), old_regime_deductions: Number(document.querySelector("#old-deductions").value)})});
    const target = document.querySelector("#tax-results"); target.replaceChildren();
    const recommendation = document.createElement("div"); recommendation.className = "recommendation";
    const label = document.createElement("span"); label.textContent = "Estimated recommendation"; const regime = document.createElement("strong"); regime.textContent = `${result.recommended_regime} regime`; const saving = document.createElement("span"); saving.textContent = `Potential saving: ${currency.format(result.estimated_saving)}`; recommendation.append(label, regime, saving);
    const grid = document.createElement("div"); grid.className = "regime-grid";
    [["Old regime", result.old_regime], ["New regime", result.new_regime]].forEach(([title, data]) => { const card = document.createElement("article"); card.className = "regime-card"; const heading = document.createElement("span"); heading.textContent = title; const total = document.createElement("strong"); total.textContent = currency.format(data.total_tax); const taxable = document.createElement("small"); taxable.textContent = `Taxable income: ${currency.format(data.taxable_income)}`; card.append(heading, total, taxable); grid.append(card); });
    const disclaimer = document.createElement("p"); disclaimer.className = "empty-state"; disclaimer.textContent = result.disclaimer; target.append(recommendation, grid, disclaimer);
  } catch (error) { showMessage(globalMessage, error.message); }
  finally { setBusy(button, false); }
});

document.querySelector("#rag-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; const textarea = document.querySelector("#rag-question"); const question = textarea.value.trim(); const button = form.querySelector("button");
  const messages = document.querySelector("#chat-messages"); const userMessage = document.createElement("div"); userMessage.className = "chat-message user-message"; userMessage.textContent = question; messages.append(userMessage); textarea.value = ""; setBusy(button, true, "Thinking…");
  try {
    const result = await apiFetch("/knowledge/ask", {method: "POST", body: JSON.stringify({question, include_documents: document.querySelector("#include-documents").checked})}); const answer = document.createElement("div"); answer.className = "chat-message assistant-message"; answer.textContent = result.answer;
    if (result.sources.length) { const sources = document.createElement("div"); sources.className = "chat-sources"; sources.textContent = "Sources: ";
      result.sources.forEach((source) => {
        const item = document.createElement(source.source_url ? "a" : "span");
        item.textContent = `${source.source_name} `;
        if (source.source_url) {
          const url = new URL(source.source_url);
          if (["https:", "http:"].includes(url.protocol)) { item.href = url.href; item.target = "_blank"; item.rel = "noopener noreferrer"; }
        }
        sources.append(item);
      }); answer.append(sources); }
    messages.append(answer);
  } catch (error) { const answer = document.createElement("div"); answer.className = "chat-message assistant-message"; answer.textContent = error.message; messages.append(answer); }
  finally { setBusy(button, false); messages.scrollTop = messages.scrollHeight; }
});

Promise.all([loadUser(), loadDocuments()]).catch((error) => showMessage(globalMessage, error.message));

document.querySelector("#close-preview").addEventListener("click", () => document.querySelector("#document-preview").close());
let polling = false;
setInterval(async () => {
  if (polling || document.hidden || !documents.some((item) => ["QUEUED", "PROCESSING"].includes(item.processing_status))) return;
  polling = true;
  try { await loadDocuments(); } catch (error) { showMessage(globalMessage, error.message); }
  finally { polling = false; }
}, 4000);
