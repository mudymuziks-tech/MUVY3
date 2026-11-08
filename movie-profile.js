(() => {
  const params = new URLSearchParams(window.location.search);
  const title = params.get('title')?.trim() || 'Movie';
  const posterFallback = params.get('image') || '';
  const yearFallback = params.get('year') || '';
  const media = params.get('media') || 'movie';
  const tmdbId = Number(params.get('tmdb_id')) || null;
  const genreFallback = (params.get('genres') || '').split(',').map((genre) => genre.trim()).filter(Boolean);
  const imageBase = 'https://image.tmdb.org/t/p/';
  const titleElement = document.getElementById('profile-title');
  const metaElement = document.getElementById('profile-meta');
  const ratingElement = document.getElementById('profile-rating');
  const genreContainer = document.getElementById('profile-genres');
  const overviewSection = document.getElementById('overview-section');
  const overviewElement = document.getElementById('profile-overview');
  const backdrop = document.getElementById('profile-backdrop');
  const poster = document.getElementById('profile-poster');
  const statusElement = document.getElementById('profile-status');
  const saveButtons = [...document.querySelectorAll('[data-save-movie]')];
  const storageKey = 'muvy.savedMovies';
  let currentDetails = null;
  let savedTitles = [];

  document.title = `${title} | MUVY`;
  titleElement.textContent = title;
  poster.alt = `${title} poster`;

  function setStatus(message) {
    statusElement.textContent = message;
  }

  function normalizedTitle(value) {
    return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  }

  function imageUrl(path, size) {
    return typeof path === 'string' && path.startsWith('/') ? `${imageBase}${size}${path}` : '';
  }

  function formatRuntime(minutes) {
    if (!Number.isFinite(minutes) || minutes <= 0) return '';
    const hours = Math.floor(minutes / 60);
    const remainder = minutes % 60;
    return [hours ? `${hours}h` : '', remainder ? `${remainder}m` : ''].filter(Boolean).join(' ');
  }

  function getGenreNames(movie) {
    const names = Array.isArray(movie.genres)
      ? movie.genres.map((genre) => genre?.name).filter((name) => typeof name === 'string' && name.trim())
      : [];
    return names.length ? names : genreFallback;
  }

  function renderMetadata(movie) {
    const releaseDate = movie.release_date || movie.first_air_date || '';
    const releaseYear = releaseDate.slice(0, 4) || yearFallback;
    const runtime = formatRuntime(movie.runtime);
    const meta = [releaseYear, media === 'tv' ? 'TV Series' : 'Movie', runtime].filter(Boolean);
    metaElement.replaceChildren(...meta.map((value) => {
      const item = document.createElement('span');
      item.textContent = value;
      return item;
    }));

    if (Number.isFinite(movie.vote_average) && movie.vote_average > 0) {
      const votes = Number.isFinite(movie.vote_count) && movie.vote_count > 0
        ? ` (${new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(movie.vote_count)} votes)`
        : '';
      ratingElement.textContent = `★ ${movie.vote_average.toFixed(1)}${votes}`;
      ratingElement.hidden = false;
    }

    const genres = getGenreNames(movie);
    genreContainer.replaceChildren(...genres.map((name) => {
      const chip = document.createElement('span');
      chip.className = 'profile-genre';
      chip.textContent = name;
      return chip;
    }));
    genreContainer.hidden = genres.length === 0;

    if (typeof movie.overview === 'string' && movie.overview.trim()) {
      overviewElement.textContent = movie.overview;
      overviewSection.hidden = false;
    }

    const posterPath = imageUrl(movie.poster_path, 'w500');
    const backdropPath = imageUrl(movie.backdrop_path, 'w1280') || params.get('backdrop') || posterFallback;
    if (posterPath || posterFallback) {
      poster.src = posterPath || posterFallback;
      poster.hidden = false;
    }
    if (backdropPath) {
      backdrop.src = backdropPath;
      backdrop.hidden = false;
      backdrop.addEventListener('error', () => {
        if (posterFallback && backdrop.src !== posterFallback) backdrop.src = posterFallback;
        else backdrop.hidden = true;
      }, { once: true });
    }

    renderCast(movie.credits?.cast);
    renderProduction(movie.production_companies);
    renderProviders(movie['watch/providers']?.results);
    renderRecommendations(movie.recommendations?.results);
    renderTrailer(movie.videos?.results);
  }

  function renderCast(cast) {
    if (!Array.isArray(cast)) return;
    const people = cast.filter((person) => person?.name).slice(0, 12);
    if (!people.length) return;
    const container = document.getElementById('profile-cast');
    container.replaceChildren(...people.map((person) => {
      const card = document.createElement('div');
      card.className = 'cast-person';
      const name = document.createElement('strong');
      name.textContent = person.name;
      card.append(name);
      if (person.character) {
        const role = document.createElement('span');
        role.textContent = person.character;
        card.append(role);
      }
      return card;
    }));
    document.getElementById('cast-section').hidden = false;
  }

  function renderProduction(companies) {
    if (!Array.isArray(companies)) return;
    const names = companies.map((company) => company?.name).filter((name) => typeof name === 'string' && name.trim());
    if (!names.length) return;
    const container = document.getElementById('profile-production');
    container.replaceChildren(...names.map((name) => {
      const company = document.createElement('span');
      company.className = 'production-company';
      company.textContent = name;
      return company;
    }));
    document.getElementById('production-section').hidden = false;
  }

  function renderProviders(regions) {
    if (!regions || typeof regions !== 'object') return;
    const region = navigator.language.split('-')[1]?.toUpperCase();
    const available = region ? regions[region] : null;
    if (!available) return;
    const providers = [
      ...(available.flatrate || []).map((provider) => ({ ...provider, availability: 'Stream' })),
      ...(available.free || []).map((provider) => ({ ...provider, availability: 'Free' })),
      ...(available.ads || []).map((provider) => ({ ...provider, availability: 'With ads' })),
      ...(available.rent || []).map((provider) => ({ ...provider, availability: 'Rent' })),
      ...(available.buy || []).map((provider) => ({ ...provider, availability: 'Buy' })),
    ];
    const uniqueProviders = [...new Map(providers.map((provider) => [`${provider.provider_id}:${provider.availability}`, provider])).values()];
    if (!uniqueProviders.length) return;
    document.getElementById('provider-region').textContent = `(${region})`;
    const container = document.getElementById('profile-providers');
    container.replaceChildren(...uniqueProviders.map((provider) => {
      const item = available.link ? document.createElement('a') : document.createElement('span');
      item.className = 'watch-provider';
      if (available.link) {
        item.href = available.link;
        item.target = '_blank';
        item.rel = 'noopener noreferrer';
      }
      item.textContent = `${provider.provider_name} · ${provider.availability}`;
      return item;
    }));
    document.getElementById('provider-section').hidden = false;
  }

  function renderRecommendations(recommendations) {
    if (!Array.isArray(recommendations)) return;
    const movies = recommendations.filter((movie) => movie?.id && movie?.title && movie?.poster_path).slice(0, 10);
    if (!movies.length) return;
    const container = document.getElementById('similar-movies');
    container.replaceChildren(...movies.map((movie) => {
      const link = document.createElement('a');
      link.className = 'similar-card';
      link.href = `movie-profile.html?${new URLSearchParams({
        title: movie.title,
        tmdb_id: String(movie.id),
        image: imageUrl(movie.poster_path, 'w500'),
        backdrop: imageUrl(movie.backdrop_path, 'w1280'),
        year: (movie.release_date || '').slice(0, 4),
      }).toString()}`;
      const image = document.createElement('img');
      image.src = imageUrl(movie.poster_path, 'w500');
      image.alt = '';
      image.loading = 'lazy';
      const label = document.createElement('span');
      label.textContent = movie.title;
      link.append(image, label);
      return link;
    }));
    document.getElementById('similar-section').hidden = false;
  }

  function renderTrailer(videos) {
    if (!Array.isArray(videos)) return;
    const trailer = videos.find((video) => video?.site === 'YouTube' && video?.type === 'Trailer' && video?.key);
    if (!trailer) return;
    const link = document.getElementById('trailer-link');
    link.href = `https://www.youtube.com/watch?v=${encodeURIComponent(trailer.key)}`;
    link.hidden = false;
  }

  async function fetchJson(url) {
    const response = await fetch(url, { headers: { 'Accept-Language': document.documentElement.lang || 'en-US' } });
    if (!response.ok) throw new Error(`Movie metadata request failed (${response.status}).`);
    return response.json();
  }

  async function loadDetails() {
    const apiBase = window.MUVY_API_BASE_URL;
    if (!apiBase || media === 'tv') return;

    let matchedId = tmdbId;
    if (!matchedId) {
      const searchResults = await fetchJson(`${apiBase}/tmdb/search?q=${encodeURIComponent(title)}`);
      if (!Array.isArray(searchResults)) throw new Error('Movie search returned an invalid response.');
      const exactMatches = searchResults.filter((movie) => normalizedTitle(movie.title || '') === normalizedTitle(title));
      const yearMatch = yearFallback && exactMatches.find((movie) => (movie.release_date || '').startsWith(yearFallback));
      matchedId = yearMatch?.id || exactMatches[0]?.id || null;
    }
    if (!matchedId) return;
    currentDetails = await fetchJson(`${apiBase}/tmdb/movies/${matchedId}`);
    renderMetadata(currentDetails);
  }

  function readSaved() {
    try {
      const stored = JSON.parse(localStorage.getItem(storageKey) || '[]');
      return Array.isArray(stored) ? stored.filter((item) => item && typeof item.title === 'string') : [];
    } catch (error) {
      console.error('Unable to read MUVY bookmarks:', error);
      setStatus('Bookmarks are unavailable in this browser.');
      return [];
    }
  }

  function updateSaveButton() {
    const isSaved = savedTitles.some((item) => normalizedTitle(item.title) === normalizedTitle(title));
    saveButtons.forEach((button) => {
      button.setAttribute('aria-pressed', String(isSaved));
      button.setAttribute('aria-label', isSaved ? 'Remove bookmark' : 'Bookmark movie');
      const label = button.querySelector('span');
      if (label) label.textContent = isSaved ? 'Saved' : 'Save';
    });
  }

  savedTitles = readSaved();
  updateSaveButton();
  saveButtons.forEach((saveButton) => saveButton.addEventListener('click', () => {
    const existingIndex = savedTitles.findIndex((item) => normalizedTitle(item.title) === normalizedTitle(title));
    if (existingIndex >= 0) {
      savedTitles.splice(existingIndex, 1);
      setStatus('Removed from Bookmarks.');
    } else {
      savedTitles.push({
        title,
        year: currentDetails?.release_date?.slice(0, 4) || yearFallback,
        image: posterFallback || imageUrl(currentDetails?.poster_path, 'w500'),
        genres: getGenreNames(currentDetails || {}).join(', '),
        media,
      });
      setStatus('Added to Bookmarks.');
    }
    try {
      localStorage.setItem(storageKey, JSON.stringify(savedTitles));
      updateSaveButton();
    } catch (error) {
      console.error('Unable to save MUVY bookmark:', error);
      setStatus('This bookmark could not be saved in this browser.');
    }
  }));

  document.getElementById('share-movie').addEventListener('click', async () => {
    try {
      if (navigator.share) {
        await navigator.share({ title: `${title} | MUVY`, url: window.location.href });
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(window.location.href);
        setStatus('Movie link copied.');
      } else {
        throw new Error('Sharing is not supported in this browser.');
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Unable to share movie:', error);
        setStatus('Unable to share this movie from this browser.');
      }
    }
  });

  const initialMetadata = {
    release_date: yearFallback,
    genres: genreFallback.map((name) => ({ name })),
  };
  renderMetadata(initialMetadata);
  loadDetails().catch((error) => {
    console.error('Unable to load movie details:', error);
    setStatus('Some movie details could not be loaded.');
  });
})();
