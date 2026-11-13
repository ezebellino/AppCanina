(() => {
  const data = document.getElementById('linked-animal-data');
  const select = document.getElementById('id_patient');
  if (!data || !select) return;
  const animals = JSON.parse(data.textContent);
  const photo = document.getElementById('id_photo');
  const preview = document.getElementById('animal-photo-preview');
  const help = document.getElementById('animal-photo-help');
  const clear = document.getElementById('photo-clear_id');
  function updatePhoto() {
    const animal = animals[select.value];
    const uploaded = photo.files && photo.files.length;
    const usePhoto = animal && animal.photo && !uploaded && !(clear && clear.checked);
    preview.hidden = !usePhoto;
    if (usePhoto) preview.src = animal.photo;
    else preview.removeAttribute('src');
    help.textContent = uploaded ? 'Se usará la foto que subiste.' :
      usePhoto ? 'Si no subís otra, se usará la foto de su ficha al crear el aviso. Al editar, se conserva la foto actual del aviso salvo que cambies de animal.' :
      animal ? 'Podés subir una foto para ayudar a reconocerlo.' : '';
  }
  select.addEventListener('change', () => {
    const animal = animals[select.value];
    for (const name of ['name', 'species', 'breed']) {
      document.getElementById('id_' + name).value = animal ? animal[name] : '';
    }
    updatePhoto();
  });
  photo.addEventListener('change', updatePhoto);
  if (clear) clear.addEventListener('change', updatePhoto);
  // Keep entered values on validation errors and existing report edits.
  updatePhoto();
})();
