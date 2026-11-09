(() => {
  const params = new URLSearchParams(location.hash.slice(1));
  if (!params.has('code')) return;
  const code = params.get('code').trim();
  // Do not leave the bearer code in browser history or subsequent navigation.
  history.replaceState(null, '', location.pathname + location.search);
  const status = document.getElementById('family-link-status');
  if (!/^FAM-[A-Za-z0-9_-]{1,76}$/.test(code)) {
    status.textContent = 'El enlace no contiene un código válido. Pedí una nueva invitación o pegá el código manualmente.';
    return;
  }
  const form = document.getElementById('family-link-prepare');
  form.elements.namedItem('code').value = code;
  status.textContent = 'Preparando tu invitación…';
  // Only prepare: acceptance always needs an explicit authenticated POST.
  form.requestSubmit();
})();
