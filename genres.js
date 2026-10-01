// GENRES MENU: show and dismiss the compact genre selector.
const genresMenuButton = document.getElementById('genres-menu-toggle');
const genresMenuPanel = document.getElementById('genres-menu-panel');
genresMenuButton.addEventListener('click', () => {
  const opening = genresMenuPanel.hidden;
  genresMenuPanel.hidden = !opening;
  genresMenuButton.setAttribute('aria-expanded', String(opening));
});
document.addEventListener('click', (event) => {
  if (!genresMenuPanel.hidden && !genresMenuPanel.contains(event.target) && !genresMenuButton.contains(event.target)) {
    genresMenuPanel.hidden = true;
    genresMenuButton.setAttribute('aria-expanded', 'false');
  }
});

// GENRE NAVIGATION: return the chosen genre to Explore through its URL query.
document.querySelectorAll('.genre-choice').forEach((choice) => {
  choice.addEventListener('click', () => {
    const genre = choice.dataset.genre;
    const destination = genre === 'all'
      ? 'explore.html'
      : `explore.html?genre=${encodeURIComponent(genre)}`;
    window.location.href = destination;
  });
});
