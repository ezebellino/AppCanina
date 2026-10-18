from django.contrib import admin
from .models import ClinicalRecord, Contact, OwnerAccountLink, Patient, PatientContact, PatientSharingConsent, TravelCredential


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
admin.site.register(OwnerAccountLink)
admin.site.register(PatientSharingConsent)
admin.site.register(TravelCredential)
