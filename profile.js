// Profile name from the temporary local sign-in plus the small-screen app menu.
const account = window.MUVYAuth?.getSession();
if (account) {
  document.getElementById('profile-name').textContent = account.name || 'MUVY Member';
  document.getElementById('profile-email').textContent = account.email || '';
}

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
