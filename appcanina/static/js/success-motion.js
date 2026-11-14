(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  document.querySelectorAll('[data-success-motion]').forEach(element => {
    if (element.dataset.motionPlayed) return;
    element.dataset.motionPlayed = 'true';
    // Only dismiss floating confirmations; visit details stay in the page.
    const toast = element.closest('.toast');
    if (toast) {
      setTimeout(() => {
        if (reduced.matches || !toast.animate) { toast.remove(); return; }
        const exit = toast.animate([{opacity: 1}, {opacity: 0}], {duration: 250, fill: 'forwards'});
        exit.onfinish = () => toast.remove();
      }, 3000);
    }
    const key = element.dataset.motionKey;
    if (key) {
      try {
        if (sessionStorage.getItem(`lazuna-motion:${key}`)) return;
        sessionStorage.setItem(`lazuna-motion:${key}`, 'seen');
      } catch { /* Server read receipts still prevent replay after reloading. */ }
    }
    if (!reduced.matches) {
      element.classList.add('motion-play');
      if (element.dataset.successMotion === 'visit') {
        element.closest('[data-visit-details]')?.classList.add('motion-reveal');
      }
    }
  });
})();
