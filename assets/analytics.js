/**
 * Dual-send analytics to GoatCounter and Umami.
 * CV clicks (click/cv-xx) become Umami event cv-download with { language: 'xx' }.
 */
(function (global) {
  function siteTrack(path) {
    if (!path) return;

    try {
      if (typeof goatcounter !== 'undefined' && goatcounter.count) {
        goatcounter.count({ path: path, event: true, title: path });
      }
    } catch (e) { /* goatcounter unavailable */ }

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
