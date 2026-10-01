// EARLY THEME SETUP: apply the saved theme before stylesheets render to prevent a color flash.
try {
  document.documentElement.dataset.theme = localStorage.getItem('muvy-theme') === 'light' ? 'light' : 'dark';
} catch {
  // Use dark mode when browser storage is unavailable.
  document.documentElement.dataset.theme = 'dark';
}
