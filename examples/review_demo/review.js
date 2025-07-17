"use strict";
const cards = [...document.querySelectorAll("article")];
const connection = document.querySelector("#connection");
let revision = 0, token = null, saving = false;
const dirty = new Set();
const decisions = {unreviewed:"Unreviewed", confirmed:"Confirmed", corrected:"Corrected", unreadable:"Cannot read"};
function status(element, message, error = false) {
  element.textContent = message;
  element.classList.toggle("error", error);
}
function updateProgress(data) {
  revision = data.revision;
  document.querySelector("#count").textContent = `${data.reviewed} / ${data.total}`;
  for (const card of cards) {
    const entry = data.entries[card.dataset.id];
    card.dataset.decision = entry?.decision || "unreviewed";
    card.querySelector(".badge").textContent = decisions[card.dataset.decision];
  }
}
function filter() {
  const query = document.querySelector("#search").value.toLowerCase();
  const pending = document.querySelector("#pending").checked;
  let visible = 0;
  for (const card of cards) {
    const haystack = card.textContent + " " + card.querySelector('[name="names"]').value;
    const unresolved = ["unreviewed", "unreadable"].includes(card.dataset.decision || "unreviewed");
    card.hidden = (!haystack.toLowerCase().includes(query) || (pending && !unresolved)) && !dirty.has(card.dataset.id);
    if (!card.hidden) visible++;
  }
  document.querySelector("#empty").hidden = visible !== 0;
}
async function post(route, payload) {
  const response = await fetch(route, {method:"POST",headers:{"Content-Type":"application/json","X-Review-Token":token},body:JSON.stringify(payload)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Could not save. Retry while the review server is running.");
  return result;
}
for (const card of cards) {
  const form = card.querySelector("form");
  const names = form.elements.names, decision = form.elements.decision;
  form.addEventListener("input", event => {
    dirty.add(card.dataset.id);
    if (event.target === names) decision.value = names.value.trim() === names.dataset.original ? "confirmed" : "corrected";
    status(card.querySelector(".save-status"), "Unsaved changes");
  });
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (!token || saving) return;
    saving = true;
    const button = form.querySelector("button[type=submit]");
    for (const field of form.elements) field.disabled = true;
    for (const submit of document.querySelectorAll("button[type=submit]")) submit.disabled = true;
    status(card.querySelector(".save-status"), "Saving…");
    try {
      const result = await post("/api/save", {id:card.dataset.id, revision, names:names.value, decision:decision.value, notes:form.elements.notes.value});
      dirty.delete(card.dataset.id);
      updateProgress(result);
      status(card.querySelector(".save-status"), result.export_errors.length ? "Correction saved. Export needs attention." : "Saved · Excel and CSV updated", result.export_errors.length > 0);
      status(connection, result.export_errors.join(" ") || "All saved corrections are on disk. Excel and CSV are up to date.", result.export_errors.length > 0);
      filter();
    } catch (error) {
      status(card.querySelector(".save-status"), error.message, true);
    } finally {
      saving = false;
      for (const field of form.elements) field.disabled = false;
      for (const submit of document.querySelectorAll("button[type=submit]")) submit.disabled = false;
    }
  });
}
document.querySelector("#export").addEventListener("click", async () => {
  if (saving) return;
  try {
    const result = await post("/api/export", {});
    status(connection, result.export_errors.join(" ") || "Excel and CSV refreshed from saved corrections.", result.export_errors.length > 0);
  } catch (error) {status(connection,error.message,true);}
});
for (const link of document.querySelectorAll(".downloads a")) link.addEventListener("click", event => {
  if (!token) {event.preventDefault();status(connection,"Start the local review server to download exports.",true);}
  else if (dirty.size && !window.confirm("Some edits are unsaved. Download the last saved version?")) event.preventDefault();
});
document.querySelector("#search").addEventListener("input", filter);
document.querySelector("#pending").addEventListener("change", filter);
const lightbox = document.querySelector("#lightbox");
for (const button of document.querySelectorAll(".frame-open")) button.addEventListener("click", () => {
  document.querySelector("#enlarged").src = button.dataset.full;
  document.querySelector("#caption").textContent = button.dataset.caption;
  lightbox.showModal();
});
document.querySelector("#close").addEventListener("click", () => lightbox.close());
window.addEventListener("beforeunload", event => {if (dirty.size) {event.preventDefault();event.returnValue = "";}});
async function connect() {
  if (location.protocol === "file:") {
    status(connection, "Preview only. To save edits, run: python -m instagram_ocr review <this results folder>");
    return;
  }
  try {
    const response = await fetch("/api/state");
    if (!response.ok) throw new Error("The review server is unavailable.");
    const data = await response.json();
    token = data.token;
    updateProgress(data);
    for (const card of cards) {
      const form = card.querySelector("form"), entry = data.entries[card.dataset.id];
      if (entry) {
        form.elements.decision.value = entry.decision;
        form.elements.names.value = entry.decision === "unreviewed" ? form.elements.names.dataset.original : entry.names.join(", ");
        form.elements.notes.value = entry.notes;
      }
      form.querySelector("button[type=submit]").disabled = false;
      status(card.querySelector(".save-status"), entry ? "Saved correction loaded" : "Check the frames, then choose a decision.");
    }
    document.querySelector("#export").disabled = false;
    status(connection, "Connected locally. Save a correction to update Excel and CSV.");
    filter();
  } catch (error) {status(connection, `${error.message} Reopen the URL printed by the review command.`, true);}
}
connect();
