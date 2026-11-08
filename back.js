// BACK CONTROLS: use browser history when available and preserve each link's direct-entry fallback.
const appBackControls = document.querySelectorAll('[data-app-back]');

appBackControls.forEach((control) => {
  if (control.dataset.appBackBound === 'true') return;
  control.dataset.appBackBound = 'true';
  if (control.tagName === 'BUTTON') control.hidden = window.history.length <= 1;

  control.addEventListener('click', (event) => {
    if (window.history.length <= 1) return;
    event.preventDefault();
    window.history.back();
  });
});
