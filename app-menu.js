// Shared small-screen account menu for Home and Explore.
const appMenuButton = document.getElementById('app-menu-button');
const appMenuPanel = document.getElementById('app-menu-panel');
appMenuButton?.addEventListener('click', () => {
  const opening = appMenuPanel.hidden;
  appMenuPanel.hidden = !opening;
  appMenuButton.setAttribute('aria-expanded', String(opening));
});
document.addEventListener('click', (event) => {
  if (appMenuPanel && !appMenuPanel.hidden && !appMenuPanel.contains(event.target) && !appMenuButton.contains(event.target)) {
    appMenuPanel.hidden = true;
    appMenuButton.setAttribute('aria-expanded', 'false');
  }
});
