from django.contrib import admin
from .models import ClinicalRecord, Contact, Patient, PatientContact


class PatientContactInline(admin.TabularInline):
    model = PatientContact
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "organization")
    search_fields = ("name", "microchip")
    inlines = [PatientContactInline]


admin.site.register(Contact)
admin.site.register(ClinicalRecord)
