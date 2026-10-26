const params = new URLSearchParams(window.location.search);
const title = params.get('title') || 'Movie';
const poster = params.get('image') || '';
const year = params.get('year') || '';
const media = params.get('media') || 'movie';
const genres = (params.get('genres') || '').split(',').filter(Boolean);
const key = title.toLocaleLowerCase();
const profiles = {
  'dune': { year: '2021', runtime: '2h 35m', rating: '8.0/10', genres: ['Action', 'Adventure', 'Drama', 'Sci-Fi'], overview: 'Paul Atreides, a brilliant and gifted young man, must travel to the most dangerous planet in the universe to ensure the future of his family and his people.', cast: [['Timothée Chalamet', 'Paul Atreides'], ['Rebecca Ferguson', 'Lady Jessica'], ['Oscar Isaac', 'Duke Leto'], ['Zendaya', 'Chani']] },
  'john wick': { year: '2014', runtime: '1h 41m', rating: '7.4/10', genres: ['Action', 'Thriller'], overview: 'A retired hitman returns to the underworld after a devastating loss puts him on a path of revenge.' },
  'wakanda forever': { year: '2022', runtime: '2h 41m', rating: '6.7/10', genres: ['Action', 'Adventure', 'Drama'], overview: 'The people of Wakanda face new threats as they mourn the loss of their king and protect their home.' },
  'the pursuit of happyness': { year: '2006', runtime: '1h 57m', rating: '8.0/10', genres: ['Drama'], overview: 'A determined father works to build a better life for himself and his young son.' },
  'jumanji: the next level': { year: '2019', runtime: '2h 3m', rating: '6.7/10', genres: ['Adventure', 'Comedy'], overview: 'The players return to Jumanji, where new challenges and unfamiliar terrain await.' },
  'the expendables 3': { year: '2014', runtime: '2h 6m', rating: '6.1/10', genres: ['Action', 'Adventure'], overview: 'The Expendables face a new enemy with a personal connection to their past.' },
  'the last of us': { year: '2023', runtime: 'TV series', rating: '', genres: ['Drama', 'Adventure'], overview: 'A hardened survivor and a young girl travel across a dangerous post-apocalyptic world.' }
};
const profile = profiles[key] || {};
const displayYear = profile.year || year;
document.title = `${title} | MUVY`;
document.getElementById('profile-title').textContent = title;
document.getElementById('profile-meta').textContent = [displayYear, media === 'tv' ? 'TV Series' : 'Movie', profile.runtime].filter(Boolean).join('  •  ');
document.getElementById('profile-rating').textContent = profile.rating ? `★ ${profile.rating}` : '';
document.getElementById('profile-overview').textContent = profile.overview || 'Explore this title and check the latest streaming options for your region.';
const backdrop = document.getElementById('profile-backdrop');
if (poster) { backdrop.src = poster; backdrop.alt = `${title} artwork`; } else { backdrop.hidden = true; }
const genreList = profile.genres || genres;
const genreContainer = document.getElementById('profile-genres');
genreList.forEach((genre) => {
  const chip = document.createElement('a');
  chip.href = `explore.html?genre=${encodeURIComponent(genre.toLowerCase())}`;
  chip.textContent = genre;
  genreContainer.append(chip);
});
const cast = profile.cast || [];
if (cast.length) {
  document.getElementById('cast-section').hidden = false;
  const castContainer = document.getElementById('profile-cast');
  cast.forEach(([name, role]) => {
    const person = document.createElement('div');
    person.className = 'cast-person';
    const portrait = document.createElement('div');
    portrait.className = 'cast-portrait';
    portrait.textContent = name.split(/\s+/).map((part) => part[0]).slice(0, 2).join('');
    const actor = document.createElement('strong');
    actor.textContent = name;
    const character = document.createElement('span');
    character.textContent = role;
    person.append(portrait, actor, character);
    castContainer.append(person);
  });
}
const services = [
  ['Netflix', (q) => `https://www.netflix.com/search?q=${q}`],
  ['Prime Video', (q) => `https://www.primevideo.com/search/ref=atv_nb_sr?phrase=${q}`],
  ['Showmax', (q) => `https://www.showmax.com/ng/search?q=${q}`],
  ['Disney+', (q) => `https://www.disneyplus.com/search/${q}`],
  ['Apple TV', (q) => `https://tv.apple.com/search?term=${q}`],
  ['JustWatch', (q) => `https://www.justwatch.com/ng/search?q=${q}`]
];
const encodedTitle = encodeURIComponent(title);
const serviceList = document.getElementById('streaming-options');
services.forEach(([name, makeUrl]) => {
  const option = document.createElement('a');
  option.href = makeUrl(encodedTitle);
  option.target = '_blank';
  option.rel = 'noopener noreferrer';
  option.textContent = name;
  serviceList.append(option);
});
const streamingDialog = document.getElementById('streaming-dialog');
document.getElementById('play-movie').addEventListener('click', () => streamingDialog.showModal());
let saved = [];
try { saved = JSON.parse(localStorage.getItem('muvy-watchlist') || '[]'); } catch { saved = []; }
const saveButton = document.getElementById('save-movie');
const profileStatus = document.getElementById('profile-status');
let statusTimer;
function showStatus(message) {
  profileStatus.textContent = message;
  profileStatus.classList.add('is-visible');
  window.clearTimeout(statusTimer);
  statusTimer = window.setTimeout(() => profileStatus.classList.remove('is-visible'), 2600);
}
function updateSaveButton() {
  saveButton.querySelector('span').textContent = 'Save to Watchlist';
  saveButton.firstChild.textContent = '♡ ';
}
updateSaveButton();
saveButton.addEventListener('click', () => {
  const index = saved.findIndex((item) => item.title.toLowerCase() === title.toLowerCase());
  if (index < 0) {
    saved.push({ title, year: displayYear, image: poster, media });
    localStorage.setItem('muvy-watchlist', JSON.stringify(saved));
  }
  updateSaveButton();
  showStatus(index >= 0 ? 'This movie is already in your watchlist.' : 'Movie saved to your watchlist.');
});
document.getElementById('share-movie').addEventListener('click', async () => {
  const shareData = { title: `${title} | MUVY`, url: window.location.href };
  try {
    if (navigator.share) await navigator.share(shareData);
    else { await navigator.clipboard.writeText(window.location.href); showStatus('Link copied to clipboard.'); }
  } catch (error) { if (error.name !== 'AbortError') showStatus('Unable to share this link.'); }
});
