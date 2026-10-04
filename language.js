const languageButtons = [...document.querySelectorAll('[data-language]')];
const activeLanguage = window.MUVYLocale?.currentLanguage || 'en';

languageButtons.forEach((button) => {
  const selected = button.dataset.language === activeLanguage;
  button.setAttribute('aria-pressed', String(selected));
  button.addEventListener('click', () => {
    window.MUVYLocale?.setLanguage(button.dataset.language);
    window.location.href = 'profile.html';
  });
});
