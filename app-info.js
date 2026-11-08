(() => {
  const sections = [...document.querySelectorAll('.info-state')];
  if (!sections.length) return;

  const selectSection = () => {
    const targetId = decodeURIComponent(window.location.hash.slice(1));
    const selected = sections.find((section) => section.id === targetId) || sections[0];
    sections.forEach((section) => section.classList.toggle('is-default', section === selected));
    const heading = selected.querySelector('h1');
    const pageTitle = document.getElementById('info-header-title');
    if (heading && pageTitle) pageTitle.textContent = heading.textContent;
  };

  selectSection();
  window.addEventListener('hashchange', selectSection);
})();
