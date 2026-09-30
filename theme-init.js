// Apply the saved theme before stylesheets render, avoiding a dark-to-light flash.
try {
  document.documentElement.dataset.theme = localStorage.getItem('muvy-theme') === 'light' ? 'light' : 'dark';
} catch {
  document.documentElement.dataset.theme = 'dark';
}
