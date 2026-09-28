document.querySelectorAll('.genre-choice').forEach((choice) => {
  choice.addEventListener('click', () => {
    const genre = choice.dataset.genre;
    const destination = genre === 'all'
      ? 'explore.html'
      : `explore.html?genre=${encodeURIComponent(genre)}`;
    window.location.href = destination;
  });
});
