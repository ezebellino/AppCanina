(() => {
  const menu = document.querySelector('.mobile-navigation');
  const overlay = document.getElementById('page-loading');
  const main = document.querySelector('main');
  const status = document.getElementById('page-loading-status');
  let showTimer, slowTimer;
  const closeMenu = () => { if (menu?.dataset.motionMenu) menu.dispatchEvent(new Event('navigation-close')); else if (menu) menu.open = false; };
  function reset() {
    clearTimeout(showTimer);
    clearTimeout(slowTimer);
    overlay.hidden = true;
    main?.removeAttribute('aria-busy');
  }
  function start() {
    reset();
    closeMenu();
    showTimer = setTimeout(() => {
      overlay.hidden = false;
      main?.setAttribute('aria-busy', 'true');
      status.textContent = 'Cargando información…';
      slowTimer = setTimeout(() => {
        status.textContent = 'La carga está tardando. Podés seguir viendo esta página mientras esperás.';
      }, 10000);
    }, 250);
  }
  // Full-page Django navigation: show placeholders while awaiting the next HTML.
  // Do not intercept downloads, external links, modified clicks, or form POSTs.
  document.addEventListener('click', event => {
    if (menu?.open && !menu.dataset.motionMenu && !menu.contains(event.target)) menu.open = false;
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.hasAttribute('download') || (link.target && link.target !== '_self')) return;
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || url.hash || !/^\/(extraviados\/(adopciones|$)|buscar\/|cuenta\/perfil\/)/.test(url.pathname)) return;
    start();
  });
  document.addEventListener('submit', event => {
    if (!event.defaultPrevented && event.target.method.toLowerCase() === 'get' && !event.target.target) start();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') { reset(); if (!menu?.dataset.motionMenu) closeMenu(); }
  });
  document.getElementById('page-loading-dismiss')?.addEventListener('click', reset);
  window.addEventListener('pageshow', reset);
})();
