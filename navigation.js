// Keep each app navigation indicator synced with the page, including browser Back/Forward restores.
const appNavigationLinks = document.querySelectorAll(
  '.bottom-nav .nav-item, .recognize-bottom-nav a, .watchlist-bottom-nav a, .profile-bottom-nav a, .settings-bottom-nav a, ' +
  '.recognize-sidebar nav a, .watchlist-sidebar nav a, .profile-sidebar nav a, .settings-sidebar nav a'
);

function navigationKeyFromPath(pathname) {
  const file = pathname.split('/').filter(Boolean).pop() || 'home.html';
  if (file === 'genres.html') return 'browse';
  return file.replace(/\.html?$/i, '').replace(/^index$/, 'home');
}

function navigationKeyFromLink(link) {
  const href = link.getAttribute('href') || '';
  if (href === '#home') return 'home';
  if (href === '#explore') return 'explore';
  const path = new URL(href, window.location.href).pathname;
  return navigationKeyFromPath(path);
}

function syncAppNavigation() {
  const pageKey = navigationKeyFromPath(window.location.pathname);

  appNavigationLinks.forEach((link) => {
    link.classList.remove('is-active', 'active');
    link.removeAttribute('aria-current');

    const isBottomNav = Boolean(link.closest('.bottom-nav, .recognize-bottom-nav, .watchlist-bottom-nav, .profile-bottom-nav, .settings-bottom-nav'));
    const wantedKey = pageKey === 'browse' && isBottomNav ? 'explore' : pageKey;
    const linkKey = navigationKeyFromLink(link);
    const matches = linkKey === wantedKey || (pageKey === 'settings' && isBottomNav && linkKey === 'profile');

    if (!matches) return;

    const activeClass = link.classList.contains('nav-item') || link.closest('.recognize-bottom-nav, .recognize-sidebar')
      ? 'is-active'
      : 'active';
    link.classList.add(activeClass);
    link.setAttribute('aria-current', 'page');
  });
}

syncAppNavigation();
window.addEventListener('pageshow', syncAppNavigation);
appNavigationLinks.forEach((link) => link.addEventListener('click', syncAppNavigation));
