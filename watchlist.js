// WATCHLIST: toast feedback for placeholder actions.
const toast = document.getElementById('watchlist-toast');
let toastTimeout;
function showToast(message) {
  toast.textContent = window.MUVYLocale?.t(message) ?? message;
  toast.classList.add('visible');
  window.clearTimeout(toastTimeout);
  toastTimeout = window.setTimeout(() => toast.classList.remove('visible'), 3000);
}

document.querySelectorAll('[data-message]').forEach((button) => {
  button.addEventListener('click', () => showToast(button.dataset.message));
});

// WATCHLIST TABS: switch between the saved list and recently viewed titles.
const myListTab = document.getElementById('my-list-tab');
const recentTab = document.getElementById('recent-tab');
const myList = document.getElementById('my-list');
const recentList = document.getElementById('recent-list');
function selectList(showRecent) {
  myList.hidden = showRecent;
  recentList.hidden = !showRecent;
  myListTab.classList.toggle('selected', !showRecent);
  recentTab.classList.toggle('selected', showRecent);
  myListTab.setAttribute('aria-selected', String(!showRecent));
  recentTab.setAttribute('aria-selected', String(showRecent));
}
myListTab.addEventListener('click', () => selectList(false));
recentTab.addEventListener('click', () => selectList(true));

// WATCHLIST MENU: toggle the mobile menu and dismiss it when clicking outside.
const menuButton = document.getElementById('watchlist-menu-button');
const mobileMenu = document.getElementById('watchlist-mobile-menu');
menuButton.addEventListener('click', () => {
  const opening = mobileMenu.hidden;
  mobileMenu.hidden = !opening;
  menuButton.setAttribute('aria-expanded', String(opening));
});
document.addEventListener('click', (event) => {
  if (!mobileMenu.hidden && !mobileMenu.contains(event.target) && !menuButton.contains(event.target)) {
    mobileMenu.hidden = true;
    menuButton.setAttribute('aria-expanded', 'false');
  }
});
