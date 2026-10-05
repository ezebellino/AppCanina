from django import forms
from .models import GroomingAppointment, GroomingService


class GroomingServiceForm(forms.ModelForm):
    class Meta:
        model = GroomingService
        fields = ["name", "duration_minutes", "price", "active"]
        labels = {"name": "Nombre del servicio", "duration_minutes": "Duración en minutos", "price": "Precio sugerido", "active": "Disponible para nuevos turnos"}


class GroomingAppointmentForm(forms.ModelForm):
    additional_services = forms.ModelMultipleChoiceField(label="Servicios adicionales", queryset=GroomingService.objects.filter(active=True), required=False, help_text="Por ejemplo: corte de uñas, limpieza de oídos o cepillado.")
    class Meta:
        model = GroomingAppointment
        fields = ["patient", "service", "assigned_to", "starts_at", "status", "notes"]
        widgets = {"starts_at": forms.DateTimeInput(attrs={"type":"datetime-local"}), "notes": forms.Textarea(attrs={"rows":3})}
        labels = {"patient": "Paciente", "service": "Servicio", "assigned_to": "Profesional asignado", "starts_at": "Fecha y hora", "status": "Estado", "notes": "Notas"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["additional_services"].initial = self.instance.additional_services.all()

    def clean_additional_services(self):
        services = self.cleaned_data["additional_services"]
        if self.cleaned_data.get("service") in services:
            raise forms.ValidationError("El servicio principal no debe repetirse como adicional.")
        return services

    def save(self, commit=True):
        appointment = super().save(commit=commit)
        if commit:
            appointment.additional_services.set(self.cleaned_data["additional_services"])
            appointment.update_end_time_from_services()
        return appointment
