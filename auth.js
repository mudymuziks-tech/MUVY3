// AUTH: temporary browser-only sign-in for the static prototype; passwords are never stored.
(() => {
  const sessionKey = 'muvyLocalSession';
  const sessionDurationMs = 8 * 60 * 60 * 1000;
  const protectedPages = new Set(['home.html', 'explore.html', 'recognize.html', 'watchlist.html', 'genres.html', 'settings.html', 'profile.html']);

  // STORAGE: prefer local storage, with session storage as a fallback.
  function getStore() {
    try {
      localStorage.setItem('__muvy_storage_check__', '1');
      localStorage.removeItem('__muvy_storage_check__');
      return localStorage;
    } catch {
      return sessionStorage;
    }
  }

  // SESSION: read, expire, and clear the signed-in account details.
  const store = getStore();
  function getSession() {
    try {
      const session = JSON.parse(store.getItem(sessionKey) || 'null');
      if (!session || !session.email || !session.expiresAt || session.expiresAt <= Date.now()) {
        store.removeItem(sessionKey);
        return null;
      }
      return session;
    } catch {
      store.removeItem(sessionKey);
      return null;
    }
  }

  function clearSession() {
    store.removeItem(sessionKey);
    try { sessionStorage.removeItem('muvyActiveNav'); } catch {}
  }

  // ACCESS CONTROL: process logout and protect app pages from signed-out visits.
  const url = new URL(window.location.href);
  if (url.searchParams.has('logout')) {
    clearSession();
    url.searchParams.delete('logout');
    window.history.replaceState({}, '', url);
  }

  const currentPage = window.location.pathname.split('/').pop().toLowerCase();
  if (protectedPages.has(currentPage) && !getSession()) {
    window.location.replace('login.html');
    return;
  }

  window.MUVYAuth = { getSession, clearSession };
  const session = getSession();
  document.querySelectorAll('[data-premium-upsell]').forEach((upsell) => {
    upsell.hidden = session?.isPremium === true;
  });

  // LOGIN AND SIGN-UP FORM: switch modes and update the matching fields and copy.
  const form = document.getElementById('auth-form');
  if (!form) return;

  const tabs = document.querySelectorAll('.auth-tab');
  const nameField = document.getElementById('name-field');
  const nameInput = document.getElementById('name');
  const passwordInput = document.getElementById('password');
  const confirmPasswordField = document.getElementById('confirm-password-field');
  const confirmPasswordInput = document.getElementById('confirm-password');
  const emailInput = document.getElementById('email');
  const title = document.getElementById('auth-title');
  const description = document.getElementById('auth-description');
  const submit = document.getElementById('auth-submit');
  const message = document.getElementById('auth-message');
  let mode = 'login';

  function setMode(nextMode) {
    mode = nextMode === 'signup' ? 'signup' : 'login';
    const signingUp = mode === 'signup';
    nameField.hidden = !signingUp;
    nameInput.required = signingUp;
    confirmPasswordField.hidden = !signingUp;
    confirmPasswordInput.required = signingUp;
    passwordInput.autocomplete = signingUp ? 'new-password' : 'current-password';
    confirmPasswordInput.autocomplete = 'new-password';
    confirmPasswordInput.setCustomValidity('');
    title.textContent = signingUp ? 'Make yourself at home.' : 'Welcome back.';
    description.textContent = signingUp
      ? 'Create an account and keep every discovery close.'
      : 'Log in to continue discovering what to watch.';
    submit.textContent = signingUp ? 'Create account' : 'Log in';
    message.textContent = '';
    tabs.forEach((tab) => {
      const active = tab.dataset.mode === mode;
      tab.classList.toggle('is-active', active);
      tab.setAttribute('aria-pressed', String(active));
    });
    document.title = signingUp ? 'Sign up for MUVY' : 'Log in to MUVY';
  }

  tabs.forEach((tab) => tab.addEventListener('click', () => setMode(tab.dataset.mode)));
  // SIGN-UP VALIDATION: confirm password is required only in account creation mode.
  function validatePasswordConfirmation() {
    if (mode !== 'signup' || !confirmPasswordInput.value) {
      confirmPasswordInput.setCustomValidity('');
      return;
    }
    confirmPasswordInput.setCustomValidity(
      passwordInput.value === confirmPasswordInput.value ? '' : 'Passwords do not match.'
    );
  }
  passwordInput.addEventListener('input', validatePasswordConfirmation);
  confirmPasswordInput.addEventListener('input', validatePasswordConfirmation);
  // FORM SUBMISSION: validate credentials, create the temporary session, then open Home.
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    validatePasswordConfirmation();
    if (!form.reportValidity()) return;

    const email = emailInput.value.trim().toLowerCase();
    let name = mode === 'signup' ? nameInput.value.trim() : '';
    if (!name) {
      const previous = getSession();
      name = previous?.email === email && previous.name
        ? previous.name
        : email.split('@')[0].replace(/[._-]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
    }

    const session = { name, email, expiresAt: Date.now() + sessionDurationMs };
    try {
      store.setItem(sessionKey, JSON.stringify(session));
      message.textContent = 'Signed in on this device. Opening MUVY…';
      window.location.assign('home.html');
    } catch {
      message.textContent = 'Browser storage is unavailable. Allow local storage, then try again.';
    }
  });

  setMode(window.location.hash === '#signup' ? 'signup' : 'login');
})();
