// Give every catalog card the same reusable movie profile destination.
document.querySelectorAll('.movie-card').forEach((card) => {
  const title = card.dataset.title || card.querySelector('.movie-title')?.textContent?.trim();
  if (!title) return;
  const artwork = card.querySelector('.poster-art');
  const query = new URLSearchParams({
    title,
    image: artwork?.getAttribute('src') ? new URL(artwork.getAttribute('src'), document.baseURI).href : '',
    year: card.dataset.year || card.querySelector('.movie-year')?.textContent?.trim() || '',
    media: card.dataset.media || 'movie',
    genres: card.dataset.genres || ''
  });
  card.href = `movie-profile.html?${query.toString()}`;
});
