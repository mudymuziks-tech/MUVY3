// THEME STORAGE: read the saved preference, defaulting to dark mode.
let savedTheme = 'dark';
try {
  savedTheme = localStorage.getItem('muvy-theme') === 'light' ? 'light' : 'dark';
} catch {
  // Keep the default dark theme if browser storage is unavailable.
}
document.documentElement.dataset.theme = savedTheme;

// THEME CONTROLS: keep each toggle's state, label, and icon in sync.
const themeToggles = document.querySelectorAll('#theme-toggle, [data-theme-toggle]');
function updateThemeControls(theme) {
  themeToggles.forEach((toggle) => {
    if (toggle.type === 'checkbox') {
      toggle.checked = theme === 'light';
      return;
    }
    const useLight = theme !== 'light';
    const icon = toggle.querySelector('img');
    toggle.setAttribute('aria-pressed', String(!useLight));
    const label = useLight ? 'Switch to light mode' : 'Switch to dark mode';
    toggle.setAttribute('aria-label', window.MUVYLocale?.t(label) ?? label);
    if (icon) icon.src = useLight
      ? 'images/nav%20tools/light_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg'
      : 'images/nav%20tools/dark_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg';
  });
}
updateThemeControls(savedTheme);
// APPLY THEME: update the page immediately and persist the preference.
function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  updateThemeControls(theme);
  try {
    localStorage.setItem('muvy-theme', theme);
  } catch {
    // The current page still changes theme even when persistence is unavailable.
  }
}

// THEME EVENTS: support both switch controls and icon buttons.
themeToggles.forEach((themeToggle) => {
  if (themeToggle.type === 'checkbox') {
    themeToggle.addEventListener('change', () => setTheme(themeToggle.checked ? 'light' : 'dark'));
  } else {
    themeToggle.addEventListener('click', () => {
      setTheme(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light');
    });
  }
});
