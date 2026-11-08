(() => {
  const script = document.querySelector('script[data-adoption-updates-url]');
  if (!script) return;
  let pending = false;
  async function refresh() {
    if (document.hidden || pending) return;
    pending = true;
    try {
      const response = await fetch(script.dataset.adoptionUpdatesUrl, {credentials: 'same-origin', cache: 'no-store'});
      if (!response.ok || response.redirected) return;
      const counts = await response.json();
      document.querySelectorAll('[data-request-audience]').forEach(link => {
        const count = counts[`${link.dataset.requestAudience}_unread_count`];
        if (!Number.isInteger(count) || count < 0) return;
        const badge = link.querySelector('.request-unread-badge');
        link.classList.toggle('has-updates', count > 0);
        badge.hidden = count === 0;
        badge.textContent = String(count);
        badge.setAttribute('aria-label', `${count} solicitudes con novedades`);
      });
    } catch (_) {
      // Keep the last known count when the network is unavailable.
    } finally {
      pending = false;
    }
  }
  setInterval(refresh, 30000);
  document.addEventListener('visibilitychange', refresh);
})();
