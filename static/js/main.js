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
// Prevent duplicate form submissions
let isSubmitting = false;

// Signup Form Handler
document.addEventListener('DOMContentLoaded', function() {
    const signupForm = document.querySelector('.signup-form');
    
    if (signupForm) {
        signupForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Prevent duplicate submissions
            if (isSubmitting) {
                console.log('Already submitting, ignoring...');
                return;
            }
            
            isSubmitting = true;
            
            // Get form elements
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            
            // Disable button and show loading
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating Account...';
            
            // Get form data
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            // Get CSRF token if using Flask-WTF
            const csrfToken = this.querySelector('[name="csrf_token"]')?.value;
            
            try {
                const response = await fetch('/signup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken || ''
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    // Show success message
                    showToast('Account created successfully! Redirecting...', 'success');
                    
                    // Redirect after short delay
                    setTimeout(() => {
                        window.location.href = result.redirect_url || '/login';
                    }, 1500);
                } else {
                    // Show error
                    showToast(result.error || 'Signup failed. Please try again.', 'error');
                    
                    // Re-enable button
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                }
            } catch (error) {
                console.error('Signup error:', error);
                showToast('Network error. Please check your connection.', 'error');
                
                // Re-enable button
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            } finally {
                // Reset submission flag after delay
                setTimeout(() => {
                    isSubmitting = false;
                }, 2000);
            }
        });
    }
    
    // Login Form Handler (same pattern)
    const loginForm = document.querySelector('.login-form');
    
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (isSubmitting) return;
            isSubmitting = true;
            
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Logging in...';
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            const csrfToken = this.querySelector('[name="csrf_token"]')?.value;
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken || ''
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showToast('Login successful! Redirecting...', 'success');
                    setTimeout(() => {
                        window.location.href = result.redirect_url || '/';
                    }, 1500);
                } else {
                    showToast(result.error || 'Login failed. Please check your credentials.', 'error');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                }
            } catch (error) {
                showToast('Network error. Please try again.', 'error');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            } finally {
                setTimeout(() => {
                    isSubmitting = false;
                }, 2000);
            }
        });
    }
});

// Toast notification function
function showToast(message, type = 'info') {
    // Remove existing toasts
    document.querySelectorAll('.toast-notification').forEach(t => t.remove());
    
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    // Add styles if not already present
    if (!document.getElementById('toast-styles')) {
        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.textContent = `
            .toast-notification {
                position: fixed;
                bottom: 20px;
                right: 20px;
                padding: 1rem 1.5rem;
                border-radius: 8px;
                color: white;
                display: flex;
                align-items: center;
                gap: 0.75rem;
                animation: slideInRight 0.3s ease;
                z-index: 9999;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            .toast-success { background: linear-gradient(135deg, #10b981, #059669); }
            .toast-error { background: linear-gradient(135deg, #ef4444, #dc2626); }
            .toast-info { background: linear-gradient(135deg, #3b82f6, #2563eb); }
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(toast);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
// Add at the top of your form handlers
let isSubmitting = false;

function handleFormSubmit(formElement) {
    if (isSubmitting) {
        return false; // Prevent duplicate
    }
    isSubmitting = true;
    
    // Disable button
    const btn = formElement.querySelector('button[type="submit"]');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    }
    
    // Your existing AJAX code here...
    
    // Reset on completion (success or error)
    setTimeout(() => {
        isSubmitting = false;
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = 'Sign Up';
        }
    }, 2000);
}
// Global loading overlay
function showLoading() {
    const overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading-spinner">
            <i class="fas fa-circle-notch fa-spin fa-3x"></i>
            <p>Loading...</p>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.remove();
}

// Empty states
function showEmptyState(container, message, icon = 'inbox') {
    container.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-${icon} fa-3x text-muted mb-3"></i>
            <p class="text-muted">${message}</p>
        </div>
    `;
}

// Toast notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.remove(), 3000);
}
