(() => {
  const STORAGE_KEY = "trivia_arena_meta";
  const POLL_MS = 1000;
  const CSRF_HEADER = "X-CSRF-Token";

  const els = {
    home: document.getElementById("view-home"),
    game: document.getElementById("view-game"),
    displayName: document.getElementById("display-name"),
    packSelect: document.getElementById("pack-select"),
    packHint: document.getElementById("pack-hint"),
    roomCode: document.getElementById("room-code"),
    homeError: document.getElementById("home-error"),
    gameError: document.getElementById("game-error"),
    metaCode: document.getElementById("meta-code"),
    metaRound: document.getElementById("meta-round"),
    metaTimer: document.getElementById("meta-timer"),
    gameStatus: document.getElementById("game-status"),
    questionBlock: document.getElementById("question-block"),
    questionPrompt: document.getElementById("question-prompt"),
    choices: document.getElementById("choices"),
    revealBlock: document.getElementById("reveal-block"),
    revealPrompt: document.getElementById("reveal-prompt"),
    revealChoices: document.getElementById("reveal-choices"),
    revealAnswers: document.getElementById("reveal-answers"),
    scoreboard: document.getElementById("scoreboard"),
    hostActions: document.getElementById("host-actions"),
    btnCreate: document.getElementById("btn-create"),
    btnJoin: document.getElementById("btn-join"),
    btnStart: document.getElementById("btn-start"),
    btnNext: document.getElementById("btn-next"),
    btnLeave: document.getElementById("btn-leave"),
  };

  /** @type {{ code: string, is_host: boolean, player_id: number } | null} */
  let session = loadSession();
  /** @type {ReturnType<typeof setInterval> | null} */
  let pollTimer = null;
  let answering = false;
  /** @type {string} */
  let csrfToken = "";

  /** @type {Array<{id:string,title:string,description:string,source:string,question_count:number}>} */
  let packs = [];

  els.btnCreate.addEventListener("click", () => createRoom());
  els.btnJoin.addEventListener("click", () => joinRoom());
  els.btnStart.addEventListener("click", () => postAction("start"));
  els.btnNext.addEventListener("click", () => postAction("next"));
  els.btnLeave.addEventListener("click", leaveRoom);
  els.packSelect.addEventListener("change", updatePackHint);

  boot();

  async function boot() {
    try {
      await ensureCsrf();
      await loadPacks();
      if (session) {
        showGame();
        startPolling();
      }
    } catch (err) {
      showError(els.homeError, err.message);
    }
  }

  async function ensureCsrf() {
    const data = await api("/api/auth/csrf", { method: "GET" });
    csrfToken = data.csrf_token;
  }

  async function loadPacks() {
    packs = await api("/api/packs");
    els.packSelect.replaceChildren();
    packs.forEach((pack) => {
      const opt = document.createElement("option");
      opt.value = pack.id;
      opt.textContent = `${pack.title} (${pack.source})`;
      els.packSelect.appendChild(opt);
    });
    if (!els.packSelect.value && packs[0]) els.packSelect.value = packs[0].id;
    const preferred = packs.find((p) => p.id === "engineering");
    if (preferred) els.packSelect.value = preferred.id;
    updatePackHint();
  }

  function updatePackHint() {
    const pack = packs.find((p) => p.id === els.packSelect.value);
    els.packHint.textContent = pack
      ? `${pack.description} · ~${pack.question_count} questions`
      : "";
  }

  function loadSession() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function saveSession(next) {
    session = next;
    if (next) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    else sessionStorage.removeItem(STORAGE_KEY);
  }

  function showError(el, message) {
    if (!message) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    el.textContent = message;
  }

  function readCookie(name) {
    const parts = document.cookie.split(";").map((p) => p.trim());
    for (const part of parts) {
      if (part.startsWith(name + "=")) {
        return decodeURIComponent(part.slice(name.length + 1));
      }
    }
    return "";
  }

  async function api(path, { method = "GET", body } = {}) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (method !== "GET" && method !== "HEAD") {
      const csrf = csrfToken || readCookie("ta_csrf");
      if (csrf) headers[CSRF_HEADER] = csrf;
    }
    const res = await fetch(path, {
      method,
      headers,
      credentials: "same-origin",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    let data = null;
    const text = await res.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { detail: text };
      }
    }
    if (!res.ok) {
      const detail = data?.detail;
      const msg = typeof detail === "string" ? detail : res.statusText;
      throw new Error(msg || `HTTP ${res.status}`);
    }
    // Refresh CSRF from cookie if server rotated it on create/join.
    const rotated = readCookie("ta_csrf");
    if (rotated) csrfToken = rotated;
    return data;
  }

  async function createRoom() {
    showError(els.homeError, "");
    const display_name = els.displayName.value.trim();
    if (!display_name) {
      showError(els.homeError, "Enter a display name");
      return;
    }
    try {
      await ensureCsrf();
      const data = await api("/api/rooms", {
        method: "POST",
        body: { display_name, pack_id: els.packSelect.value || "engineering" },
      });
      // Token stays in HttpOnly cookie — never localStorage.
      saveSession({
        code: data.code,
        is_host: data.is_host,
        player_id: data.player_id,
      });
      showGame();
      startPolling();
    } catch (err) {
      showError(els.homeError, err.message);
    }
  }

  async function joinRoom() {
    showError(els.homeError, "");
    const display_name = els.displayName.value.trim();
    const code = els.roomCode.value.trim().toUpperCase();
    if (!display_name || !code) {
      showError(els.homeError, "Name and room code required");
      return;
    }
    try {
      await ensureCsrf();
      const data = await api(`/api/rooms/${encodeURIComponent(code)}/join`, {
        method: "POST",
        body: { display_name },
      });
      saveSession({
        code: data.code,
        is_host: data.is_host,
        player_id: data.player_id,
      });
      showGame();
      startPolling();
    } catch (err) {
      showError(els.homeError, err.message);
    }
  }

  async function postAction(action) {
    if (!session) return;
    showError(els.gameError, "");
    try {
      const state = await api(`/api/rooms/${encodeURIComponent(session.code)}/${action}`, {
        method: "POST",
      });
      renderState(state);
    } catch (err) {
      showError(els.gameError, err.message);
    }
  }

  async function answer(choiceIndex) {
    if (!session || answering) return;
    answering = true;
    showError(els.gameError, "");
    try {
      const state = await api(`/api/rooms/${encodeURIComponent(session.code)}/answer`, {
        method: "POST",
        body: { choice_index: choiceIndex },
      });
      renderState(state);
    } catch (err) {
      showError(els.gameError, err.message);
    } finally {
      answering = false;
    }
  }

  async function leaveRoom() {
    stopPolling();
    try {
      await ensureCsrf();
      await api("/api/auth/logout", { method: "POST" });
    } catch {
      // still clear local meta
    }
    saveSession(null);
    els.game.hidden = true;
    els.home.hidden = false;
  }

  function showGame() {
    els.home.hidden = true;
    els.game.hidden = false;
    if (session) els.metaCode.textContent = session.code;
  }

  function startPolling() {
    stopPolling();
    refresh();
    pollTimer = setInterval(refresh, POLL_MS);
  }

  function stopPolling() {
    if (pollTimer !== null) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  async function refresh() {
    if (!session) return;
    try {
      const state = await api(`/api/rooms/${encodeURIComponent(session.code)}`);
      renderState(state);
      showError(els.gameError, "");
    } catch (err) {
      showError(els.gameError, err.message);
    }
  }

  function renderState(state) {
    if (!session) return;
    els.metaCode.textContent = state.code;
    els.metaRound.textContent =
      state.status === "lobby"
        ? "Lobby"
        : state.status === "finished"
          ? "Finished"
          : `Round ${state.current_round}`;

    els.metaTimer.textContent = formatCountdown(state.phase_ends_at);
    els.hostActions.hidden = !session.is_host;
    els.btnStart.hidden = state.status !== "lobby";
    els.btnNext.hidden = state.status !== "active";

    renderScoreboard(state.players);

    if (state.status === "lobby") {
      els.gameStatus.textContent = session.is_host
        ? "Waiting for players — start when ready."
        : "Waiting for host to start…";
      els.questionBlock.hidden = true;
      els.revealBlock.hidden = true;
      return;
    }

    if (state.status === "finished") {
      els.gameStatus.textContent = "Game over.";
      els.questionBlock.hidden = true;
      if (state.last_result) {
        renderReveal(state.last_result);
        els.revealBlock.hidden = false;
      } else {
        els.revealBlock.hidden = true;
      }
      return;
    }

    if (state.last_result) {
      els.gameStatus.textContent = "Reveal";
      els.questionBlock.hidden = true;
      renderReveal(state.last_result);
      els.revealBlock.hidden = false;
      return;
    }

    if (state.question) {
      els.gameStatus.textContent = state.your_answered
        ? "Answer locked in — waiting…"
        : "Pick an answer";
      els.revealBlock.hidden = true;
      els.questionBlock.hidden = false;
      els.questionPrompt.textContent = state.question.prompt;
      els.choices.replaceChildren();
      state.question.choices.forEach((label, index) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = label;
        btn.disabled = Boolean(state.your_answered);
        btn.addEventListener("click", () => answer(index));
        els.choices.appendChild(btn);
      });
      return;
    }

    els.gameStatus.textContent = "…";
    els.questionBlock.hidden = true;
    els.revealBlock.hidden = true;
  }

  function renderReveal(result) {
    els.revealPrompt.textContent = result.prompt;
    els.revealChoices.replaceChildren();
    result.choices.forEach((label, index) => {
      const div = document.createElement("div");
      div.className = "choice" + (index === result.correct_index ? " correct" : "");
      div.textContent = label;
      els.revealChoices.appendChild(div);
    });
    els.revealAnswers.replaceChildren();
    result.answers.forEach((a) => {
      const li = document.createElement("li");
      const name = document.createElement("span");
      name.textContent = a.display_name;
      const mark = document.createElement("span");
      if (a.choice_index === null || a.choice_index === undefined) {
        mark.textContent = "no answer";
        mark.className = "nope";
      } else if (a.correct) {
        mark.textContent = "correct";
        mark.className = "ok";
      } else {
        mark.textContent = result.choices[a.choice_index] ?? "wrong";
        mark.className = "nope";
      }
      li.append(name, mark);
      els.revealAnswers.appendChild(li);
    });
  }

  function renderScoreboard(players) {
    els.scoreboard.replaceChildren();
    [...players]
      .sort((a, b) => b.score - a.score || a.id - b.id)
      .forEach((p) => {
        const li = document.createElement("li");
        const left = document.createElement("span");
        left.textContent = `${p.display_name}${p.is_host ? " (host)" : ""}`;
        const right = document.createElement("span");
        right.textContent = String(p.score);
        li.append(left, right);
        els.scoreboard.appendChild(li);
      });
  }

  function formatCountdown(phaseEndsAt) {
    if (!phaseEndsAt) return "";
    const end = Date.parse(phaseEndsAt);
    if (Number.isNaN(end)) return "";
    const secs = Math.max(0, Math.ceil((end - Date.now()) / 1000));
    return `${secs}s`;
  }
})();
