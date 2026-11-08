const settingsLanguageName = document.getElementById('settings-language-name');
if (settingsLanguageName) {
  settingsLanguageName.textContent = window.MUVYLocale?.getLanguageName() || 'English';
}
