const loginModal = document.getElementById("loginModal");
const openLogin = document.getElementById("openLogin");
const closeLogin = document.getElementById("closeLogin");
const loginForm = document.getElementById("loginForm");
const loginStatus = document.getElementById("loginStatus");
const loginPassword = document.getElementById("loginPassword");
const togglePassword = document.getElementById("togglePassword");
const loginSubmit = document.getElementById("loginSubmit");
const signupModal = document.getElementById("signupModal");
const openSignup = document.getElementById("openSignup");
const closeSignup = document.getElementById("closeSignup");
const signupPrompt = document.getElementById("signupPrompt");
const signupForm = document.getElementById("signupForm");
const signupStatus = document.getElementById("signupStatus");
const signupSubmit = document.getElementById("signupSubmit");
const accessToast = document.getElementById("accessToast");

let loginSubmitting = false;
let signupSubmitting = false;
let loginRedirecting = false;

function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || "";
}

function resetSignupTurnstile() {
  if (window.turnstile?.reset) window.turnstile.reset();
}

function showAccessToast(message, type = "error") {
  if (!accessToast) return;
  accessToast.textContent = message;
  accessToast.className = `toast access-toast toast-${type}`;
  accessToast.hidden = false;
}

function showLogin() {
  if (!loginModal) return;
  loginModal.hidden = false;
  document.body.classList.add("modal-open");
  document.getElementById("loginEmail")?.focus();
}

function hideLogin() {
  if (!loginModal) return;
  loginModal.hidden = true;
  document.body.classList.remove("modal-open");
}

function showSignup() {
  if (!signupModal) return;
  hideLogin();
  signupModal.hidden = false;
  document.body.classList.add("modal-open");
  document.getElementById("signupName")?.focus();
}

function hideSignup() {
  if (!signupModal) return;
  signupModal.hidden = true;
  document.body.classList.remove("modal-open");
}

openLogin?.addEventListener("click", showLogin);
closeLogin?.addEventListener("click", hideLogin);
openSignup?.addEventListener("click", showSignup);
closeSignup?.addEventListener("click", hideSignup);
signupPrompt?.addEventListener("click", showSignup);

loginModal?.addEventListener("click", (event) => {
  if (event.target === loginModal) hideLogin();
});

signupModal?.addEventListener("click", (event) => {
  if (event.target === signupModal) hideSignup();
});

togglePassword?.addEventListener("click", () => {
  const isPassword = loginPassword?.type === "password";
  if (!loginPassword) return;
  loginPassword.type = isPassword ? "text" : "password";
  togglePassword.textContent = isPassword ? "HIDE" : "SHOW";
  togglePassword.setAttribute(
    "aria-label",
    isPassword ? "Hide password" : "Show password",
  );
});

loginForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (loginSubmitting || loginRedirecting) return;
  if (!loginForm.reportValidity()) return;

  loginSubmitting = true;
  loginForm.setAttribute("aria-busy", "true");
  loginSubmit?.setAttribute("aria-disabled", "true");
  if (loginSubmit) {
    loginSubmit.disabled = true;
    loginSubmit.textContent = "Authenticating…";
  }
  loginStatus.textContent = "AUTHENTICATING...";
  loginStatus.className = "login-status";

  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        email: document.getElementById("loginEmail").value.trim(),
        password: loginPassword.value,
      }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      loginStatus.textContent = result.message || "Login could not be completed.";
      return;
    }

    loginStatus.textContent = result.message || "Access granted.";
    loginStatus.className = "login-status success";
    loginRedirecting = true;
    window.location.assign("/dashboard");
  } catch (_error) {
    loginStatus.textContent = "Network error. Please try again.";
  } finally {
    loginSubmitting = false;
    loginForm.removeAttribute("aria-busy");
    loginSubmit?.removeAttribute("aria-disabled");
    if (loginSubmit && !loginRedirecting) {
      loginSubmit.disabled = false;
      loginSubmit.textContent = "Continue ↗";
    }
  }
});

signupForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (signupSubmitting) return;

  const nameInput = document.getElementById("signupName");
  const emailInput = document.getElementById("signupEmail");
  const passwordInput = document.getElementById("signupPassword");
  const confirmInput = document.getElementById("signupConfirm");
  if (!nameInput || !emailInput || !passwordInput || !confirmInput) return;

  const name = nameInput.value.trim();
  const email = emailInput.value.trim();
  const password = passwordInput.value;
  const confirmPassword = confirmInput.value;
  const turnstileToken = signupForm.querySelector(
    'input[name="cf-turnstile-response"]',
  )?.value;

  signupStatus.textContent = "";
  signupStatus.className = "login-status";

  if (!name) {
    signupStatus.textContent = "Please enter your name.";
    nameInput.focus();
    return;
  }
  if (!emailInput.checkValidity()) {
    signupStatus.textContent = "Please enter a valid email address.";
    emailInput.focus();
    return;
  }
  if (password.length < 8) {
    signupStatus.textContent = "Password must be at least 8 characters.";
    passwordInput.focus();
    return;
  }
  if (password !== confirmPassword) {
    signupStatus.textContent = "Passwords do not match.";
    confirmInput.focus();
    return;
  }
  if (!turnstileToken) {
    signupStatus.textContent =
      "Security check failed or expired. Please complete it again.";
    return;
  }

  signupSubmitting = true;
  signupForm.setAttribute("aria-busy", "true");
  signupSubmit?.setAttribute("aria-disabled", "true");
  if (signupSubmit) {
    signupSubmit.disabled = true;
    signupSubmit.textContent = "Creating account…";
  }

  let resetTurnstileAfterRequest = false;
  try {
    const response = await fetch("/api/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        name,
        email,
        password,
        confirm_password: confirmPassword,
        turnstile_token: turnstileToken,
      }),
    });
    const result = await response.json().catch(() => ({}));
    resetTurnstileAfterRequest = result.turnstile_reset === true;
    const message = typeof result.message === "string" && result.message
      ? result.message
      : response.ok
        ? "Account created successfully."
        : "Signup could not be completed. Please try again.";

    showAccessToast(message, response.ok ? "success" : "error");
    if (response.ok) {
      signupForm.reset();
      hideSignup();
    }
  } catch (_error) {
    showAccessToast("Network error. Please try again.", "error");
  } finally {
    if (resetTurnstileAfterRequest) resetSignupTurnstile();
    signupSubmitting = false;
    signupForm.removeAttribute("aria-busy");
    signupSubmit?.removeAttribute("aria-disabled");
    if (signupSubmit) {
      signupSubmit.disabled = false;
      signupSubmit.textContent = "Create account";
    }
  }
});

