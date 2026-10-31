// Shared language switcher used by every page.
// Pages call SiteLang.pick() for the starting language, SiteLang.renderButtons()
// to draw the flags, and SiteLang.store() to remember the choice.
const SiteLang = (() => {
  const LANGS = ['es', 'en', 'fr'];
  const NAMES = { es: 'Español', en: 'English', fr: 'Français' };
  const STORAGE_KEY = 'site-lang';

  const FLAGS = {
    es: '<svg viewBox="0 0 60 40" aria-hidden="true" focusable="false"><rect width="60" height="40" fill="#AA151B"/><rect y="10" width="60" height="20" fill="#F1BF00"/></svg>',
    en: '<svg viewBox="0 0 60 40" aria-hidden="true" focusable="false"><rect width="60" height="40" fill="#012169"/><path d="M0,0 L60,40 M60,0 L0,40" stroke="#fff" stroke-width="8"/><path d="M0,0 L60,40 M60,0 L0,40" stroke="#C8102E" stroke-width="3"/><path d="M30,0 V40 M0,20 H60" stroke="#fff" stroke-width="12"/><path d="M30,0 V40 M0,20 H60" stroke="#C8102E" stroke-width="7"/></svg>',
    fr: '<svg viewBox="0 0 60 40" aria-hidden="true" focusable="false"><rect width="20" height="40" fill="#002395"/><rect x="20" width="20" height="40" fill="#fff"/><rect x="40" width="20" height="40" fill="#ED2939"/></svg>'
  };

  function readStored() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }

  function pick() {
    const stored = readStored();
    if (LANGS.includes(stored)) return stored;
    const browser = (navigator.language || 'en').slice(0, 2).toLowerCase();
    return LANGS.includes(browser) ? browser : 'en';
  }

  function store(lang) {
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* storage unavailable */ }
  }

  function renderButtons(container, current, onPick) {
    container.textContent = '';
    LANGS.forEach(code => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.setAttribute('aria-label', NAMES[code]);
      btn.setAttribute('aria-pressed', String(code === current));
      btn.title = NAMES[code];
      btn.innerHTML = FLAGS[code];
      btn.addEventListener('click', () => onPick(code));
      container.appendChild(btn);
    });
  }

  return { LANGS, NAMES, pick, store, renderButtons };
})();
