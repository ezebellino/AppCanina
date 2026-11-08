(() => {
  const copy = document.querySelector('[data-copy-code]');
  copy?.addEventListener('click', async () => {
    const input = document.querySelector('#family-code');
    const status = document.querySelector('[data-copy-status]');
    try { await navigator.clipboard.writeText(input.value); status.textContent = 'Código copiado.'; }
    catch { input.focus(); input.select(); status.textContent = 'Seleccionamos el código. Usá Copiar para enviarlo.'; }
  });
  const panel = document.querySelector('#credential-sharing');
  if (!panel) return;
  const status = panel.querySelector('[data-share-status]');
  const share = panel.querySelector('[data-share-file]');
  const download = panel.querySelector('[data-download-file]');
  let file, objectUrl, controller;
  const clear = () => {
    controller?.abort(); controller = null;
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = null; file = null; share.hidden = true; download.hidden = true;
    download.removeAttribute('href');
  };
  document.querySelectorAll('[data-credential-url]').forEach(button => {
    button.addEventListener('click', async () => {
      clear(); panel.hidden = false;
      panel.scrollIntoView({block: 'center'});
      status.textContent = 'Preparando tu credencial…';
      const current = new AbortController(); controller = current;
      try {
        const response = await fetch(button.dataset.credentialUrl, {credentials: 'same-origin', cache: 'no-store', signal: current.signal});
        if (!response.ok || !response.headers.get('content-type')?.includes('application/pdf')) throw new Error('pdf');
        const blob = await response.blob();
        if (controller !== current) return;
        file = new File([blob], 'credencial-animal.pdf', {type: 'application/pdf'});
        objectUrl = URL.createObjectURL(file);
        download.href = objectUrl; download.download = file.name; download.hidden = false;
        const supported = !!navigator.share && !!navigator.canShare?.({files: [file]});
        share.hidden = !supported;
        status.textContent = supported ? 'Lista. Tocá Compartir y elegí WhatsApp y el contacto.' : 'Tu navegador no permite compartir archivos directamente. Descargá el PDF y adjuntalo como documento en WhatsApp.';
      } catch (error) {
        if (controller !== current || error.name === 'AbortError') return;
        status.textContent = 'No pudimos preparar la credencial. Revisá tu conexión y volvé a intentarlo.';
      }
    });
  });
  share.addEventListener('click', async () => {
    if (!file) return;
    try { await navigator.share({files: [file], title: 'Credencial de mi animal'}); }
    catch (error) { if (error.name !== 'AbortError') status.textContent = 'No se pudo compartir. Podés descargar el PDF y adjuntarlo en WhatsApp.'; }
  });
  panel.querySelector('[data-close-share]').addEventListener('click', () => { clear(); panel.hidden = true; });
  window.addEventListener('pagehide', clear);
})();
