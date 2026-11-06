// Christmas mode: an opt-in toggle in the header, remembered in localStorage under 'site-xmas'.
// Loaded in <head> by every page so the saved choice is applied before the first paint.
(function () {
  var KEY = 'site-xmas';
  var root = document.documentElement;
  var reduced = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  var LABELS = {
    en: ['Turn on Christmas mode', 'Turn off Christmas mode'],
    es: ['Activar el modo Navidad', 'Desactivar el modo Navidad'],
    fr: ['Activer le mode Noël', 'Désactiver le mode Noël']
  };
  var GREETING = 'Merry Christmas · Joyeux Noël · Feliz Navidad';
  var TREE = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"><path d="M12 3 7 10h3l-4 6h4l-3 4h12l-3-4h4l-4-6h3z"/><path d="M12 20v2"/></svg>';
  var HAT = '<svg viewBox="0 0 100 80" aria-hidden="true" focusable="false"><path d="M8 62C20 22 52 6 82 14c-8 16-4 32 10 48z" fill="#c62828"/><rect x="4" y="56" width="92" height="18" rx="9" fill="#fff"/><circle cx="84" cy="14" r="9" fill="#fff"/></svg>';

  function read() { try { return localStorage.getItem(KEY) === 'on'; } catch (e) { return false; } }
  function hasChoice() { try { return localStorage.getItem(KEY) !== null; } catch (e) { return true; } }
  function write(on) { try { localStorage.setItem(KEY, on ? 'on' : 'off'); } catch (e) { /* storage unavailable */ } }

  var on = read();
  if (on) root.setAttribute('data-xmas', 'on');

  var button = null, canvas = null, raf = 0, snowStop = null;

  function label() {
    var lang = (root.lang || 'en').slice(0, 2);
    return (LABELS[lang] || LABELS.en)[on ? 1 : 0];
  }

  function refreshButton() {
    if (!button) return;
    var text = label();
    button.setAttribute('aria-pressed', String(on));
    button.setAttribute('aria-label', text);
    button.setAttribute('data-tip', text);
    button.removeAttribute('title');
  }

  function addGreeting() {
    if (document.querySelector('.xmas-greeting')) return;
    var header = document.querySelector('.site-header');
    if (!header) return;
    var p = document.createElement('p');
    p.className = 'xmas-greeting';
    p.textContent = GREETING;
    header.insertAdjacentElement('afterend', p);
  }
  function removeGreeting() {
    var p = document.querySelector('.xmas-greeting');
    if (p) p.remove();
  }

  function addHat() {
    var img = document.querySelector('.avatar');
    if (!img || (img.parentNode.classList && img.parentNode.classList.contains('avatar-wrap'))) return;
    var wrap = document.createElement('span');
    wrap.className = 'avatar-wrap';
    img.parentNode.insertBefore(wrap, img);
    wrap.appendChild(img);
    var hat = document.createElement('span');
    hat.className = 'xmas-hat';
    hat.setAttribute('aria-hidden', 'true');
    hat.innerHTML = HAT;
    wrap.appendChild(hat);
  }
  function removeHat() {
    var wrap = document.querySelector('.avatar-wrap');
    if (!wrap) return;
    var img = wrap.querySelector('.avatar');
    if (img) wrap.parentNode.insertBefore(img, wrap);
    wrap.remove();
  }

  var CORNERS = [
    ['left', [['\u26C4', 'big'], ['\uD83C\uDF81', 'small']]],
    ['right', [['\uD83C\uDF81', 'small'], ['\uD83E\uDD8C', 'big'], ['\uD83C\uDF84', 'big']]]
  ];
  function addCorners() {
    if (document.querySelector('.xmas-corner')) return;
    CORNERS.forEach(function (corner) {
      var box = document.createElement('div');
      box.className = 'xmas-corner ' + corner[0];
      box.setAttribute('aria-hidden', 'true');
      corner[1].forEach(function (item, i) {
        var span = document.createElement('span');
        span.className = 'xmas-char ' + item[1];
        span.style.animationDelay = (i * 0.9 + (corner[0] === 'right' ? 0.4 : 0)) + 's';
        span.textContent = item[0];
        box.appendChild(span);
      });
      document.body.appendChild(box);
    });
  }
  function removeCorners() {
    document.querySelectorAll('.xmas-corner').forEach(function (box) { box.remove(); });
  }

  function startSnow() {
    if (reduced || canvas) return;
    canvas = document.createElement('canvas');
    canvas.className = 'xmas-snow';
    canvas.setAttribute('aria-hidden', 'true');
    document.body.appendChild(canvas);
    var ctx = canvas.getContext('2d');
    var flakes = [], w = 0, h = 0;
    var rgb = root.getAttribute('data-theme') === 'light' ? '159,195,232' : '255,255,255';

    function make(anywhere) {
      return { x: Math.random() * w, y: anywhere ? Math.random() * h : -6, r: 1 + Math.random() * 2.2, v: 0.2 + Math.random() * 0.5, p: Math.random() * 6.28, s: 0.15 + Math.random() * 0.3 };
    }
    function resize() {
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth; h = window.innerHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var count = Math.max(40, Math.min(90, Math.round(w / 16)));
      while (flakes.length < count) flakes.push(make(true));
      flakes.length = count;
    }
    var last = 0;
    function frame(now) {
      // Speeds are per 60 Hz frame; scale by elapsed time so 120 Hz screens fall at the same pace.
      var dt = last ? Math.min(3, (now - last) / 16.667) : 1;
      last = now;
      ctx.clearRect(0, 0, w, h);
      for (var i = 0; i < flakes.length; i++) {
        var f = flakes[i];
        f.y += f.v * dt; f.p += 0.006 * dt; f.x += Math.sin(f.p) * f.s * dt;
        if (f.y > h + 6 || f.x < -10 || f.x > w + 10) { flakes[i] = make(false); f = flakes[i]; }
        ctx.beginPath();
        ctx.fillStyle = 'rgba(' + rgb + ',' + Math.min(0.85, 0.45 + f.r / 6) + ')';
        ctx.arc(f.x, f.y, f.r, 0, 6.2832);
        ctx.fill();
      }
      raf = requestAnimationFrame(frame);
    }
    function onVisibility() {
      if (document.hidden) { cancelAnimationFrame(raf); raf = 0; }
      else if (!raf) { last = 0; raf = requestAnimationFrame(frame); }
    }
    var themeWatch = new MutationObserver(function () {
      rgb = root.getAttribute('data-theme') === 'light' ? '159,195,232' : '255,255,255';
    });
    themeWatch.observe(root, { attributes: true, attributeFilter: ['data-theme'] });
    window.addEventListener('resize', resize);
    document.addEventListener('visibilitychange', onVisibility);
    resize();
    raf = requestAnimationFrame(frame);

    snowStop = function () {
      cancelAnimationFrame(raf); raf = 0;
      themeWatch.disconnect();
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', onVisibility);
      canvas.remove(); canvas = null; snowStop = null;
    };
  }
  function stopSnow() { if (snowStop) snowStop(); }

  function apply() {
    if (on) {
      root.setAttribute('data-xmas', 'on');
      addGreeting(); addHat(); addCorners(); startSnow();
    } else {
      root.removeAttribute('data-xmas');
      removeGreeting(); removeHat(); removeCorners(); stopSnow();
    }
    refreshButton();
  }

  function track() {
    if (typeof goatcounter === 'undefined' || !goatcounter.count) return;
    var path = 'click/christmas-' + (on ? 'on' : 'off');
    try { goatcounter.count({ path: path, event: true, title: path }); } catch (e) { /* analytics unavailable */ }
  }

  function init() {
    var wrap = document.querySelector('.site-header .wrap');
    if (wrap) {
      button = document.createElement('button');
      button.type = 'button';
      button.className = 'theme-toggle xmas-toggle';
      button.innerHTML = TREE;
      if (!hasChoice()) button.classList.add('xmas-new');
      button.addEventListener('click', function () { button.classList.remove('xmas-new'); on = !on; write(on); apply(); track(); });
      var anchor = document.getElementById('theme-toggle');
      if (anchor) anchor.insertAdjacentElement('afterend', button); else wrap.appendChild(button);
      new MutationObserver(refreshButton).observe(root, { attributes: true, attributeFilter: ['lang'] });
    }
    apply();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
