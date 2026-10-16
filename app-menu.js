// HOME MENU: position the panel beneath the hamburger that controls it.
const appMenuButton = document.getElementById('app-menu-button');
const appMenuPanel = document.getElementById('app-menu-panel');
const appMenuClose = document.getElementById('app-menu-close');

function positionAppMenu() {
  if (!appMenuButton || !appMenuPanel || appMenuPanel.hidden) return;
  const buttonBounds = appMenuButton.getBoundingClientRect();
  appMenuPanel.style.left = '0px';
  appMenuPanel.style.right = 'auto';
  appMenuPanel.style.top = `${buttonBounds.bottom + 8}px`;
}

// HOME MENU CONTROLS: toggle, close on outside click, and reposition after resize.
appMenuButton?.addEventListener('click', () => {
  const opening = appMenuPanel.hidden;
  appMenuPanel.hidden = !opening;
  appMenuButton.setAttribute('aria-expanded', String(opening));
  if (opening) positionAppMenu();
});
appMenuClose?.addEventListener('click', () => {
  appMenuPanel.hidden = true;
  appMenuButton?.setAttribute('aria-expanded', 'false');
});
document.addEventListener('click', (event) => {
  if (appMenuPanel && appMenuButton && !appMenuPanel.hidden && !appMenuPanel.contains(event.target) && !appMenuButton.contains(event.target)) {
    appMenuPanel.hidden = true;
    appMenuButton.setAttribute('aria-expanded', 'false');
  }
});
window.addEventListener('resize', positionAppMenu);
