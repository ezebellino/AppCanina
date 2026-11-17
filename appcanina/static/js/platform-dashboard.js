(() => {
  const panel = document.getElementById('platform-summary');
  const button = document.getElementById('platform-refresh');
  const status = document.getElementById('platform-refresh-status');
  if (!panel || !button || !status) return;
  const hint = 'Actualización automática cada 60 segundos mientras el panel esté visible.';
  let pending = false;
  button.hidden = false;
  status.textContent = hint;
  async function refresh() {
    // Do not replace a link while someone is navigating the summary by keyboard.
    if (pending || document.hidden || panel.contains(document.activeElement)) return;
    pending = true;
    button.disabled = true;
    panel.setAttribute('aria-busy', 'true');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(panel.dataset.refreshUrl, {
        credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
      });
      if (response.redirected || response.status === 403) {
        status.textContent = 'La sesión venció o cambió tu acceso. Recargá la página para continuar.';
        return;
      }
      if (!response.ok) throw new Error('refresh failed');
      const parsed = new DOMParser().parseFromString(await response.text(), 'text/html');
      const summary = parsed.querySelector('[data-platform-summary]');
      if (!summary) throw new Error('invalid summary');
      if (panel.contains(document.activeElement)) return;
      panel.replaceChildren(summary);
      status.textContent = hint;
    } catch (_) {
      status.textContent = 'No pudimos actualizar. Se conservan los últimos datos; podés reintentar con Actualizar ahora.';
    } finally {
      clearTimeout(timeout);
      pending = false;
      button.disabled = false;
      panel.removeAttribute('aria-busy');
    }
  }
  button.addEventListener('click', refresh);
  setInterval(refresh, 60000);
  document.addEventListener('visibilitychange', refresh);
  window.addEventListener('pageshow', event => { if (event.persisted) refresh(); });
})();
