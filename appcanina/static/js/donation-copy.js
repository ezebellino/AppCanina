document.querySelectorAll('[data-copy-donation]').forEach(button => {
  button.addEventListener('click', async () => {
    const status = button.parentElement.querySelector('[data-donation-status]');
    try {
      await navigator.clipboard.writeText(button.dataset.copyDonation);
      status.textContent = 'Alias copiado. Ya podés pegarlo en tu banco o billetera.';
    } catch {
      status.textContent = 'No pudimos copiarlo. Mantené presionado o seleccioná el alias para copiarlo manualmente.';
    }
  });
});