const menuToggle = document.querySelector(
  ".menu-toggle, #menuToggle, [data-menu-toggle]",
);
const navLinks = document.getElementById("nav-links");

function closeMenu() {
  if (!navLinks) return;
  navLinks.classList.remove("open", "is-open");
  menuToggle?.setAttribute("aria-expanded", "false");
  menuToggle?.setAttribute("aria-label", "Open menu");
}

menuToggle?.addEventListener("click", () => {
  if (!navLinks) return;
  const isOpen = !navLinks.classList.contains("is-open");
  navLinks.classList.toggle("open", isOpen);
  navLinks.classList.toggle("is-open", isOpen);
  menuToggle.setAttribute("aria-expanded", String(isOpen));
  menuToggle.setAttribute("aria-label", isOpen ? "Close menu" : "Open menu");
});

navLinks?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", closeMenu);
});

document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener("click", (event) => {
    const selector = link.getAttribute("href");
    if (!selector || selector === "#") return;
    const target = document.querySelector(selector);
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

const gameData = document.getElementById("game-data");
let games = [];
try {
  games = JSON.parse(gameData?.textContent || "[]");
} catch (_error) {
  games = [];
}

const featuredArt = document.getElementById("featured-art");
const featuredMeta = document.getElementById("featured-meta");
const thumbnails = [...document.querySelectorAll(".game-thumb")];
const progressFill = document.getElementById("progress-fill");
let activeGame = 0;
let carouselTimer = null;
const allowedArtClasses = new Set(["art-rift", "art-chroma", "art-void", "art-echo"]);

function renderGame(index) {
  if (!games.length || !featuredArt) return;
  activeGame = (index + games.length) % games.length;
  const game = games[activeGame];
  const artClass = allowedArtClasses.has(game.art_class) ? game.art_class : "art-rift";
  featuredArt.className = `game-art ${artClass}`;
  featuredArt.querySelector(".art-label").textContent = `NXS // ${game.title.split(" ")[0]}`;
  featuredArt.querySelector(".art-title").textContent = game.title;
  document.getElementById("game-title").textContent = game.title;
  document.getElementById("game-description").textContent = game.description;
  document.getElementById("game-genre").textContent = game.genre.toUpperCase();
  document.getElementById("game-eyebrow").textContent = game.eyebrow.toUpperCase();
  document.getElementById("game-players").textContent = `${game.players} ONLINE`;
  thumbnails.forEach((thumbnail, thumbnailIndex) => {
    thumbnail.classList.toggle("active", thumbnailIndex === activeGame);
  });
  if (progressFill) progressFill.style.width = `${((activeGame + 1) / games.length) * 100}%`;
  featuredMeta?.classList.remove("is-refreshing");
  window.requestAnimationFrame(() => featuredMeta?.classList.add("is-refreshing"));
}

thumbnails.forEach((thumbnail) => {
  thumbnail.addEventListener("click", () => renderGame(Number(thumbnail.dataset.index)));
});
document.getElementById("prev-game")?.addEventListener("click", () => renderGame(activeGame - 1));
document.getElementById("next-game")?.addEventListener("click", () => renderGame(activeGame + 1));
if (games.length && featuredArt) {
  renderGame(0);
  carouselTimer = window.setInterval(() => renderGame(activeGame + 1), 6500);
}

const trailerModal = document.getElementById("trailer-modal");
const trailerClose = trailerModal?.querySelector(".modal-close");
function closeTrailer() {
  if (!trailerModal) return;
  trailerModal.hidden = true;
  document.body.classList.remove("modal-open");
}
document.querySelector(".trailer-button")?.addEventListener("click", () => {
  if (!trailerModal) return;
  trailerModal.hidden = false;
  document.body.classList.add("modal-open");
});
trailerClose?.addEventListener("click", closeTrailer);
trailerModal?.addEventListener("click", (event) => {
  if (event.target === trailerModal) closeTrailer();
});

document.querySelector(".download-button")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  const status = document.querySelector(".download-status");
  button.disabled = true;
  status.textContent = "Preparing your portal...";
  try {
    const response = await fetch("/api/download", {
      method: "POST",
      headers: { "X-CSRFToken": getCsrfToken() },
    });
    const result = await response.json().catch(() => ({}));
    status.textContent = response.ok
      ? result.message
      : "Download is temporarily unavailable.";
  } catch (_error) {
    status.textContent = "Download is temporarily unavailable.";
  } finally {
    button.disabled = false;
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  closeMenu();
  if (loginModal && !loginModal.hidden) hideLogin();
  if (signupModal && !signupModal.hidden) hideSignup();
  if (trailerModal && !trailerModal.hidden) closeTrailer();
});

window.addEventListener("pagehide", () => {
  if (carouselTimer) window.clearInterval(carouselTimer);
});
