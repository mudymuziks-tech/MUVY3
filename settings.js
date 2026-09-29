// Settings navigation menu for phone and tablet headers.
const menuButton = document.getElementById('settings-menu-button');
const menuPanel = document.getElementById('settings-menu-panel');
menuButton.addEventListener('click', () => {
  const opening = menuPanel.hidden;
  menuPanel.hidden = !opening;
  menuButton.setAttribute('aria-expanded', String(opening));
});
document.addEventListener('click', (event) => {
  if (!menuPanel.hidden && !menuPanel.contains(event.target) && !menuButton.contains(event.target)) {
    menuPanel.hidden = true;
    menuButton.setAttribute('aria-expanded', 'false');
  }
});
