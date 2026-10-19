const cameraInput = document.getElementById("cameraInput");
const fileInput = document.getElementById("fileInput");
const preview = document.getElementById("preview");
const analyzeBtn = document.getElementById("analyzeBtn");
const statusEl = document.getElementById("status");
const results = document.getElementById("results");

let selectedFile = null;

function setStatus(text, isError) {
  statusEl.textContent = text;
  statusEl.className = isError ? "error" : "";
}

function pick(file) {
  if (!file) return;
  selectedFile = file;
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  analyzeBtn.disabled = false;
  results.hidden = true;
  setStatus("");
}

cameraInput.addEventListener("change", (e) => pick(e.target.files[0]));
fileInput.addEventListener("change", (e) => pick(e.target.files[0]));

// Shrink big phone photos so uploads are fast and under the size limit
function resizeImage(file, maxSide) {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      canvas.toBlob((blob) => resolve(blob || file), "image/jpeg", 0.9);
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
    img.src = url;
  });
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderDetections(list) {
  const ul = document.getElementById("detList");
  ul.replaceChildren();
  if (!list.length) {
    ul.appendChild(el("li", "empty", "Nothing detected"));
    return;
  }
  list.forEach((d) => {
    const li = el("li");
    li.appendChild(el("span", "", d.label + " " + Math.round(d.confidence * 100) + "%"));
    li.appendChild(el("span", "tag " + d.group, d.group));
    ul.appendChild(li);
  });
}

function renderAI(v) {
  const box = document.getElementById("aiBox");
  box.replaceChildren();
  if (!v || v.status !== "ok") {
    const why = v && v.reason ? v.reason : "unavailable";
    box.appendChild(el("p", "", "Not available: " + why));
    return;
  }
  const risk = String(v.risk_level || "low").toLowerCase();
  box.appendChild(el("span", "risk " + risk, "Risk: " + risk));
  if (v.summary) box.appendChild(el("p", "", v.summary));
  box.appendChild(el("p", "", "Humans seen: " + (v.humans ?? "?")));
  const fmt = (arr) => (arr || []).map((a) => a.count + " " + a.type).join(", ") || "none";
  box.appendChild(el("p", "", "Domestic: " + fmt(v.domestic_animals)));
  box.appendChild(el("p", "", "Wild: " + fmt(v.wild_animals)));
  if (v.corrections) box.appendChild(el("p", "", "Correction: " + v.corrections));
}

function renderAlerts(list) {
  const box = document.getElementById("alertsBox");
  box.replaceChildren();
  if (!list.length) {
    box.appendChild(el("p", "", "No alert needed (no wildlife detected)."));
    return;
  }
  list.forEach((a) => {
    const row = el("div", "alert-row");
    row.appendChild(el("span", "", a.channel));
    row.appendChild(el("span", a.status, a.status));
    box.appendChild(row);
  });
}

analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  analyzeBtn.disabled = true;
  setStatus("Analyzing...");
  try {
    const blob = await resizeImage(selectedFile, 1600);
    const form = new FormData();
    form.append("image", blob, "photo.jpg");

    const res = await fetch("/analyze", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Server error");

    document.getElementById("cHuman").textContent = data.counts.human;
    document.getElementById("cDomestic").textContent = data.counts.domestic;
    document.getElementById("cWild").textContent = data.counts.wild;
    document.getElementById("annotatedImg").src = data.annotated_url + "?t=" + Date.now();

    renderDetections(data.detections);
    renderAI(data.claude);
    renderAlerts(data.alerts);

    results.hidden = false;
    results.scrollIntoView({ behavior: "smooth" });
    setStatus("");
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    analyzeBtn.disabled = false;
  }
});
