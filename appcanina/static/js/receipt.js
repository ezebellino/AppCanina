(() => {
  const text = document.getElementById('receipt-text');
  const copy = document.getElementById('receipt-copy');
  const print = document.getElementById('receipt-print');
  const feedback = document.getElementById('receipt-feedback');
  if (!text || !copy || !print) return;
  copy.hidden = false;
  print.hidden = false;
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(text.value);
      feedback.textContent = 'Comprobante copiado. Ya podés pegarlo en WhatsApp.';
    } catch {
      document.getElementById('receipt-text-details').open = true;
      text.focus(); text.select();
      feedback.textContent = 'Seleccionamos el texto: usá Copiar para enviarlo.';
    }
  });
  print.addEventListener('click', () => window.print());
})();
