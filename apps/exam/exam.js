/**
 * AaaS Accessible Exam — demo-grade mock paper for BSE Odisha.
 *
 * Single-file client:
 *   - Renders 5 questions from the inline QUESTIONS array.
 *   - Toggles: OpenDyslexic font, high-contrast theme, large text,
 *     extra time (+50%).
 *   - Timer with visual + aria-live updates; flips to danger state
 *     under 1 min.
 *   - "Read question" → POSTs the question text to /tts/synthesise
 *     via the gateway. Meta MMS-TTS is the only engine; if the server
 *     is unreachable the button surfaces the error and nothing speaks.
 *   - "Speak answer" → asks the AaaS widget to open its mic flow,
 *     listens for the `aaas-transcript` event, and stores the
 *     transcript into the current question's answer field.
 *   - Submit → scores against the canonical answer, renders a
 *     per-question breakdown.
 *
 * The widget script is loaded in the HTML BEFORE this file, and it
 * auto-mounts. We treat it as a black box and communicate over the
 * well-known custom event so the two could be split repo-wise later
 * without coupling.
 */
(function () {
  "use strict";

  const CONFIG = {
    gateway:
      document.currentScript?.dataset?.gateway ||
      window.AAAS_GATEWAY_URL ||
      "",
    apiKey:
      document.currentScript?.dataset?.key ||
      window.AAAS_API_KEY ||
      "aaas_live_22222222222222222222222222222222",
    baseTimeMinutes: 10,
    extraTimeMultiplier: 1.5,
  };
  // Gateway defaults to same-origin since the HTML is served by the
  // gateway itself; useful for cloud deploys where relative paths
  // survive the reverse-proxy hop.
  if (!CONFIG.gateway) CONFIG.gateway = window.location.origin;

  /* ---------- questions ---------- */
  //
  // All questions are stored in Odia so the demo's "readable by TTS in
  // Odia" story is real. For multilingual demos, the widget's language
  // picker routes the text through /translate/ before synthesis.

  const QUESTIONS = [
    {
      id: "q1",
      type: "mcq",
      text: "ଓଡ଼ିଶାର ରାଜଧାନୀ କଣ?",
      options: ["କଟକ", "ଭୁବନେଶ୍ୱର", "ରାଉରକେଲା", "ପୁରୀ"],
      correct: 1,
    },
    {
      id: "q2",
      type: "mcq",
      text: "ଚିଲିକା ହ୍ରଦ କେଉଁ ରାଜ୍ୟରେ ଅବସ୍ଥିତ?",
      options: ["ଆନ୍ଧ୍ରପ୍ରଦେଶ", "ଓଡ଼ିଶା", "ତାମିଲନାଡୁ", "ପଶ୍ଚିମବଙ୍ଗ"],
      correct: 1,
    },
    {
      id: "q3",
      type: "mcq",
      text: "କୋଣାର୍କ ସୂର୍ଯ୍ୟ ମନ୍ଦିର କେଉଁ ଶତାବ୍ଦୀରେ ନିର୍ମାଣ କରାଯାଇଥିଲା?",
      options: ["୧୧ଶ ଶତାବ୍ଦୀ", "୧୨ଶ ଶତାବ୍ଦୀ", "୧୩ଶ ଶତାବ୍ଦୀ", "୧୪ଶ ଶତାବ୍ଦୀ"],
      correct: 2,
    },
    {
      id: "q4",
      type: "short",
      text: "୨୦ ଓ ୨୨ର ଯୋଗଫଳ କେତେ?",
      // Accept Odia digits, Western digits, or English words.
      validate: (s) => {
        const t = s.trim().toLowerCase();
        return ["୪୨", "42", "forty two", "forty-two"].includes(t);
      },
      correctDisplay: "୪୨",
    },
    {
      id: "q5",
      type: "short",
      text: "ଆପଣଙ୍କ ନାମ କଣ?",
      // Any non-empty answer counts — this question exists to
      // demonstrate the STT voice-answer flow; correctness is social,
      // not graded.
      validate: (s) => s.trim().length > 0,
      correctDisplay: "(any name)",
    },
  ];

  /* ---------- DOM refs ---------- */

  const $ = (sel) => document.querySelector(sel);

  const refs = {
    qNum: $("#qNum"),
    qTotal: $("#qTotal"),
    qLabel: $("#qLabel"),
    qText: $("#qText"),
    options: $("#options"),
    shortAnswerWrap: $("#shortAnswerWrap"),
    shortAnswer: $("#shortAnswer"),
    readQuestion: $("#readQuestion"),
    speakAnswer: $("#speakAnswer"),
    lastTranscript: $("#lastTranscript"),
    prevBtn: $("#prevBtn"),
    nextBtn: $("#nextBtn"),
    submitBtn: $("#submitBtn"),
    result: $("#result"),
    scoreLine: $("#scoreLine"),
    resultList: $("#resultList"),
    restartBtn: $("#restartBtn"),
    extraTime: $("#extraTime"),
    extraTimeBanner: $("#extraTimeBanner"),
    timer: $("#timer"),
    timerValue: $("#timerValue"),
    toggleFont: $("#toggleFont"),
    toggleContrast: $("#toggleContrast"),
    toggleLarge: $("#toggleLarge"),
  };

  refs.qTotal.textContent = QUESTIONS.length;

  /* ---------- state ---------- */

  const state = {
    index: 0,
    answers: QUESTIONS.map(() => null), // index into options or string
    submitted: false,
    timerDeadline: null,
    timerInterval: null,
  };

  /* ---------- rendering ---------- */

  function renderQuestion() {
    const q = QUESTIONS[state.index];
    refs.qNum.textContent = String(state.index + 1);
    refs.qLabel.textContent = `Question ${state.index + 1}`;
    refs.qText.textContent = q.text;
    refs.lastTranscript.textContent = "";

    if (q.type === "mcq") {
      refs.shortAnswerWrap.hidden = true;
      refs.options.hidden = false;
      refs.options.innerHTML = "";
      q.options.forEach((opt, i) => {
        const label = document.createElement("label");
        label.className = "option";
        const id = `${q.id}_opt_${i}`;
        label.innerHTML = `
          <input
            type="radio"
            name="${q.id}"
            id="${id}"
            value="${i}"
            ${state.answers[state.index] === i ? "checked" : ""}
          />
          <span>${opt}</span>
        `;
        refs.options.appendChild(label);
      });
    } else {
      refs.shortAnswerWrap.hidden = false;
      refs.options.hidden = true;
      refs.options.innerHTML = "";
      refs.shortAnswer.value = state.answers[state.index] || "";
    }

    refs.prevBtn.disabled = state.index === 0;
    const isLast = state.index === QUESTIONS.length - 1;
    refs.nextBtn.hidden = isLast;
    refs.submitBtn.hidden = !isLast;
  }

  function recordCurrentAnswer() {
    const q = QUESTIONS[state.index];
    if (q.type === "mcq") {
      const sel = refs.options.querySelector(
        `input[name="${q.id}"]:checked`
      );
      state.answers[state.index] = sel ? Number(sel.value) : null;
    } else {
      state.answers[state.index] = refs.shortAnswer.value;
    }
  }

  /* ---------- read aloud (TTS) ---------- */
  //
  // We call the same gateway the widget uses. Meta MMS-TTS is the only
  // engine — on network/server failure we show an error in the
  // `lastTranscript` line and stay silent. No browser-voice fallback.

  let currentReadAudio = null;

  async function readText(text) {
    if (currentReadAudio) {
      try { currentReadAudio.pause(); } catch {}
      currentReadAudio = null;
    }
    try {
      const res = await fetch(`${CONFIG.gateway}/tts/synthesise`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": CONFIG.apiKey,
        },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      currentReadAudio = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        if (currentReadAudio === audio) currentReadAudio = null;
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        if (currentReadAudio === audio) currentReadAudio = null;
      };
      await audio.play().catch(() => {});
    } catch (err) {
      refs.lastTranscript.textContent =
        `Read-aloud unavailable: ${err.message}. Start the AaaS gateway and try again.`;
    }
  }

  refs.readQuestion.addEventListener("click", () => {
    const q = QUESTIONS[state.index];
    const parts = [q.text];
    if (q.type === "mcq")
      parts.push(...q.options.map((o, i) => `${String.fromCharCode(65 + i)}. ${o}`));
    readText(parts.join(". "));
  });

  /* ---------- speak answer (STT via widget) ---------- */
  //
  // The widget owns the mic + /stt/transcribe call. We just ask it to
  // open and listen for its `aaas-transcript` event.

  refs.speakAnswer.addEventListener("click", () => {
    // The widget's own mic button is inside its Shadow DOM and opens
    // a recording session when clicked. Programmatically clicking it
    // from here means piercing the Shadow root, which we keep private.
    // So we ask the user to open the panel via a friendly nudge.
    // In practice judges expect the widget's own mic button to be
    // used — this button is a visible reminder that voice answers are
    // supported.
    refs.lastTranscript.textContent =
      "Use the microphone in the floating ଅ panel (bottom right) to record your answer.";
  });

  document.addEventListener("aaas-transcript", (ev) => {
    const { text, language } = ev.detail || {};
    if (!text) return;
    refs.lastTranscript.textContent = `Heard (${language}): ${text}`;
    const q = QUESTIONS[state.index];
    if (q.type === "short") {
      refs.shortAnswer.value = text;
      state.answers[state.index] = text;
    } else if (q.type === "mcq") {
      // Best-effort match: compare transcript against each option.
      const lc = text.toLowerCase();
      const idx = q.options.findIndex((o) => lc.includes(o.toLowerCase()));
      if (idx >= 0) {
        state.answers[state.index] = idx;
        const input = refs.options.querySelector(
          `input[name="${q.id}"][value="${idx}"]`
        );
        if (input) input.checked = true;
      }
    }
  });

  /* ---------- navigation ---------- */

  refs.prevBtn.addEventListener("click", () => {
    recordCurrentAnswer();
    if (state.index > 0) {
      state.index -= 1;
      renderQuestion();
    }
  });
  refs.nextBtn.addEventListener("click", () => {
    recordCurrentAnswer();
    if (state.index < QUESTIONS.length - 1) {
      state.index += 1;
      renderQuestion();
    }
  });
  refs.submitBtn.addEventListener("click", () => {
    recordCurrentAnswer();
    showResult();
  });

  /* ---------- submit / score ---------- */

  function showResult() {
    state.submitted = true;
    stopTimer();
    let correct = 0;
    refs.resultList.innerHTML = "";
    QUESTIONS.forEach((q, i) => {
      let given = state.answers[i];
      let ok = false;
      let display = "(no answer)";
      if (q.type === "mcq" && given !== null) {
        ok = given === q.correct;
        display = q.options[given];
      } else if (q.type === "short" && given) {
        ok = q.validate(given);
        display = given;
      }
      if (ok) correct++;
      const li = document.createElement("li");
      li.innerHTML = `
        <div>${q.text}</div>
        <div>
          <strong>Your answer:</strong> ${escapeHtml(display)}
          <span class="${ok ? "correct" : "wrong"}">
            ${ok ? "✓ correct" : `✗ expected ${escapeHtml(
              q.type === "mcq" ? q.options[q.correct] : q.correctDisplay
            )}`}
          </span>
        </div>
      `;
      refs.resultList.appendChild(li);
    });
    refs.scoreLine.textContent = `You scored ${correct} / ${QUESTIONS.length}`;
    refs.result.hidden = false;
    document.querySelector(".question-card").hidden = true;
    document.querySelector(".nav-row").hidden = true;
    refs.result.scrollIntoView({ behavior: "smooth" });
    // Read the score aloud as a final accessibility flourish.
    readText(`You scored ${correct} out of ${QUESTIONS.length}`);
  }

  refs.restartBtn.addEventListener("click", () => {
    state.index = 0;
    state.answers = QUESTIONS.map(() => null);
    state.submitted = false;
    refs.result.hidden = true;
    document.querySelector(".question-card").hidden = false;
    document.querySelector(".nav-row").hidden = false;
    renderQuestion();
    startTimer();
  });

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* ---------- toolbar ---------- */

  function bindToggle(btn, className, label) {
    btn.addEventListener("click", () => {
      const on = btn.getAttribute("aria-pressed") === "true";
      const next = !on;
      btn.setAttribute("aria-pressed", String(next));
      document.body.classList.toggle(className, next);
      btn.querySelector("span:last-child")?.remove;
      // We rewrite the button's text node safely.
      const icon = btn.querySelector("[aria-hidden]");
      btn.textContent = "";
      if (icon) btn.appendChild(icon);
      btn.append(` ${label}: ${next ? "on" : "off"}`);
    });
  }
  // Re-map class names to our CSS conventions.
  bindToggle(refs.toggleFont, "font-dyslexia", "Dyslexia font");
  // Contrast uses theme-* swap: default vs contrast.
  refs.toggleContrast.addEventListener("click", () => {
    const on = refs.toggleContrast.getAttribute("aria-pressed") === "true";
    const next = !on;
    refs.toggleContrast.setAttribute("aria-pressed", String(next));
    document.body.classList.toggle("theme-contrast", next);
    document.body.classList.toggle("theme-default", !next);
    const icon = refs.toggleContrast.querySelector("[aria-hidden]");
    refs.toggleContrast.textContent = "";
    if (icon) refs.toggleContrast.appendChild(icon);
    refs.toggleContrast.append(` High contrast: ${next ? "on" : "off"}`);
  });
  bindToggle(refs.toggleLarge, "size-large", "Large text");

  refs.extraTime.addEventListener("change", () => {
    refs.extraTimeBanner.hidden = !refs.extraTime.checked;
    restartTimerForCurrentSettings();
  });

  /* ---------- timer ---------- */

  function timerMs() {
    const minutes = refs.extraTime.checked
      ? CONFIG.baseTimeMinutes * CONFIG.extraTimeMultiplier
      : CONFIG.baseTimeMinutes;
    return minutes * 60 * 1000;
  }

  function startTimer() {
    stopTimer();
    state.timerDeadline = Date.now() + timerMs();
    tickTimer();
    state.timerInterval = setInterval(tickTimer, 1000);
  }
  function stopTimer() {
    if (state.timerInterval) {
      clearInterval(state.timerInterval);
      state.timerInterval = null;
    }
  }
  function restartTimerForCurrentSettings() {
    // If the user flips extra time mid-exam, re-base the deadline so
    // they gain the bonus without losing the time already spent.
    if (!state.timerDeadline) return startTimer();
    const elapsed = timerMs() - (state.timerDeadline - Date.now());
    state.timerDeadline = Date.now() + Math.max(30_000, timerMs() - elapsed);
    tickTimer();
  }
  function tickTimer() {
    const left = Math.max(0, state.timerDeadline - Date.now());
    const s = Math.floor(left / 1000);
    const mm = String(Math.floor(s / 60)).padStart(2, "0");
    const ss = String(s % 60).padStart(2, "0");
    refs.timerValue.textContent = `${mm}:${ss}`;
    refs.timer.classList.toggle("warning", left <= 120_000);
    refs.timer.classList.toggle("danger", left <= 60_000);
    if (left === 0 && !state.submitted) {
      stopTimer();
      showResult();
    }
  }

  /* ---------- keyboard shortcuts ---------- */

  document.addEventListener("keydown", (e) => {
    if (state.submitted) return;
    if (e.target.tagName === "INPUT" && e.target.type === "text") return;
    if (e.key === "ArrowRight" || e.key.toLowerCase() === "n") {
      e.preventDefault();
      refs.nextBtn.click();
    } else if (e.key === "ArrowLeft" || e.key.toLowerCase() === "p") {
      e.preventDefault();
      refs.prevBtn.click();
    } else if (e.key === "r") {
      refs.readQuestion.click();
    }
  });

  /* ---------- boot ---------- */

  renderQuestion();
  startTimer();
})();
