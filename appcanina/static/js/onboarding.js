(() => {
  const startButtons = document.querySelectorAll('[data-onboarding-start]');
  if (!startButtons.length || !window.driver?.js?.driver) return;

  const dashboardSteps = [
    {element: '#onboarding-welcome', popover: {title: 'Este es tu punto de partida', description: 'Inicio concentra los datos importantes del día. Podés volver acá cuando necesites ubicarte rápido.', side: 'bottom', align: 'start'}},
    {element: '#onboarding-metrics', popover: {title: 'Números útiles', description: 'Cada tarjeta te lleva al detalle: pacientes, agenda, ventas o alertas que requieren atención.', side: 'bottom', align: 'start'}},
    {element: '#onboarding-workspaces', popover: {title: 'Tres áreas para trabajar', description: 'Atención animal reúne fichas, consultas y cuidados. Peluquería canina organiza turnos de estética. Comercio concentra inventario, ventas y caja.', side: 'top', align: 'center'}},
    {element: '.sidebar-nav', popover: {title: 'Navegación siempre disponible', description: 'Usá el menú lateral para cambiar de área sin perder el contexto. Las opciones visibles dependen de tu permiso.', side: 'right', align: 'start'}},
    {element: '[data-onboarding-start="dashboard"]', popover: {title: 'Podés repetir esta guía', description: 'No se abre sola para no interrumpir el trabajo. Este botón la inicia nuevamente cuando la necesites.', side: 'bottom', align: 'end'}},
  ];
  const patientFormSteps = [
    {element: '#onboarding-patient-section', popover: {title: 'Primero, la mascota', description: 'Completá nombre y especie para crear la ficha. Raza, fecha de nacimiento, chip y foto pueden agregarse ahora o después.', side: 'right', align: 'start'}},
    {element: '#id_patient-name', popover: {title: 'Nombre del paciente', description: 'Es el dato principal para encontrar la ficha rápidamente desde búsqueda, turnos y ventas.', side: 'bottom', align: 'start'}},
    {element: '#id_patient-species', popover: {title: 'Especie', description: 'Indicá si es perro, gato u otra especie para organizar correctamente la atención.', side: 'bottom', align: 'start'}},
    {element: '#onboarding-contact-section', popover: {title: 'Responsable o institución', description: 'Asociá a la persona responsable o a la organización. Luego se podrán vincular más pacientes con ese mismo contacto.', side: 'left', align: 'start'}},
    {element: '.form-actions', popover: {title: 'Guardá la ficha', description: 'Al guardar, la mascota queda disponible para turnos, historial clínico, recordatorios y ventas asociadas.', side: 'top', align: 'end'}},
  ];
  const saleSteps = [
    {element: '#onboarding-sale-heading', popover: {title: 'Un cobro para todo', description: 'En una misma venta podés combinar alimentos, medicamentos, accesorios y servicios.', side: 'bottom', align: 'start'}},
    {element: '#onboarding-sale-finder', popover: {title: 'Buscá antes de seleccionar', description: 'Escribí nombre, marca o código interno. Si hace falta, filtrá por categoría para encontrar el producto más rápido.', side: 'bottom', align: 'start'}},
    {element: '#onboarding-sale-product-form', popover: {title: 'Sumá productos', description: 'Elegí el producto y luego indicá gramos si se vende por kilo, o cantidad para unidades y bolsas.', side: 'right', align: 'start'}},
    {element: '#onboarding-sale-service-form', popover: {title: 'Servicios de peluquería', description: 'Sumá baño, corte de uñas u otros servicios de estética. Las consultas se cobran desde la ficha del paciente, dentro de Atención animal.', side: 'right', align: 'start'}},
    {element: '#onboarding-sale-cart', popover: {title: 'Revisá y confirmá', description: 'El carrito calcula el total. Al agregar un ítem aparecen paciente, medio de cobro y Confirmar venta. Para efectivo, primero necesitás abrir caja.', side: 'left', align: 'start'}},
  ];
  const cashOpenSteps = [
    {element: '#onboarding-cash-open-heading', popover: {title: 'Empezá por abrir caja', description: 'Abrí una caja cada día que cobres en efectivo. Así el sistema puede calcular el saldo esperado al cierre.', side: 'bottom', align: 'start'}},
    {element: '#id_opening_amount', popover: {title: 'Monto inicial', description: 'Ingresá el efectivo real con el que comienza el día. Si no hay efectivo, podés usar $0 y el sistema te pedirá confirmación.', side: 'bottom', align: 'start'}},
    {element: '#cash-open-form', popover: {title: 'Confirmá la apertura', description: 'Al abrirla, las ventas en efectivo y los movimientos manuales quedan asociados a esta jornada.', side: 'top', align: 'end'}},
    {element: '[data-onboarding-start="cash-open"]', popover: {title: 'Guía siempre disponible', description: 'Podés repetirla cuando una persona nueva necesite conocer el proceso.', side: 'bottom', align: 'end'}},
  ];
  const cashDashboardSteps = [
    {element: '#onboarding-cash-heading', popover: {title: 'Caja abierta', description: 'Desde acá se controla la jornada actual. El efectivo esperado se actualiza con cada venta y movimiento.', side: 'bottom', align: 'start'}},
    {element: '#onboarding-cash-summary', popover: {title: 'Efectivo esperado', description: 'Es el monto que debería haber físicamente: inicial más ventas en efectivo e ingresos, menos retiros.', side: 'bottom', align: 'start'}},
    {element: '#onboarding-cash-movement', popover: {title: 'Movimientos manuales', description: 'Registrá ingresos o retiros que no sean una venta, siempre indicando el motivo.', side: 'right', align: 'start'}},
    {element: '#onboarding-cash-close', popover: {title: 'Arqueo y cierre', description: 'Contá sólo el efectivo real. La diferencia se calcula en vivo antes de cerrar la caja.', side: 'left', align: 'start'}},
    {element: '[data-onboarding-start="cash-dashboard"]', popover: {title: 'Repetí la guía cuando quieras', description: 'No se muestra sola para que el cierre del día sea ágil.', side: 'bottom', align: 'end'}},
  ];

  const startTour = (type) => {
    const steps = type === 'patient-form' ? patientFormSteps : type === 'sale' ? saleSteps : type === 'cash-open' ? cashOpenSteps : type === 'cash-dashboard' ? cashDashboardSteps : dashboardSteps;
    const tour = window.driver.js.driver({
      animate: true,
      allowClose: true,
      overlayColor: '#00352c',
      overlayOpacity: 0.55,
      showProgress: true,
      popoverClass: 'driverjs-theme',
      progressText: '{{current}} de {{total}}',
      nextBtnText: 'Siguiente',
      prevBtnText: 'Anterior',
      doneBtnText: 'Listo',
      steps,
    });
    tour.drive();
  };

  startButtons.forEach((button) => button.addEventListener('click', () => startTour(button.dataset.onboardingStart)));
})();
