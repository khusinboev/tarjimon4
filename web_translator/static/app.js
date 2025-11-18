document.addEventListener("DOMContentLoaded", () => {
  const textEl = document.getElementById("text");
  const sourceEl = document.getElementById("source");
  const targetEl = document.getElementById("target");
  const translateBtn = document.getElementById("translateBtn");
  const clearBtn = document.getElementById("clearBtn");
  const resultEl = document.getElementById("result");
  const copyBtn = document.getElementById("copyBtn");
  const alertPlaceholder = document.getElementById("alertPlaceholder");
  const charCount = document.getElementById("charCount");
  const swapBtn = document.getElementById("swapBtn");
  const exampleBtn = document.getElementById("exampleBtn");
  const detectedLang = document.getElementById("detectedLang");

  const MAX_LEN = parseInt(textEl.getAttribute("maxlength") || "5000", 10);

  const updateCharCount = () => {
    charCount.innerText = `${textEl.value.length} / ${MAX_LEN}`;
  };

  textEl.addEventListener("input", updateCharCount);
  updateCharCount();

  function showAlert(type, message, timeout=4000) {
    alertPlaceholder.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    if (timeout) setTimeout(()=> alertPlaceholder.innerHTML = "", timeout);
  }

  function clearAlert() {
    alertPlaceholder.innerHTML = "";
  }

  swapBtn.addEventListener("click", () => {
    const s = sourceEl.value;
    const t = targetEl.value;
    if (s === "auto") {
      showAlert("warning", "Manba tili avtomatik aniqlangan holatda almashtirishni amalga oshirib bo'lmaydi.", 2500);
      return;
    }
    sourceEl.value = t;
    targetEl.value = s;
    clearAlert();
  });

  exampleBtn.addEventListener("click", () => {
    textEl.value = "Assalomu alaykum, bugun ob-havo qanday?";
    updateCharCount();
  });

  clearBtn.addEventListener("click", () => {
    textEl.value = "";
    resultEl.innerText = "";
    detectedLang.innerText = "";
    updateCharCount();
    clearAlert();
  });

  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(resultEl.innerText || "");
      showAlert("success", "Natija nusxalandi");
    } catch (e) {
      showAlert("danger", "Nusxalashda xato: brauzer tomonidan rad etildi.");
    }
  });

  translateBtn.addEventListener("click", async () => {
    clearAlert();
    resultEl.innerText = "";
    detectedLang.innerText = "";

    const text = textEl.value.trim();
    if (!text) {
      showAlert("warning", "Iltimos, tarjima qilinadigan matn kiriting.");
      return;
    }
    if (text.length > MAX_LEN) {
      showAlert("warning", `Matn uzunligi ${MAX_LEN} belgidan oshmasligi kerak.`);
      return;
    }

    const payload = {
      text: text,
      source: sourceEl.value,
      target: targetEl.value
    };

    translateBtn.disabled = true;
    translateBtn.innerText = "Tarjima qilinmoqda...";

    try {
      const resp = await fetch("/translate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });

      const data = await resp.json().catch(()=>({ok:false,error:"Server javobi JSON emas"}));

      if (!resp.ok) {
        const msg = data && data.error ? data.error : `Server xatosi (${resp.status})`;
        showAlert("danger", msg);
      } else if (!data.ok) {
        showAlert("warning", data.error || "Tarjima bajarilmadi");
      } else {
        resultEl.innerText = data.translated || "";
        if (data.detected) {
          const det = data.detected;
          const info = LANG_MAP && LANG_MAP[det] ? LANG_MAP[det] : null;
          detectedLang.innerText = info ? `aniqlangan til: ${info.flag} ${info.name} — ${det}` : `aniqlangan til: ${det}`;
        }
      }
    } catch (err) {
      console.error(err);
      showAlert("danger", "Tarmoq xatosi yoki serverga ulanish imkoni yo'q.");
    } finally {
      translateBtn.disabled = false;
      translateBtn.innerText = "Tarjima qilish";
    }
  });

});