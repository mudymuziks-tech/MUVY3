// PROFILE DETAILS: show the name and email from the temporary signed-in session.
const account = window.MUVYAuth?.getSession();
if (account) {
  document.getElementById('profile-name').textContent = account.name || window.MUVYLocale?.t('MUVY Member') || 'MUVY Member';
  document.getElementById('profile-email').textContent = account.email || '';
}

const profileLanguageName = document.getElementById('profile-language-name');
if (profileLanguageName) {
  profileLanguageName.textContent = window.MUVYLocale?.getLanguageName() || 'English';
}

// PROFILE MENU: toggle the small-screen menu and close it on outside click.
const profileMenuButton = document.getElementById('profile-menu-button');
const profileMenuPanel = document.getElementById('profile-menu-panel');
profileMenuButton.addEventListener('click', () => {
  const opening = profileMenuPanel.hidden;
  profileMenuPanel.hidden = !opening;
  profileMenuButton.setAttribute('aria-expanded', String(opening));
});
document.addEventListener('click', (event) => {
  if (!profileMenuPanel.hidden && !profileMenuPanel.contains(event.target) && !profileMenuButton.contains(event.target)) {
    profileMenuPanel.hidden = true;
    profileMenuButton.setAttribute('aria-expanded', 'false');
  }
});

