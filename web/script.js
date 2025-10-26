const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const scanBtn = document.getElementById("scanBtn");
const translateBtn = document.getElementById("translateBtn");
const targetLangSelect = document.getElementById("targetLang");
// removed side panel UI
const overlay = document.getElementById("overlay");
const overlayTitle = document.getElementById("overlayTitle");
const overlayText = document.getElementById("overlayText");
const saveBtn = document.getElementById("saveBtn");
const closeOverlayBtn = document.getElementById("closeOverlayBtn");

const BACKEND_URL = "http://127.0.0.1:5001";

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
    video.srcObject = stream;
  } catch (err) {
    console.error("Camera error:", err);
    alert("Unable to access camera. Please allow camera permissions.");
  }
}

function captureFrame() {
  const w = video.videoWidth || 720;
  const h = video.videoHeight || 1280;
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, w, h);
  return canvas.toDataURL("image/png");
}

function showOverlay(name, info) {
  if (name) {
    overlayTitle.textContent = name;
    overlayTitle.classList.remove("hidden");
  } else {
    overlayTitle.textContent = "";
    overlayTitle.classList.add("hidden");
  }
  overlayText.textContent = info || "";
  overlay.classList.remove("hidden");
}

function hideOverlay() {
  overlay.classList.add("hidden");
}

function saveToPassport(entry) {
  const key = "passportEntries";
  const existing = JSON.parse(localStorage.getItem(key) || "[]");
  existing.unshift(entry);
  localStorage.setItem(key, JSON.stringify(existing));
}

async function analyzeImage(imageDataUrl) {
  const res = await fetch(`${BACKEND_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: imageDataUrl })
  });
  if (!res.ok) throw new Error(`Analyze failed: ${res.status}`);
  return res.json();
}

async function ocrTranslate(imageDataUrl, targetLang) {
  const res = await fetch(`${BACKEND_URL}/ocr_translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: imageDataUrl, target: targetLang })
  });
  if (!res.ok) throw new Error(`OCR translate failed: ${res.status}`);
  return res.json();
}

document.addEventListener("DOMContentLoaded", () => {
  if (video) startCamera();

  if (scanBtn) {
    scanBtn.addEventListener("click", async () => {
      const dataUrl = captureFrame();
      try {
        const result = await analyzeImage(dataUrl);
        const { landmark, info } = result;
        showOverlay(landmark, info);
        // Ensure save button is visible for landmark saves
        if (saveBtn) saveBtn.style.display = "";

        saveBtn.onclick = () => {
          saveToPassport({
            name: landmark || "Unknown",
            info: info || "",
            image: dataUrl,
            timestamp: new Date().toISOString()
          });
          hideOverlay();
          alert("Saved to Passport");
        };
      } catch (e) {
        console.error(e);
        alert("Scan failed. Ensure backend is running.");
      }
    });
  }

  if (translateBtn) {
    translateBtn.addEventListener("click", async () => {
      const dataUrl = captureFrame();
      const target = (targetLangSelect && targetLangSelect.value) || "en";
      try {
        const result = await ocrTranslate(dataUrl, target);
        const { detected_text, translated_text, source_lang, target_lang } = result;
        const info = translated_text || '';
        const title = `Translation (${(source_lang || 'auto').toUpperCase()} → ${(target_lang || target).toUpperCase()})`;
        showOverlay(title, info);
        // Hide save button for translations (do not save translated text)
        if (saveBtn) saveBtn.style.display = "none";
      } catch (e) {
        console.error(e);
        alert("Translate failed. Ensure backend is running.");
      }
    });
  }
  if (closeOverlayBtn) {
    closeOverlayBtn.addEventListener("click", () => {
      hideOverlay();
      // Reset save button visibility for next time
      if (saveBtn) saveBtn.style.display = "";
    });
  }
});


