import { animate, inView, stagger } from "https://cdn.jsdelivr.net/npm/motion@latest/+esm";

const menuButton = document.querySelector(".menu-toggle");
const navLinks = document.querySelector(".nav-links");

menuButton?.addEventListener("click", () => {
  const isOpen = menuButton.getAttribute("aria-expanded") === "true";
  menuButton.setAttribute("aria-expanded", String(!isOpen));
  menuButton.setAttribute("aria-label", isOpen ? "Open menu" : "Close menu");
  navLinks?.classList.toggle("is-open", !isOpen);
});

navLinks?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => {
  menuButton?.setAttribute("aria-expanded", "false");
  navLinks.classList.remove("is-open");
}));

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (!reduceMotion) {
  animate(".hero-copy .eyebrow, .hero-copy h1, .hero-copy .hero-text, .hero-copy .hero-actions, .hero-copy .hero-proof", { opacity: [0, 1], y: [20, 0] }, { delay: stagger(0.1), duration: 0.7, ease: [0.22, 1, 0.36, 1] });
  animate(".hero-visual", { opacity: [0, 1], scale: [0.88, 1], rotate: [-3, 0] }, { duration: 1.1, delay: 0.15, ease: [0.22, 1, 0.36, 1] });
  animate(".orbit-a", { rotate: 360 }, { duration: 25, repeat: Infinity, ease: "linear" });
  animate(".orbit-b", { rotate: -360 }, { duration: 19, repeat: Infinity, ease: "linear" });
  animate(".chip-one", { y: [0, -9, 0] }, { duration: 4, repeat: Infinity, ease: "easeInOut" });
  animate(".chip-two", { y: [0, 10, 0] }, { duration: 3.5, repeat: Infinity, ease: "easeInOut", delay: 0.35 });
  animate(".download-disc", { rotateZ: [0, 8, 0] }, { duration: 5, repeat: Infinity, ease: "easeInOut" });
  animate(".pulse-graph i", { scaleY: [0.45, 1, 0.6, 0.9] }, { duration: 1.8, repeat: Infinity, delay: stagger(0.08), ease: "easeInOut" });
}

document.querySelectorAll(".reveal").forEach((element) => {
  if (reduceMotion) {
    element.classList.add("is-visible");
    return;
  }
  inView(element, () => {
    animate(element, { opacity: [0, 1], y: [22, 0] }, { duration: 0.65, ease: [0.22, 1, 0.36, 1] });
  });
});

const games = JSON.parse(document.querySelector("#game-data")?.textContent || "[]");
const featuredArt = document.querySelector("#featured-art");
const featuredMeta = document.querySelector("#featured-meta");
const gameTitle = document.querySelector("#game-title");
const gameDescription = document.querySelector("#game-description");
const gameGenre = document.querySelector("#game-genre");
const gameEyebrow = document.querySelector("#game-eyebrow");
const gamePlayers = document.querySelector("#game-players");
const progressFill = document.querySelector("#progress-fill");
const thumbnails = [...document.querySelectorAll(".game-thumb")];
let activeGame = 0;

function renderGame(index) {
  if (!games.length) return;
  activeGame = (index + games.length) % games.length;
  const game = games[activeGame];
  featuredArt.className = `game-art ${game.art_class}`;
  featuredArt.innerHTML = `<div class="art-grid"></div><div class="art-glow"></div><div class="art-orb"></div><div class="art-ring"></div><div class="art-scanline"></div><span class="art-coordinates">44° 07' / 09° 31'</span><span class="art-label">NXS // ${game.title.split(" ")[0]}</span><strong class="art-title">${game.title}</strong>`;
  gameTitle.textContent = game.title;
  gameDescription.textContent = game.description;
  gameGenre.textContent = game.genre.toUpperCase();
  gameEyebrow.textContent = game.eyebrow.toUpperCase();
  gamePlayers.textContent = `${game.players} ONLINE`;
  thumbnails.forEach((thumbnail, thumbnailIndex) => thumbnail.classList.toggle("active", thumbnailIndex === activeGame));
  progressFill.style.width = `${((activeGame + 1) / games.length) * 100}%`;
  if (!reduceMotion) {
    animate(featuredArt, { opacity: [0, 1], scale: [0.98, 1] }, { duration: 0.45, ease: [0.22, 1, 0.36, 1] });
    animate(featuredMeta, { opacity: [0.4, 1], y: [7, 0] }, { duration: 0.35 });
  }
}

thumbnails.forEach((thumbnail) => thumbnail.addEventListener("click", () => renderGame(Number(thumbnail.dataset.index))));
document.querySelector("#prev-game")?.addEventListener("click", () => renderGame(activeGame - 1));
document.querySelector("#next-game")?.addEventListener("click", () => renderGame(activeGame + 1));
window.setInterval(() => renderGame(activeGame + 1), 6500);

const modal = document.querySelector("#trailer-modal");
const openModal = () => { modal.hidden = false; document.body.classList.add("modal-open"); };
const closeModal = () => { modal.hidden = true; document.body.classList.remove("modal-open"); };
document.querySelector(".trailer-button")?.addEventListener("click", openModal);
document.querySelector(".modal-close")?.addEventListener("click", closeModal);
modal?.addEventListener("click", (event) => { if (event.target === modal) closeModal(); });
window.addEventListener("keydown", (event) => { if (event.key === "Escape") closeModal(); });

document.querySelector(".download-button")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  const status = document.querySelector(".download-status");
  button.disabled = true;
  status.textContent = "Preparing your portal...";
  try {
    const response = await fetch("/api/download", { method: "POST" });
    const result = await response.json();
    status.textContent = response.ok ? result.message : "Download is temporarily unavailable.";
  } catch (_error) {
    status.textContent = "Download is ready — connect your launcher to continue.";
  } finally {
    button.disabled = false;
  }
});
