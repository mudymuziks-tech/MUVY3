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

// Saved titles from movie profiles are persisted locally and shown at the top of My List.
const savedTitles = (() => {
  try { return JSON.parse(localStorage.getItem('muvy-watchlist') || '[]'); }
  catch { return []; }
})();
if (savedTitles.length) {
  savedTitles.slice().reverse().forEach((movie) => {
    const article = document.createElement('article');
    article.className = 'watchlist-item';
    const image = document.createElement('img');
    image.src = movie.image || '';
    image.alt = `${movie.title} poster`;
    const copy = document.createElement('div');
    copy.className = 'watchlist-item-copy';
    const heading = document.createElement('h2');
    heading.textContent = movie.title;
    const year = document.createElement('p');
    year.textContent = movie.year || (movie.media === 'tv' ? 'TV Series' : '');
    const type = document.createElement('span');
    type.textContent = movie.media === 'tv' ? 'TV Series' : 'Movie';
    copy.append(heading, year, type);
    const open = document.createElement('a');
    open.className = 'item-more';
    open.setAttribute('aria-label', `View ${movie.title}`);
    open.textContent = '›';
    const query = new URLSearchParams({ title: movie.title, image: movie.image || '', year: movie.year || '', media: movie.media || 'movie' });
    open.href = `movie-profile.html?${query.toString()}`;
    article.append(image, copy, open);
    myList.prepend(article);
  });
}

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
