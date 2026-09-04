(() => {
  const canvas = document.getElementById("neonRunnerCanvas");
  const ctx = canvas?.getContext("2d");
  const startButton = document.getElementById("startGame");
  const pauseButton = document.getElementById("pauseGame");
  const soundButton = document.getElementById("soundToggle");
  const gameOverlay = document.getElementById("gameOverlay");
  const gameStatus = document.getElementById("gameStatus");
  const gameMessage = document.getElementById("gameMessage");
  const scoreOutput = document.getElementById("gameScore");
  const distanceOutput = document.getElementById("gameDistance");
  const timerOutput = document.getElementById("gameTimer");
  const leaderboard = document.getElementById("runnerLeaderboard");
  const leftButton = document.getElementById("moveLeft");
  const rightButton = document.getElementById("moveRight");
  const overlayKicker = gameOverlay?.querySelector(".section-kicker");
  const overlayTitle = document.getElementById("game-title");
  const overlayCopy = gameOverlay?.querySelector("p");

  if (!canvas || !ctx) return;

  const width = canvas.width;
  const height = canvas.height;
  const keys = new Set();
  const state = {
    running: false,
    paused: false,
    starting: false,
    ending: false,
    scoreSubmitted: false,
    sessionToken: "",
    startedAt: 0,
    elapsed: 0,
    score: 0,
    distance: 0,
    lastFrame: 0,
    spawnClock: 0,
    animationFrame: 0,
    player: { x: width / 2 - 18, y: height - 90, width: 36, height: 42 },
    obstacles: [],
    stars: Array.from({ length: 70 }, (_, index) => ({
      x: (index * 137) % width,
      y: (index * 83) % height,
      size: index % 4 === 0 ? 2 : 1,
      speed: 10 + (index % 5) * 7,
    })),
  };

  function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || "";
  }

  function setStatus(message, type = "ready") {
    if (!gameStatus) return;
    gameStatus.textContent = message;
    gameStatus.className = type;
  }

  function setScoreboard() {
    scoreOutput.textContent = String(Math.floor(state.score)).padStart(6, "0");
    distanceOutput.textContent = `${String(Math.floor(state.distance)).padStart(4, "0")}m`;
    const seconds = Math.floor(state.elapsed);
    timerOutput.textContent = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  }

  function drawBackground() {
    ctx.fillStyle = "#070912";
    ctx.fillRect(0, 0, width, height);
    const glow = ctx.createRadialGradient(width * 0.5, height * 0.25, 10, width * 0.5, height * 0.25, height * 0.8);
    glow.addColorStop(0, "rgba(105, 233, 255, .22)");
    glow.addColorStop(0.48, "rgba(59, 41, 139, .11)");
    glow.addColorStop(1, "rgba(7, 9, 18, 0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, width, height);

    state.stars.forEach((star) => {
      ctx.fillStyle = `rgba(194, 239, 255, ${0.24 + (star.x % 5) / 20})`;
      ctx.fillRect(star.x, star.y, star.size, star.size);
    });

    ctx.strokeStyle = "rgba(105, 233, 255, .12)";
    ctx.lineWidth = 1;
    for (let x = 0; x <= width; x += 80) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y += 60) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    ctx.fillStyle = "rgba(255, 91, 216, .1)";
    ctx.fillRect(width * 0.25, 0, 2, height);
    ctx.fillRect(width * 0.75, 0, 2, height);
  }

  function drawPlayer() {
    const player = state.player;
    ctx.save();
    ctx.translate(player.x + player.width / 2, player.y + player.height / 2);
    ctx.shadowBlur = 24;
    ctx.shadowColor = "#69e9ff";
    ctx.fillStyle = "#69e9ff";
    ctx.beginPath();
    ctx.moveTo(0, -player.height / 2);
    ctx.lineTo(player.width / 2, player.height / 2);
    ctx.lineTo(0, player.height / 3);
    ctx.lineTo(-player.width / 2, player.height / 2);
    ctx.closePath();
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.fillStyle = "#ff5bd8";
    ctx.fillRect(-3, 0, 6, 12);
    ctx.restore();
  }

  function drawObstacles() {
    state.obstacles.forEach((obstacle) => {
      ctx.save();
      ctx.shadowBlur = 18;
      ctx.shadowColor = obstacle.color;
      ctx.fillStyle = obstacle.color;
      ctx.fillRect(obstacle.x, obstacle.y, obstacle.width, obstacle.height);
      ctx.shadowBlur = 0;
      ctx.strokeStyle = "rgba(255, 255, 255, .68)";
      ctx.strokeRect(obstacle.x + 5, obstacle.y + 5, obstacle.width - 10, obstacle.height - 10);
      ctx.restore();
    });
  }

  function draw() {
    drawBackground();
    drawObstacles();
    drawPlayer();
  }

  function move(direction) {
    const amount = 300;
    state.player.x += direction * amount * 0.05;
    state.player.x = Math.max(24, Math.min(width - state.player.width - 24, state.player.x));
  }

  function intersects(first, second) {
    return first.x < second.x + second.width
      && first.x + first.width > second.x
      && first.y < second.y + second.height
      && first.y + first.height > second.y;
  }

  function spawnObstacle() {
    const obstacleWidth = 34 + Math.floor(Math.random() * 36);
    const lane = Math.floor(Math.random() * 5);
    state.obstacles.push({
      x: 72 + lane * 174 + Math.random() * 30,
      y: -60,
      width: obstacleWidth,
      height: 28 + Math.floor(Math.random() * 25),
      color: Math.random() > 0.5 ? "#ff5bd8" : "#9583ff",
      counted: false,
    });
  }

  function update(delta) {
    const speed = 190 + state.elapsed * 5;
    const movement = (keys.has("ArrowLeft") || keys.has("a") ? -1 : 0)
      + (keys.has("ArrowRight") || keys.has("d") ? 1 : 0);
    if (movement) move(movement);

    state.elapsed = (performance.now() - state.startedAt) / 1000;
    state.distance += delta * (10 + state.elapsed * 0.4);
    state.score += delta * 12;
    state.spawnClock += delta;
    if (state.spawnClock >= Math.max(0.45, 0.95 - state.elapsed / 120)) {
      state.spawnClock = 0;
      spawnObstacle();
    }

    state.stars.forEach((star) => {
      star.y += delta * star.speed;
      if (star.y > height) star.y = -4;
    });

    state.obstacles.forEach((obstacle) => {
      obstacle.y += delta * speed;
      if (!obstacle.counted && obstacle.y > state.player.y + state.player.height) {
        obstacle.counted = true;
        state.score += 25;
      }
    });
    state.obstacles = state.obstacles.filter((obstacle) => obstacle.y < height + 80);

    if (state.obstacles.some((obstacle) => intersects(state.player, obstacle))) {
      finishGame("Signal interrupted. Securing your run…");
    }
    setScoreboard();
  }

  function loop(timestamp) {
    if (!state.running) return;
    const delta = state.lastFrame ? Math.min(0.05, (timestamp - state.lastFrame) / 1000) : 0;
    state.lastFrame = timestamp;
    if (!state.paused) update(delta);
    draw();
    if (state.running) state.animationFrame = window.requestAnimationFrame(loop);
  }

  async function startSession() {
    const response = await fetch("/api/play/neon-runner/start", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: JSON.stringify({ game: "neon-runner" }),
    });
    const result = await response.json().catch(() => ({}));
    if (response.status === 401) {
      window.location.assign("/");
      throw new Error("Please log in to play.");
    }
    if (!response.ok || !result.session_token) {
      throw new Error(result.message || "Could not start a secure run.");
    }
    return result.session_token;
  }

  async function submitScore() {
    if (state.scoreSubmitted || !state.sessionToken) return;
    state.scoreSubmitted = true;
    setStatus("SCORE / VERIFYING", "pending");
    if (gameMessage) gameMessage.textContent = "Verifying one final signal with the NEXUS server…";
    try {
      const response = await fetch("/api/play/neon-runner/score", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
        },
        body: JSON.stringify({
          game: "neon-runner",
          session_token: state.sessionToken,
          score: Math.floor(state.score),
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.message || "Score could not be verified.");
      setStatus("SCORE / LOCKED", "success");
      if (gameMessage) gameMessage.textContent = `${result.message || "Run secured."} +${result.xp_awarded || 0} XP.`;
      await loadLeaderboard();
    } catch (error) {
      setStatus("SCORE / RETRY NEEDED", "error");
      if (gameMessage) gameMessage.textContent = error.message;
    } finally {
      if (startButton) {
        startButton.disabled = false;
        startButton.textContent = "Run again ↗";
      }
      if (gameOverlay) gameOverlay.hidden = false;
    }
  }

  function finishGame(message) {
    if (state.ending || !state.running) return;
    state.ending = true;
    state.running = false;
    state.paused = false;
    window.cancelAnimationFrame(state.animationFrame);
    pauseButton.disabled = true;
    pauseButton.textContent = "Pause";
    setStatus("RUN COMPLETE / PENDING SCORE", "pending");
    overlayKicker.textContent = "RUN COMPLETE";
    overlayTitle.textContent = "Signal\nsecured.";
    overlayCopy.textContent = message || "Your run ended. Secure the score to log it on the board.";
    submitScore();
  }

  async function startGame() {
    if (state.starting || state.running) return;
    state.starting = true;
    startButton.disabled = true;
    startButton.textContent = "Opening channel…";
    setStatus("SESSION / OPENING", "pending");
    if (gameMessage) gameMessage.textContent = "Opening a short server-tracked play session…";
    try {
      state.sessionToken = await startSession();
      state.running = true;
      state.paused = false;
      state.ending = false;
      state.scoreSubmitted = false;
      state.startedAt = performance.now();
      state.elapsed = 0;
      state.score = 0;
      state.distance = 0;
      state.lastFrame = 0;
      state.spawnClock = 0;
      state.obstacles = [];
      state.player.x = width / 2 - state.player.width / 2;
      gameOverlay.hidden = true;
      pauseButton.disabled = false;
      pauseButton.textContent = "Pause";
      setStatus("RUNNING / LIVE", "success");
      if (gameMessage) gameMessage.textContent = "Dodge the static and stay in the lane.";
      setScoreboard();
      window.cancelAnimationFrame(state.animationFrame);
      state.animationFrame = window.requestAnimationFrame(loop);
    } catch (error) {
      setStatus("SESSION / FAILED", "error");
      if (gameMessage) gameMessage.textContent = error.message;
      startButton.disabled = false;
      startButton.textContent = "Start run ↗";
    } finally {
      state.starting = false;
    }
  }

  function togglePause() {
    if (!state.running) return;
    state.paused = !state.paused;
    pauseButton.textContent = state.paused ? "Resume" : "Pause";
    setStatus(state.paused ? "RUN PAUSED" : "RUNNING / LIVE", state.paused ? "pending" : "success");
  }

  function toggleSound() {
    const enabled = soundButton.getAttribute("aria-pressed") === "true";
    soundButton.setAttribute("aria-pressed", String(!enabled));
    soundButton.textContent = `Sound: ${enabled ? "off" : "on"}`;
  }

  function bindHoldButton(button, key, direction) {
    if (!button) return;
    button.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      keys.add(key);
      move(direction);
    });
    ["pointerup", "pointercancel", "pointerleave"].forEach((eventName) => {
      button.addEventListener(eventName, () => keys.delete(key));
    });
    button.addEventListener("click", () => move(direction));
  }

  function onKeyDown(event) {
    if (["ArrowLeft", "ArrowRight", "a", "d", "A", "D", " "].includes(event.key)) {
      event.preventDefault();
    }
    if (event.key === " ") {
      togglePause();
      return;
    }
    const key = event.key.toLowerCase();
    if (key === "a" || event.key === "ArrowLeft") keys.add(event.key === "ArrowLeft" ? "ArrowLeft" : "a");
    if (key === "d" || event.key === "ArrowRight") keys.add(event.key === "ArrowRight" ? "ArrowRight" : "d");
  }

  function onKeyUp(event) {
    keys.delete(event.key);
    keys.delete(event.key.toLowerCase());
  }

  function renderLeaderboard(entries) {
    if (!leaderboard) return;
    leaderboard.replaceChildren();
    if (!entries?.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state compact-empty";
      const mark = document.createElement("span");
      mark.textContent = "⌁";
      const title = document.createElement("strong");
      title.textContent = "Board is open.";
      const copy = document.createElement("p");
      copy.textContent = "Be the first player to lock in a score.";
      empty.append(mark, title, copy);
      leaderboard.append(empty);
      return;
    }
    entries.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "leaderboard-row";
      const rank = document.createElement("span");
      rank.textContent = `#${entry.rank}`;
      const name = document.createElement("strong");
      name.textContent = entry.name || "Anonymous player";
      const score = document.createElement("b");
      score.textContent = String(Number(entry.score) || 0);
      row.append(rank, name, score);
      leaderboard.append(row);
    });
  }

  async function loadLeaderboard() {
    try {
      const response = await fetch("/api/leaderboard?game=neon-runner", { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("Leaderboard unavailable.");
      const result = await response.json();
      renderLeaderboard(result.entries);
    } catch (_error) {
      if (gameMessage) gameMessage.textContent = "Run saved locally; the board is temporarily unavailable.";
    }
  }

  startButton?.addEventListener("click", startGame);
  pauseButton?.addEventListener("click", togglePause);
  soundButton?.addEventListener("click", toggleSound);
  window.addEventListener("keydown", onKeyDown);
  window.addEventListener("keyup", onKeyUp);
  bindHoldButton(leftButton, "touch-left", -1);
  bindHoldButton(rightButton, "touch-right", 1);
  window.addEventListener("pagehide", () => {
    state.running = false;
    window.cancelAnimationFrame(state.animationFrame);
    window.removeEventListener("keydown", onKeyDown);
    window.removeEventListener("keyup", onKeyUp);
  }, { once: true });

  setScoreboard();
  draw();
  loadLeaderboard();
})();
