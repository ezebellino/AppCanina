(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  document.querySelectorAll('[data-success-motion]').forEach(element => {
    if (element.dataset.motionPlayed) return;
    element.dataset.motionPlayed = 'true';
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
