/* Shared GSAP enter / scroll motion for metro and training dashboards. */
(function (global) {
  var heroDone = false;

  function canAnimate() {
    if (typeof gsap === 'undefined') return false;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return false;
    }
    return true;
  }

  function ensurePlugin() {
    if (typeof ScrollTrigger !== 'undefined') gsap.registerPlugin(ScrollTrigger);
  }

  function killPageTriggers() {
    if (typeof ScrollTrigger === 'undefined') return;
    ScrollTrigger.getAll().forEach(function (t) {
      t.kill();
    });
  }

  function from(els, vars) {
    var list = gsap.utils.toArray(els).filter(Boolean);
    if (!list.length) return;
    gsap.from(
      list,
      Object.assign(
        {
          opacity: 0,
          y: 18,
          duration: 0.5,
          stagger: 0.05,
          ease: 'power2.out',
          clearProps: 'transform,opacity'
        },
        vars || {}
      )
    );
  }

  function initHeroOnce() {
    if (!canAnimate() || heroDone) return;
    ensurePlugin();
    heroDone = true;
    from('.detail > .wrap > .back, .detail > .wrap > .tag, .detail > .wrap > h1, .detail > .wrap > .lead');
  }

  function initMetroDashboard() {
    if (!canAnimate()) return;
    ensurePlugin();
    killPageTriggers();
    initHeroOnce();
    var dash = document.getElementById('dashboard');
    if (!dash || dash.hidden) return;
    from('#summary-line > *', {
      scrollTrigger: { trigger: '#summary-line', start: 'top 90%', once: true }
    });
    from('#line-grid > *', {
      scrollTrigger: { trigger: '#line-grid', start: 'top 88%', once: true }
    });
    from(['#h-detail', '#detail-panel', '#how'], {
      scrollTrigger: { trigger: '#h-detail', start: 'top 90%', once: true }
    });
  }

  function initTrainingDashboard() {
    if (!canAnimate()) return;
    ensurePlugin();
    killPageTriggers();
    initHeroOnce();
    var dash = document.getElementById('dashboard');
    if (!dash || dash.hidden) return;
    from('#summary-line > *', {
      scrollTrigger: { trigger: '#summary-line', start: 'top 90%', once: true }
    });
    from('.dash-grid > div, .pb-block, .dash-mixed > div, #how', {
      scrollTrigger: { trigger: '#dashboard', start: 'top 85%', once: true },
      stagger: 0.08
    });
  }

  global.SiteMotion = {
    canAnimate: canAnimate,
    initMetroDashboard: initMetroDashboard,
    initTrainingDashboard: initTrainingDashboard
  };
})(window);
