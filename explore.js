// EXPLORE PAGE: toast feedback for placeholder actions.
const toast = document.getElementById('explore-toast');
let toastTimer;
function showToast(message) {
  toast.textContent = window.MUVYLocale?.t(message) ?? message;
  toast.classList.add('is-visible');
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), 3000);
}

document.querySelectorAll('[data-message]').forEach((button) => {
  button.addEventListener('click', () => showToast(button.dataset.message));
});

// CATALOG FILTERS: keep category, genre, and search state for the visible cards.
const searchForm = document.getElementById('explore-search');
const searchInput = document.getElementById('explore-query');
const categoryChips = [...document.querySelectorAll('.category-chip')];
const cards = [...document.querySelectorAll('.explore-card')];
const sections = [...document.querySelectorAll('.explore-section')];
const emptyMessage = document.getElementById('explore-empty');
let activeCategory = 'for-you';
let activeGenre = 'all';

searchForm.addEventListener('click', (event) => {
  if (event.target !== searchInput) searchInput.focus();
});

// CATEGORY SELECTION: update the selected chip and its accessibility state.
function setCategory(category) {
  activeCategory = category;
  categoryChips.forEach((chip) => {
    const active = chip.dataset.category === category;
    chip.classList.toggle('is-selected', active);
    chip.setAttribute('aria-pressed', String(active));
  });
}

// CARD FILTERING: match the query and filters, then show empty-state feedback.
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

// EXPLORE CONTROLS: navigate to Genres or apply a category and search.
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

searchInput.addEventListener('input', filterCards);
searchForm.addEventListener('submit', (event) => { event.preventDefault(); filterCards(); });
cards.forEach((card) => card.addEventListener('click', (event) => {
  event.preventDefault();
  showToast(`${card.dataset.title} details are coming soon.`);
}));

// DEEP LINK: restore a selected genre when arriving from the Genres page.
const requestedGenre = new URLSearchParams(window.location.search).get('genre');
if (requestedGenre) {
  activeGenre = requestedGenre;
  setCategory('genres');
}
filterCards();
