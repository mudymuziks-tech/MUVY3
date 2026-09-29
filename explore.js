// Explore interactions: preserve nav state, filter and search the local catalog, and show feedback.
const toast = document.getElementById('explore-toast');
let toastTimer;
function showToast(message) {
  toast.textContent = message;
  toast.classList.add('is-visible');
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), 3000);
}

const navItems = document.querySelectorAll('.nav-item');
let savedNav = '';
try { savedNav = sessionStorage.getItem('muvyActiveNav') || ''; } catch {}
if (!savedNav) savedNav = 'explore';
navItems.forEach((item) => {
  if (item.dataset.nav === savedNav) {
    item.classList.add('is-active');
    if (item.tagName === 'A') item.setAttribute('aria-current', 'page');
  }
  item.addEventListener('click', () => {
    if (!item.dataset.nav) return;
    navItems.forEach((navItem) => {
      navItem.classList.remove('is-active');
      navItem.removeAttribute('aria-current');
    });
    item.classList.add('is-active');
    if (item.tagName === 'A') item.setAttribute('aria-current', 'page');
    try { sessionStorage.setItem('muvyActiveNav', item.dataset.nav); } catch {}
  });
});
document.querySelectorAll('[data-message]').forEach((button) => {
  button.addEventListener('click', () => showToast(button.dataset.message));
});

const searchForm = document.getElementById('explore-search');
const searchInput = document.getElementById('explore-query');
const filterToggle = document.getElementById('filter-toggle');
const genrePanel = document.getElementById('genre-filter-panel');
const genresChip = document.getElementById('genres-chip');
const categoryChips = [...document.querySelectorAll('.category-chip')];
const genreButtons = [...genrePanel.querySelectorAll('[data-genre]')];
const cards = [...document.querySelectorAll('.explore-card')];
const sections = [...document.querySelectorAll('.explore-section')];
const emptyMessage = document.getElementById('explore-empty');
let activeCategory = 'for-you';
let activeGenre = 'all';

function setCategory(category) {
  activeCategory = category;
  categoryChips.forEach((chip) => {
    const active = chip.dataset.category === category;
    chip.classList.toggle('is-selected', active);
    chip.setAttribute('aria-pressed', String(active));
  });
  if (category !== 'genres') {
    genrePanel.hidden = true;
    filterToggle.dataset.open = 'false';
    filterToggle.setAttribute('aria-expanded', 'false');
  }
}

function filterCards() {
  const query = searchInput.value.trim().toLowerCase();
  let visibleCount = 0;
  cards.forEach((card) => {
    const matchesCategory = activeCategory === 'for-you' || activeCategory === 'genres' || card.dataset.media === activeCategory;
    const matchesGenre = activeGenre === 'all' || card.dataset.genres.split(',').includes(activeGenre);
    const searchText = `${card.dataset.title} ${card.dataset.search}`.toLowerCase();
    const matchesQuery = !query || searchText.includes(query);
    const visible = matchesCategory && matchesGenre && matchesQuery;
    card.hidden = !visible;
    if (visible) visibleCount += 1;
  });
  sections.forEach((section) => {
    section.hidden = !section.querySelector('.explore-card:not([hidden])');
  });
  emptyMessage.hidden = visibleCount > 0;
}

categoryChips.forEach((chip) => {
  chip.addEventListener('click', () => {
    const category = chip.dataset.category;
    if (category === 'genres') {
      window.location.href = 'genres.html';
      return;
    }
    if (category !== 'genres') activeGenre = 'all';
    setCategory(category);
    filterCards();
  });
});

filterToggle.addEventListener('click', () => {
  const opening = genrePanel.hidden;
  genrePanel.hidden = !opening;
  filterToggle.dataset.open = String(opening);
  filterToggle.setAttribute('aria-expanded', String(opening));
  if (opening) setCategory('genres');
  genrePanel.hidden = !opening;
  filterCards();
});

genreButtons.forEach((button) => {
  button.addEventListener('click', () => {
    activeGenre = button.dataset.genre;
    genreButtons.forEach((genreButton) => genreButton.classList.toggle('is-selected', genreButton === button));
    setCategory('genres');
    filterCards();
  });
});

searchInput.addEventListener('input', filterCards);
searchForm.addEventListener('submit', (event) => { event.preventDefault(); filterCards(); });
cards.forEach((card) => card.addEventListener('click', (event) => {
  event.preventDefault();
  showToast(`${card.dataset.title} details are coming soon.`);
}));

const requestedGenre = new URLSearchParams(window.location.search).get('genre');
if (requestedGenre) {
  activeGenre = requestedGenre;
  setCategory('genres');
  genreButtons.forEach((button) => button.classList.toggle('is-selected', button.dataset.genre === requestedGenre));
}
filterCards();
