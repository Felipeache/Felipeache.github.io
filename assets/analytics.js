/**
 * Umami analytics helper.
 * CV clicks (click/cv-xx) become event cv-download with { language: 'xx' }.
 */
(function (global) {
  function siteTrack(path) {
    if (!path) return;

    try {
      if (typeof umami !== 'undefined' && typeof umami.track === 'function') {
        var cv = path.match(/^click\/cv-([a-z]{2})$/);
        if (cv) {
          umami.track('cv-download', { language: cv[1] });
        } else {
          umami.track(path);
        }
      }
    } catch (e) { /* umami unavailable */ }
  }

  global.siteTrack = siteTrack;
})(typeof window !== 'undefined' ? window : this);
