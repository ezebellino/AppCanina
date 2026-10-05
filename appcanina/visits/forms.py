from django import forms

from patients.models import Contact, Patient, PatientContact

from .models import HomeVisit


class HomeVisitForm(forms.ModelForm):
    patient = forms.ModelChoiceField(label="Paciente existente", queryset=Patient.objects.filter(active=True), required=False, empty_label="Seleccionar paciente")
    new_patient_name = forms.CharField(label="Nombre del paciente nuevo", max_length=100, required=False)
    new_patient_species = forms.ChoiceField(label="Especie", choices=[("", "Seleccionar especie"), *Patient.Species.choices], required=False)
    new_contact_name = forms.CharField(label="Responsable del paciente nuevo", max_length=160, required=False)
    new_contact_phone = forms.CharField(label="Teléfono", max_length=40, required=False)

    class Meta:
        model = HomeVisit
        fields = ["patient", "assigned_to", "scheduled_for", "visit_type", "status", "address", "zone", "reason", "notes", "price"]
        widgets = {"scheduled_for": forms.DateTimeInput(attrs={"type": "datetime-local"}), "notes": forms.Textarea(attrs={"rows": 3})}
        labels = {"assigned_to": "Profesional asignado", "scheduled_for": "Fecha y hora", "visit_type": "Tipo de visita", "status": "Estado", "address": "Dirección", "zone": "Zona o barrio", "reason": "Motivo", "notes": "Observaciones", "price": "Valor sugerido"}

    def clean(self):
        cleaned = super().clean()
        patient = cleaned.get("patient")
        new_name = (cleaned.get("new_patient_name") or "").strip()
        if patient and new_name:
            self.add_error("new_patient_name", "Elegí un paciente existente o cargá uno nuevo, no ambos.")
        elif not patient and not new_name:
            self.add_error("patient", "Elegí un paciente existente o cargá los datos del paciente nuevo.")
        elif new_name:
            if not cleaned.get("new_patient_species"):
                self.add_error("new_patient_species", "Indicá la especie.")
            if not (cleaned.get("new_contact_name") or "").strip():
                self.add_error("new_contact_name", "Indicá un responsable para la nueva ficha.")
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_patient_name"].widget.attrs["placeholder"] = "Nombre de la mascota"
        self.fields["new_contact_name"].widget.attrs["placeholder"] = "Nombre del responsable"
        self.fields["new_contact_phone"].widget.attrs["placeholder"] = "Teléfono"

    def create_patient_if_needed(self):
        patient = self.cleaned_data.get("patient")
        if patient:
            return patient
        patient = Patient.objects.create(name=self.cleaned_data["new_patient_name"].strip(), species=self.cleaned_data["new_patient_species"], notes="Ficha creada desde una visita a domicilio.")
        contact = Contact.objects.create(full_name=self.cleaned_data["new_contact_name"].strip(), phone=self.cleaned_data.get("new_contact_phone", "").strip())
        PatientContact.objects.create(patient=patient, contact=contact, role=PatientContact.Role.RESPONSIBLE, is_primary=True)
        return patient
