(() => {
  let busy = false;
  async function flyToArchive(card, trigger) {
    if (!card?.animate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const bounds = trigger.getBoundingClientRect();
    const envelope = document.createElement('div');
    envelope.className = 'archive-envelope';
    envelope.setAttribute('aria-hidden', 'true');
    const tray = document.createElement('div');
    tray.className = 'archive-tray';
    tray.setAttribute('aria-hidden', 'true');
    tray.textContent = 'Archivadas';
    const startX = Math.max(60, Math.min(window.innerWidth - 60, bounds.left + bounds.width / 2));
    const startY = Math.max(60, Math.min(window.innerHeight - 100, bounds.top));
    envelope.style.left = `${startX - 40}px`;
    envelope.style.top = `${startY - 28}px`;
    document.body.append(tray, envelope);
    try {
      const target = tray.getBoundingClientRect();
      const dx = target.left + target.width / 2 - startX;
      const dy = target.top - startY;
      const folding = card.animate([
        {opacity: 1, transform: 'perspective(900px) rotateX(0deg) scale(1)'},
        {opacity: 0.5, transform: 'perspective(900px) rotateX(55deg) scale(.65, .4)'},
        {opacity: 0, transform: 'perspective(900px) rotateX(80deg) scale(.25, .1)'},
      ], {duration: 360, easing: 'ease-in', fill: 'forwards'});
      const flying = envelope.animate([
        {opacity: 0, transform: 'scale(.35) rotate(-8deg)', offset: 0},
        {opacity: 1, transform: 'scale(1) rotate(-8deg)', offset: .3},
        {opacity: 1, transform: `translate(${dx * .55}px, ${dy * .4 - 35}px) scale(.85) rotate(8deg)`, offset: .65},
        {opacity: 0, transform: `translate(${dx}px, ${dy + 12}px) scale(.15) rotate(0deg)`, offset: 1},
      ], {duration: 850, easing: 'ease-in-out', fill: 'forwards'});
      await Promise.all([folding.finished, flying.finished]);
      await tray.animate([{transform: 'scale(1)'}, {transform: 'scale(1.08)'}, {transform: 'scale(1)'}], {duration: 180}).finished;
    } catch {
      // A cancelled animation must never undo or block a confirmed archive.
    } finally {
      envelope.remove(); tray.remove();
    }
  }
  document.querySelectorAll('[data-archive-form]').forEach(form => {
    form.addEventListener('submit', async event => {
      if (!window.fetch || !event.submitter) return;
      event.preventDefault();
      if (busy) return;
      busy = true;
      const button = event.submitter;
      const status = form.parentElement.querySelector('[data-archive-status]');
      const payload = new FormData(form);
      payload.set('action', button.value);
      button.disabled = true;
      form.setAttribute('aria-busy', 'true');
      status.textContent = button.value === 'archive' ? 'Guardando en Archivadas…' : 'Restaurando solicitud…';
      try {
        const response = await fetch(form.action, {method: 'POST', body: payload, credentials: 'same-origin', headers: {Accept: 'application/json'}});
        const data = await response.json();
        if (!response.ok) throw Error(data.detail || 'No pudimos guardar el cambio. Actualizá la bandeja.');
        const target = new URL(data.redirect_url, location.href);
        if (target.origin !== location.origin) throw Error('Actualizá la bandeja para comprobar el resultado.');
        status.textContent = data.detail;
        if (button.value === 'archive') await flyToArchive(form.closest('article'), button);
        window.location.assign(target.href);
      } catch (error) {
        status.textContent = error.message || 'Revisá tu conexión y actualizá la bandeja para comprobar si se guardó.';
        button.disabled = false;
        busy = false;
        form.removeAttribute('aria-busy');
      }
    });
  });
})();
