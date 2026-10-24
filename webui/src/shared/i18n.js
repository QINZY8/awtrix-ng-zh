// Local fork: German and Chinese translations for the Web UI.
//
// Upstream ships English only (shared/strings.js plus English literals inside the
// views). To follow upstream without keeping a hand-maintained index.html, every
// translation lives in files upstream does not have:
//
//   shared/i18n-de.js, shared/i18n-zh.js   STR entries, keyed like strings.js
//   shared/i18n-txt.js                     English literals used inside the views
//
// Upstream files only call t() and tx(). t() closes over STR by reference, so
// filling STR here is enough to localise every string that already uses it, and
// tx() looks up the English literal of fields, options and messages.
//
// The language is picked from ?lang=, then localStorage, then the browser.
// Append "#/<tab>" after it, for example "/?lang=zh#/system".

const STR_EN = Object.assign({}, STR);
const I18N = {en: I18N_EN, de: I18N_DE, zh: I18N_ZH};
const TXT = {de: TXT_DE, zh: TXT_ZH};
const LANGS = ['en', 'de', 'zh'];
const LANG_BADGE = {en: 'EN', de: 'DE', zh: '中文'};
let LANG = 'en';

(function pickLang() {
  let q = null;
  try { q = new URLSearchParams(location.search).get('lang'); } catch (e) {}
  let saved = null;
  try { saved = localStorage.awtrixLang; } catch (e) {}
  const nav = String(navigator.language || '').toLowerCase();
  LANG = [q, saved].find(v => LANGS.includes(v))
    || (nav.startsWith('zh') ? 'zh' : nav.startsWith('de') ? 'de' : 'en');
})();

function applyLang() {
  for (const k in STR) if (!(k in STR_EN)) delete STR[k];
  Object.assign(STR, STR_EN);
  const d = I18N[LANG];
  if (d) for (const k in d) if (d[k]) STR[k] = d[k];
}

// Translate an English literal from a view. Unknown text stays as it is, so a
// new upstream string shows up in English instead of disappearing.
function tx(s) {
  if (s == null || LANG === 'en') return s;
  const d = TXT[LANG];
  if (!d) return s;
  const hit = d[s];
  return hit === undefined ? s : hit;
}

function paintShell() {
  document.documentElement.lang = LANG === 'zh' ? 'zh-CN' : LANG;
  for (const [id, key] of [['kofibtn', 'kofiBtn'], ['hubbtn', 'hubBtn'],
    ['docsbtn', 'docsBtn'], ['themebtn', 'themeBtn']]) {
    const b = document.getElementById(id);
    if (b) b.title = t(key);
  }
  const lb = document.getElementById('langbtn');
  if (lb) {
    lb.replaceChildren(LANG_BADGE[LANG]);
    lb.title = t('langBtn');
    lb.setAttribute('aria-label', t('langBtn'));
  }
  const skip = document.getElementById('skip');
  if (skip) skip.textContent = t('skip');
}

function setLang(lang) {
  LANG = LANGS.includes(lang) ? lang : 'en';
  try { localStorage.awtrixLang = LANG; } catch (e) {}
  applyLang();
  paintShell();
  render();
}

applyLang();

document.getElementById('langbtn').addEventListener('click', () => {
  setLang(LANGS[(LANGS.indexOf(LANG) + 1) % LANGS.length]);
});
paintShell();
