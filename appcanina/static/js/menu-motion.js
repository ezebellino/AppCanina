(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  document.querySelectorAll('details.mobile-navigation, details.account-menu').forEach(menu => {
    const summary = menu.querySelector('summary');
    const panel = summary?.nextElementSibling;
    if (!panel) return;
    let animation, desired = menu.open, sequence = 0;
    function change(open, focus = false) {
      desired = open;
      const current = ++sequence;
      animation?.cancel();
      summary.setAttribute('aria-expanded', String(open));
      panel.inert = !open;
      if (focus) summary.focus();
      if (open) menu.open = true;
      if (reduced.matches || !panel.animate || !menu.open) {
        menu.open = open;
        panel.inert = false;
        return;
      }
      animation = panel.animate([
        {opacity: open ? 0 : 1, transform: `translateY(${open ? '-10px' : '0'})`},
        {opacity: open ? 1 : 0, transform: `translateY(${open ? '0' : '-10px'})`},
      ], {duration: open ? 210 : 160, easing: 'ease-out'});
      animation.onfinish = () => {
        if (current !== sequence) return;
        menu.open = open;
        panel.inert = false;
      };
    }
    summary.setAttribute('aria-expanded', String(menu.open));
    summary.addEventListener('click', event => {event.preventDefault(); change(!desired);});
    menu.addEventListener('navigation-close', () => change(false));
    menu.dataset.motionMenu = 'true';
    document.addEventListener('click', event => {if (desired && !menu.contains(event.target)) change(false);});
    document.addEventListener('keydown', event => {if (event.key === 'Escape' && desired) change(false, true);});
    reduced.addEventListener('change', () => {if (reduced.matches) change(desired);});
  });
})();
