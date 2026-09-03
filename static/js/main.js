const loginModal = document.getElementById("loginModal");
const openLogin = document.getElementById("openLogin");
const closeLogin = document.getElementById("closeLogin");
const loginForm = document.getElementById("loginForm");
const loginStatus = document.getElementById("loginStatus");
const passwordInput = document.getElementById("loginPassword");
const togglePassword = document.getElementById("togglePassword");

function showLogin() {
    loginModal.hidden = false;
    document.body.classList.add("modal-open");
}

function hideLogin() {
    loginModal.hidden = true;
    document.body.classList.remove("modal-open");
}

openLogin.addEventListener("click", showLogin);
closeLogin.addEventListener("click", hideLogin);

loginModal.addEventListener("click", function(event) {
    if (event.target === loginModal) {
        hideLogin();
    }
});

togglePassword.addEventListener("click", function() {
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        togglePassword.textContent = "HIDE";
    } else {
        passwordInput.type = "password";
        togglePassword.textContent = "SHOW";
    }
});

loginForm.addEventListener("submit", async function(event) {
    event.preventDefault();

    loginStatus.textContent = "AUTHENTICATING...";

    const email = document.getElementById("loginEmail").value;
    const password = passwordInput.value;

    const response = await fetch("/api/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            email: email,
            password: password
        })
    });

    const result = await response.json();

    if (response.ok) {
        loginStatus.textContent = result.message;
        loginStatus.className = "login-status success";
    } else {
        loginStatus.textContent = result.message;
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
  }
});
const signupModal = document.getElementById("signupModal");
const openSignup = document.getElementById("openSignup");
const closeSignup = document.getElementById("closeSignup");
const signupForm = document.getElementById("signupForm");
const signupStatus = document.getElementById("signupStatus");

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

signupModal?.addEventListener("click", (event) => {
  if (event.target === signupModal) {
    hideSignup();
  }
});

signupForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  const name = document.getElementById("signupName").value.trim();
  const email = document.getElementById("signupEmail").value.trim();
  const password = document.getElementById("signupPassword").value;
  const confirmPassword = document.getElementById("signupConfirm").value;
  const turnstileToken = signupForm.querySelector(
    'input[name="cf-turnstile-response"]'
  )?.value;

  if (password !== confirmPassword) {
    signupStatus.textContent = "Passwords do not match.";
    return;
  }

  if (!turnstileToken) {
    signupStatus.textContent = "Please complete the security check.";
    return;
  }

  signupStatus.textContent = "CREATING ACCOUNT...";
  signupStatus.className = "login-status";

  try {
    const response = await fetch("/api/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        name,
        email,
        password,
        confirm_password: confirmPassword,
        turnstile_token: turnstileToken
      })
    });

    const result = await response.json();

    signupStatus.textContent =
      result.message || "Account created successfully.";

    if (response.ok) {
      signupStatus.className = "login-status success";
      signupForm.reset();

      if (window.turnstile) {
        window.turnstile.reset();
      }
    } else {
      signupStatus.className = "login-status";
    }
  } catch (error) {
    signupStatus.textContent = "Network error. Please try again.";
    signupStatus.className = "login-status";
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && signupModal && !signupModal.hidden) {
    hideSignup();
  }
});
