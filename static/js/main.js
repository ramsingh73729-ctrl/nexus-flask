const loginModal = document.getElementById("loginModal");
const openLogin = document.getElementById("openLogin");
const closeLogin = document.getElementById("closeLogin");
const loginForm = document.getElementById("loginForm");
const loginStatus = document.getElementById("loginStatus");
const passwordInput = document.getElementById("loginPassword");
const togglePassword = document.getElementById("togglePassword");
const loginSubmit = document.getElementById("loginSubmit");
const signupPrompt = document.getElementById("signupPrompt");
const accessToast = document.getElementById("accessToast");

let loginSubmitting = false;
let signupSubmitting = false;

function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || "";
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
}

function hideLogin() {
    if (!loginModal) return;

    loginModal.hidden = true;
    document.body.classList.remove("modal-open");
}

openLogin?.addEventListener("click", showLogin);
closeLogin?.addEventListener("click", hideLogin);

loginModal?.addEventListener("click", function(event) {
    if (event.target === loginModal) {
        hideLogin();
    }
});

togglePassword?.addEventListener("click", function() {
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        togglePassword.textContent = "HIDE";
        togglePassword.setAttribute("aria-label", "Hide password");
    } else {
        passwordInput.type = "password";
        togglePassword.textContent = "SHOW";
        togglePassword.setAttribute("aria-label", "Show password");
    }
});

loginForm?.addEventListener("submit", async function(event) {
    event.preventDefault();

    if (loginSubmitting) return;
    if (!loginForm.reportValidity()) return;

    loginSubmitting = true;
    loginForm.setAttribute("aria-busy", "true");
    if (loginSubmit) {
        loginSubmit.disabled = true;
        loginSubmit.textContent = "Authenticating…";
    }

    loginStatus.textContent = "AUTHENTICATING...";
    loginStatus.className = "login-status";

    const email = document.getElementById("loginEmail").value;
    const password = passwordInput.value;

    try {
        const response = await fetch("/api/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken()
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        });

        let result = {};
        try {
            result = await response.json();
        } catch (error) {
            result = {};
        }

        loginStatus.textContent = result.message ||
            "Login could not be completed. Please try again.";
        loginStatus.className = response.ok
            ? "login-status success"
            : "login-status";
    } catch (error) {
        loginStatus.textContent = "Network error. Please try again.";
        loginStatus.className = "login-status";
    } finally {
        loginSubmitting = false;
        loginForm.removeAttribute("aria-busy");
        if (loginSubmit) {
            loginSubmit.disabled = false;
            loginSubmit.textContent = "Continue ↗";
        }
    }
});
const menuToggle = document.querySelector(
  ".menu-toggle, #menuToggle, [data-menu-toggle]"
);
const navLinks = document.getElementById("nav-links");

function closeMenu() {
  if (!navLinks) return;
  navLinks.classList.remove("open", "is-open");
  if (menuToggle) {
    menuToggle.setAttribute("aria-expanded", "false");
  }
}

if (menuToggle && navLinks) {
  menuToggle.addEventListener("click", () => {
    const isOpen = !navLinks.classList.contains("open");

    navLinks.classList.toggle("open", isOpen);
    navLinks.classList.toggle("is-open", isOpen);
    menuToggle.setAttribute("aria-expanded", String(isOpen));
  });

  navLinks.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeMenu);
  });
}

document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener("click", (event) => {
    const selector = link.getAttribute("href");

    if (!selector || selector === "#") return;

    const target = document.querySelector(selector);
    if (!target) return;

    event.preventDefault();
    target.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  });
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeMenu();

    if (loginModal && !loginModal.hidden) {
      hideLogin();
    }

    if (signupModal && !signupModal.hidden) {
      hideSignup();
    }
  }
});
const signupModal = document.getElementById("signupModal");
const openSignup = document.getElementById("openSignup");
const closeSignup = document.getElementById("closeSignup");
const signupForm = document.getElementById("signupForm");
const signupStatus = document.getElementById("signupStatus");
const signupSubmit = document.getElementById("signupSubmit");

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

openSignup?.addEventListener("click", showSignup);
closeSignup?.addEventListener("click", hideSignup);
signupPrompt?.addEventListener("click", showSignup);

signupModal?.addEventListener("click", (event) => {
  if (event.target === signupModal) {
    hideSignup();
  }
});

signupForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (signupSubmitting) return;

  const nameInput = document.getElementById("signupName");
  const emailInput = document.getElementById("signupEmail");
  const passwordInput = document.getElementById("signupPassword");
  const confirmInput = document.getElementById("signupConfirm");
  const name = nameInput.value.trim();
  const email = emailInput.value.trim();
  const password = passwordInput.value;
  const confirmPassword = confirmInput.value;
  const turnstileToken = signupForm.querySelector(
    'input[name="cf-turnstile-response"]'
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
  if (signupSubmit) {
    signupSubmit.disabled = true;
    signupSubmit.textContent = "Creating account…";
  }

  let tokenSubmitted = false;

  try {
    tokenSubmitted = true;
    const response = await fetch("/api/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken()
      },
      body: JSON.stringify({
        name,
        email,
        password,
        confirm_password: confirmPassword,
        turnstile_token: turnstileToken
      })
    });

    let result = {};
    try {
      result = await response.json();
    } catch (error) {
      result = {};
    }

    const message = typeof result.message === "string" && result.message
      ? result.message
      : response.ok
        ? "Account created successfully."
        : "Signup could not be completed. Please try again.";

    signupStatus.textContent = "";
    showAccessToast(message, response.ok ? "success" : "error");

    if (response.ok) {
      signupForm.reset();
    }
  } catch (error) {
    signupStatus.textContent = "";
    showAccessToast("Network error. Please try again.", "error");
  } finally {
    if (tokenSubmitted && window.turnstile?.reset) {
      window.turnstile.reset();
    }

    signupSubmitting = false;
    signupForm.removeAttribute("aria-busy");
    if (signupSubmit) {
      signupSubmit.disabled = false;
      signupSubmit.textContent = "Create account";
    }
  }
});
