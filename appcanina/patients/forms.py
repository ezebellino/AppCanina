from django import forms
from .models import CareReminder, ClinicalRecord, Contact, Patient, PatientContact


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ["name", "species", "breed", "birth_date", "microchip", "photo", "allergies", "notes", "active"]
        widgets = {"birth_date": forms.DateInput(attrs={"type": "date"}), "allergies": forms.Textarea(attrs={"rows": 2}), "notes": forms.Textarea(attrs={"rows": 3})}


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["full_name", "kind", "phone", "email"]


class PatientContactForm(forms.ModelForm):
    class Meta:
        model = PatientContact
        fields = ["role", "is_primary"]


class ExistingPatientContactForm(forms.Form):
    contact = forms.ModelChoiceField(label="Responsable o institución existente", queryset=Contact.objects.order_by("full_name"), empty_label="Seleccioná un contacto")
    role = forms.ChoiceField(label="Vínculo", choices=PatientContact.Role.choices)
    is_primary = forms.BooleanField(label="Es el contacto principal", required=False)


class ClinicalRecordForm(forms.ModelForm):
    class Meta:
        model = ClinicalRecord
        fields = ["occurred_on", "reason", "notes"]
        widgets = {
            "occurred_on": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class CareReminderForm(forms.ModelForm):
    class Meta:
        model = CareReminder
        fields = ["kind", "due_on", "notes"]
        labels = {"kind": "Recordatorio", "due_on": "Fecha prevista", "notes": "Detalle"}
        widgets = {"due_on": forms.DateInput(attrs={"type": "date"})}
